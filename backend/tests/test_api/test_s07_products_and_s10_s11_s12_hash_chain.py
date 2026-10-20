from __future__ import annotations

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models.batch import Batch
from app.models.chain_event import ReadOnlyChainEventError
from app.models.organization import Organization
from app.models.product import Product
from app.models.user import User, UserRole
from app.services.hash_chain_service import (
    GENESIS_HASH,
    calculate_event_hash,
    canonicalize_event_data,
    record_chain_event,
)


def get_auth_headers(email: str, role: str, org_id: int | None = None) -> dict[str, str]:
    token = create_access_token(subject=email, role=role, organization_id=org_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seed_s07_s10(db_session: Session) -> dict:
    org_admin = Organization(name="Cơ quan Quản trị Hệ thống", code="ORG_ADMIN")
    org_farm = Organization(name="HTX Nông sản Hữu cơ Đà Lạt", code="ORG_FARM_DL")
    org_coop = Organization(name="HTX Chế biến Rau củ", code="ORG_COOP")
    db_session.add_all([org_admin, org_farm, org_coop])
    db_session.flush()

    user_admin = User(
        email="admin_sys@trace.gov.vn",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Quản trị viên Hệ thống",
        role=UserRole.ADMIN.value,
        organization_id=org_admin.id,
        is_active=True,
    )
    user_farm = User(
        email="nongdan_dalat@trace.vn",
        hashed_password=get_password_hash("FarmPass123!"),
        full_name="Nguyễn Văn Nông Dân",
        role=UserRole.FARM.value,
        organization_id=org_farm.id,
        is_active=True,
    )
    user_inspector = User(
        email="inspector_quocgia@trace.gov.vn",
        hashed_password=get_password_hash("Inspect123!"),
        full_name="Cán bộ Thanh tra An toàn Nông sản",
        role=UserRole.INSPECTOR.value,
        organization_id=None,
        is_active=True,
    )
    db_session.add_all([user_admin, user_farm, user_inspector])
    db_session.flush()

    batch_test = Batch(
        batch_code="VN-DL-2026-CH01",
        product_name="Dâu tây giống Nhật New Zealand",
        organization_id=org_farm.id,
        initial_quantity=500.0,
        remaining_quantity=500.0,
        unit="kg",
    )
    db_session.add(batch_test)
    db_session.commit()

    return {
        "org_admin": org_admin,
        "org_farm": org_farm,
        "user_admin": user_admin,
        "user_farm": user_farm,
        "user_inspector": user_inspector,
        "batch": batch_test,
    }


# ============================================================================
# USER STORY S-07: DANH MỤC SẢN PHẨM & ĐƠN VỊ TÍNH ĐÓNG (T-16, T-17)
# ============================================================================


class TestS07ProductCatalog:
    def test_admin_can_create_product_with_valid_unit(
        self, client: TestClient, seed_s07_s10: dict
    ):
        """Admin tạo sản phẩm với đơn vị tính đóng hợp lệ ('kg', 'tấn', 'thùng')."""
        admin_headers = get_auth_headers(
            seed_s07_s10["user_admin"].email,
            seed_s07_s10["user_admin"].role,
            seed_s07_s10["org_admin"].id,
        )

        payload = {
            "name": "Sầu riêng Ri6 sấy thăng hoa",
            "unit": "kg",
            "description": "Sản phẩm OCOP 5 sao tỉnh Lâm Đồng",
        }
        res = client.post("/api/v1/products", json=payload, headers=admin_headers)
        assert res.status_code == status.HTTP_201_CREATED
        data = res.json()
        assert data["name"] == "Sầu riêng Ri6 sấy thăng hoa"
        assert data["unit"] == "kg"
        assert "id" in data

    def test_block_invalid_unit_free_text(
        self, client: TestClient, seed_s07_s10: dict
    ):
        """Đơn vị tính bắt buộc chọn từ enum: nhập chữ tự do (hộp, bó, lạng) bị chặn 422."""
        admin_headers = get_auth_headers(
            seed_s07_s10["user_admin"].email,
            seed_s07_s10["user_admin"].role,
            seed_s07_s10["org_admin"].id,
        )

        payload = {
            "name": "Cà chua bi sô cô la",
            "unit": "hộp",  # Sai enum! Chỉ cho phép 'kg', 'tấn', 'thùng'
        }
        res = client.post("/api/v1/products", json=payload, headers=admin_headers)
        assert res.status_code in (
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            422,
        )

    def test_block_duplicate_product_name(
        self, client: TestClient, seed_s07_s10: dict
    ):
        """Chặn thêm sản phẩm trùng tên (trả về 400 Bad Request)."""
        admin_headers = get_auth_headers(
            seed_s07_s10["user_admin"].email,
            seed_s07_s10["user_admin"].role,
            seed_s07_s10["org_admin"].id,
        )

        payload = {"name": "Gạo ST25 Ông Cua", "unit": "tấn"}
        res1 = client.post("/api/v1/products", json=payload, headers=admin_headers)
        assert res1.status_code == status.HTTP_201_CREATED

        # Cố tình tạo lại với cùng tên
        res2 = client.post("/api/v1/products", json=payload, headers=admin_headers)
        assert res2.status_code == status.HTTP_400_BAD_REQUEST
        assert "đã tồn tại" in res2.json()["detail"]

    def test_non_admin_cannot_create_or_modify_products(
        self, client: TestClient, seed_s07_s10: dict
    ):
        """Chỉ Admin mới có quyền ghi. Các vai trò khác (Farm, Inspector) bị chặn 403."""
        farm_headers = get_auth_headers(
            seed_s07_s10["user_farm"].email,
            seed_s07_s10["user_farm"].role,
            seed_s07_s10["org_farm"].id,
        )
        inspector_headers = get_auth_headers(
            seed_s07_s10["user_inspector"].email,
            seed_s07_s10["user_inspector"].role,
            None,
        )

        payload = {"name": "Hành tây Đà Lạt", "unit": "thùng"}

        # Vùng trồng gọi POST -> 403 Forbidden
        res_farm = client.post("/api/v1/products", json=payload, headers=farm_headers)
        assert res_farm.status_code == status.HTTP_403_FORBIDDEN

        # Inspector gọi POST -> 403 Forbidden
        res_insp = client.post(
            "/api/v1/products", json=payload, headers=inspector_headers
        )
        assert res_insp.status_code == status.HTTP_403_FORBIDDEN

    def test_all_roles_can_view_product_catalog(
        self, client: TestClient, db_session: Session, seed_s07_s10: dict
    ):
        """Danh mục sản phẩm không lọc theo organization_id: Mọi vai trò đều xem được."""
        p = Product(name="Mắc ca Lâm Đồng", unit="kg", description="Hạt khô xuất khẩu")
        db_session.add(p)
        db_session.commit()

        farm_headers = get_auth_headers(
            seed_s07_s10["user_farm"].email,
            seed_s07_s10["user_farm"].role,
            seed_s07_s10["org_farm"].id,
        )
        res = client.get("/api/v1/products", headers=farm_headers)
        assert res.status_code == status.HTTP_200_OK
        items = res.json()
        assert any(item["name"] == "Mắc ca Lâm Đồng" for item in items)


# ============================================================================
# USER STORIES S-10, S-11, S-12: CHUỖI HASH, APPEND-ONLY & KIỂM TRA TOÀN VẸN
# ============================================================================


class TestS10S11S12HashChainAndTamperDetection:
    def test_canonical_json_hashing_key_order_invariance(self):
        """
        Task T-24: Băm hai lần với thứ tự khóa JSON khác nhau vẫn ra cùng một mã hash!
        Định dạng ngày và số thực được chuẩn hóa cố định.
        """
        payload1 = {
            "temperature": 4.5,
            "humidity": 85.0,
            "location": "Kho lạnh A",
            "metadata": {"weight": 100.0, "quality": "Grade A"},
        }
        payload2 = {
            "metadata": {"quality": "Grade A", "weight": 100.0},
            "location": "Kho lạnh A",
            "humidity": 85.0,
            "temperature": 4.5,
        }

        canon1 = canonicalize_event_data(payload1)
        canon2 = canonicalize_event_data(payload2)
        assert canon1 == canon2

        hash1 = calculate_event_hash(
            batch_id=1,
            event_type="COLD_STORAGE",
            event_data=payload1,
            org_id=10,
            prev_hash=GENESIS_HASH,
            timestamp_str="2026-10-21T08:00:00Z",
        )
        hash2 = calculate_event_hash(
            batch_id=1,
            event_type="COLD_STORAGE",
            event_data=payload2,
            org_id=10,
            prev_hash=GENESIS_HASH,
            timestamp_str="2026-10-21T08:00:00Z",
        )
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_first_event_uses_genesis_hash(
        self, db_session: Session, seed_s07_s10: dict
    ):
        """Task T-24: Sự kiện đầu tiên của lô dùng prev_hash là chuỗi khởi đầu cố định (GENESIS)."""
        batch = seed_s07_s10["batch"]
        e1 = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="BATCH_INITIALIZED",
            event_data={"action": "Gieo mầm", "plot_id": 1},
            organization_id=seed_s07_s10["org_farm"].id,
        )
        assert e1.previous_hash == GENESIS_HASH
        assert len(e1.current_hash) == 64

        # Sự kiện thứ hai nối tiếp e1
        e2 = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="HARVESTED",
            event_data={"quantity": 500.0},
            organization_id=seed_s07_s10["org_farm"].id,
        )
        assert e2.previous_hash == e1.current_hash
        db_session.commit()

    def test_append_only_block_update_and_delete_api(
        self, client: TestClient, db_session: Session, seed_s07_s10: dict
    ):
        """
        User Story S-11: Bảng batch_events/chain_events là chỉ-thêm (append-only).
        Không có bất kỳ API nào cho phép UPDATE hoặc DELETE sự kiện đã ghi.
        """
        batch = seed_s07_s10["batch"]
        e1 = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="BATCH_INITIALIZED",
            event_data={"msg": "Sự kiện ban đầu"},
            organization_id=seed_s07_s10["org_farm"].id,
        )
        db_session.commit()

        admin_headers = get_auth_headers(
            seed_s07_s10["user_admin"].email,
            seed_s07_s10["user_admin"].role,
            seed_s07_s10["org_admin"].id,
        )

        # Cố gọi PUT -> 405 Method Not Allowed
        res_put = client.put(
            f"/api/v1/chain-events/{e1.id}",
            json={"event_data": "sửa lén"},
            headers=admin_headers,
        )
        assert res_put.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert "chỉ-thêm" in res_put.json()["detail"]

        # Cố gọi DELETE -> 405 Method Not Allowed
        res_del = client.delete(
            f"/api/v1/chain-events/{e1.id}", headers=admin_headers
        )
        assert res_del.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_orm_level_prevents_direct_update(
        self, db_session: Session, seed_s07_s10: dict
    ):
        """User Story S-11: Tầng ORM listener chặn trực tiếp mọi thao tác UPDATE."""
        batch = seed_s07_s10["batch"]
        event = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="BATCH_TEST_IMMUTABLE",
            event_data="Dữ liệu gốc",
            organization_id=seed_s07_s10["org_farm"].id,
        )
        db_session.flush()

        event.event_data = "Dữ liệu bị sửa qua ORM"
        with pytest.raises(ReadOnlyChainEventError):
            db_session.flush()

    def test_orm_level_prevents_direct_delete(
        self, db_session: Session, seed_s07_s10: dict
    ):
        """User Story S-11: Tầng ORM listener chặn trực tiếp mọi thao tác DELETE."""
        batch = seed_s07_s10["batch"]
        event = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="BATCH_TEST_IMMUTABLE_DEL",
            event_data="Dữ liệu gốc không thể xóa",
            organization_id=seed_s07_s10["org_farm"].id,
        )
        db_session.flush()

        with pytest.raises(ReadOnlyChainEventError):
            db_session.delete(event)
            db_session.flush()

    def test_verify_chain_integrity_valid_chain(
        self, client: TestClient, db_session: Session, seed_s07_s10: dict
    ):
        """S-12, T-29: Kiểm tra toàn vẹn chuỗi hợp lệ trả về valid=True và danh sách sự kiện."""
        batch = seed_s07_s10["batch"]
        record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="E1_PLANTING",
            event_data={"plot": "Khu A"},
            organization_id=seed_s07_s10["org_farm"].id,
        )
        record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="E2_HARVEST",
            event_data={"yield": 480.0},
            organization_id=seed_s07_s10["org_farm"].id,
        )
        db_session.commit()

        inspector_headers = get_auth_headers(
            seed_s07_s10["user_inspector"].email,
            seed_s07_s10["user_inspector"].role,
            None,
        )
        res = client.get(
            f"/api/v1/chain-events/verify?batch_code={batch.batch_code}",
            headers=inspector_headers,
        )
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["valid"] is True
        assert data["total_events"] == 2
        assert data["broken_event_id"] is None
        assert all(e["status"] == "valid" for e in data["events"])

    def test_simulation_tamper_data_detects_first_broken_and_compromises_after(
        self, client: TestClient, db_session: Session, seed_s07_s10: dict
    ):
        """
        Test T-30, User Story S-12:
        Mô phỏng sửa lén SQL tại sự kiện giữa chuỗi:
        - Hệ thống phát hiện chính xác vị trí sự kiện đầu tiên bị sửa.
        - Đánh dấu nghi vấn (compromised) mọi sự kiện phía sau nó!
        """
        batch = seed_s07_s10["batch"]
        # Tạo chuỗi 4 sự kiện
        e1 = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="E1_SEED",
            event_data="Hạt giống chất lượng cao",
            organization_id=seed_s07_s10["org_farm"].id,
        )
        e2 = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="E2_HARVEST",
            event_data="Thu hoạch đợt 1",
            organization_id=seed_s07_s10["org_farm"].id,
        )
        e3 = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="E3_PROCESSING",
            event_data="Sơ chế đóng hộp",
            organization_id=seed_s07_s10["org_farm"].id,
        )
        e4 = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="E4_DISTRIBUTION",
            event_data="Xuất kho phân phối",
            organization_id=seed_s07_s10["org_farm"].id,
        )
        db_session.commit()

        inspector_headers = get_auth_headers(
            seed_s07_s10["user_inspector"].email,
            seed_s07_s10["user_inspector"].role,
            None,
        )

        # 1. Gọi API mô phỏng sửa lén SQL sự kiện e2
        sim_payload = {
            "batch_code": batch.batch_code,
            "action": "tamper_data",
            "event_id": e2.id,
            "tamper_value": "Dữ liệu đã bị Hacker sửa lén trực tiếp bằng SQL!",
        }
        res_sim = client.post(
            "/api/v1/chain-events/simulate-tamper",
            json=sim_payload,
            headers=inspector_headers,
        )
        assert res_sim.status_code == status.HTTP_200_OK
        assert res_sim.json()["success"] is True

        # 2. Chạy kiểm tra toàn vẹn
        res_verify = client.get(
            f"/api/v1/chain-events/verify?batch_code={batch.batch_code}",
            headers=inspector_headers,
        )
        assert res_verify.status_code == status.HTTP_200_OK
        report = res_verify.json()

        assert report["valid"] is False
        assert report["broken_event_id"] == e2.id
        assert report["broken_event_index"] == 2
        assert "đã bị sửa lén trong CSDL" in report["first_failure_reason"]

        events_res = report["events"]
        assert len(events_res) == 4

        # Sự kiện 1: Hợp lệ
        assert events_res[0]["id"] == e1.id
        assert events_res[0]["status"] == "valid"

        # Sự kiện 2: Bị sửa lén (tampered)
        assert events_res[1]["id"] == e2.id
        assert events_res[1]["status"] == "tampered"

        # Sự kiện 3 & 4: Đánh dấu nghi vấn (compromised)
        assert events_res[2]["id"] == e3.id
        assert events_res[2]["status"] == "compromised"
        assert "Nghi vấn" in events_res[2]["message"]

        assert events_res[3]["id"] == e4.id
        assert events_res[3]["status"] == "compromised"
        assert "Nghi vấn" in events_res[3]["message"]

    def test_simulation_delete_event_detects_broken_link(
        self, client: TestClient, db_session: Session, seed_s07_s10: dict
    ):
        """Test T-30: Mô phỏng xóa sự kiện giữa chuỗi gây đứt mạch liên kết previous_hash."""
        batch = seed_s07_s10["batch"]
        record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="STEP_1",
            event_data="Bắt đầu",
            organization_id=seed_s07_s10["org_farm"].id,
        )
        e2 = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="STEP_2",
            event_data="Ở giữa",
            organization_id=seed_s07_s10["org_farm"].id,
        )
        e3 = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="STEP_3",
            event_data="Kết thúc",
            organization_id=seed_s07_s10["org_farm"].id,
        )
        db_session.commit()

        admin_headers = get_auth_headers(
            seed_s07_s10["user_admin"].email,
            seed_s07_s10["user_admin"].role,
            seed_s07_s10["org_admin"].id,
        )

        # Mô phỏng xóa sự kiện e2
        res_del_sim = client.post(
            "/api/v1/chain-events/simulate-tamper",
            json={
                "batch_code": batch.batch_code,
                "action": "delete_event",
                "event_id": e2.id,
            },
            headers=admin_headers,
        )
        assert res_del_sim.status_code == status.HTTP_200_OK

        # Chạy kiểm tra toàn vẹn
        res_verify = client.get(
            f"/api/v1/chain-events/verify?batch_code={batch.batch_code}",
            headers=admin_headers,
        )
        report = res_verify.json()
        assert report["valid"] is False
        # Sự kiện e3 hiện là vị trí thứ 2 và previous_hash của nó trỏ vào e2 đã biến mất!
        assert report["broken_event_id"] == e3.id
        assert report["broken_event_index"] == 2
        assert "Đứt gãy liên kết chuỗi" in report["first_failure_reason"]
