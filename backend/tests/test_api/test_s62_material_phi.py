from __future__ import annotations

import pytest
from app.core.security import create_access_token, get_password_hash
from app.models.batch import Batch
from app.models.land_plot import LandPlot
from app.models.user import User, UserRole


def get_auth_headers(user_email: str, role: str, org_id: int | None) -> dict[str, str]:
    """Tạo header Authorization Bearer token phục vụ test."""
    token = create_access_token(subject=user_email, role=role, organization_id=org_id)
    return {"Authorization": f"Bearer {token}"}


class TestStoryS62MaterialPHI:
    """
    Bộ kiểm thử tích hợp cho User Story S-62:
    'Ghi nhận vật tư (phân bón, thuốc BVTV) đã dùng gắn với một lô hàng cụ thể
    để phục vụ việc kiểm tra thời gian cách ly khi thu hoạch'.
    """

    @pytest.fixture
    def test_setup(self, db_session, seed_data):
        org1 = seed_data["org1"]
        org2 = seed_data["org2"]

        farmer = User(
            id=50,
            email="farmer_s62@thangloi.vn",
            hashed_password=get_password_hash("password123"),
            full_name="Nguyễn Văn Nông Nghiệp",
            role=UserRole.FARM_OWNER.value,
            organization_id=org1.id,
            is_active=True,
        )

        other_farmer = User(
            id=51,
            email="farmer_other@hoabinh.vn",
            hashed_password=get_password_hash("password123"),
            full_name="Lê Văn Hợp Tác",
            role=UserRole.FARM_OWNER.value,
            organization_id=org2.id,
            is_active=True,
        )

        inspector = User(
            id=52,
            email="inspector_s62@gov.vn",
            hashed_password=get_password_hash("password123"),
            full_name="Đoàn Thanh Tra VietGAP",
            role=UserRole.INSPECTOR.value,
            organization_id=None,
            is_active=True,
        )

        db_session.add_all([farmer, other_farmer, inspector])
        db_session.commit()

        # Tạo thửa đất và lô hàng thuộc Tổ chức 1
        plot1 = LandPlot(
            id=500,
            name="Thửa Thảo Mộc 01",
            area=3000.0,
            unit="m2",
            latitude=11.95,
            longitude=108.45,
            organization_id=org1.id,
        )
        batch1 = Batch(
            id=500,
            batch_code="BATCH-S62-TOMATO-01",
            product_name="Cà chua Beef Đà Lạt",
            organization_id=org1.id,
            land_plot_id=500,
        )

        # Lô hàng thuộc Tổ chức 2
        batch2 = Batch(
            id=501,
            batch_code="BATCH-S62-MELON-02",
            product_name="Dưa lưới Nhật",
            organization_id=org2.id,
        )

        db_session.add_all([plot1, batch1, batch2])
        db_session.commit()

        return {
            "farmer": farmer,
            "other_farmer": other_farmer,
            "inspector": inspector,
            "batch1": batch1,
            "batch2": batch2,
        }

    def test_record_material_usage_for_batch_success(self, client, test_setup):
        """
        Ghi nhận sử dụng phân bón/thuốc BVTV cho lô hàng cụ thể thành công.
        Tự động tính ngày an toàn thu hoạch = applied_date + isolation_days.
        """
        farmer = test_setup["farmer"]
        batch = test_setup["batch1"]
        headers = get_auth_headers(farmer.email, farmer.role, farmer.organization_id)

        payload = {
            "material_name": "Chế phẩm sinh học phòng trừ sâu BT",
            "category": "pesticide",
            "dosage": "50ml / 20 lít nước",
            "applied_date": "2026-10-10",
            "isolation_days": 7,
            "applied_by": "Nguyễn Văn Nông Nghiệp",
            "notes": "Phun phòng trừ sâu đục quả lứa 2",
        }

        response = client.post(
            f"/api/v1/batches/{batch.id}/materials",
            json=payload,
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["batch_id"] == batch.id
        assert data["material_name"] == "Chế phẩm sinh học phòng trừ sâu BT"
        assert data["applied_date"] == "2026-10-10"
        assert data["isolation_days"] == 7
        assert data["safe_harvest_date"] == "2026-10-17"  # 10 + 7 = 17

    def test_phi_check_violating_when_before_safe_harvest_date(
        self, client, test_setup
    ):
        """
        Kiểm tra thời gian cách ly: nếu ngày thu hoạch dự kiến sớm hơn ngày an toàn,
        hệ thống trả về cảnh báo vi phạm cách ly (violating).
        """
        farmer = test_setup["farmer"]
        batch = test_setup["batch1"]
        headers = get_auth_headers(farmer.email, farmer.role, farmer.organization_id)

        # Phun thuốc ngày 2026-10-15 với thời gian cách ly 14 ngày -> an toàn từ 2026-10-29
        client.post(
            f"/api/v1/batches/{batch.id}/materials",
            json={
                "material_name": "Thuốc trừ bọ trĩ sinh học Neem Oil",
                "category": "pesticide",
                "dosage": "100ml / bình",
                "applied_date": "2026-10-15",
                "isolation_days": 14,
            },
            headers=headers,
        )

        # Dự kiến thu hoạch sớm vào ngày 2026-10-20 (mới cách ly 5 ngày, còn thiếu 9 ngày)
        response = client.get(
            f"/api/v1/batches/{batch.id}/phi-check?harvest_date=2026-10-20",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_safe_to_harvest"] is False
        assert data["status"] == "violating"
        assert data["days_remaining"] == 9
        assert data["max_safe_harvest_date"] == "2026-10-29"
        assert "CẢNH BÁO: Chưa đủ thời gian cách ly an toàn" in data["message"]

    def test_phi_check_compliant_when_on_or_after_safe_date(self, client, test_setup):
        """
        Kiểm tra thời gian cách ly: nếu ngày thu hoạch bằng hoặc sau ngày an toàn,
        hệ thống trả về ĐỦ ĐIỀU KIỆN AN TOÀN THU HOẠCH.
        """
        farmer = test_setup["farmer"]
        batch = test_setup["batch1"]
        headers = get_auth_headers(farmer.email, farmer.role, farmer.organization_id)

        # Ghi nhận thuốc BVTV cách ly 7 ngày từ 2026-10-10 -> an toàn từ 2026-10-17
        client.post(
            f"/api/v1/batches/{batch.id}/materials",
            json={
                "material_name": "Chế phẩm nấm Trichoderma",
                "category": "pesticide",
                "dosage": "50g/bình",
                "applied_date": "2026-10-10",
                "isolation_days": 7,
            },
            headers=headers,
        )

        # Kiểm tra vào ngày 2026-10-20 (đã qua ngày an toàn 2026-10-17)
        response = client.get(
            f"/api/v1/batches/{batch.id}/phi-check?harvest_date=2026-10-20",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_safe_to_harvest"] is True
        assert data["status"] == "compliant"
        assert data["days_remaining"] == 0
        assert "ĐỦ ĐIỀU KIỆN AN TOÀN THU HOẠCH" in data["message"]

    def test_cross_tenant_cannot_record_material_for_other_org_batch(
        self, client, test_setup
    ):
        """
        Người dùng tổ chức 1 không thể ghi nhận vật tư vào lô hàng của tổ chức 2 (403 Forbidden).
        """
        farmer = test_setup["farmer"]  # Org 1
        batch_org2 = test_setup["batch2"]  # Org 2
        headers = get_auth_headers(farmer.email, farmer.role, farmer.organization_id)

        response = client.post(
            f"/api/v1/batches/{batch_org2.id}/materials",
            json={
                "material_name": "Phân bón NPK",
                "category": "fertilizer",
                "dosage": "20kg",
                "applied_date": "2026-10-10",
                "isolation_days": 3,
            },
            headers=headers,
        )

        assert response.status_code == 403
        assert (
            "Không có quyền truy cập dữ liệu của tổ chức khác"
            in response.json()["detail"]
        )

    def test_inspector_can_view_materials_and_phi_check_read_only(
        self, client, test_setup
    ):
        """
        Cán bộ kiểm tra (Inspector) xem được nhật ký vật tư và kiểm tra PHI của mọi tổ chức,
        nhưng bị từ chối (403) khi cố tình ghi nhận/chỉnh sửa.
        """
        inspector = test_setup["inspector"]
        batch = test_setup["batch1"]
        headers = get_auth_headers(
            inspector.email, inspector.role, inspector.organization_id
        )

        # 1. Đọc danh sách vật tư -> Thành công
        get_res = client.get(
            f"/api/v1/batches/{batch.id}/materials",
            headers=headers,
        )
        assert get_res.status_code == 200

        # 2. Kiểm tra PHI -> Thành công
        phi_res = client.get(
            f"/api/v1/batches/{batch.id}/phi-check",
            headers=headers,
        )
        assert phi_res.status_code == 200

        # 3. Cố tình ghi thêm vật tư -> 403 Forbidden (chế độ chỉ đọc)
        post_res = client.post(
            f"/api/v1/batches/{batch.id}/materials",
            json={
                "material_name": "Test Thuốc",
                "category": "pesticide",
                "dosage": "10ml",
                "applied_date": "2026-10-10",
                "isolation_days": 5,
            },
            headers=headers,
        )
        assert post_res.status_code == 403
        assert "chỉ có quyền xem dữ liệu (chế độ chỉ đọc)" in post_res.json()["detail"]
