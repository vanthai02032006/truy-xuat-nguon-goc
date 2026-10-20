from __future__ import annotations

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.core.security import create_access_token
from app.models.batch import Batch
from app.models.chain_event import ChainEvent
from app.models.user import User
from app.services.database_seeder import run_full_database_seed, seed_database_if_empty


def get_auth_headers(email: str, role: str, org_id: int | None = None) -> dict[str, str]:
    token = create_access_token(subject=email, role=role, organization_id=org_id)
    return {"Authorization": f"Bearer {token}"}



class TestP0SecurityAndDataSafety:
    """Bộ kiểm thử xác thực các tiêu chuẩn an toàn P0 và chống mất dữ liệu."""

    # 1. Người chưa đăng nhập không thể lấy token quản trị
    def test_unauthenticated_cannot_get_admin_token(self, client: TestClient):
        """Người dùng chưa đăng nhập gọi /quick-role-token phải bị từ chối 401 hoặc 403."""
        # Gọi không có token xác thực
        res_admin = client.post("/api/v1/auth/quick-role-token?role=system_admin")
        assert res_admin.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

        res_farm = client.post("/api/v1/auth/quick-role-token?role=farm")
        assert res_farm.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    # 2. Staging / Production không mở endpoint chuyển vai trò demo
    def test_staging_and_production_block_demo_role_switch(
        self, client: TestClient, db_session: Session, monkeypatch
    ):
        """Môi trường staging và production luôn trả về 403 Forbidden cho /quick-role-token."""
        from app.api.v1.auth import ensure_supply_chain_demo_users

        ensure_supply_chain_demo_users(db_session)
        farm_user = db_session.query(User).filter(User.email == "manager@nongtraixanh.vn").first()
        farm_headers = get_auth_headers(
            farm_user.email, farm_user.role, farm_user.organization_id
        )

        for env_name in ["staging", "production"]:
            monkeypatch.setattr(settings, "APP_ENV", env_name)
            monkeypatch.setattr(settings, "ENABLE_DEMO_ROLE_SWITCH", True)

            res = client.post(
                "/api/v1/auth/quick-role-token?role=coop", headers=farm_headers
            )
            assert (
                res.status_code == status.HTTP_403_FORBIDDEN
            ), f"Môi trường {env_name} không được phép mở demo role switch"
            assert "vô hiệu hóa" in res.json()["detail"].lower()

    # 3. Kể cả ở development, không được phép cấp quyền quản trị qua demo endpoint
    def test_demo_endpoint_cannot_grant_system_admin(
        self, client: TestClient, db_session: Session, monkeypatch
    ):
        """Kể cả khi bật cờ demo ở development, endpoint không được cấp quyền system_admin."""
        from app.api.v1.auth import ensure_supply_chain_demo_users

        ensure_supply_chain_demo_users(db_session)
        farm_user = db_session.query(User).filter(User.email == "manager@nongtraixanh.vn").first()
        farm_headers = get_auth_headers(
            farm_user.email, farm_user.role, farm_user.organization_id
        )

        monkeypatch.setattr(settings, "APP_ENV", "development")
        monkeypatch.setattr(settings, "ENABLE_DEMO_ROLE_SWITCH", True)

        for admin_role in ["system_admin", "admin", "quan_tri"]:
            res = client.post(
                f"/api/v1/auth/quick-role-token?role={admin_role}", headers=farm_headers
            )
            assert (
                res.status_code == status.HTTP_403_FORBIDDEN
            ), f"Không được phép cấp quyền quản trị {admin_role} qua demo"


    # 4. Đăng nhập sai vẫn giữ cơ chế khóa 15 phút sau 5 lần sai liên tiếp
    def test_lockout_mechanism_after_5_failed_attempts(
        self, client: TestClient, db_session: Session
    ):
        """Nhập sai mật khẩu 5 lần -> khóa 15 phút. Lần thứ 6 kể cả nhập đúng vẫn bị từ chối 423."""
        # Reset trạng thái user farm trước
        from app.api.v1.auth import ensure_supply_chain_demo_users

        ensure_supply_chain_demo_users(db_session)
        user = (
            db_session.query(User)
            .filter(User.email == "manager@nongtraixanh.vn")
            .first()
        )
        assert user is not None
        user.failed_attempts = 0
        user.locked_until = None
        db_session.commit()

        # 4 lần sai đầu: 401 Unauthorized
        for attempt in range(1, 5):
            res = client.post(
                "/api/v1/auth/login",
                json={"email": user.email, "password": "wrongpassword"},
            )
            assert res.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Email hoặc mật khẩu không chính xác" in res.json()["detail"]

        # Lần thứ 5 sai: Bị khóa 15 phút (HTTP 423 Locked)
        res_5 = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "wrongpassword"},
        )
        assert res_5.status_code == status.HTTP_423_LOCKED
        assert "tạm khóa" in res_5.json()["detail"].lower()

        # Lần thứ 6: KỂ CẢ NHẬP ĐÚNG MẬT KHẨU ("pass123") -> Vẫn bị từ chối 423 Locked
        res_6_correct = client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "pass123"}
        )
        assert res_6_correct.status_code == status.HTTP_423_LOCKED
        assert "khóa tạm thời" in res_6_correct.json()["detail"].lower()

        # Dọn dẹp mở khóa sau test
        user.failed_attempts = 0
        user.locked_until = None
        db_session.commit()

    # 5. Cookie có HttpOnly, Secure và phiên hợp lệ được kiểm tra đúng qua /auth/me
    def test_login_cookie_httponly_and_me_session_validation(
        self, client: TestClient, db_session: Session, monkeypatch
    ):
        """Đăng nhập thành công trả về cookie access_token có HttpOnly; /auth/me xác thực cookie hợp lệ; logout xóa cookie."""
        from app.api.v1.auth import ensure_supply_chain_demo_users

        ensure_supply_chain_demo_users(db_session)

        # Giả lập môi trường production để kiểm tra cờ Secure
        monkeypatch.setattr(settings, "APP_ENV", "production")
        monkeypatch.setattr(settings, "COOKIE_SECURE", True)

        res_login = client.post(
            "/api/v1/auth/login",
            json={"email": "manager@nongtraixanh.vn", "password": "pass123"},
        )
        assert res_login.status_code == status.HTTP_200_OK
        data = res_login.json()
        assert "access_token" in data
        assert data["role"] == "farm"

        # Kiểm tra cookie trong header Set-Cookie
        cookies = res_login.headers.get_list("set-cookie")
        cookie_header = "; ".join(cookies)
        assert "access_token=" in cookie_header
        assert "HttpOnly" in cookie_header or "httponly" in cookie_header.lower()
        assert "Secure" in cookie_header or "secure" in cookie_header.lower()

        # Gọi /api/v1/auth/me với cookie phiên
        client.cookies.set("access_token", data["access_token"])
        res_me = client.get("/api/v1/auth/me")
        assert res_me.status_code == status.HTTP_200_OK
        user_info = res_me.json()
        assert user_info["email"] == "manager@nongtraixanh.vn"
        assert user_info["role"] == "farm"

        # Gọi đăng xuất /api/v1/auth/logout -> Xóa cookie
        res_logout = client.post("/api/v1/auth/logout")
        assert res_logout.status_code == status.HTTP_200_OK
        logout_cookies = res_logout.headers.get_list("set-cookie")
        logout_header = "; ".join(logout_cookies)
        # Cookie bị xóa thường có max-age=0 hoặc expires trong quá khứ
        assert "access_token=" in logout_header

    # 6. Thiếu biến môi trường bắt buộc làm ứng dụng dừng với thông báo rõ ràng
    def test_missing_required_environment_variables_halt_safely(self, monkeypatch):
        """Kiểm tra Settings.validate_required_env dừng khởi động nếu thiếu biến bắt buộc."""
        # 1. Thiếu SECRET_KEY
        s_no_secret = Settings(
            APP_ENV="production",
            SECRET_KEY="",
            POSTGRES_PASSWORD="strong_password_123",
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
        )
        monkeypatch.setattr(Settings, "IS_TEST", property(lambda self: False))
        with pytest.raises(RuntimeError) as exc_info:
            s_no_secret.validate_required_env()
        assert "SECRET_KEY" in str(exc_info.value)

        # 2. SECRET_KEY dùng chuỗi mặc định không an toàn trong production
        s_insecure_secret = Settings(
            APP_ENV="production",
            SECRET_KEY="truyxuatnguongoc-super-secret-key-s05-2026",
            POSTGRES_PASSWORD="strong_password_123",
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
        )
        with pytest.raises(RuntimeError) as exc_info2:
            s_insecure_secret.validate_required_env()
        assert "SECRET_KEY" in str(exc_info2.value)

        # 3. Thiếu mật khẩu database
        s_no_db_pass = Settings(
            APP_ENV="production",
            SECRET_KEY="a_very_secure_random_key_with_more_than_32_characters",
            POSTGRES_PASSWORD="",
            DATABASE_URL="",
        )
        with pytest.raises(RuntimeError) as exc_info3:
            s_no_db_pass.validate_required_env()
        assert "POSTGRES_PASSWORD" in str(exc_info3.value)

        # 4. Chứa wildcard trong CORS ở production
        s_wildcard_cors = Settings(
            APP_ENV="production",
            SECRET_KEY="a_very_secure_random_key_with_more_than_32_characters",
            POSTGRES_PASSWORD="strong_password_123",
            DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/db",
            ALLOWED_HOSTS=["localhost", "*"],
            CORS_ORIGINS=["https://example.com", "*"],
        )
        with pytest.raises(RuntimeError) as exc_info4:
            s_wildcard_cors.validate_required_env()
        assert "wildcard" in str(exc_info4.value).lower()

    # 7. Restart ứng dụng không xóa lô hàng hay lịch sử sự kiện & Chạy seed 2 lần không nhân đôi dữ liệu
    def test_seed_idempotency_and_no_data_loss_on_restart(
        self, db_session: Session, client: TestClient, monkeypatch
    ):
        """
        Chứng minh:
        1. Chạy seed 2 lần không nhân đôi dữ liệu (idempotent).
        2. Không xóa dữ liệu lô hàng hay sự kiện đã có.
        3. Force reset bị cấm trên production/staging.
        """
        # Nạp dữ liệu lần 1
        res1 = run_full_database_seed(db_session, force_reset=True)
        assert res1["status"] == "success"
        initial_batches_count = db_session.query(Batch).count()
        initial_events_count = db_session.query(ChainEvent).count()
        assert initial_batches_count >= 12
        assert initial_events_count > 0

        # Lấy danh sách ID lô hàng ban đầu
        initial_ids = {b.id for b in db_session.query(Batch).all()}

        # Chạy seed lần 2 với force_reset=False (mặc định)
        res2 = run_full_database_seed(db_session, force_reset=False)
        assert res2["status"] == "skipped"
        assert "idempotent" in res2["message"].lower()

        # Kiểm tra số lượng lô hàng và sự kiện giữ nguyên 100%, không bị nhân đôi
        after_batches_count = db_session.query(Batch).count()
        after_events_count = db_session.query(ChainEvent).count()
        assert after_batches_count == initial_batches_count
        assert after_events_count == initial_events_count

        after_ids = {b.id for b in db_session.query(Batch).all()}
        assert (
            after_ids == initial_ids
        ), "ID các lô hàng phải giữ nguyên vẹn, không bị xóa hay thay đổi"

        # Kiểm tra seed_database_if_empty (giả lập restart ứng dụng)
        res_empty = seed_database_if_empty(db_session)
        assert res_empty["status"] == "skipped"
        assert db_session.query(Batch).count() == initial_batches_count

        # Kiểm tra chặn force_reset trên production / staging
        for prod_env in ["production", "staging"]:
            monkeypatch.setattr(settings, "APP_ENV", prod_env)
            with pytest.raises(RuntimeError) as exc_info:
                run_full_database_seed(db_session, force_reset=True)
            assert "NGĂN CHẶN MẤT DỮ LIỆU" in str(exc_info.value)
