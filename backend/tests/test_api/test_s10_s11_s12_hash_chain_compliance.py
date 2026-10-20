from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models.batch import Batch
from app.models.chain_event import ChainEvent, ReadOnlyChainEventError
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.services.hash_chain_service import (
    GENESIS_HASH,
    record_chain_event,
    verify_chain_integrity,
)


def get_auth_headers(email: str, role: str, org_id: int | None = None) -> dict[str, str]:
    token = create_access_token(subject=email, role=role, organization_id=org_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seed_compliance(db_session: Session) -> dict:
    org_farm = Organization(name="HTX Nông trại Hữu cơ An Toàn", code="ORG_COMPLIANCE_FARM")
    org_admin = Organization(name="Cơ quan Giám sát Chuỗi Cung ứng", code="ORG_COMPLIANCE_ADMIN")
    db_session.add_all([org_farm, org_admin])
    db_session.flush()

    user_farm = User(
        email="farmer_compliance@trace.vn",
        hashed_password=get_password_hash("FarmSecure123!"),
        full_name="Trần Văn Nông Nghiệp",
        role=UserRole.FARM.value,
        organization_id=org_farm.id,
        is_active=True,
    )
    user_admin = User(
        email="admin_compliance@trace.vn",
        hashed_password=get_password_hash("AdminSecure123!"),
        full_name="Lê Quản Trị Hệ Thống",
        role=UserRole.ADMIN.value,
        organization_id=org_admin.id,
        is_active=True,
    )
    user_inspector = User(
        email="inspector_compliance@trace.gov.vn",
        hashed_password=get_password_hash("InspectorPass123!"),
        full_name="Nguyễn Thanh Tra",
        role=UserRole.INSPECTOR.value,
        organization_id=None,
        is_active=True,
    )
    db_session.add_all([user_farm, user_admin, user_inspector])
    db_session.commit()

    return {
        "org_farm": org_farm,
        "org_admin": org_admin,
        "user_farm": user_farm,
        "user_admin": user_admin,
        "user_inspector": user_inspector,
    }


class TestS10S11S12Compliance:
    """Kiểm tra tuân thủ đầy đủ các yêu cầu S-10, S-11 và S-12."""

    def test_single_event_chain_is_valid(self, db_session: Session, seed_compliance: dict):
        """Yêu cầu 4: Chuỗi 1 sự kiện duy nhất vẫn được xem là hợp lệ."""
        batch = Batch(
            batch_code="VN-SINGLE-2026-001",
            product_name="Dưa lưới Huỳnh Long",
            organization_id=seed_compliance["org_farm"].id,
            initial_quantity=100.0,
            remaining_quantity=100.0,
            unit="kg",
        )
        db_session.add(batch)
        db_session.commit()

        event = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="BATCH_CREATED",
            event_data={"plot": "Vườn A", "supervisor": "Nguyễn Văn Nông Nghiệp"},
            organization_id=seed_compliance["org_farm"].id,
        )
        db_session.commit()

        assert event.previous_hash == GENESIS_HASH
        report = verify_chain_integrity(db=db_session, batch_id=batch.id)
        assert report["valid"] is True
        assert report["total_events"] == 1
        assert report["broken_event_id"] is None
        assert report["broken_event_index"] is None
        assert report["events"][0]["status"] == "valid"

    def test_atomic_batch_creation_success(
        self, client: TestClient, db_session: Session, seed_compliance: dict
    ):
        """
        Yêu cầu 5: Thao tác tạo lô và ghi sự kiện nằm trong cùng một transaction.
        Khi thành công: Cả lô và sự kiện BATCH_CREATED đều được ghi vào database.
        """
        headers = get_auth_headers(
            seed_compliance["user_farm"].email,
            seed_compliance["user_farm"].role,
            seed_compliance["org_farm"].id,
        )

        payload = {
            "batch_code": "VN-ATOMIC-2026-OK",
            "product_name": "Bưởi Da Xanh Bến Tre",
            "initial_quantity": 250.0,
            "unit": "kg",
        }

        response = client.post("/api/v1/batches", json=payload, headers=headers)
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)
        res_data = response.json()
        batch_id = res_data["id"]

        # Kiểm tra lô tồn tại trong DB
        batch_db = db_session.query(Batch).filter(Batch.id == batch_id).first()
        assert batch_db is not None
        assert batch_db.batch_code == "VN-ATOMIC-2026-OK"

        # Kiểm tra sự kiện khởi tạo tồn tại trong DB
        events = db_session.query(ChainEvent).filter(ChainEvent.batch_id == batch_id).all()
        assert len(events) == 1
        assert events[0].event_type == "BATCH_INITIALIZED"
        assert events[0].previous_hash == GENESIS_HASH

    def test_atomic_batch_creation_rolls_back_on_event_failure(
        self, client: TestClient, db_session: Session, seed_compliance: dict
    ):
        """
        Yêu cầu 5: Nếu việc ghi sự kiện chuỗi băm thất bại giữa chừng,
        giao dịch phải ROLLBACK hoàn toàn: Không để lại lô thiếu sự kiện (orphan batch).
        """
        headers = get_auth_headers(
            seed_compliance["user_farm"].email,
            seed_compliance["user_farm"].role,
            seed_compliance["org_farm"].id,
        )

        payload = {
            "batch_code": "VN-ATOMIC-2026-FAIL",
            "product_name": "Thanh Long Ruột Đỏ",
            "initial_quantity": 500.0,
            "unit": "kg",
        }

        # Giả lập lỗi xảy ra trong quá trình ghi sự kiện chuỗi băm
        with patch("app.api.v1.batches.record_chain_event") as mock_record:
            mock_record.side_effect = RuntimeError("Mô phỏng lỗi ghi sự kiện chuỗi băm!")

            with pytest.raises(RuntimeError, match="Mô phỏng lỗi ghi sự kiện chuỗi băm!"):
                client.post("/api/v1/batches", json=payload, headers=headers)

        # Kiểm tra database: Không được có lô hàng nào với batch_code 'VN-ATOMIC-2026-FAIL'
        orphan_batch = (
            db_session.query(Batch).filter(Batch.batch_code == "VN-ATOMIC-2026-FAIL").first()
        )
        assert orphan_batch is None, "Lô hàng không được lưu lại khi ghi sự kiện thất bại!"

        # Không có sự kiện mồ côi nào
        events = (
            db_session.query(ChainEvent)
            .filter(ChainEvent.batch_id == (orphan_batch.id if orphan_batch else -999))
            .all()
        )
        assert len(events) == 0

    def test_batch_deletion_blocked_when_chain_events_exist(
        self, client: TestClient, db_session: Session, seed_compliance: dict
    ):
        """
        Yêu cầu 2: Ngăn chặn xóa một lô kéo theo cascade xóa các sự kiện đã ghi.
        API từ chối xóa lô (HTTP 400) khi lô đã có lịch sử chuỗi sự kiện.
        """
        batch = Batch(
            batch_code="VN-NO-DELETE-2026",
            product_name="Cà phê Robusta Đắk Lắk",
            organization_id=seed_compliance["org_farm"].id,
            initial_quantity=1000.0,
            remaining_quantity=1000.0,
            unit="kg",
        )
        db_session.add(batch)
        db_session.commit()

        # Ghi sự kiện cho lô
        record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="BATCH_CREATED",
            event_data={"note": "Lô thử nghiệm chống xóa"},
            organization_id=seed_compliance["org_farm"].id,
        )
        db_session.commit()

        headers = get_auth_headers(
            seed_compliance["user_admin"].email,
            seed_compliance["user_admin"].role,
            seed_compliance["org_admin"].id,
        )

        response = client.delete(f"/api/v1/batches/{batch.id}", headers=headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "nghiêm cấm xóa" in data["detail"].lower() or "s-11" in data["detail"].lower()

        # Kiểm tra lô và sự kiện vẫn nguyên vẹn trong DB
        assert db_session.query(Batch).filter(Batch.id == batch.id).first() is not None
        assert (
            db_session.query(ChainEvent).filter(ChainEvent.batch_id == batch.id).count() == 1
        )

    def test_multi_event_chain_broken_link_exact_index(
        self, db_session: Session, seed_compliance: dict
    ):
        """
        Yêu cầu 4: Một chuỗi nhiều sự kiện bị xóa một sự kiện ở giữa,
        thuật toán phát hiện chính xác vị trí đứt mạch (broken link) và đánh dấu nghi vấn phía sau.
        """
        batch = Batch(
            batch_code="VN-MULTI-BROKEN-2026",
            product_name="Hồ tiêu Chư Sê",
            organization_id=seed_compliance["org_farm"].id,
            initial_quantity=300.0,
            remaining_quantity=300.0,
            unit="kg",
        )
        db_session.add(batch)
        db_session.commit()

        e1 = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="STAGE_1_PLANT",
            event_data={"detail": "Trồng trọt"},
            organization_id=seed_compliance["org_farm"].id,
        )
        e2 = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="STAGE_2_HARVEST",
            event_data={"detail": "Thu hoạch"},
            organization_id=seed_compliance["org_farm"].id,
        )
        e3 = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="STAGE_3_DRY",
            event_data={"detail": "Phơi sấy"},
            organization_id=seed_compliance["org_farm"].id,
        )
        e4 = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="STAGE_4_PACK",
            event_data={"detail": "Đóng gói"},
            organization_id=seed_compliance["org_farm"].id,
        )
        db_session.commit()

        # Chuỗi ban đầu hợp lệ 100%
        initial_check = verify_chain_integrity(db=db_session, batch_id=batch.id)
        assert initial_check["valid"] is True
        assert initial_check["total_events"] == 4

        # Giả lập xóa sự kiện e2 bằng lệnh SQL trực tiếp (bỏ qua ORM listener)
        db_session.execute(text(f"DELETE FROM chain_events WHERE id = {e2.id}"))
        db_session.commit()

        # Kiểm tra lại: e3 hiện tại đứng ở vị trí thứ 2, có previous_hash trỏ tới hash của e2 (không tồn tại)
        # e3 không khớp với current_hash của e1
        report = verify_chain_integrity(db=db_session, batch_id=batch.id)
        assert report["valid"] is False
        assert report["total_events"] == 3
        # Vị trí đứt mạch là index 2 (sự kiện e3)
        assert report["broken_event_index"] == 2
        assert report["broken_event_id"] == e3.id
        assert "Đứt gãy liên kết chuỗi" in report["first_failure_reason"]

        events_result = report["events"]
        assert events_result[0]["id"] == e1.id
        assert events_result[0]["status"] == "valid"

        assert events_result[1]["id"] == e3.id
        assert events_result[1]["status"] == "broken_link"

        # e4 đứng sau vị trí đứt mạch phải bị đánh dấu compromised
        assert events_result[2]["id"] == e4.id
        assert events_result[2]["status"] == "compromised"

    def test_multi_event_chain_tampered_data_exact_index(
        self, db_session: Session, seed_compliance: dict
    ):
        """
        Yêu cầu 4: Sự kiện bị sửa dữ liệu mà không tính lại hash,
        thuật toán phát hiện đúng vị trí sự kiện bị sửa lén (tampered).
        """
        batch = Batch(
            batch_code="VN-MULTI-TAMPER-2026",
            product_name="Xoài Cát Hòa Lộc",
            organization_id=seed_compliance["org_farm"].id,
            initial_quantity=800.0,
            remaining_quantity=800.0,
            unit="kg",
        )
        db_session.add(batch)
        db_session.commit()

        record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="STEP_1",
            event_data={"plot": "Vườn B"},
            organization_id=seed_compliance["org_farm"].id,
        )
        e2 = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="STEP_2",
            event_data={"quality": "Loại 1"},
            organization_id=seed_compliance["org_farm"].id,
        )
        record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="STEP_3",
            event_data={"status": "Xuất khẩu"},
            organization_id=seed_compliance["org_farm"].id,
        )
        db_session.commit()

        # Sửa dữ liệu của e2 bằng SQL trực tiếp
        db_session.execute(
            text(f"UPDATE chain_events SET event_data = '{{\"quality\":\"Loại 3 (Sửa lén)\"}}' WHERE id = {e2.id}")
        )
        db_session.commit()

        report = verify_chain_integrity(db=db_session, batch_id=batch.id)
        assert report["valid"] is False
        assert report["broken_event_index"] == 2
        assert report["broken_event_id"] == e2.id
        assert "đã bị sửa lén trong CSDL" in report["first_failure_reason"]

        assert report["events"][0]["status"] == "valid"
        assert report["events"][1]["status"] == "tampered"
        assert report["events"][2]["status"] == "compromised"

    def test_orm_listener_rejects_update(
        self, db_session: Session, seed_compliance: dict
    ):
        """Yêu cầu 2 & 4: Tầng ORM listener chặn triệt để thao tác UPDATE."""
        batch = Batch(
            batch_code="VN-ORM-UPDATE-2026",
            product_name="Chè Shan Tuyết Cổ Thụ",
            organization_id=seed_compliance["org_farm"].id,
            initial_quantity=50.0,
            remaining_quantity=50.0,
            unit="kg",
        )
        db_session.add(batch)
        db_session.commit()

        event = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="INITIAL",
            event_data={"msg": "Dữ liệu ban đầu"},
            organization_id=seed_compliance["org_farm"].id,
        )
        db_session.commit()

        event.event_data = "Cố tình sửa qua ORM"
        with pytest.raises(ReadOnlyChainEventError):
            db_session.flush()

    def test_orm_listener_rejects_delete(
        self, db_session: Session, seed_compliance: dict
    ):
        """Yêu cầu 2 & 4: Tầng ORM listener chặn triệt để thao tác DELETE."""
        batch = Batch(
            batch_code="VN-ORM-DELETE-2026",
            product_name="Măng Cụt Lái Thiêu",
            organization_id=seed_compliance["org_farm"].id,
            initial_quantity=80.0,
            remaining_quantity=80.0,
            unit="kg",
        )
        db_session.add(batch)
        db_session.commit()

        event = record_chain_event(
            db=db_session,
            batch_id=batch.id,
            event_type="INITIAL",
            event_data={"msg": "Dữ liệu ban đầu"},
            organization_id=seed_compliance["org_farm"].id,
        )
        db_session.commit()

        with pytest.raises(ReadOnlyChainEventError):
            db_session.delete(event)
            db_session.flush()
