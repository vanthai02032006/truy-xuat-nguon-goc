from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.models.land_plot import LandPlot
from app.models.organization import Organization
from app.models.user import STANDARDIZED_ROLES, SUPPLY_CHAIN_ROLES, User, UserRole


def get_auth_headers(email: str, role: str, org_id: int | None = None) -> dict[str, str]:
    token = create_access_token(subject=email, role=role, organization_id=org_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_setup(db_session):
    # 1. Tạo 4 tổ chức đại diện cho chuỗi cung ứng
    org_farm = Organization(id=10, name="HTX Nông Nghiệp Thắng Lợi", code="FARM-TL")
    org_coop = Organization(id=20, name="HTX Sơ Chế Bảo Lộc", code="COOP-BL")
    org_log = Organization(id=30, name="Công Ty Vận Tải Lạnh Express", code="LOG-EXP")
    org_dist = Organization(id=40, name="Hệ Thống Bán Lẻ BioMart", code="RET-BIO")
    db_session.add_all([org_farm, org_coop, org_log, org_dist])
    db_session.flush()

    # 2. Tạo người dùng chuẩn hóa cho 6 vai trò
    user_farm = User(
        id=201,
        email="manager@nongtraixanh.vn",
        hashed_password=get_password_hash("pass123"),
        full_name="Nguyễn Văn Nông (Vùng trồng)",
        role=UserRole.FARM.value,
        organization_id=org_farm.id,
        is_active=True,
    )
    user_coop = User(
        id=202,
        email="operator@sochebaoloc.vn",
        hashed_password=get_password_hash("pass123"),
        full_name="Trần Thị Sơ Chế (HTX Sơ chế)",
        role=UserRole.COOP.value,
        organization_id=org_coop.id,
        is_active=True,
    )
    user_logistics = User(
        id=203,
        email="driver@coldexpress.vn",
        hashed_password=get_password_hash("pass123"),
        full_name="Lê Vận Tải (Vận chuyển lạnh)",
        role=UserRole.LOGISTICS.value,
        organization_id=org_log.id,
        is_active=True,
    )
    user_distributor = User(
        id=204,
        email="store@biomart.vn",
        hashed_password=get_password_hash("pass123"),
        full_name="Phạm Bán Lẻ (Nhà phân phối / Bán lẻ)",
        role=UserRole.DISTRIBUTOR.value,
        organization_id=org_dist.id,
        is_active=True,
    )
    user_inspector = User(
        id=205,
        email="inspector.safe@kiemdinh.gov.vn",
        hashed_password=get_password_hash("pass123"),
        full_name="Đoàn Thanh Tra (Cán bộ kiểm tra)",
        role=UserRole.INSPECTOR.value,
        organization_id=None,
        is_active=True,
    )
    user_sysadmin = User(
        id=206,
        email="sysadmin@nongsanlanh.gov.vn",
        hashed_password=get_password_hash("pass123"),
        full_name="Quản Trị Hệ Thống",
        role=UserRole.SYSTEM_ADMIN.value,
        organization_id=None,
        is_active=True,
    )
    db_session.add_all([
        user_farm,
        user_coop,
        user_logistics,
        user_distributor,
        user_inspector,
        user_sysadmin,
    ])

    # 3. Thửa đất mẫu thuộc org 10
    plot_10 = LandPlot(
        id=21,
        name="Thửa Thử Nghiệm Chuẩn Hóa",
        area=3500.0,
        unit="m2",
        latitude=11.94,
        longitude=108.45,
        organization_id=org_farm.id,
    )
    db_session.add(plot_10)
    db_session.commit()

    return {
        "org_farm": org_farm,
        "org_coop": org_coop,
        "org_log": org_log,
        "org_dist": org_dist,
        "user_farm": user_farm,
        "user_coop": user_coop,
        "user_logistics": user_logistics,
        "user_distributor": user_distributor,
        "user_inspector": user_inspector,
        "user_sysadmin": user_sysadmin,
        "plot_10": plot_10,
    }


class TestRoleStandardizationAndAccessMatrix:
    """Kiểm thử toàn diện việc chuẩn hóa vai trò và ma trận phân quyền."""

    def test_standardized_role_constants(self):
        """Hệ thống chuẩn hóa 6 hằng số vai trò duy nhất."""
        assert UserRole.FARM.value == "farm"
        assert UserRole.COOP.value == "coop"
        assert UserRole.LOGISTICS.value == "logistics"
        assert UserRole.DISTRIBUTOR.value == "distributor"
        assert UserRole.INSPECTOR.value == "inspector"
        assert UserRole.SYSTEM_ADMIN.value == "system_admin"

        for role_name in ["farm", "coop", "logistics", "distributor", "inspector", "system_admin"]:
            assert role_name in STANDARDIZED_ROLES
            assert role_name in SUPPLY_CHAIN_ROLES

    def test_quick_role_token_endpoint_aliases(self, client: TestClient, test_setup, monkeypatch):
        """
        Bảo mật P0:
        1. Người chưa đăng nhập bị từ chối 401 Unauthorized.
        2. Khi đã đăng nhập và bật cờ demo ở development, cấp token cho các vai trò chuẩn hóa và alias (trừ admin).
        3. Tuyệt đối không cấp quyền admin/system_admin qua endpoint demo (403 Forbidden).
        """
        from app.core.config import settings

        # 1. Chưa đăng nhập -> 401
        res_unauth = client.post("/api/v1/auth/quick-role-token?role=farm")
        assert res_unauth.status_code == 401

        # Cấu hình môi trường development + ENABLE_DEMO_ROLE_SWITCH=True
        monkeypatch.setattr(settings, "APP_ENV", "development")
        monkeypatch.setattr(settings, "ENABLE_DEMO_ROLE_SWITCH", True)

        farm_user = test_setup["user_farm"]
        farm_headers = get_auth_headers(farm_user.email, farm_user.role, farm_user.organization_id)

        roles_to_test = [
            ("farm", "farm"),
            ("coop", "coop"),
            ("processing", "coop"),
            ("logistics", "logistics"),
            ("distributor", "distributor"),
            ("retailer", "distributor"),
            ("inspector", "inspector"),
        ]
        for role_input, expected_role in roles_to_test:
            res = client.post(f"/api/v1/auth/quick-role-token?role={role_input}", headers=farm_headers)
            assert res.status_code == 200, f"Thất bại với vai trò: {role_input} - {res.text}"
            data = res.json()
            assert data["role"] == expected_role, f"Mong đợi {expected_role}, nhận {data['role']}"
            assert "access_token" in data

        # 2. Không cho phép cấp quyền quản trị qua endpoint demo
        for admin_alias in ["system_admin", "admin", "quan_tri"]:
            res_admin = client.post(f"/api/v1/auth/quick-role-token?role={admin_alias}", headers=farm_headers)
            assert res_admin.status_code == 403, f"Endpoint demo không được phép cấp quyền quản trị {admin_alias}"


    def test_system_admin_full_administrative_access(self, client: TestClient, test_setup):
        """system_admin truy cập được Nhật ký an ninh (S-31), Sản phẩm (S-07), Thửa đất, Vật tư, Canh tác, Tài chính."""
        sysadmin = test_setup["user_sysadmin"]
        headers = get_auth_headers(sysadmin.email, sysadmin.role, sysadmin.organization_id)

        # 1. Nhật ký bảo mật / an ninh (S-31): system_admin truy cập được
        res_audit = client.get("/api/v1/audit/security-logs", headers=headers)
        assert res_audit.status_code == 200, f"Audit logs failed: {res_audit.text}"

        # 2. Danh mục sản phẩm (S-07): Tạo và xem
        prod_res = client.post(
            "/api/v1/products",
            headers=headers,
            json={
                "name": "Nho Xanh Chuẩn Hóa Test",
                "unit": "kg",
                "description": "Sản phẩm test cho system_admin",
            },
        )
        assert prod_res.status_code in [201, 400]  # 201 Created hoặc 400 nếu trùng tên

        # 3. Quản trị thửa đất: xem được tất cả thửa đất mà không bị 403
        plot_res = client.get("/api/v1/land-plots", headers=headers)
        assert plot_res.status_code == 200
        assert len(plot_res.json()) >= 1

        # 4. Quản trị vật tư nông trại: không bị 403
        mat_res = client.get("/api/v1/materials", headers=headers)
        assert mat_res.status_code == 200

        # 5. Nhật ký canh tác: không bị 403
        farm_res = client.get("/api/v1/farming/logs", headers=headers)
        assert farm_res.status_code == 200

        # 6. Tài chính / P&L summary: không bị 403
        fin_res = client.get("/api/v1/finance/summary", headers=headers)
        assert fin_res.status_code == 200

    def test_inspector_is_strictly_read_only_and_cannot_view_security_logs(
        self, client: TestClient, test_setup
    ):
        """inspector CHỈ ĐỌC dữ liệu, BỊ CHẶN 403 ở Audit Logs và mọi thao tác ghi/sửa/xóa."""
        inspector = test_setup["user_inspector"]
        headers = get_auth_headers(inspector.email, inspector.role, inspector.organization_id)

        # 1. Bị CHẶN xem Nhật ký an ninh riêng của Quản trị hệ thống (HTTP 403 Forbidden)
        res_audit = client.get("/api/v1/audit/security-logs", headers=headers)
        assert res_audit.status_code == 403, "Cán bộ kiểm tra không được phép xem nhật ký an ninh!"

        # 2. Được ĐỌC toàn bộ thửa đất (HTTP 200)
        res_plots = client.get("/api/v1/land-plots", headers=headers)
        assert res_plots.status_code == 200

        # 3. Được ĐỌC toàn bộ vật tư (HTTP 200)
        res_materials = client.get("/api/v1/materials", headers=headers)
        assert res_materials.status_code == 200

        # 4. Được ĐỌC nhật ký canh tác (HTTP 200)
        res_farming = client.get("/api/v1/farming/logs", headers=headers)
        assert res_farming.status_code == 200

        # 5. Được ĐỌC lô hàng (HTTP 200)
        res_batches = client.get("/api/v1/batches", headers=headers)
        assert res_batches.status_code == 200

        # 6. Bị CHẶN khi cố tình TẠO thửa đất mới (HTTP 403 Forbidden)
        res_create_plot = client.post(
            "/api/v1/land-plots",
            headers=headers,
            json={
                "name": "Thửa Trái Phép Do Thanh Tra Tạo",
                "area": 1000,
                "unit": "m2",
                "latitude": 11.9,
                "longitude": 108.4,
            },
        )
        assert res_create_plot.status_code == 403

        # 7. Bị CHẶN khi cố tình TẠO sản phẩm (HTTP 403 Forbidden)
        res_create_prod = client.post(
            "/api/v1/products",
            headers=headers,
            json={"name": "Sản Phẩm Trái Phép", "unit": "kg"},
        )
        assert res_create_prod.status_code == 403

    def test_organization_cross_tenant_isolation(self, client: TestClient, test_setup):
        """Các tổ chức (farm, coop, logistics, distributor) bị cách ly theo organization_id."""
        farm_user = test_setup["user_farm"]
        dist_user = test_setup["user_distributor"]
        plot_10 = test_setup["plot_10"]

        farm_headers = get_auth_headers(farm_user.email, farm_user.role, farm_user.organization_id)
        dist_headers = get_auth_headers(dist_user.email, dist_user.role, dist_user.organization_id)

        # 1. Farm truy cập thửa đất của tổ chức mình -> 200 OK
        res_own = client.get(f"/api/v1/land-plots/{plot_10.id}", headers=farm_headers)
        assert res_own.status_code == 200

        # 2. Distributor gọi thẳng API lấy thửa đất của Farm (khác tổ chức) -> 403 Forbidden
        res_cross = client.get(f"/api/v1/land-plots/{plot_10.id}", headers=dist_headers)
        assert res_cross.status_code == 403

    def test_mark_batch_consumed_s29(self, client: TestClient, test_setup, db_session):
        """User Story S-29: Đánh dấu lô đã bán hết cho người tiêu dùng (status=CONSUMED)."""
        from app.models.batch import Batch

        dist_user = test_setup["user_distributor"]
        batch = Batch(
            batch_code="BATCH-RETAIL-SELL-01",
            product_name="Dâu Tây New Zealand",
            organization_id=dist_user.organization_id,
            initial_quantity=200.0,
            remaining_quantity=80.0,
            unit="kg",
            status="ACTIVE",
        )
        db_session.add(batch)
        db_session.commit()

        dist_headers = get_auth_headers(dist_user.email, dist_user.role, dist_user.organization_id)
        res = client.post(f"/api/v1/batches/{batch.id}/consume", headers=dist_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["remaining_quantity"] == 0.0
        assert data["status"] == "CONSUMED"

    def test_organization_locations_and_transfer_s30(self, client: TestClient, test_setup, db_session):
        """User Story S-30: Quản lý địa điểm/cửa hàng và chuyển lô về cửa hàng."""
        from app.models.batch import Batch

        dist_user = test_setup["user_distributor"]
        dist_headers = get_auth_headers(dist_user.email, dist_user.role, dist_user.organization_id)

        # 1. Tạo cửa hàng mới
        res_loc = client.post(
            "/api/v1/organizations/locations",
            headers=dist_headers,
            json={
                "name": "BioMart Tây Hồ - Hà Nội",
                "address": "88 Xuân Diệu, Quảng An, Tây Hồ",
                "location_type": "STORE",
            },
        )
        assert res_loc.status_code == 201
        loc_id = res_loc.json()["id"]

        # 2. Xem danh sách địa điểm
        res_list = client.get("/api/v1/organizations/locations", headers=dist_headers)
        assert res_list.status_code == 200
        assert any(l["id"] == loc_id for l in res_list.json())

        # 3. Tạo lô và chuyển lô về cửa hàng
        batch = Batch(
            batch_code="BATCH-STORE-TRANSFER-01",
            product_name="Cà Chua Cherry",
            organization_id=dist_user.organization_id,
            initial_quantity=100.0,
            remaining_quantity=100.0,
            unit="kg",
            status="ACTIVE",
        )
        db_session.add(batch)
        db_session.commit()

        res_transfer = client.post(
            f"/api/v1/organizations/batches/{batch.id}/transfer-location",
            headers=dist_headers,
            json={"location_id": loc_id, "notes": "Phân phối đợt sáng"},
        )
        assert res_transfer.status_code == 200
        assert res_transfer.json()["status"] == "ok"

    def test_csv_import_products_and_land_plots_s32(self, client: TestClient, test_setup):
        """User Story S-32: Nhập danh mục sản phẩm và thửa đất từ CSV."""
        admin_user = test_setup["user_sysadmin"]
        farm_user = test_setup["user_farm"]
        admin_headers = get_auth_headers(admin_user.email, admin_user.role)
        farm_headers = get_auth_headers(farm_user.email, farm_user.role, farm_user.organization_id)

        # 1. Import danh mục sản phẩm CSV (Admin)
        csv_products = """name,unit,description,standard
Xoài Cát Hòa Lộc,kg,Xoài đặc sản Tiền Giang,VietGAP
Gạo ST25 Hữu Cơ,tấn,Gạo ngon nhất thế giới,Hữu cơ
Nho Mẫu Đơn Ninh Thuận,thùng,Nho ngọt thơm,GlobalGAP
Trái Cây Lỗi Đơn Vị,bó,Không hợp lệ,Test
"""
        res_prod = client.post(
            "/api/v1/products/import-csv",
            headers=admin_headers,
            json={"csv_content": csv_products},
        )
        assert res_prod.status_code == 200
        data_p = res_prod.json()
        assert data_p["imported_count"] == 3
        assert data_p["skipped_count"] == 1  # Đơn vị 'bó' bị từ chối
        assert len(data_p["errors"]) == 1

        # 2. Import danh sách thửa đất CSV (Farm)
        csv_plots = """name,address,area,latitude,longitude
Khu Vực Bưởi Da Xanh 01,Mỏ Cày Nam Bến Tre,2.5,10.24,106.37
Khu Vực Sầu Riêng Ri6 02,Cai Lậy Tiền Giang,3.0,10.35,106.12
"""
        res_plots = client.post(
            "/api/v1/land-plots/import-csv",
            headers=farm_headers,
            json={"csv_content": csv_plots},
        )
        assert res_plots.status_code == 200
        data_plots = res_plots.json()
        assert data_plots["imported_count"] == 2
        assert len(data_plots["errors"]) == 0

