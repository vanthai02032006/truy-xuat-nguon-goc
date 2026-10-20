from __future__ import annotations

from fastapi import status
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.batch import Batch
from app.models.chain_event import ChainEvent
from app.models.farmer import FarmerIdentity
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.services.hash_chain_service import (
    simulate_tamper_attack,
    verify_chain_integrity,
)


class TestFinalBacklogSprint678:
    """Kiểm thử 3 nhóm tính năng cuối của Backlog: Chuỗi lạnh (S-40-45), Hồ sơ PDF (S-52,53), Ẩn danh PII (S-56)."""

    def _setup_environment(self, db_session):
        # 1. Tổ chức Nông trại
        farm_org = Organization(name="HTX Nông Nghiệp Thắng Lợi", code="FARM_TL")
        # 2. Tổ chức Vận chuyển lạnh
        transporter_org = Organization(name="Logistics Lạnh Miền Trung", code="LOGISTICS_MT")
        # 3. Tổ chức Siêu thị
        market_org = Organization(name="Hệ Thống Siêu Thị Xanh", code="SUPERMARKET_X")
        db_session.add_all([farm_org, transporter_org, market_org])
        db_session.flush()

        # Users
        farmer_user = User(
            email="farmer_leader@thangloi.vn",
            hashed_password="pw",
            full_name="Nguyễn Văn Nông Dân",
            role=UserRole.FARMER.value,
            organization_id=farm_org.id,
            is_active=True,
        )
        transporter_user = User(
            email="logistics_driver@mientrung.vn",
            hashed_password="pw",
            full_name="Lê Vận Chuyển",
            role=UserRole.LOGISTICS.value,
            organization_id=transporter_org.id,
            is_active=True,
        )
        inspector_user = User(
            email="inspector_officer@dost.gov.vn",
            hashed_password="pw",
            full_name="Đoàn Thanh Tra Chất Lượng",
            role=UserRole.INSPECTOR.value,
            organization_id=None,
            is_active=True,
        )
        market_user = User(
            email="manager@sieuthixanh.vn",
            hashed_password="pw",
            full_name="Trần Quản Lý Siêu Thị",
            role=UserRole.RETAILER.value,
            organization_id=market_org.id,
            is_active=True,
        )
        db_session.add_all([farmer_user, transporter_user, inspector_user, market_user])
        db_session.flush()

        # Tokens
        t_farmer = create_access_token(farmer_user.email, farmer_user.role, farm_org.id)
        t_transporter = create_access_token(transporter_user.email, transporter_user.role, transporter_org.id)
        t_inspector = create_access_token(inspector_user.email, inspector_user.role, None)
        t_market = create_access_token(market_user.email, market_user.role, market_org.id)

        # Batch
        batch = Batch(
            batch_code="BATCH-SPRINT-01",
            product_name="Dâu Tây Thủy Canh VietGAP",
            organization_id=farm_org.id,
            initial_quantity=500.0,
            remaining_quantity=500.0,
            unit="kg",
        )
        db_session.add(batch)
        db_session.commit()

        return {
            "farm_org": farm_org,
            "transporter_org": transporter_org,
            "market_org": market_org,
            "farmer_user": farmer_user,
            "transporter_user": transporter_user,
            "inspector_user": inspector_user,
            "market_user": market_user,
            "t_farmer": t_farmer,
            "t_transporter": t_transporter,
            "t_inspector": t_inspector,
            "t_market": t_market,
            "batch": batch,
        }

    # =========================================================================
    # NHÓM 1: GIÁM SÁT CHUỖI LẠNH & 5 KỊCH BẢN GIẢ LẬP S-42, S-45
    # =========================================================================

    def test_s40_s42_cold_chain_5_scenarios_simulation(self, client: TestClient, db_session):
        """User Story S-40 -> S-45: Mở chuyến xe lạnh và kiểm thử cả 5 kịch bản cảm biến mẫu."""
        ctx = self._setup_environment(db_session)
        headers_transporter = {"Authorization": f"Bearer {ctx['t_transporter']}"}

        # 1. Vai trò "Vận chuyển lạnh" mở chuyến vận chuyển gắn thùng lạnh và lô hàng (S-40)
        trip_res = client.post(
            "/api/v1/cold-chain/trips",
            json={
                "vehicle_code": "REEFER-TRUCK-77A",
                "batch_ids": [ctx["batch"].id],
                "driver_name": "Tài Xế Nguyễn",
                "min_temperature": 2.0,
                "max_temperature": 8.0,
            },
            headers=headers_transporter,
        )
        assert trip_res.status_code == status.HTTP_201_CREATED
        trip_id = trip_res.json()["id"]

        # Kịch bản 1: Không vượt ngưỡng (ổn định 2°C - 8°C) -> 0 vi phạm
        sc1_res = client.post(
            f"/api/v1/cold-chain/trips/{trip_id}/simulate-scenario/1",
            headers=headers_transporter,
        )
        assert sc1_res.status_code == status.HTTP_200_OK
        data1 = sc1_res.json()
        assert data1["scenario_id"] == 1
        assert data1["violations_count"] == 0
        assert data1["is_violated"] is False

        # Kịch bản 2: Vượt ngưỡng 10 phút (mở cửa xe tạm thời) -> KHÔNG tính là vi phạm (< 30 phút)
        sc2_res = client.post(
            f"/api/v1/cold-chain/trips/{trip_id}/simulate-scenario/2",
            headers=headers_transporter,
        )
        assert sc2_res.status_code == status.HTTP_200_OK
        data2 = sc2_res.json()
        assert data2["scenario_id"] == 2
        assert data2["violations_count"] == 0
        assert data2["is_violated"] is False

        # Kịch bản 3: Vượt ngưỡng liên tục 45 phút (> 30 phút) -> Tính 1 vi phạm
        sc3_res = client.post(
            f"/api/v1/cold-chain/trips/{trip_id}/simulate-scenario/3",
            headers=headers_transporter,
        )
        assert sc3_res.status_code == status.HTTP_200_OK
        data3 = sc3_res.json()
        assert data3["scenario_id"] == 3
        assert data3["violations_count"] == 1
        assert data3["is_violated"] is True
        v3 = data3["violations"][0]
        assert v3["duration_minutes"] == 45.0
        assert v3["peak_temperature"] == 16.5
        assert v3["hash_recorded"] is True

        # Kiểm tra Hash Chain của lô hàng đã được tự động ghi sự kiện vi phạm (S-45)
        events = (
            db_session.query(ChainEvent)
            .filter(ChainEvent.batch_id == ctx["batch"].id, ChainEvent.event_type == "COLD_CHAIN_VIOLATION")
            .all()
        )
        assert len(events) >= 1
        assert "VI PHẠM CHUỖI LẠNH" in events[-1].event_data.upper()

        # Kịch bản 4: Hai lần vượt cách nhau dưới 5 phút -> Gộp thành 1 vi phạm
        sc4_res = client.post(
            f"/api/v1/cold-chain/trips/{trip_id}/simulate-scenario/4",
            headers=headers_transporter,
        )
        assert sc4_res.status_code == status.HTTP_200_OK
        data4 = sc4_res.json()
        assert data4["scenario_id"] == 4
        assert data4["violations_count"] == 1
        assert data4["is_violated"] is True
        v4 = data4["violations"][0]
        assert v4["duration_minutes"] == 41.0
        assert v4["peak_temperature"] == 15.5

        # Kịch bản 5: Vượt qua nửa đêm (cross-midnight)
        sc5_res = client.post(
            f"/api/v1/cold-chain/trips/{trip_id}/simulate-scenario/5",
            headers=headers_transporter,
        )
        assert sc5_res.status_code == status.HTTP_200_OK
        data5 = sc5_res.json()
        assert data5["scenario_id"] == 5
        assert data5["violations_count"] == 1
        assert data5["is_violated"] is True
        v5 = data5["violations"][0]
        assert v5["duration_minutes"] == 45.0
        assert v5["peak_temperature"] == 15.8

    def test_s45_handover_warning_on_cold_chain_violation(self, client: TestClient, db_session):
        """User Story S-45: Khi bàn giao lô hàng có vi phạm chuỗi lạnh, hệ thống hiển thị cảnh báo."""
        ctx = self._setup_environment(db_session)
        headers_farmer = {"Authorization": f"Bearer {ctx['t_farmer']}"}

        # Ghi một sự kiện vi phạm chuỗi lạnh vào lô hàng
        from app.services.hash_chain_service import record_chain_event

        record_chain_event(
            db=db_session,
            batch_id=ctx["batch"].id,
            event_type="COLD_CHAIN_VIOLATION",
            event_data="CẢNH BÁO VI PHẠM CHUỖI LẠNH: Nhiệt độ đỉnh 16.5°C vượt ngưỡng 8.0°C liên tục 45 phút.",
            organization_id=ctx["transporter_org"].id,
        )
        db_session.commit()

        # Tạo lệnh bàn giao từ Nông trại sang Siêu thị
        ho_res = client.post(
            "/api/v1/handovers",
            json={"batch_id": ctx["batch"].id, "to_org_id": ctx["market_org"].id},
            headers=headers_farmer,
        )
        assert ho_res.status_code == status.HTTP_201_CREATED
        ho_data = ho_res.json()

        # S-45: Cảnh báo vi phạm chuỗi lạnh xuất hiện rõ ràng trong phản hồi bàn giao
        assert ho_data["has_cold_chain_violation"] is True
        assert ho_data["cold_chain_warning"] is not None
        assert "CẢNH BÁO VI PHẠM CHUỖI LẠNH" in ho_data["cold_chain_warning"]

    # =========================================================================
    # NHÓM 2: XUẤT HỒ SƠ KIỂM TRA TRUY XUẤT NGUỒN GỐC S-52, S-53
    # =========================================================================

    def test_s52_s53_inspection_dossier_with_hash_integrity(self, client: TestClient, db_session):
        """User Story S-52, S-53: Cán bộ kiểm tra xuất hồ sơ kiểm tra đầy đủ phả hệ, sự kiện và kiểm tra toàn vẹn."""
        ctx = self._setup_environment(db_session)
        headers_inspector = {"Authorization": f"Bearer {ctx['t_inspector']}"}

        # Ghi thêm sự kiện vào lô hàng
        from app.services.hash_chain_service import record_chain_event

        record_chain_event(
            db=db_session,
            batch_id=ctx["batch"].id,
            event_type="HARVEST",
            event_data="Thu hoạch nông sản tại Thửa đất A1 Đạt chuẩn VietGAP.",
            organization_id=ctx["farm_org"].id,
        )
        db_session.commit()

        # Gọi API xuất hồ sơ kiểm tra
        res = client.get(
            f"/api/v1/batches/{ctx['batch'].id}/inspection-dossier",
            headers=headers_inspector,
        )
        assert res.status_code == status.HTTP_200_OK
        dossier = res.json()

        # 1. Thông tin lô
        assert dossier["batch_info"]["batch_code"] == "BATCH-SPRINT-01"
        assert dossier["batch_info"]["product_name"] == "Dâu Tây Thủy Canh VietGAP"

        # 2. Toàn vẹn chuỗi Hash SHA-256
        assert dossier["integrity_verification"]["valid"] is True
        assert "TOÀN VẸN 100%" in dossier["integrity_verification"]["status_label"]
        assert len(dossier["integrity_verification"]["terminal_current_hash"]) == 64

        # 3. Dòng thời gian sự kiện
        assert len(dossier["event_timeline"]) >= 1

        # 4. Phả hệ & Chuỗi lạnh & Thu hồi & Metadata
        assert "ancestors" in dossier["lineage"]
        assert "violations" in dossier["cold_chain"]
        assert "is_recalled" in dossier["recalls"]
        assert dossier["export_metadata"]["official_dossier_code"].startswith("HSKT-")
        assert dossier["export_metadata"]["inspector_name"] == ctx["inspector_user"].full_name

        # Mô phỏng sửa lén dữ liệu (Tamper Attack) -> Hồ sơ phải đổi sang cảnh báo
        simulate_tamper_attack(db=db_session, batch_id=ctx["batch"].id, action="tamper_data")
        res_tampered = client.get(
            f"/api/v1/batches/{ctx['batch'].id}/inspection-dossier",
            headers=headers_inspector,
        )
        assert res_tampered.status_code == status.HTTP_200_OK
        dossier_tampered = res_tampered.json()
        assert dossier_tampered["integrity_verification"]["valid"] is False
        assert "PHÁT HIỆN CAN THIỆP" in dossier_tampered["integrity_verification"]["status_label"]

    # =========================================================================
    # NHÓM 3: XÓA DỮ LIỆU ĐỊNH DANH PII THEO NĐ 13/2023/NĐ-CP MÀ KHÔNG VỠ CHUỖI HASH (S-56)
    # =========================================================================

    def test_s56_anonymize_farmer_pii_preserves_hash_chain_integrity(self, client: TestClient, db_session):
        """
        User Story S-56 & Nghị định 13/2023/NĐ-CP:
        1. Tách thông tin PII nông hộ vào bảng riêng.
        2. Sự kiện băm chỉ lưu bí danh farmer_ref_id.
        3. Khi xóa/ẩn danh dữ liệu cá nhân theo yêu cầu:
           - PII bị xóa hoàn toàn khỏi hệ thống.
           - Kiểm tra toàn vẹn SHA-256 (S-12) vẫn KHỚP 100% VÀ BÁO HỢP LỆ!
        """
        ctx = self._setup_environment(db_session)
        headers_farmer = {"Authorization": f"Bearer {ctx['t_farmer']}"}

        # 1. Đăng ký thông tin định danh cá nhân nông hộ (Họ tên, SĐT, CCCD, Địa chỉ chi tiết)
        farmer_payload = {
            "full_name": "Trần Văn Nông Dân Cụ Thể",
            "phone": "0987654321",
            "id_card": "049090001234",
            "detail_address": "Số 12 Thôn 3, Xã Lạc Dương, Huyện Lạc Dương",
            "province": "Lâm Đồng",
            "organization_id": ctx["farm_org"].id,
            "farmer_ref_id": "FMR-DL-9988",
        }
        res_create_farmer = client.post("/api/v1/farmers", json=farmer_payload, headers=headers_farmer)
        assert res_create_farmer.status_code == status.HTTP_201_CREATED
        farmer_data = res_create_farmer.json()
        ref_id = farmer_data["farmer_ref_id"]
        assert farmer_data["full_name"] == "Trần Văn Nông Dân Cụ Thể"

        # 2. Tạo lô hàng gắn với farmer_ref_id
        batch_payload = {
            "batch_code": "BATCH-FARMER-PII-01",
            "product_name": "Cà Chua Beef Đà Lạt",
            "farmer_ref_id": ref_id,
            "initial_quantity": 400.0,
            "remaining_quantity": 400.0,
            "unit": "kg",
        }
        res_create_batch = client.post("/api/v1/batches", json=batch_payload, headers=headers_farmer)
        assert res_create_batch.status_code == status.HTTP_201_CREATED
        batch_id = res_create_batch.json()["id"]

        # Kiểm tra sự kiện khởi tạo trong bảng chain_events: CHỈ LƯU mã farmer_ref_id, KHÔNG lưu tên/sđt
        event = db_session.query(ChainEvent).filter(ChainEvent.batch_id == batch_id).first()
        assert event is not None
        assert ref_id in event.event_data
        assert "0987654321" not in event.event_data
        assert "Trần Văn Nông Dân Cụ Thể" not in event.event_data

        # Kiểm tra toàn vẹn ban đầu
        integrity_before = verify_chain_integrity(db=db_session, batch_id=batch_id)
        assert integrity_before["valid"] is True

        # 3. Nông hộ thực hiện quyền xóa dữ liệu cá nhân theo Nghị định 13/2023/NĐ-CP (S-56)
        anonymize_payload = {
            "reason": "Yêu cầu xóa thông tin cá nhân theo Điều 16 Nghị định 13/2023/NĐ-CP"
        }
        res_anonymize = client.post(
            f"/api/v1/farmers/{ref_id}/anonymize",
            json=anonymize_payload,
            headers=headers_farmer,
        )
        assert res_anonymize.status_code == status.HTTP_200_OK
        anon_data = res_anonymize.json()
        assert anon_data["is_anonymized"] is True
        assert anon_data["chain_integrity_valid"] is True

        # 4. Kiểm tra dữ liệu trong bảng farmer_identities đã bị xóa sạch PII
        farmer_after = db_session.query(FarmerIdentity).filter_by(farmer_ref_id=ref_id).first()
        assert farmer_after.full_name is None
        assert farmer_after.phone is None
        assert farmer_after.id_card is None
        assert farmer_after.detail_address is None
        assert farmer_after.is_anonymized is True

        # 5. Gọi API lấy thông tin nông hộ -> Hiển thị tên ẩn danh
        res_get_farmer = client.get(f"/api/v1/farmers/{ref_id}", headers=headers_farmer)
        assert res_get_farmer.status_code == status.HTTP_200_OK
        anon_farmer_resp = res_get_farmer.json()
        assert anon_farmer_resp["display_name"] == f"Nông hộ ẩn danh ({ref_id})"
        assert anon_farmer_resp["full_name"] is None
        assert anon_farmer_resp["phone"] is None

        # 6. QUAN TRỌNG NHẤT: Chạy lại thuật toán kiểm tra toàn vẹn SHA-256 (S-12)
        # Chuỗi hash của lô hàng vẫn KHỚP 100% VÀ BÁO HỢP LỆ (valid = True)
        integrity_after = verify_chain_integrity(db=db_session, batch_id=batch_id)
        assert integrity_after["valid"] is True
        assert integrity_after["broken_event_id"] is None
        assert "Chuỗi hash toàn vẹn 100%" in integrity_after["message"]
