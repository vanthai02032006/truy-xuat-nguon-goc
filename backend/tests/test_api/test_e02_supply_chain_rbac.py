from __future__ import annotations

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models.batch import Batch
from app.models.organization import Organization
from app.models.security_log import SecurityLog
from app.models.user import SUPPLY_CHAIN_ROLES, User, UserRole


def get_auth_headers(user_email: str, role: str, org_id: int | None) -> dict[str, str]:
    """Tạo header Authorization Bearer token phục vụ kiểm thử."""
    token = create_access_token(subject=user_email, role=role, organization_id=org_id)
    return {"Authorization": f"Bearer {token}"}


class TestEpicE02SupplyChainRBAC:
    """
    Bộ kiểm thử tự động cho Backlog Epic E-02:
    'Hệ sinh thái phân quyền chuỗi cung ứng đa tổ chức (Multi-tenant RBAC)'
    1. Hệ sinh thái gồm 7 vai trò thuộc các tổ chức độc lập trong chuỗi cung ứng.
    2. Middleware cô lập dữ liệu theo Organization ID: mỗi tổ chức chỉ xem và thao tác
       trên các lô hàng thuộc quyền quản lý của mình (lọc ở tầng truy vấn DB).
       Cố tình gọi API lấy lô của tổ chức khác phải trả về HTTP 403 Forbidden và ghi log an ninh.
    3. Vai trò 'Cán bộ kiểm tra' (Inspector) có quyền tra cứu lô trên mọi tổ chức nhưng CHỈ Ở CHẾ ĐỘ READ-ONLY.
    4. Người tiêu dùng (Consumer) tra cứu công khai không cần đăng nhập.
    """

    @pytest.fixture
    def supply_chain_seed(self, db_session: Session):
        """Khởi tạo 4 tổ chức độc lập trong chuỗi cung ứng và các tài khoản tương ứng."""
        # 1. Bốn tổ chức độc lập thuộc chuỗi cung ứng
        org_farm = Organization(
            id=10, name="Vùng Trồng Nông Trại Xanh", code="FARM-NTX"
        )
        org_coop = Organization(id=20, name="HTX Sơ Chế Bảo Lộc", code="COOP-BL")
        org_logistics = Organization(
            id=30, name="Công Ty Vận Tải Lạnh Express", code="LOG-EXP"
        )
        org_retailer = Organization(
            id=40, name="Hệ Thống Bán Lẻ BioMart", code="RET-BIO"
        )
        db_session.add_all([org_farm, org_coop, org_logistics, org_retailer])
        db_session.flush()

        # 2. Người dùng đại diện cho 7 vai trò chuỗi cung ứng
        user_farm = User(
            id=101,
            email="manager@nongtraixanh.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Nguyễn Văn Nông (Vùng trồng)",
            role=UserRole.FARM.value,
            organization_id=org_farm.id,
            is_active=True,
        )
        user_coop = User(
            id=102,
            email="operator@sochebaoloc.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Trần Thị Sơ Chế (HTX Sơ chế)",
            role=UserRole.PROCESSING.value,
            organization_id=org_coop.id,
            is_active=True,
        )
        user_logistics = User(
            id=103,
            email="driver@coldexpress.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Lê Vận Tải (Đơn vị vận chuyển lạnh)",
            role=UserRole.LOGISTICS.value,
            organization_id=org_logistics.id,
            is_active=True,
        )
        user_retailer = User(
            id=104,
            email="store@biomart.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Phạm Bán Lẻ (Nhà phân phối / Bán lẻ)",
            role=UserRole.RETAILER.value,
            organization_id=org_retailer.id,
            is_active=True,
        )
        user_inspector = User(
            id=105,
            email="inspector.safe@kiemdinh.gov.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Đoàn Thanh Tra Chất Lượng (Cán bộ kiểm tra)",
            role=UserRole.INSPECTOR.value,
            organization_id=None,  # Cán bộ kiểm tra độc lập, không thuộc tổ chức nào
            is_active=True,
        )
        user_sysadmin = User(
            id=106,
            email="sysadmin@nongsanlanh.gov.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Quản Trị Hệ Thống Toàn Nền Tảng",
            role=UserRole.SYSTEM_ADMIN.value,
            organization_id=None,
            is_active=True,
        )

        db_session.add_all(
            [
                user_farm,
                user_coop,
                user_logistics,
                user_retailer,
                user_inspector,
                user_sysadmin,
            ]
        )
        db_session.flush()

        # 3. Các lô hàng thuộc quyền quản lý của từng tổ chức
        batch_farm_1 = Batch(
            id=101,
            batch_code="BCH-FRM1-01",
            product_name="Cà chua Beef Đà Lạt",
            organization_id=org_farm.id,
        )
        batch_farm_2 = Batch(
            id=102,
            batch_code="BCH-FRM1-02",
            product_name="Ớt chuông Sweet Pepper",
            organization_id=org_farm.id,
        )
        batch_coop_1 = Batch(
            id=103,
            batch_code="BCH-COP2-01",
            product_name="Dâu tây sơ chế đóng hộp",
            organization_id=org_coop.id,
        )
        batch_logistics_1 = Batch(
            id=104,
            batch_code="BCH-LOG3-01",
            product_name="Lô nông sản vận chuyển container #8",
            organization_id=org_logistics.id,
        )
        batch_retailer_1 = Batch(
            id=105,
            batch_code="BCH-RET4-01",
            product_name="Xà lách thủy canh quầy siêu thị",
            organization_id=org_retailer.id,
        )

        db_session.add_all(
            [
                batch_farm_1,
                batch_farm_2,
                batch_coop_1,
                batch_logistics_1,
                batch_retailer_1,
            ]
        )
        db_session.commit()

        return {
            "org_farm": org_farm,
            "org_coop": org_coop,
            "org_logistics": org_logistics,
            "org_retailer": org_retailer,
            "user_farm": user_farm,
            "user_coop": user_coop,
            "user_logistics": user_logistics,
            "user_retailer": user_retailer,
            "user_inspector": user_inspector,
            "user_sysadmin": user_sysadmin,
            "batch_farm_1": batch_farm_1,
            "batch_farm_2": batch_farm_2,
            "batch_coop_1": batch_coop_1,
            "batch_logistics_1": batch_logistics_1,
            "batch_retailer_1": batch_retailer_1,
        }

    # =========================================================================
    # YÊU CẦU 1: HỆ SINH THÁI GỒM 7 VAI TRÒ CHUỖI CUNG ỨNG ĐỘC LẬP
    # =========================================================================

    def test_e02_all_seven_supply_chain_roles_are_supported(self):
        """Kiểm tra hệ thống hỗ trợ đầy đủ các vai trò chuỗi cung ứng theo Epic E-02."""
        expected_roles = {
            "farm",  # 1. Vùng trồng (Farm)
            "coop",  # 2. Hợp tác xã sơ chế (Co-op)
            "logistics",  # 3. Đơn vị vận chuyển lạnh (Logistics / Cold Chain Transporter)
            "distributor",  # 4. Nhà phân phối / Bán lẻ (Distributor / Retailer)
            "inspector",  # 5. Cán bộ kiểm tra (Inspector)
            "system_admin",  # 6. Quản trị hệ thống (System Admin)
            "consumer",  # 7. Người tiêu dùng (Consumer - không cần đăng nhập)
        }
        assert expected_roles.issubset(SUPPLY_CHAIN_ROLES)
        assert UserRole.FARM.value == "farm"
        assert UserRole.COOP.value == "coop"
        assert UserRole.LOGISTICS.value == "logistics"
        assert UserRole.DISTRIBUTOR.value == "distributor"
        assert UserRole.INSPECTOR.value == "inspector"
        assert UserRole.SYSTEM_ADMIN.value == "system_admin"
        assert UserRole.CONSUMER.value == "consumer"

    # =========================================================================
    # YÊU CẦU 2: CÔ LẬP DỮ LIỆU THEO ORGANIZATION ID (TẦNG DB QUERY)
    # =========================================================================

    def test_e02_organization_only_sees_own_batches_filtered_at_db_query(
        self, client: TestClient, supply_chain_seed
    ):
        """
        Mỗi tổ chức chỉ xem danh sách các lô hàng đang thuộc quyền quản lý của mình.
        Bộ lọc được thực thi ở tầng DB query (SQL WHERE clause), không lọc ở giao diện.
        """
        # 1. Vùng trồng (Org 10): Phải thấy đúng 2 lô của mình, không thấy của Sơ chế, Vận chuyển, Bán lẻ
        headers_farm = get_auth_headers(
            supply_chain_seed["user_farm"].email,
            supply_chain_seed["user_farm"].role,
            supply_chain_seed["user_farm"].organization_id,
        )
        res_farm = client.get("/api/v1/batches", headers=headers_farm)
        assert res_farm.status_code == status.HTTP_200_OK
        data_farm = res_farm.json()
        assert len(data_farm) == 2
        farm_codes = {b["batch_code"] for b in data_farm}
        assert "BCH-FRM1-01" in farm_codes
        assert "BCH-FRM1-02" in farm_codes
        assert "BCH-COP2-01" not in farm_codes
        assert "BCH-LOG3-01" not in farm_codes
        assert "BCH-RET4-01" not in farm_codes

        # 2. Hợp tác xã sơ chế (Org 20): Chỉ thấy đúng lô của Org 20
        headers_coop = get_auth_headers(
            supply_chain_seed["user_coop"].email,
            supply_chain_seed["user_coop"].role,
            supply_chain_seed["user_coop"].organization_id,
        )
        res_coop = client.get("/api/v1/batches", headers=headers_coop)
        assert res_coop.status_code == status.HTTP_200_OK
        data_coop = res_coop.json()
        assert len(data_coop) == 1
        assert data_coop[0]["batch_code"] == "BCH-COP2-01"
        assert data_coop[0]["organization_id"] == 20

        # 3. Đơn vị vận chuyển lạnh (Org 30): Chỉ thấy lô của Org 30
        headers_log = get_auth_headers(
            supply_chain_seed["user_logistics"].email,
            supply_chain_seed["user_logistics"].role,
            supply_chain_seed["user_logistics"].organization_id,
        )
        res_log = client.get("/api/v1/batches", headers=headers_log)
        assert res_log.status_code == status.HTTP_200_OK
        data_log = res_log.json()
        assert len(data_log) == 1
        assert data_log[0]["batch_code"] == "BCH-LOG3-01"
        assert data_log[0]["organization_id"] == 30

        # 4. Nhà phân phối / Bán lẻ (Org 40): Chỉ thấy lô của Org 40
        headers_ret = get_auth_headers(
            supply_chain_seed["user_retailer"].email,
            supply_chain_seed["user_retailer"].role,
            supply_chain_seed["user_retailer"].organization_id,
        )
        res_ret = client.get("/api/v1/batches", headers=headers_ret)
        assert res_ret.status_code == status.HTTP_200_OK
        data_ret = res_ret.json()
        assert len(data_ret) == 1
        assert data_ret[0]["batch_code"] == "BCH-RET4-01"
        assert data_ret[0]["organization_id"] == 40

    def test_e02_cross_organization_access_attempt_returns_403_and_logs_security(
        self, client: TestClient, db_session: Session, supply_chain_seed
    ):
        """
        Cố tình gọi API lấy lô của tổ chức khác phải trả về HTTP 403 Forbidden
        và ghi nhận ngay vào bảng SecurityLog (nhật ký an ninh).
        """
        # User Vùng trồng (Org 10) cố tình truy cập lô #103 của HTX Sơ chế (Org 20)
        headers_farm = get_auth_headers(
            supply_chain_seed["user_farm"].email,
            supply_chain_seed["user_farm"].role,
            supply_chain_seed["user_farm"].organization_id,
        )
        target_batch_id = supply_chain_seed["batch_coop_1"].id

        res = client.get(f"/api/v1/batches/{target_batch_id}", headers=headers_farm)
        assert res.status_code == status.HTTP_403_FORBIDDEN
        assert (
            "Không có quyền truy cập dữ liệu của tổ chức khác" in res.json()["detail"]
        )

        # Kiểm tra bảng SecurityLog xem đã ghi nhận vi phạm an ninh chưa
        sec_log = (
            db_session.query(SecurityLog)
            .filter(
                SecurityLog.user_email == supply_chain_seed["user_farm"].email,
                SecurityLog.attempt_type == "cross_tenant_access_denied",
                SecurityLog.target_resource == "batch",
                SecurityLog.target_id == str(target_batch_id),
            )
            .first()
        )
        assert sec_log is not None
        assert sec_log.target_org_id == 20
        assert f"/api/v1/batches/{target_batch_id}" in sec_log.endpoint
        assert sec_log.method == "GET"

        # Tương tự: Nhà phân phối (Org 40) cố tình xóa lô của Vùng trồng (Org 10)
        headers_ret = get_auth_headers(
            supply_chain_seed["user_retailer"].email,
            supply_chain_seed["user_retailer"].role,
            supply_chain_seed["user_retailer"].organization_id,
        )
        target_farm_batch_id = supply_chain_seed["batch_farm_1"].id
        res_del = client.delete(
            f"/api/v1/batches/{target_farm_batch_id}", headers=headers_ret
        )
        assert res_del.status_code == status.HTTP_403_FORBIDDEN

        del_log = (
            db_session.query(SecurityLog)
            .filter(
                SecurityLog.user_email == supply_chain_seed["user_retailer"].email,
                SecurityLog.attempt_type == "cross_tenant_access_denied",
                SecurityLog.target_id == str(target_farm_batch_id),
            )
            .first()
        )
        assert del_log is not None

    # =========================================================================
    # YÊU CẦU 3: CÁN BỘ KIỂM TRA (INSPECTOR) - READ-ONLY TOÀN CHUỖI
    # =========================================================================

    def test_e02_inspector_can_query_batches_across_all_organizations(
        self, client: TestClient, supply_chain_seed
    ):
        """
        Cán bộ kiểm tra (Inspector) có quyền tra cứu lô trên mọi tổ chức độc lập.
        """
        headers_inspector = get_auth_headers(
            supply_chain_seed["user_inspector"].email,
            supply_chain_seed["user_inspector"].role,
            supply_chain_seed["user_inspector"].organization_id,
        )

        # 1. Cán bộ kiểm tra xem danh sách: Thấy đủ toàn bộ các lô của tất cả tổ chức (5 lô)
        res_list = client.get("/api/v1/batches", headers=headers_inspector)
        assert res_list.status_code == status.HTTP_200_OK
        all_batches = res_list.json()
        assert len(all_batches) == 5

        # 2. Cán bộ kiểm tra xem chi tiết từng lô của từng tổ chức khác nhau: Đều 200 OK
        # Xem lô của Vùng trồng (Org 10)
        res_b1 = client.get(
            f"/api/v1/batches/{supply_chain_seed['batch_farm_1'].id}",
            headers=headers_inspector,
        )
        assert res_b1.status_code == status.HTTP_200_OK
        assert res_b1.json()["batch_code"] == "BCH-FRM1-01"

        # Xem lô của HTX Sơ chế (Org 20)
        res_b2 = client.get(
            f"/api/v1/batches/{supply_chain_seed['batch_coop_1'].id}",
            headers=headers_inspector,
        )
        assert res_b2.status_code == status.HTTP_200_OK
        assert res_b2.json()["batch_code"] == "BCH-COP2-01"

        # Xem lô của Đơn vị vận chuyển (Org 30)
        res_b3 = client.get(
            f"/api/v1/batches/{supply_chain_seed['batch_logistics_1'].id}",
            headers=headers_inspector,
        )
        assert res_b3.status_code == status.HTTP_200_OK
        assert res_b3.json()["batch_code"] == "BCH-LOG3-01"

        # Xem lô của Bán lẻ (Org 40)
        res_b4 = client.get(
            f"/api/v1/batches/{supply_chain_seed['batch_retailer_1'].id}",
            headers=headers_inspector,
        )
        assert res_b4.status_code == status.HTTP_200_OK
        assert res_b4.json()["batch_code"] == "BCH-RET4-01"

    def test_e02_inspector_is_strictly_read_only_and_forbidden_on_write_operations(
        self, client: TestClient, db_session: Session, supply_chain_seed
    ):
        """
        Cán bộ kiểm tra CHỈ CÓ QUYỀN READ-ONLY.
        Cố tình thực hiện thao tác ghi/tạo/xóa (POST, DELETE) phải bị HTTP 403 Forbidden
        và ghi nhận log an ninh cảnh báo inspector_write_violation.
        """
        headers_inspector = get_auth_headers(
            supply_chain_seed["user_inspector"].email,
            supply_chain_seed["user_inspector"].role,
            supply_chain_seed["user_inspector"].organization_id,
        )

        # 1. Cố tình tạo mới lô hàng (POST /api/v1/batches) -> Bị 403 Forbidden
        res_create = client.post(
            "/api/v1/batches",
            headers=headers_inspector,
            json={
                "batch_code": "INSP-TEST-99",
                "product_name": "Lô thử nghiệm thanh tra",
            },
        )
        assert res_create.status_code == status.HTTP_403_FORBIDDEN
        assert "chế độ chỉ đọc" in res_create.json()["detail"]

        # Kiểm tra SecurityLog đã ghi nhận cố tình tạo mới
        create_log = (
            db_session.query(SecurityLog)
            .filter(
                SecurityLog.user_email == supply_chain_seed["user_inspector"].email,
                SecurityLog.attempt_type == "inspector_write_violation",
            )
            .first()
        )
        assert create_log is not None
        assert "chỉ được phép đọc" in create_log.description

        # 2. Cố tình xóa lô hàng (DELETE /api/v1/batches/{id}) -> Bị 403 Forbidden
        target_batch_id = supply_chain_seed["batch_farm_1"].id
        res_del = client.delete(
            f"/api/v1/batches/{target_batch_id}", headers=headers_inspector
        )
        assert res_del.status_code == status.HTTP_403_FORBIDDEN
        assert "chế độ chỉ đọc" in res_del.json()["detail"]

        # 3. Cố tình thêm nhật ký vật tư vào lô (POST /api/v1/batches/{id}/materials) -> Bị 403
        res_mat = client.post(
            f"/api/v1/batches/{target_batch_id}/materials",
            headers=headers_inspector,
            json={
                "material_name": "Thuốc BVTV kiểm tra",
                "category": "pesticide",
                "dosage": "10ml",
                "applied_date": "2026-10-20",
                "isolation_days": 7,
            },
        )
        assert res_mat.status_code == status.HTTP_403_FORBIDDEN
        assert "chế độ chỉ đọc" in res_mat.json()["detail"]

    # =========================================================================
    # YÊU CẦU 4: NGƯỜI TIÊU DÙNG (CONSUMER) - TRA CỨU CÔNG KHAI KHÔNG CẦN LOGIN
    # =========================================================================

    def test_e02_consumer_can_query_public_batch_trace_without_login(
        self, client: TestClient, supply_chain_seed
    ):
        """
        Người tiêu dùng (Consumer) tra cứu công khai không cần đăng nhập.
        Đảm bảo không bị lộ dữ liệu nhạy cảm nội bộ theo S-48.
        """
        batch_code = supply_chain_seed["batch_farm_1"].batch_code

        # Gọi API công khai hoàn toàn không có header Authorization
        res_public = client.get(f"/api/v1/batches/public/{batch_code}")
        assert res_public.status_code == status.HTTP_200_OK
        data = res_public.json()

        assert data["batch_code"] == batch_code
        assert data["product_name"] == "Cà chua Beef Đà Lạt"
        assert "journey_milestones" in data
        assert len(data["journey_milestones"]) > 0

        # Tuyệt đối không để lộ dữ liệu nội bộ
        assert "revenue" not in data
        assert "price" not in data
        assert "quantity" not in data
        assert "organization_id" not in data

        # Nhưng nếu người chưa đăng nhập cố gọi API nội bộ -> Phải bị 401 Unauthorized
        res_private = client.get("/api/v1/batches")
        assert res_private.status_code == status.HTTP_401_UNAUTHORIZED
