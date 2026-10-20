from __future__ import annotations

import pytest
from app.core.security import create_access_token, get_password_hash
from app.models.batch import Batch
from app.models.land_plot import LandPlot
from app.models.security_log import SecurityLog
from app.models.user import User, UserRole


def get_auth_headers(user_email: str, role: str, org_id: int | None) -> dict[str, str]:
    """Tạo header Authorization Bearer token phục vụ test."""
    token = create_access_token(subject=user_email, role=role, organization_id=org_id)
    return {"Authorization": f"Bearer {token}"}


class TestStoryS06LandPlots:
    """
    Bộ test kiểm thử tích hợp (Integration Tests) cho Story S-06:
    'Vùng trồng khai báo thửa đất của mình' (Sprint 1 / E-03).
    """

    @pytest.fixture
    def farmer_user(self, db_session, seed_data):
        """Khởi tạo tài khoản nông dân thuộc Tổ chức 1."""
        farmer = User(
            id=10,
            email="farmer1@thangloi.vn",
            hashed_password=get_password_hash("password123"),
            full_name="Nguyễn Văn Nông Dân",
            role=UserRole.FARMER.value,
            organization_id=seed_data["org1"].id,
            is_active=True,
        )
        db_session.add(farmer)
        db_session.commit()
        db_session.refresh(farmer)
        return farmer

    def test_ac1_farmer_declares_land_plot_successfully(
        self, client, farmer_user, seed_data
    ):
        """
        AC 1: Giả sử đã đăng nhập bằng vai trò vùng trồng,
              Khi khai báo thửa với tên, diện tích và toạ độ hợp lệ,
              Thì thửa được lưu và thuộc tổ chức của tôi.
        """
        headers = get_auth_headers(
            user_email=farmer_user.email,
            role=farmer_user.role,
            org_id=farmer_user.organization_id,
        )

        payload = {
            "name": "Thửa A1 - Vườn Cà Chua Thắng Lợi",
            "area": 2500.5,
            "unit": "m2",
            "latitude": 11.940419,
            "longitude": 108.458313,
            "address": "Xã Lạc Dương, Tỉnh Lâm Đồng",
        }

        response = client.post("/api/v1/land-plots", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()

        assert data["id"] is not None
        assert data["name"] == "Thửa A1 - Vườn Cà Chua Thắng Lợi"
        assert data["area"] == 2500.5
        assert data["unit"] == "m2"
        assert data["latitude"] == pytest.approx(11.940419)
        assert data["longitude"] == pytest.approx(108.458313)
        assert data["address"] == "Xã Lạc Dương, Tỉnh Lâm Đồng"
        # Đảm bảo thuộc đúng tổ chức của người dùng đang đăng nhập
        assert data["organization_id"] == seed_data["org1"].id

    def test_ac2_negative_or_zero_area_is_rejected_with_clear_message(
        self, client, farmer_user
    ):
        """
        AC 2: Giả sử tôi nhập diện tích âm hoặc bằng 0,
              Khi lưu, Thì bị chặn kèm thông báo rõ lý do.
        """
        headers = get_auth_headers(
            user_email=farmer_user.email,
            role=farmer_user.role,
            org_id=farmer_user.organization_id,
        )

        # 1. Thử diện tích = 0
        payload_zero = {
            "name": "Thửa Thử Nghiệm Số Không",
            "area": 0,
            "unit": "m2",
            "latitude": 11.94,
            "longitude": 108.45,
        }
        res_zero = client.post("/api/v1/land-plots", json=payload_zero, headers=headers)
        assert res_zero.status_code == 422
        assert "Diện tích thửa đất phải lớn hơn 0" in str(res_zero.json())

        # 2. Thử diện tích âm
        payload_negative = {
            "name": "Thửa Thử Nghiệm Số Âm",
            "area": -150.75,
            "unit": "m2",
            "latitude": 11.94,
            "longitude": 108.45,
        }
        res_neg = client.post(
            "/api/v1/land-plots", json=payload_negative, headers=headers
        )
        assert res_neg.status_code == 422
        assert "Diện tích thửa đất phải lớn hơn 0" in str(res_neg.json())

    def test_ac3_organization_only_sees_its_own_land_plots(
        self, client, db_session, farmer_user, seed_data
    ):
        """
        AC 3: Giả sử tôi xem danh sách thửa,
              Khi tải trang, Thì chỉ thấy thửa của tổ chức mình.
        """
        # Tạo 2 thửa cho Tổ chức 1
        plot1_org1 = LandPlot(
            name="Thửa 1 - Tổ chức 1",
            area=1200.0,
            unit="m2",
            latitude=11.94,
            longitude=108.45,
            organization_id=seed_data["org1"].id,
        )
        plot2_org1 = LandPlot(
            name="Thửa 2 - Tổ chức 1",
            area=3000.0,
            unit="m2",
            latitude=11.95,
            longitude=108.46,
            organization_id=seed_data["org1"].id,
        )
        # Tạo 1 thửa cho Tổ chức 2
        plot3_org2 = LandPlot(
            name="Thửa 3 - Tổ chức 2",
            area=5000.0,
            unit="m2",
            latitude=11.96,
            longitude=108.47,
            organization_id=seed_data["org2"].id,
        )
        db_session.add_all([plot1_org1, plot2_org1, plot3_org2])
        db_session.commit()

        # 1. Người dùng Tổ chức 1 lấy danh sách
        headers_org1 = get_auth_headers(
            user_email=farmer_user.email,
            role=farmer_user.role,
            org_id=farmer_user.organization_id,
        )
        res_org1 = client.get("/api/v1/land-plots", headers=headers_org1)
        assert res_org1.status_code == 200
        data_org1 = res_org1.json()

        assert len(data_org1) == 2
        names_org1 = {p["name"] for p in data_org1}
        assert "Thửa 1 - Tổ chức 1" in names_org1
        assert "Thửa 2 - Tổ chức 1" in names_org1
        assert "Thửa 3 - Tổ chức 2" not in names_org1

        # 2. Người dùng Tổ chức 2 lấy danh sách
        headers_org2 = get_auth_headers(
            user_email=seed_data["user_org2"].email,
            role=seed_data["user_org2"].role,
            org_id=seed_data["user_org2"].organization_id,
        )
        res_org2 = client.get("/api/v1/land-plots", headers=headers_org2)
        assert res_org2.status_code == 200
        data_org2 = res_org2.json()

        assert len(data_org2) == 1
        assert data_org2[0]["name"] == "Thửa 3 - Tổ chức 2"
        assert data_org2[0]["organization_id"] == seed_data["org2"].id

        # 3. Cán bộ kiểm tra (Inspector) xem được tất cả các thửa ở chế độ đọc
        headers_inspector = get_auth_headers(
            user_email=seed_data["inspector"].email,
            role=seed_data["inspector"].role,
            org_id=None,
        )
        res_inspector = client.get("/api/v1/land-plots", headers=headers_inspector)
        assert res_inspector.status_code == 200
        data_inspector = res_inspector.json()
        assert len(data_inspector) == 3

    def test_ac4_updating_plot_name_preserves_batch_association(
        self, client, db_session, farmer_user, seed_data
    ):
        """
        AC 4: Giả sử tôi sửa tên thửa,
              Khi lưu, Thì lô đã gắn với thửa vẫn trỏ đúng thửa đó.
        """
        headers = get_auth_headers(
            user_email=farmer_user.email,
            role=farmer_user.role,
            org_id=farmer_user.organization_id,
        )

        # 1. Tạo thửa đất ban đầu
        plot = LandPlot(
            name="Thửa Ban Đầu",
            area=1800.0,
            unit="m2",
            latitude=11.941,
            longitude=108.452,
            organization_id=seed_data["org1"].id,
        )
        db_session.add(plot)
        db_session.commit()
        db_session.refresh(plot)
        plot_id = plot.id

        # 2. Gắn lô hàng với thửa đất này
        batch = Batch(
            batch_code="BATCH-S06-001",
            product_name="Dâu tây New Zealand",
            organization_id=seed_data["org1"].id,
            land_plot_id=plot_id,
        )
        db_session.add(batch)
        db_session.commit()
        db_session.refresh(batch)

        assert batch.land_plot_id == plot_id
        assert batch.land_plot.name == "Thửa Ban Đầu"

        # 3. Sửa tên thửa đất thông qua API
        update_payload = {"name": "Thửa Mới Đã Đổi Tên"}
        res_update = client.put(
            f"/api/v1/land-plots/{plot_id}",
            json=update_payload,
            headers=headers,
        )
        assert res_update.status_code == 200
        assert res_update.json()["name"] == "Thửa Mới Đã Đổi Tên"

        # 4. Kiểm tra lô hàng vẫn trỏ đúng thửa đất đó (plot_id không đổi)
        db_session.expire_all()
        reloaded_batch = (
            db_session.query(Batch).filter(Batch.batch_code == "BATCH-S06-001").first()
        )
        assert reloaded_batch is not None
        assert reloaded_batch.land_plot_id == plot_id
        assert reloaded_batch.land_plot.name == "Thửa Mới Đã Đổi Tên"

    def test_cross_tenant_access_denied_and_logged(self, client, db_session, seed_data):
        """
        Kiểm tra truy cập chéo tổ chức: Người dùng Tổ chức 1 không được xem/sửa
        thửa của Tổ chức 2. Trả về 403 và ghi SecurityLog.
        """
        plot_org2 = LandPlot(
            name="Thửa Bí Mật Tổ Chức 2",
            area=2000.0,
            unit="m2",
            latitude=10.12,
            longitude=105.34,
            organization_id=seed_data["org2"].id,
        )
        db_session.add(plot_org2)
        db_session.commit()
        db_session.refresh(plot_org2)

        headers_org1 = get_auth_headers(
            user_email=seed_data["user_org1"].email,
            role=seed_data["user_org1"].role,
            org_id=seed_data["user_org1"].organization_id,
        )

        # Cố tình gọi trực tiếp thửa đất của tổ chức 2
        response = client.get(
            f"/api/v1/land-plots/{plot_org2.id}", headers=headers_org1
        )
        assert response.status_code == 403
        assert (
            "Không có quyền truy cập dữ liệu thửa đất của tổ chức khác"
            in response.json()["detail"]
        )

        # Kiểm tra SecurityLog
        log_entry = (
            db_session.query(SecurityLog)
            .filter(
                SecurityLog.user_id == seed_data["user_org1"].id,
                SecurityLog.target_resource == "land_plot",
                SecurityLog.target_id == str(plot_org2.id),
            )
            .first()
        )
        assert log_entry is not None
        assert log_entry.attempt_type == "cross_tenant_access_denied"
        assert log_entry.target_org_id == seed_data["org2"].id

    def test_inspector_cannot_create_or_modify_plots(
        self, client, db_session, seed_data
    ):
        """
        Cán bộ kiểm tra (Inspector) chỉ ở chế độ đọc, bị chặn khi cố tạo hoặc sửa thửa đất (403).
        """
        headers_inspector = get_auth_headers(
            user_email=seed_data["inspector"].email,
            role=seed_data["inspector"].role,
            org_id=None,
        )

        # 1. Thử tạo mới
        payload = {
            "name": "Thửa Do Inspector Tạo",
            "area": 1000.0,
            "unit": "m2",
            "latitude": 10.0,
            "longitude": 106.0,
        }
        res_post = client.post(
            "/api/v1/land-plots", json=payload, headers=headers_inspector
        )
        assert res_post.status_code == 403

        # 2. Thử sửa
        plot = LandPlot(
            name="Thửa Đất Có Sẵn",
            area=1000.0,
            unit="m2",
            latitude=10.0,
            longitude=106.0,
            organization_id=seed_data["org1"].id,
        )
        db_session.add(plot)
        db_session.commit()
        db_session.refresh(plot)

        res_put = client.put(
            f"/api/v1/land-plots/{plot.id}",
            json={"name": "Sửa Tên"},
            headers=headers_inspector,
        )
        assert res_put.status_code == 403

    def test_nfr_coordinate_precision(self, client, farmer_user):
        """
        NFR: Toạ độ lưu ở dạng số thực đủ chính xác để hiện vị trí trên bản đồ ở S-60.
        """
        headers = get_auth_headers(
            user_email=farmer_user.email,
            role=farmer_user.role,
            org_id=farmer_user.organization_id,
        )

        precise_lat = 11.9404192345
        precise_lng = 108.4583134567

        payload = {
            "name": "Thửa Đất Toạ Độ Chính Xác Cao",
            "area": 3500.25,
            "unit": "m2",
            "latitude": precise_lat,
            "longitude": precise_lng,
        }
        res = client.post("/api/v1/land-plots", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()

        assert abs(data["latitude"] - precise_lat) < 1e-6
        assert abs(data["longitude"] - precise_lng) < 1e-6
