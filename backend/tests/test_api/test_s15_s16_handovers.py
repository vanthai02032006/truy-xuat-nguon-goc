from __future__ import annotations

import pytest
from app.core.security import create_access_token, get_password_hash
from app.models.batch import Batch
from app.models.chain_event import ChainEvent
from app.models.handover import HandoverStatus
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.services.hash_chain_service import verify_chain_integrity
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def get_auth_headers(user_email: str, role: str, org_id: int | None) -> dict[str, str]:
    """Tạo header Authorization Bearer token phục vụ kiểm thử."""
    token = create_access_token(subject=user_email, role=role, organization_id=org_id)
    return {"Authorization": f"Bearer {token}"}


class TestS15S16HandoverAndHashChain:
    """
    Bộ kiểm thử tự động cho User Story S-15 và S-16:
    'Bàn giao lô hàng giữa các tổ chức độc lập và toàn vẹn chuỗi hash SHA-256'
    1. Bảng handovers và chain_events lưu trữ đúng cấu trúc.
    2. Tổ chức A tạo bàn giao sang B: Lô chuyển 'chờ xác nhận', A vẫn giữ quyền sở hữu,
       chặn không cho tạo lệnh bàn giao thứ hai khi đang có lệnh chờ.
    3. Tổ chức B 'Xác nhận': Chuyển quyền giữ lô (batches.organization_id) sang B
       và ghi một sự kiện xác nhận vào chuỗi hash trong cùng một Database Transaction.
    4. Tổ chức B 'Từ chối': Bắt buộc nhập lý do (tối thiểu 10 ký tự), lô vẫn thuộc quyền
       giữ của A và ghi nhận sự kiện từ chối kèm lý do vào chuỗi hash.
    5. Cán bộ kiểm tra (Inspector) chỉ có quyền xem, bị chặn ghi/sửa (HTTP 403).
    """

    @pytest.fixture
    def handover_seed(self, db_session: Session):
        """Khởi tạo 3 tổ chức độc lập, người dùng đại diện và các lô hàng mẫu."""
        # 1. Ba tổ chức độc lập
        org_a = Organization(id=10, name="HTX Vùng Trồng Thắng Lợi", code="ORG-A-FARM")
        org_b = Organization(id=20, name="HTX Sơ Chế Đà Lạt Lành", code="ORG-B-COOP")
        org_c = Organization(id=30, name="Đội Xe Lạnh Express", code="ORG-C-LOGISTICS")
        db_session.add_all([org_a, org_b, org_c])
        db_session.flush()

        # 2. Người dùng thuộc từng tổ chức
        user_a = User(
            id=101,
            email="farmer_a@thangloi.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Nguyễn Văn A (Vùng Trồng)",
            role=UserRole.FARM.value,
            organization_id=org_a.id,
            is_active=True,
        )
        user_b = User(
            id=201,
            email="manager_b@dalatlanh.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Trần Thị B (Sơ Chế)",
            role=UserRole.PROCESSING.value,
            organization_id=org_b.id,
            is_active=True,
        )
        user_c = User(
            id=301,
            email="driver_c@express.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Lê Văn C (Logistics)",
            role=UserRole.LOGISTICS.value,
            organization_id=org_c.id,
            is_active=True,
        )
        inspector = User(
            id=901,
            email="inspector@kiemdinh.gov.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Vũ Kiểm Định",
            role=UserRole.INSPECTOR.value,
            organization_id=None,
            is_active=True,
        )
        db_session.add_all([user_a, user_b, user_c, inspector])
        db_session.flush()

        # 3. Lô hàng của tổ chức A
        batch_1 = Batch(
            id=1001,
            batch_code="B-TOMATO-01",
            product_name="Cà chua Beef Đà Lạt",
            organization_id=org_a.id,
            status="active",
        )
        batch_2 = Batch(
            id=1002,
            batch_code="B-BERRY-02",
            product_name="Dâu tây New Zealand",
            organization_id=org_a.id,
            status="active",
        )
        db_session.add_all([batch_1, batch_2])
        db_session.commit()

        return {
            "org_a": org_a,
            "org_b": org_b,
            "org_c": org_c,
            "user_a": user_a,
            "user_b": user_b,
            "user_c": user_c,
            "inspector": inspector,
            "batch_1": batch_1,
            "batch_2": batch_2,
        }

    # =========================================================================
    # 1. TIÊU CHÍ S-15: TẠO BÀN GIAO, TRẠNG THÁI VÀ CHẶN LỆNH BÀN GIAO THỨ HAI
    # =========================================================================

    def test_create_handover_success(
        self, client: TestClient, db_session: Session, handover_seed: dict
    ):
        """
        Khi tổ chức A tạo bàn giao sang tổ chức B:
        - Lô chuyển sang trạng thái 'chờ xác nhận'.
        - Tổ chức A vẫn tạm thời giữ quyền sở hữu (batches.organization_id == A).
        - Ghi nhận sự kiện khởi tạo vào chuỗi hash SHA-256.
        """
        headers_a = get_auth_headers(
            handover_seed["user_a"].email,
            handover_seed["user_a"].role,
            handover_seed["org_a"].id,
        )

        payload = {
            "batch_id": handover_seed["batch_1"].id,
            "to_org_id": handover_seed["org_b"].id,
            "temperature": 4.5,
            "notes": "Bàn giao lô cà chua sang kho sơ chế",
        }

        resp = client.post("/api/v1/handovers", json=payload, headers=headers_a)
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["batch_id"] == handover_seed["batch_1"].id
        assert data["from_org_id"] == handover_seed["org_a"].id
        assert data["to_org_id"] == handover_seed["org_b"].id
        assert data["status"] == HandoverStatus.PENDING.value
        assert data["batch_status"] == "chờ xác nhận"

        # Kiểm tra Database: Lô đổi status sang 'chờ xác nhận', nhưng quyền sở hữu VẪN LÀ A
        db_session.expire_all()
        batch = (
            db_session.query(Batch).filter_by(id=handover_seed["batch_1"].id).first()
        )
        assert batch.status == "chờ xác nhận"
        assert batch.organization_id == handover_seed["org_a"].id

        # Kiểm tra chuỗi hash: Đã ghi nhận sự kiện HANDOVER_PENDING_CREATED
        events = (
            db_session.query(ChainEvent)
            .filter_by(batch_id=batch.id)
            .order_by(ChainEvent.id.asc())
            .all()
        )
        assert len(events) >= 1
        last_event = events[-1]
        assert last_event.event_type == "HANDOVER_CREATED"
        assert last_event.organization_id == handover_seed["org_a"].id
        assert verify_chain_integrity(db_session, batch.id)["valid"] is True

    def test_block_duplicate_pending_handover(
        self, client: TestClient, db_session: Session, handover_seed: dict
    ):
        """
        Chặn không cho tạo lệnh bàn giao thứ hai khi đang có lệnh chờ xác nhận (S-15).
        """
        headers_a = get_auth_headers(
            handover_seed["user_a"].email,
            handover_seed["user_a"].role,
            handover_seed["org_a"].id,
        )

        payload1 = {
            "batch_id": handover_seed["batch_1"].id,
            "to_org_id": handover_seed["org_b"].id,
            "temperature": 4.0,
        }
        resp1 = client.post("/api/v1/handovers", json=payload1, headers=headers_a)
        assert resp1.status_code == status.HTTP_201_CREATED

        # Cố tình tạo lệnh bàn giao thứ 2 cho cùng lô hàng
        payload2 = {
            "batch_id": handover_seed["batch_1"].id,
            "to_org_id": handover_seed["org_c"].id,
            "temperature": 3.8,
        }
        resp2 = client.post("/api/v1/handovers", json=payload2, headers=headers_a)
        assert resp2.status_code == status.HTTP_400_BAD_REQUEST
        assert "đang có một lệnh bàn giao chờ xác nhận" in resp2.json()["detail"]

    def test_prevent_self_handover(
        self, client: TestClient, db_session: Session, handover_seed: dict
    ):
        """Không cho phép tự bàn giao cho chính tổ chức của mình."""
        headers_a = get_auth_headers(
            handover_seed["user_a"].email,
            handover_seed["user_a"].role,
            handover_seed["org_a"].id,
        )

        payload = {
            "batch_id": handover_seed["batch_1"].id,
            "to_org_id": handover_seed["org_a"].id,
            "temperature": 5.0,
        }
        resp = client.post("/api/v1/handovers", json=payload, headers=headers_a)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert (
            "Không thể bàn giao lô hàng cho chính tổ chức của mình"
            in resp.json()["detail"]
        )

    def test_prevent_cross_tenant_handover_creation(
        self, client: TestClient, db_session: Session, handover_seed: dict
    ):
        """Người dùng tổ chức B không thể tạo lệnh bàn giao cho lô thuộc sở hữu của tổ chức A."""
        headers_b = get_auth_headers(
            handover_seed["user_b"].email,
            handover_seed["user_b"].role,
            handover_seed["org_b"].id,
        )

        payload = {
            "batch_id": handover_seed["batch_1"].id,
            "to_org_id": handover_seed["org_c"].id,
        }
        resp = client.post("/api/v1/handovers", json=payload, headers=headers_b)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    # =========================================================================
    # 2. TIÊU CHÍ S-16: BÊN B XÁC NHẬN BÀN GIAO & NGUYÊN TỬ TRONG GIAO DỊCH
    # =========================================================================

    def test_accept_handover_atomic_custody_transfer(
        self, client: TestClient, db_session: Session, handover_seed: dict
    ):
        """
        Khi tổ chức B 'Xác nhận':
        - Chuyển quyền giữ lô (batches.organization_id) sang B.
        - Lô chuyển trạng thái 'active'.
        - Lệnh bàn giao chuyển sang ACCEPTED.
        - Ghi một sự kiện xác nhận vào chuỗi hash trong cùng một Database Transaction.
        """
        headers_a = get_auth_headers(
            handover_seed["user_a"].email,
            handover_seed["user_a"].role,
            handover_seed["org_a"].id,
        )
        headers_b = get_auth_headers(
            handover_seed["user_b"].email,
            handover_seed["user_b"].role,
            handover_seed["org_b"].id,
        )

        # 1. Tổ chức A tạo bàn giao sang B
        create_resp = client.post(
            "/api/v1/handovers",
            json={
                "batch_id": handover_seed["batch_1"].id,
                "to_org_id": handover_seed["org_b"].id,
                "temperature": 4.2,
            },
            headers=headers_a,
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        ho_id = create_resp.json()["id"]

        # 2. Tổ chức B gọi xác nhận tiếp nhận
        accept_resp = client.post(
            f"/api/v1/handovers/{ho_id}/accept", headers=headers_b
        )
        assert accept_resp.status_code == status.HTTP_200_OK
        data = accept_resp.json()
        assert data["status"] == HandoverStatus.ACCEPTED.value
        assert data["batch_status"] == "active"

        # 3. Kiểm tra DB: Quyền giữ lô đã sang B
        db_session.expire_all()
        batch = (
            db_session.query(Batch).filter_by(id=handover_seed["batch_1"].id).first()
        )
        assert batch.organization_id == handover_seed["org_b"].id
        assert batch.status == "active"

        # 4. Kiểm tra Chuỗi Hash: Có sự kiện HANDOVER_ACCEPTED
        events = (
            db_session.query(ChainEvent)
            .filter_by(batch_id=batch.id)
            .order_by(ChainEvent.id.asc())
            .all()
        )
        accept_event = next(e for e in events if e.event_type == "HANDOVER_ACCEPTED")
        assert accept_event.organization_id == handover_seed["org_b"].id
        assert (
            f"Tổ chức #{handover_seed['org_b'].id} đã xác nhận tiếp nhận quyền quản lý"
            in accept_event.event_data
        )
        assert f"từ Tổ chức #{handover_seed['org_a'].id}" in accept_event.event_data

        # Toàn vẹn chuỗi hash SHA-256 được bảo đảm
        assert verify_chain_integrity(db_session, batch.id)["valid"] is True

    def test_accept_handover_forbidden_for_non_recipient(
        self, client: TestClient, db_session: Session, handover_seed: dict
    ):
        """Chỉ bên nhận (B) mới được quyền Xác nhận. Bên giao A hoặc người ngoài C bấm accept sẽ bị 403."""
        headers_a = get_auth_headers(
            handover_seed["user_a"].email,
            handover_seed["user_a"].role,
            handover_seed["org_a"].id,
        )
        headers_c = get_auth_headers(
            handover_seed["user_c"].email,
            handover_seed["user_c"].role,
            handover_seed["org_c"].id,
        )

        create_resp = client.post(
            "/api/v1/handovers",
            json={
                "batch_id": handover_seed["batch_1"].id,
                "to_org_id": handover_seed["org_b"].id,
            },
            headers=headers_a,
        )
        ho_id = create_resp.json()["id"]

        # Bên gửi A cố tình gọi accept -> 403
        resp_a = client.post(f"/api/v1/handovers/{ho_id}/accept", headers=headers_a)
        assert resp_a.status_code == status.HTTP_403_FORBIDDEN

        # Bên ngoài C cố tình gọi accept -> 403
        resp_c = client.post(f"/api/v1/handovers/{ho_id}/accept", headers=headers_c)
        assert resp_c.status_code == status.HTTP_403_FORBIDDEN

    # =========================================================================
    # 3. TIÊU CHÍ S-16: BÊN B TỪ CHỐI BÀN GIAO & BẮT BUỘC LÝ DO >= 10 KÝ TỰ
    # =========================================================================

    def test_reject_handover_requires_minimum_10_chars_reason(
        self, client: TestClient, db_session: Session, handover_seed: dict
    ):
        """
        Khi tổ chức B từ chối: Bắt buộc nhập lý do (tối thiểu 10 ký tự).
        Nếu lý do < 10 ký tự -> Trả về HTTP 400 hoặc 422.
        """
        headers_a = get_auth_headers(
            handover_seed["user_a"].email,
            handover_seed["user_a"].role,
            handover_seed["org_a"].id,
        )
        headers_b = get_auth_headers(
            handover_seed["user_b"].email,
            handover_seed["user_b"].role,
            handover_seed["org_b"].id,
        )

        create_resp = client.post(
            "/api/v1/handovers",
            json={
                "batch_id": handover_seed["batch_1"].id,
                "to_org_id": handover_seed["org_b"].id,
            },
            headers=headers_a,
        )
        ho_id = create_resp.json()["id"]

        # Gửi lý do quá ngắn (< 10 ký tự)
        resp_too_short = client.post(
            f"/api/v1/handovers/{ho_id}/reject",
            json={"reject_reason": "Bị hỏng"},  # 7 ký tự
            headers=headers_b,
        )
        assert resp_too_short.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_reject_handover_success_retains_ownership_at_a(
        self, client: TestClient, db_session: Session, handover_seed: dict
    ):
        """
        Khi tổ chức B từ chối hợp lệ (>= 10 ký tự):
        - Lô vẫn thuộc quyền giữ của A (batches.organization_id == A).
        - Trạng thái lô quay về 'active'.
        - Ghi nhận sự kiện từ chối kèm lý do vào chuỗi hash.
        """
        headers_a = get_auth_headers(
            handover_seed["user_a"].email,
            handover_seed["user_a"].role,
            handover_seed["org_a"].id,
        )
        headers_b = get_auth_headers(
            handover_seed["user_b"].email,
            handover_seed["user_b"].role,
            handover_seed["org_b"].id,
        )

        create_resp = client.post(
            "/api/v1/handovers",
            json={
                "batch_id": handover_seed["batch_1"].id,
                "to_org_id": handover_seed["org_b"].id,
            },
            headers=headers_a,
        )
        ho_id = create_resp.json()["id"]

        reject_reason = (
            "Nhiệt độ thùng xe lạnh vượt quá 9.5°C, vi phạm bảo quản nông sản"
        )
        resp = client.post(
            f"/api/v1/handovers/{ho_id}/reject",
            json={"reject_reason": reject_reason},
            headers=headers_b,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["status"] == HandoverStatus.REJECTED.value
        assert data["reject_reason"] == reject_reason

        # Kiểm tra DB: Quyền giữ lô VẪN THUỘC TỔ CHỨC A
        db_session.expire_all()
        batch = (
            db_session.query(Batch).filter_by(id=handover_seed["batch_1"].id).first()
        )
        assert batch.organization_id == handover_seed["org_a"].id
        assert batch.status == "active"

        # Kiểm tra Chuỗi Hash: Có sự kiện HANDOVER_REJECTED kèm reject_reason
        events = (
            db_session.query(ChainEvent)
            .filter_by(batch_id=batch.id)
            .order_by(ChainEvent.id.asc())
            .all()
        )
        reject_event = next(e for e in events if e.event_type == "HANDOVER_REJECTED")
        assert reject_reason in reject_event.event_data
        assert (
            f"Tổ chức #{handover_seed['org_b'].id} từ chối tiếp nhận"
            in reject_event.event_data
        )
        assert verify_chain_integrity(db_session, batch.id)["valid"] is True

    def test_cannot_accept_or_reject_finalized_handover(
        self, client: TestClient, db_session: Session, handover_seed: dict
    ):
        """Không thể thao tác trên lệnh bàn giao đã hoàn tất (ACCEPTED/REJECTED)."""
        headers_a = get_auth_headers(
            handover_seed["user_a"].email,
            handover_seed["user_a"].role,
            handover_seed["org_a"].id,
        )
        headers_b = get_auth_headers(
            handover_seed["user_b"].email,
            handover_seed["user_b"].role,
            handover_seed["org_b"].id,
        )

        create_resp = client.post(
            "/api/v1/handovers",
            json={
                "batch_id": handover_seed["batch_1"].id,
                "to_org_id": handover_seed["org_b"].id,
            },
            headers=headers_a,
        )
        ho_id = create_resp.json()["id"]

        # Accept lần 1 thành công
        client.post(f"/api/v1/handovers/{ho_id}/accept", headers=headers_b)

        # Cố tình gọi accept lần 2 -> 400
        resp_again = client.post(f"/api/v1/handovers/{ho_id}/accept", headers=headers_b)
        assert resp_again.status_code == status.HTTP_400_BAD_REQUEST

        # Cố tình gọi reject sau khi đã accept -> 400
        resp_reject = client.post(
            f"/api/v1/handovers/{ho_id}/reject",
            json={"reject_reason": "Lý do từ chối sau khi đã nhận lô hàng"},
            headers=headers_b,
        )
        assert resp_reject.status_code == status.HTTP_400_BAD_REQUEST

    # =========================================================================
    # 4. KIỂM TRA PHÂN QUYỀN INSPECTOR (CHỈ ĐỌC, CHẶN GHI)
    # =========================================================================

    def test_inspector_can_view_handovers_but_cannot_modify(
        self, client: TestClient, db_session: Session, handover_seed: dict
    ):
        """Cán bộ kiểm tra (Inspector) xem được danh sách bàn giao nhưng bị chặn ghi/sửa (403)."""
        headers_a = get_auth_headers(
            handover_seed["user_a"].email,
            handover_seed["user_a"].role,
            handover_seed["org_a"].id,
        )
        headers_insp = get_auth_headers(
            handover_seed["inspector"].email,
            handover_seed["inspector"].role,
            None,
        )

        # A tạo bàn giao
        create_resp = client.post(
            "/api/v1/handovers",
            json={
                "batch_id": handover_seed["batch_1"].id,
                "to_org_id": handover_seed["org_b"].id,
            },
            headers=headers_a,
        )
        ho_id = create_resp.json()["id"]

        # Inspector xem danh sách -> 200 OK
        resp_get = client.get("/api/v1/handovers", headers=headers_insp)
        assert resp_get.status_code == status.HTTP_200_OK

        # Inspector cố tình tạo bàn giao -> 403 Forbidden
        resp_post = client.post(
            "/api/v1/handovers",
            json={
                "batch_id": handover_seed["batch_2"].id,
                "to_org_id": handover_seed["org_b"].id,
            },
            headers=headers_insp,
        )
        assert resp_post.status_code == status.HTTP_403_FORBIDDEN

        # Inspector cố tình gọi accept -> 403 Forbidden
        resp_accept = client.post(
            f"/api/v1/handovers/{ho_id}/accept", headers=headers_insp
        )
        assert resp_accept.status_code == status.HTTP_403_FORBIDDEN
