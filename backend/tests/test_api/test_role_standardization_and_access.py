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

    def test_quick_role_token_endpoint_aliases(self, client: TestClient, test_setup):
        """Endpoint /quick-role-token cấp token chính xác cho các vai trò chuẩn hóa và alias."""
        roles_to_test = [
            ("farm", "farm"),
            ("coop", "coop"),
            ("processing", "coop"),
            ("logistics", "logistics"),
            ("distributor", "distributor"),
            ("retailer", "distributor"),
            ("inspector", "inspector"),
            ("system_admin", "system_admin"),
            ("admin", "system_admin"),
        ]
        for role_input, expected_role in roles_to_test:
            res = client.post(f"/api/v1/auth/quick-role-token?role={role_input}")
            assert res.status_code == 200, f"Thất bại với vai trò: {role_input}"
            data = res.json()
            assert data["role"] == expected_role, f"Mong đợi {expected_role}, nhận {data['role']}"
            assert "access_token" in data

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
