from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User, UserRole
from fastapi import status
from fastapi.testclient import TestClient


class TestUserAuthenticationAndLockoutS04:
    """
    Bộ kiểm thử tiêu chuẩn User Story S-04 và Tasks T-08, T-09, T-10:
    1. Đăng nhập thật bằng Email & Mật khẩu với băm argon2id và Cookie HttpOnly, Secure.
    2. Cùng một câu thông báo lỗi duy nhất khi sai email hoặc sai mật khẩu.
    3. Đếm số lần sai, khóa tạm 15 phút sau 5 lần sai liên tiếp.
    4. Lần thứ 6 (chưa hết 15 phút): KỂ CẢ NHẬP ĐÚNG MẬT KHẨU vẫn từ chối và báo số phút còn lại.
    5. Đăng nhập thành công sau 15 phút -> reset failed_attempts = 0.
    6. Các endpoint hỗ trợ giả lập và kiểm tra nhanh trạng thái khóa.
    """

    def _setup_test_user(self, db_session) -> tuple[User, str]:
        password = "SecretPassword123@"
        org = Organization(name="HTX Nông Sản Kiểm Thử S-04", code="TEST-S04")
        db_session.add(org)
        db_session.flush()

        # Tạo user với mật khẩu băm bằng argon2id
        hashed = get_password_hash(password)
        assert hashed.startswith("$argon2id$"), "Mật khẩu phải được băm bằng argon2id (NFR S-04)"

        user = User(
            email="farmer.s04@nongtraixanh.vn",
            hashed_password=hashed,
            full_name="Nguyễn Văn Test S-04",
            role=UserRole.FARM.value,
            organization_id=org.id,
            is_active=True,
            failed_attempts=0,
            locked_until=None,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user, password

    def test_login_success_argon2id_and_secure_cookie(self, client: TestClient, db_session):
        """1. Đăng nhập thành công với argon2id, trả về JWT và cookie HttpOnly Secure."""
        user, password = self._setup_test_user(db_session)

        response = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": password},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["user_email"] == user.email
        assert data["role"] == UserRole.FARM.value

        # Kiểm tra cờ HttpOnly và Secure trên Cookie phiên
        set_cookie_header = response.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie_header
        assert "HttpOnly" in set_cookie_header or "httponly" in set_cookie_header
        assert "Secure" in set_cookie_header or "secure" in set_cookie_header

        # Đảm bảo failed_attempts = 0 trong DB
        db_session.refresh(user)
        assert user.failed_attempts == 0
        assert user.locked_until is None

    def test_login_wrong_email_returns_generic_error(self, client: TestClient, db_session):
        """2. Sai email trả về CÙNG MỘT câu thông báo lỗi duy nhất, không tiết lộ email có tồn tại hay không."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent.email@example.com", "password": "randomPassword999"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Email hoặc mật khẩu không chính xác."

    def test_login_wrong_password_returns_same_generic_error(self, client: TestClient, db_session):
        """3. Sai mật khẩu trả về CÙNG MỘT câu thông báo lỗi duy nhất và tăng bộ đếm failed_attempts."""
        user, _ = self._setup_test_user(db_session)

        response = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "WrongPassword_Attempt_1"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Email hoặc mật khẩu không chính xác."
        assert response.headers.get("X-Failed-Attempts") == "1"

        db_session.refresh(user)
        assert user.failed_attempts == 1

    def test_lockout_after_5_consecutive_failed_attempts(self, client: TestClient, db_session):
        """4. Nhập sai 5 lần liên tiếp sẽ khóa tài khoản trong 15 phút."""
        user, _ = self._setup_test_user(db_session)

        for attempt in range(1, 5):
            res = client.post(
                "/api/v1/auth/login",
                json={"email": user.email, "password": f"Wrong_{attempt}"},
            )
            assert res.status_code == status.HTTP_401_UNAUTHORIZED
            assert res.json()["detail"] == "Email hoặc mật khẩu không chính xác."
            assert res.headers.get("X-Failed-Attempts") == str(attempt)

        # Lần sai thứ 5 -> Bị khóa 15 phút (HTTP 423 Locked)
        res_5 = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "Wrong_Attempt_5"},
        )
        assert res_5.status_code == status.HTTP_423_LOCKED
        assert "15 phút" in res_5.json()["detail"]
        assert "5 lần" in res_5.json()["detail"]

        db_session.refresh(user)
        assert user.failed_attempts == 5
        assert user.locked_until is not None
        locked_dt = user.locked_until if user.locked_until.tzinfo else user.locked_until.replace(tzinfo=UTC)
        assert locked_dt > datetime.now(UTC)

    def test_attempt_6_with_correct_password_still_rejected_while_locked(self, client: TestClient, db_session):
        """5. Ở lần thử thứ 6, KỂ CẢ KHI NHẬP ĐÚNG MẬT KHẨU vẫn từ chối và báo số phút còn lại."""
        user, password = self._setup_test_user(db_session)

        # Khóa tài khoản bằng cách giả lập sai 5 lần
        user.failed_attempts = 5
        user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
        db_session.commit()

        # Thử đăng nhập bằng MẬT KHẨU ĐÚNG 100%
        res = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": password},
        )
        assert res.status_code == status.HTTP_423_LOCKED
        assert "tài khoản đang bị khóa tạm thời" in res.json()["detail"].lower()
        assert "phút" in res.json()["detail"]

    def test_unlock_after_lockout_expires_resets_counter(self, client: TestClient, db_session):
        """6. Sau khi hết 15 phút, đăng nhập đúng mật khẩu sẽ mở khóa và reset failed_attempts = 0."""
        user, password = self._setup_test_user(db_session)

        # Giả lập thời gian khóa đã trôi qua (hết hạn 15 phút)
        user.failed_attempts = 5
        user.locked_until = datetime.now(UTC) - timedelta(minutes=1)
        db_session.commit()

        # Đăng nhập lại với mật khẩu đúng
        res = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": password},
        )
        assert res.status_code == status.HTTP_200_OK

        db_session.refresh(user)
        assert user.failed_attempts == 0
        assert user.locked_until is None

    def test_simulate_lockout_and_reset_tools(self, client: TestClient, db_session):
        """7. Test endpoints hỗ trợ giảng viên kiểm tra nhanh: Giả lập sai 5 lần và Mở khóa nhanh."""
        user, _ = self._setup_test_user(db_session)

        # 1. Gọi API Giả lập sai 5 lần
        res_sim = client.post(
            "/api/v1/auth/simulate-lockout",
            json={"email": user.email},
        )
        assert res_sim.status_code == status.HTTP_200_OK
        assert res_sim.json()["status"] == "success"
        assert res_sim.json()["failed_attempts"] == 5

        # 2. Kiểm tra status API
        res_status = client.get(
            f"/api/v1/auth/lockout-status?email={user.email}",
        )
        assert res_status.status_code == status.HTTP_200_OK
        status_data = res_status.json()
        assert status_data["is_locked"] is True
        assert status_data["failed_attempts"] == 5
        assert status_data["remaining_minutes"] is not None

        # 3. Gọi API Mở khóa nhanh
        res_reset = client.post(
            "/api/v1/auth/reset-lockout",
            json={"email": user.email},
        )
        assert res_reset.status_code == status.HTTP_200_OK
        assert res_reset.json()["status"] == "success"
        assert res_reset.json()["is_locked"] is False

        # Kiểm tra lại status API sau khi mở khóa
        res_status_after = client.get(
            f"/api/v1/auth/lockout-status?email={user.email}",
        )
        assert res_status_after.json()["is_locked"] is False
        assert res_status_after.json()["failed_attempts"] == 0

    def test_inactive_user_cannot_login(self, client: TestClient, db_session):
        """8. Tài khoản bị vô hiệu hóa bởi quản trị viên không thể đăng nhập."""
        user, password = self._setup_test_user(db_session)
        user.is_active = False
        db_session.commit()

        res = client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": password},
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN
        assert "vô hiệu hóa" in res.json()["detail"].lower()
