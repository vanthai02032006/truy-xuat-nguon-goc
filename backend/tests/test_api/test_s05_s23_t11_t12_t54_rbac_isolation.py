from __future__ import annotations

from datetime import datetime

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models.batch import Batch
from app.models.batch_relation import BatchRelation, BatchRelationType
from app.models.chain_event import ChainEvent
from app.models.handover import Handover, HandoverStatus
from app.models.land_plot import LandPlot
from app.models.organization import Organization
from app.models.security_log import SecurityLog
from app.models.user import User, UserRole
from app.services.batch_access_service import (
    apply_tenant_filter,
    can_view_batch,
    canView,
    get_viewable_chain_events,
    tenant_query,
)


def get_auth_headers(user_email: str, role: str, org_id: int | None) -> dict[str, str]:
    """Tạo header Authorization Bearer token phục vụ kiểm thử."""
    token = create_access_token(subject=user_email, role=role, organization_id=org_id)
    return {"Authorization": f"Bearer {token}"}


class TestRBACAndMultiTenantIsolationS05S23:
    """
    Bộ kiểm thử tích hợp đầy đủ cho User Story S-05, S-23 và Tasks T-11, T-12, T-54:
    1. Middleware mặc định từ chối & Cán bộ kiểm tra read-only toàn diện (T-11).
    2. Lớp truy vấn tự lọc theo organization_id & Ghi nhận Audit Log an ninh (T-12).
    3. Quy tắc xem lịch sử tổ tiên xuyên tổ chức canView(org, batch) (S-23, T-54).
    """

    @pytest.fixture
    def rbac_seed(self, db_session: Session):
        """Khởi tạo 4 tổ chức trong chuỗi cung ứng và 1 tổ chức bên ngoài không liên quan."""
        org_farm = Organization(id=101, name="Vùng Trồng Nông Trại Xanh", code="ORG-FARM")
        org_coop = Organization(id=102, name="HTX Sơ Chế Chế Biến", code="ORG-COOP")
        org_logistics = Organization(id=103, name="Vận Tải Lạnh Express", code="ORG-LOG")
        org_retailer = Organization(id=104, name="Hệ Thống Bán Lẻ BioMart", code="ORG-RET")
        org_unrelated = Organization(id=105, name="Siêu Thị Đối Thủ Không Liên Quan", code="ORG-UNRELATED")

        db_session.add_all([org_farm, org_coop, org_logistics, org_retailer, org_unrelated])
        db_session.flush()

        user_farm = User(
            id=201,
            email="farmer@nongtraixanh.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Nguyễn Nông Dân",
            role=UserRole.FARM.value,
            organization_id=org_farm.id,
            is_active=True,
        )
        user_coop = User(
            id=202,
            email="coop@soche.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Trần Sơ Chế",
            role=UserRole.PROCESSING.value,
            organization_id=org_coop.id,
            is_active=True,
        )
        user_retailer = User(
            id=203,
            email="retailer@biomart.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Phạm Bán Lẻ",
            role=UserRole.RETAILER.value,
            organization_id=org_retailer.id,
            is_active=True,
        )
        user_unrelated = User(
            id=204,
            email="stranger@doithu.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Người Lạ Không Liên Quan",
            role=UserRole.RETAILER.value,
            organization_id=org_unrelated.id,
            is_active=True,
        )
        user_inspector = User(
            id=205,
            email="inspector.rbac@kiemdinh.gov.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Thanh Tra An Toàn",
            role=UserRole.INSPECTOR.value,
            organization_id=None,
            is_active=True,
        )

        db_session.add_all([user_farm, user_coop, user_retailer, user_unrelated, user_inspector])
        db_session.flush()

        plot_farm = LandPlot(
            id=301,
            name="Thửa đất số 05 - Đồi Chè",
            organization_id=org_farm.id,
            area=5000.0,
            address="Đà Lạt, Lâm Đồng",
            latitude=11.9404,
            longitude=108.4583,
        )
        plot_unrelated = LandPlot(
            id=302,
            name="Thửa đất độc lập của tổ chức khác",
            organization_id=org_unrelated.id,
            area=2000.0,
            address="Buôn Ma Thuột, Đắk Lắk",
            latitude=12.6667,
            longitude=108.0383,
        )
        db_session.add_all([plot_farm, plot_unrelated])
        db_session.flush()

        # Lô gốc do Farm tạo
        batch_mother = Batch(
            id=401,
            batch_code="BCH-MTH-401",
            product_name="Cà Chua Beef Xuất Khẩu",
            organization_id=org_farm.id,
            land_plot_id=plot_farm.id,
            initial_quantity=1000.0,
            remaining_quantity=0.0,
        )
        db_session.add(batch_mother)
        db_session.flush()

        # Lô con do tách lô, được chuyển giao cho Retailer
        batch_child = Batch(
            id=402,
            batch_code="BCH-CHD-402",
            product_name="Cà Chua Beef Hộp 500g",
            organization_id=org_retailer.id,
            initial_quantity=400.0,
            remaining_quantity=400.0,
        )
        db_session.add(batch_child)
        db_session.flush()

        # Quan hệ phả hệ tách lô: batch_mother (cha) -> batch_child (con)
        rel_split = BatchRelation(
            parent_batch_id=batch_mother.id,
            child_batch_id=batch_child.id,
            relation_type=BatchRelationType.SPLIT.value,
            quantity=400.0,
        )
        db_session.add(rel_split)

        # Lô độc lập của Org đối thủ
        batch_unrelated = Batch(
            id=403,
            batch_code="BCH-UNR-403",
            product_name="Dưa hấu đối thủ không liên quan",
            organization_id=org_unrelated.id,
            initial_quantity=500.0,
            remaining_quantity=500.0,
        )
        db_session.add(batch_unrelated)

        db_session.commit()

        return {
            "org_farm": org_farm,
            "org_coop": org_coop,
            "org_logistics": org_logistics,
            "org_retailer": org_retailer,
            "org_unrelated": org_unrelated,
            "user_farm": user_farm,
            "user_coop": user_coop,
            "user_retailer": user_retailer,
            "user_unrelated": user_unrelated,
            "user_inspector": user_inspector,
            "plot_farm": plot_farm,
            "plot_unrelated": plot_unrelated,
            "batch_mother": batch_mother,
            "batch_child": batch_child,
            "batch_unrelated": batch_unrelated,
        }

    # =========================================================================
    # TASK T-11: MIDDLEWARE MẶC ĐỊNH TỪ CHỐI & CÁN BỘ KIỂM TRA CHỈ ĐỌC
    # =========================================================================

    def test_t11_default_deny_when_route_unconfigured(self, client: TestClient, rbac_seed):
        """
        T-11: Nếu một route mới được thêm mà quên khai báo quyền thì mặc định từ chối (HTTP 403 Forbidden).
        """
        headers = get_auth_headers(
            rbac_seed["user_farm"].email,
            rbac_seed["user_farm"].role,
            rbac_seed["user_farm"].organization_id,
        )

        res_unconfigured = client.get("/api/v1/protected/unconfigured-route", headers=headers)
        assert res_unconfigured.status_code == status.HTTP_403_FORBIDDEN
        assert "Route chưa được khai báo quyền truy cập — mặc định là chặn" in res_unconfigured.json()["detail"]

        res_configured = client.get("/api/v1/protected/declared-perm", headers=headers)
        assert res_configured.status_code == status.HTTP_200_OK

    def test_t11_inspector_blocked_from_all_write_operations(
        self, client: TestClient, db_session: Session, rbac_seed
    ):
        """
        T-11: Vai trò 'Cán bộ kiểm tra (Inspector)' được phép đọc dữ liệu của mọi tổ chức
        nhưng bị chặn mọi thao tác ghi/sửa/xóa (trả về 403) trên toàn hệ thống.
        """
        headers = get_auth_headers(
            rbac_seed["user_inspector"].email,
            rbac_seed["user_inspector"].role,
            rbac_seed["user_inspector"].organization_id,
        )

        # 1. Đọc dữ liệu: Được phép (200 OK)
        res_read_batch = client.get(f"/api/v1/batches/{rbac_seed['batch_mother'].id}", headers=headers)
        assert res_read_batch.status_code == status.HTTP_200_OK

        res_read_plot = client.get(f"/api/v1/land-plots/{rbac_seed['plot_farm'].id}", headers=headers)
        assert res_read_plot.status_code == status.HTTP_200_OK

        # 2. Thao tác ghi lô hàng (POST /api/v1/batches): Bị chặn 403
        res_post_batch = client.post(
            "/api/v1/batches",
            json={"batch_code": "TEST-INSP-01", "product_name": "Test"},
            headers=headers,
        )
        assert res_post_batch.status_code == status.HTTP_403_FORBIDDEN
        assert "chế độ chỉ đọc" in res_post_batch.json()["detail"]

        # 3. Thao tác xóa lô hàng (DELETE /api/v1/batches/{id}): Bị chặn 403
        res_del_batch = client.delete(f"/api/v1/batches/{rbac_seed['batch_mother'].id}", headers=headers)
        assert res_del_batch.status_code == status.HTTP_403_FORBIDDEN
        assert "chế độ chỉ đọc" in res_del_batch.json()["detail"]

        # 4. Thao tác tạo thửa đất (POST /api/v1/land-plots): Bị chặn 403
        res_post_plot = client.post(
            "/api/v1/land-plots",
            json={"name": "Thửa test của thanh tra", "area": 1000.0},
            headers=headers,
        )
        assert res_post_plot.status_code == status.HTTP_403_FORBIDDEN
        assert "chế độ chỉ đọc" in res_post_plot.json()["detail"]

        # 5. Thao tác xóa thửa đất (DELETE /api/v1/land-plots/{id}): Bị chặn 403
        res_del_plot = client.delete(f"/api/v1/land-plots/{rbac_seed['plot_farm'].id}", headers=headers)
        assert res_del_plot.status_code == status.HTTP_403_FORBIDDEN
        assert "chế độ chỉ đọc" in res_del_plot.json()["detail"]

        # Kiểm tra SecurityLog ghi nhận cảnh báo
        log = (
            db_session.query(SecurityLog)
            .filter(
                SecurityLog.user_email == rbac_seed["user_inspector"].email,
                SecurityLog.attempt_type == "inspector_write_violation",
            )
            .first()
        )
        assert log is not None

    # =========================================================================
    # TASK T-12: TỰ LỌC THEO ORGANIZATION_ID & AUDIT LOG AN NINH
    # =========================================================================

    def test_t12_query_level_filtering_with_tenant_query(self, db_session: Session, rbac_seed):
        """
        T-12: Viết hàm truy vấn nền tự động gắn điều kiện lọc WHERE organization_id = current_org_id
        cho các bảng nghiệp vụ (thửa đất, lô hàng đang giữ).
        """
        # Kiểm tra hàm tenant_query cho Lô hàng
        q_batches_farm = tenant_query(db_session, Batch, rbac_seed["org_farm"].id)
        batches_farm = q_batches_farm.all()
        assert len(batches_farm) == 1
        assert batches_farm[0].organization_id == rbac_seed["org_farm"].id

        # Kiểm tra hàm apply_tenant_filter cho Thửa đất
        q_plots_farm = apply_tenant_filter(db_session.query(LandPlot), LandPlot, rbac_seed["org_farm"].id)
        plots_farm = q_plots_farm.all()
        assert len(plots_farm) == 1
        assert plots_farm[0].organization_id == rbac_seed["org_farm"].id

    def test_t12_cross_tenant_direct_api_access_logged_in_audit_logs(
        self, client: TestClient, db_session: Session, rbac_seed
    ):
        """
        T-12: Nếu một tổ chức cố tình gọi thẳng API lấy hoặc thao tác trên bản ghi của tổ chức khác,
        trả về HTTP 403 Forbidden và tự động ghi một dòng vào bảng Nhật ký an ninh (Audit Logs - S-31)
        kèm địa chỉ IP, tài khoản, thời điểm và mã đối tượng.
        """
        headers_farm = get_auth_headers(
            rbac_seed["user_farm"].email,
            rbac_seed["user_farm"].role,
            rbac_seed["user_farm"].organization_id,
        )

        target_plot_id = rbac_seed["plot_unrelated"].id

        # Farm gọi thẳng API lấy thửa đất của tổ chức khác
        res = client.get(f"/api/v1/land-plots/{target_plot_id}", headers=headers_farm)
        assert res.status_code == status.HTTP_403_FORBIDDEN
        assert "Không có quyền truy cập dữ liệu thửa đất của tổ chức khác" in res.json()["detail"]

        # Kiểm tra bảng SecurityLog (Audit Logs)
        audit_log = (
            db_session.query(SecurityLog)
            .filter(
                SecurityLog.user_email == rbac_seed["user_farm"].email,
                SecurityLog.target_resource == "land_plot",
                SecurityLog.target_id == str(target_plot_id),
            )
            .first()
        )
        assert audit_log is not None
        assert audit_log.ip_address is not None
        assert audit_log.user_email == rbac_seed["user_farm"].email
        assert audit_log.created_at is not None
        assert audit_log.target_id == str(target_plot_id)
        assert audit_log.target_org_id == rbac_seed["org_unrelated"].id

    # =========================================================================
    # TASK T-54 / STORY S-23: QUY TẮC canView(org, batch) XUYÊN TỔ CHỨC
    # =========================================================================

    def test_s23_t54_rule_a_current_holder_can_view(self, db_session: Session, rbac_seed):
        """
        S-23 Điều kiện a: Tổ chức ĐƯỢC PHÉP xem nếu đang trực tiếp giữ lô đó.
        """
        farm_org_id = rbac_seed["org_farm"].id
        mother_batch = rbac_seed["batch_mother"]

        # Gọi trực tiếp hàm canView(org, batch)
        assert canView(farm_org_id, mother_batch, db_session) is True

        allowed, reason, cutoff = can_view_batch(farm_org_id, mother_batch, db_session)
        assert allowed is True
        assert reason == "CURRENT_HOLDER"
        assert cutoff is None  # Xem toàn bộ lịch sử không giới hạn

    def test_s23_t54_rule_b_ancestor_of_held_batch_can_view(
        self, client: TestClient, db_session: Session, rbac_seed
    ):
        """
        S-23 Điều kiện b: Tổ chức ĐƯỢC PHÉP xem thông tin và dòng thời gian của một lô
        nếu lô đó là TỔ TIÊN (qua các bước tách/gộp/bàn giao trước đó) của một lô mà tổ chức đang giữ
        (để nhà phân phối xem được vùng trồng và HTX sơ chế đã làm gì).
        """
        retailer_org_id = rbac_seed["org_retailer"].id
        mother_batch = rbac_seed["batch_mother"]

        # Retailer đang giữ batch_child, và batch_mother là tổ tiên của batch_child
        assert canView(retailer_org_id, mother_batch, db_session) is True

        allowed, reason, cutoff = can_view_batch(retailer_org_id, mother_batch, db_session)
        assert allowed is True
        assert reason == "ANCESTOR_OF_HELD_BATCH"
        assert cutoff is None

        # Kiểm tra qua API GET /api/v1/batches/{mother_batch_id}
        headers_retailer = get_auth_headers(
            rbac_seed["user_retailer"].email,
            rbac_seed["user_retailer"].role,
            retailer_org_id,
        )
        res = client.get(f"/api/v1/batches/{mother_batch.id}", headers=headers_retailer)
        assert res.status_code == status.HTTP_200_OK
        assert res.json()["batch_code"] == mother_batch.batch_code

    def test_s23_t54_rule_c_past_holder_limited_to_handover_timestamp(
        self, client: TestClient, db_session: Session, rbac_seed
    ):
        """
        S-23 Điều kiện c: Tổ chức từng giữ lô đó trong quá khứ ĐƯỢC PHÉP xem thông tin và dòng thời gian,
        NHƯNG CHỈ ĐƯỢC XEM LỊCH SỬ CÁC SỰ KIỆN TÍNH TỚI THỜI ĐIỂM BÀN GIAO ĐI,
        KHÔNG ĐƯỢC THẤY CÁC BƯỚC PHÁT SINH SAU KHI ĐÃ BÀN GIAO CHO BÊN KHÁC.
        """
        org_farm_id = rbac_seed["org_farm"].id
        org_retailer_id = rbac_seed["org_retailer"].id

        # Tạo một lô hàng mới được bàn giao từ Farm sang Retailer
        batch_transferred = Batch(
            batch_code="BCH-TRF-501",
            product_name="Dâu Tây Xuất Khẩu Trực Tiếp",
            organization_id=org_retailer_id,  # Hiện tại Retailer đang giữ
            initial_quantity=200.0,
            remaining_quantity=200.0,
        )
        db_session.add(batch_transferred)
        db_session.flush()

        t_base = datetime(2026, 10, 1, 8, 0, 0)
        t_handover = datetime(2026, 10, 2, 10, 0, 0)
        t_after_handover = datetime(2026, 10, 3, 14, 0, 0)

        # 1. Sự kiện khi Farm còn giữ lô (trước thời điểm bàn giao)
        event_farm = ChainEvent(
            batch_id=batch_transferred.id,
            event_type="HARVESTED",
            event_data="Thu hoạch dâu tây tại vườn Đà Lạt",
            organization_id=org_farm_id,
            previous_hash="GENESIS_HASH",
            current_hash="HASH_STEP_1",
            created_at=t_base,
        )

        # Lệnh bàn giao thành công từ Farm sang Retailer
        handover = Handover(
            batch_id=batch_transferred.id,
            from_org_id=org_farm_id,
            to_org_id=org_retailer_id,
            status=HandoverStatus.ACCEPTED.value,
            created_at=t_handover,
            updated_at=t_handover,
        )

        # Sự kiện ghi nhận việc bàn giao
        event_handover = ChainEvent(
            batch_id=batch_transferred.id,
            event_type="HANDOVER_ACCEPTED",
            event_data="Bàn giao lô sang Siêu thị BioMart",
            organization_id=org_retailer_id,
            previous_hash="HASH_STEP_1",
            current_hash="HASH_STEP_2",
            created_at=t_handover,
        )

        # 2. Sự kiện phát sinh sau khi đã bàn giao sang Retailer (trưng bày bán hàng)
        event_retailer_shelf = ChainEvent(
            batch_id=batch_transferred.id,
            event_type="SHELF_DISPLAY",
            event_data="Trưng bày tại kệ siêu thị tầng 2 BioMart",
            organization_id=org_retailer_id,
            previous_hash="HASH_STEP_2",
            current_hash="HASH_STEP_3",
            created_at=t_after_handover,
        )

        db_session.add_all([event_farm, handover, event_handover, event_retailer_shelf])
        db_session.commit()

        # Kiểm tra hàm canView(Farm, batch_transferred)
        assert canView(org_farm_id, batch_transferred, db_session) is True
        allowed, reason, cutoff = can_view_batch(org_farm_id, batch_transferred, db_session)
        assert allowed is True
        assert reason == "PAST_HOLDER"
        assert cutoff == t_handover

        # Farm gọi API lấy chain-events: Chỉ thấy các sự kiện tính tới thời điểm bàn giao đi
        headers_farm = get_auth_headers(
            rbac_seed["user_farm"].email,
            rbac_seed["user_farm"].role,
            org_farm_id,
        )
        res_farm_events = client.get(
            f"/api/v1/handovers/batches/{batch_transferred.id}/chain-events",
            headers=headers_farm,
        )
        assert res_farm_events.status_code == status.HTTP_200_OK
        farm_events_data = res_farm_events.json()

        # Farm chỉ thấy 2 sự kiện: HARVESTED và HANDOVER_ACCEPTED (<= t_handover)
        assert len(farm_events_data) == 2
        event_types_farm = {e["event_type"] for e in farm_events_data}
        assert "HARVESTED" in event_types_farm
        assert "HANDOVER_ACCEPTED" in event_types_farm
        # TUYỆT ĐỐI KHÔNG THẤY sự kiện SHELF_DISPLAY sau khi đã bàn giao
        assert "SHELF_DISPLAY" not in event_types_farm

        # Kiểm tra trực tiếp hàm get_viewable_chain_events
        farm_service_events = get_viewable_chain_events(batch_transferred.id, org_farm_id, db_session)
        assert len(farm_service_events) == 2
        assert {e.event_type for e in farm_service_events} == {"HARVESTED", "HANDOVER_ACCEPTED"}

        # Trong khi đó, Retailer (bên hiện tại đang giữ) gọi API thì thấy ĐỦ TẤT CẢ 3 SỰ KIỆN
        headers_retailer = get_auth_headers(
            rbac_seed["user_retailer"].email,
            rbac_seed["user_retailer"].role,
            org_retailer_id,
        )
        res_ret_events = client.get(
            f"/api/v1/handovers/batches/{batch_transferred.id}/chain-events",
            headers=headers_retailer,
        )
        assert res_ret_events.status_code == status.HTTP_200_OK
        ret_events_data = res_ret_events.json()
        assert len(ret_events_data) == 3
        event_types_ret = {e["event_type"] for e in ret_events_data}
        assert "SHELF_DISPLAY" in event_types_ret

    def test_s23_t54_unrelated_organization_batch_access_forbidden_403(
        self, client: TestClient, db_session: Session, rbac_seed
    ):
        """
        S-23: Nếu gọi API xem một lô khác của tổ chức đối tác mà KHÔNG liên quan phả hệ tới lô mình đang giữ
        -> trả về HTTP 403 Forbidden và ghi nhật ký an ninh.
        """
        org_unrelated_id = rbac_seed["org_unrelated"].id
        mother_batch = rbac_seed["batch_mother"]

        # Tổ chức không liên quan kiểm tra canView -> False
        assert canView(org_unrelated_id, mother_batch, db_session) is False

        headers_unrelated = get_auth_headers(
            rbac_seed["user_unrelated"].email,
            rbac_seed["user_unrelated"].role,
            org_unrelated_id,
        )

        # 1. Gọi API xem chi tiết lô -> 403 Forbidden
        res_batch = client.get(f"/api/v1/batches/{mother_batch.id}", headers=headers_unrelated)
        assert res_batch.status_code == status.HTTP_403_FORBIDDEN
        assert "Không có quyền truy cập dữ liệu của tổ chức khác" in res_batch.json()["detail"]

        # 2. Gọi API xem dòng thời gian / chuỗi sự kiện -> 403 Forbidden
        res_events = client.get(
            f"/api/v1/handovers/batches/{mother_batch.id}/chain-events",
            headers=headers_unrelated,
        )
        assert res_events.status_code == status.HTTP_403_FORBIDDEN
        assert "Không có quyền truy cập dữ liệu của tổ chức khác" in res_events.json()["detail"]

        # Kiểm tra ghi nhận vào SecurityLog
        log = (
            db_session.query(SecurityLog)
            .filter(
                SecurityLog.user_email == rbac_seed["user_unrelated"].email,
                SecurityLog.attempt_type == "cross_tenant_access_denied",
                SecurityLog.target_id == str(mother_batch.id),
            )
            .first()
        )
        assert log is not None
        assert log.target_org_id == rbac_seed["org_farm"].id

    def test_s23_t54_can_view_with_organization_instance_and_multi_generation_lineage(
        self, db_session: Session, rbac_seed
    ):
        """
        S-23/T-54: Kiểm tra canView(org, batch) hoạt động chính xác khi:
        1. org được truyền dưới dạng đối tượng Organization (thay vì chỉ int ID).
        2. Phả hệ đa thế hệ (3 thế hệ): G1 (Farm) -> G2 (Coop) -> G3 (Retailer).
           Retailer đang giữ G3 thì được phép xem cả G1 và G2 (xuyên suốt chuỗi cung ứng).
        """
        org_farm = rbac_seed["org_farm"]
        org_coop = rbac_seed["org_coop"]
        org_retailer = rbac_seed["org_retailer"]
        org_unrelated = rbac_seed["org_unrelated"]

        # Thế hệ 1: Lô G1 tại Farm
        batch_g1 = Batch(
            batch_code="BCH-GEN1-FARM",
            product_name="Dâu Tây Hữu Cơ Cấp 1",
            organization_id=org_farm.id,
            initial_quantity=500.0,
            remaining_quantity=0.0,
        )
        db_session.add(batch_g1)
        db_session.flush()

        # Thế hệ 2: Lô G2 tại Coop (sau khi tách từ G1)
        batch_g2 = Batch(
            batch_code="BCH-GEN2-COOP",
            product_name="Dâu Tây Đóng Khay 1kg Cấp 2",
            organization_id=org_coop.id,
            initial_quantity=300.0,
            remaining_quantity=0.0,
        )
        db_session.add(batch_g2)
        db_session.flush()

        rel_g1_g2 = BatchRelation(
            parent_batch_id=batch_g1.id,
            child_batch_id=batch_g2.id,
            relation_type=BatchRelationType.SPLIT.value,
            quantity=300.0,
        )
        db_session.add(rel_g1_g2)

        # Thế hệ 3: Lô G3 tại Retailer (sau khi tách từ G2 sang siêu thị)
        batch_g3 = Batch(
            batch_code="BCH-GEN3-RETAILER",
            product_name="Dâu Tây Hộp Quà Tặng BioMart Cấp 3",
            organization_id=org_retailer.id,
            initial_quantity=150.0,
            remaining_quantity=150.0,
        )
        db_session.add(batch_g3)
        db_session.flush()

        rel_g2_g3 = BatchRelation(
            parent_batch_id=batch_g2.id,
            child_batch_id=batch_g3.id,
            relation_type=BatchRelationType.SPLIT.value,
            quantity=150.0,
        )
        db_session.add(rel_g2_g3)
        db_session.commit()

        # 1. Retailer (đang giữ G3) kiểm tra canView bằng đối tượng Organization
        assert canView(org_retailer, batch_g3, db_session) is True  # Điều kiện a: đang giữ
        assert canView(org_retailer, batch_g2, db_session) is True  # Điều kiện b: tổ tiên trực tiếp
        assert canView(org_retailer, batch_g1, db_session) is True  # Điều kiện b: tổ tiên gián tiếp (ông bà)

        # 2. Truyền int ID cũng hoạt động nhất quán
        assert canView(org_retailer.id, batch_g1.id, db_session) is True
        assert canView(org_retailer.id, batch_g2.id, db_session) is True

        # 3. Tổ chức không liên quan hoàn toàn không được xem bất kỳ thế hệ nào
        assert canView(org_unrelated, batch_g1, db_session) is False
        assert canView(org_unrelated, batch_g2, db_session) is False
        assert canView(org_unrelated, batch_g3, db_session) is False

    def test_t12_cross_tenant_handover_creation_blocked_and_logged(
        self, client: TestClient, db_session: Session, rbac_seed
    ):
        """
        T-12: Nếu một tổ chức cố tình gọi API tạo bàn giao cho lô hàng thuộc quyền sở hữu của tổ chức khác
        -> Trả về HTTP 403 Forbidden và tự động ghi nhật ký an ninh SecurityLog.
        """
        # User Retailer cố tình tạo lệnh bàn giao cho lô của Farm
        headers_retailer = get_auth_headers(
            rbac_seed["user_retailer"].email,
            rbac_seed["user_retailer"].role,
            rbac_seed["org_retailer"].id,
        )
        target_mother_batch = rbac_seed["batch_mother"]

        res = client.post(
            "/api/v1/handovers",
            json={
                "batch_id": target_mother_batch.id,
                "to_org_id": rbac_seed["org_coop"].id,
            },
            headers=headers_retailer,
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN
        assert "Bạn không có quyền bàn giao lô hàng của tổ chức khác" in res.json()["detail"]

        # Kiểm tra ghi nhận vào SecurityLog
        audit_log = (
            db_session.query(SecurityLog)
            .filter(
                SecurityLog.user_email == rbac_seed["user_retailer"].email,
                SecurityLog.target_resource == "batch",
                SecurityLog.target_id == str(target_mother_batch.id),
                SecurityLog.endpoint == "/api/v1/handovers",
            )
            .first()
        )
        assert audit_log is not None
        assert audit_log.attempt_type == "cross_tenant_access_denied"
        assert audit_log.target_org_id == rbac_seed["org_farm"].id
        assert audit_log.ip_address is not None
