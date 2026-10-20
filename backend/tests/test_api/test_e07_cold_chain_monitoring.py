from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.security import create_access_token
from app.models.batch import Batch
from app.models.chain_event import ChainEvent
from app.models.cold_chain import ColdChainViolation
from app.models.organization import Organization
from app.models.user import User, UserRole
from fastapi import status
from fastapi.testclient import TestClient


class TestColdChainMonitoringEpicE07:
    """Kiểm thử tính năng Giám sát chuỗi lạnh (Epic E-07: User Stories S-40, S-41, S-43, S-45)."""

    def _setup_entities(self, db_session):
        # 1. Tạo tổ chức Vận chuyển lạnh (Transporter)
        carrier_org = Organization(name="Công ty Vận Tải Lạnh Mekong ColdChain", code="CARRIER_MK")
        db_session.add(carrier_org)

        # 2. Tạo tổ chức Vùng trồng (Farm)
        farm_org = Organization(name="HTX Nông Sản Đà Lạt", code="FARM_DL")
        db_session.add(farm_org)
        db_session.flush()

        # 3. Tạo tài khoản Transporter
        carrier_user = User(
            email="logistics@mekongcold.vn",
            hashed_password="hashed_secret_test",
            full_name="Nguyễn Văn Tài Xế",
            role=UserRole.LOGISTICS.value,
            organization_id=carrier_org.id,
            is_active=True,
        )
        db_session.add(carrier_user)

        # 4. Tạo tài khoản Inspector (Cán bộ kiểm tra)
        inspector_user = User(
            email="inspector@gov.vn",
            hashed_password="hashed_secret_test",
            full_name="Cán Bộ Kiểm Tra An Toàn",
            role=UserRole.INSPECTOR.value,
            organization_id=None,
            is_active=True,
        )
        db_session.add(inspector_user)

        # 5. Tạo 2 lô hàng đang vận chuyển
        batch1 = Batch(
            batch_code="BATCH-COLD-01",
            product_name="Dâu Tây Đà Lạt Xuất Khẩu",
            organization_id=farm_org.id,
            initial_quantity=500.0,
            remaining_quantity=500.0,
            unit="kg",
        )
        batch2 = Batch(
            batch_code="BATCH-COLD-02",
            product_name="Xà Lách Thuỷ Canh Cao Cấp",
            organization_id=farm_org.id,
            initial_quantity=300.0,
            remaining_quantity=300.0,
            unit="kg",
        )
        db_session.add_all([batch1, batch2])
        db_session.commit()

        token_carrier = create_access_token(
            subject=carrier_user.email,
            role=carrier_user.role,
            organization_id=carrier_org.id,
        )
        token_inspector = create_access_token(
            subject=inspector_user.email,
            role=inspector_user.role,
            organization_id=None,
        )

        return {
            "carrier_org": carrier_org,
            "carrier_user": carrier_user,
            "batch1": batch1,
            "batch2": batch2,
            "token_carrier": token_carrier,
            "token_inspector": token_inspector,
        }

    def test_s40_create_transport_trip_with_batches(self, client: TestClient, db_session):
        """User Story S-40: Tạo chuyến vận chuyển gồm mã chuyến, mã xe lạnh và danh sách lô hàng."""
        data = self._setup_entities(db_session)
        headers = {"Authorization": f"Bearer {data['token_carrier']}"}

        payload = {
            "vehicle_code": "REEFER-51D-999.88",
            "batch_ids": [data["batch1"].id, data["batch2"].id],
            "driver_name": "Trần Văn Lái Xe",
            "min_temperature": 2.0,
            "max_temperature": 8.0,
        }

        resp = client.post("/api/v1/cold-chain/trips", json=payload, headers=headers)
        assert resp.status_code == status.HTTP_201_CREATED
        trip_data = resp.json()

        assert trip_data["vehicle_code"] == "REEFER-51D-999.88"
        assert trip_data["trip_code"].startswith("TRIP-")
        assert len(trip_data["batches"]) == 2
        batch_codes = [b["batch_code"] for b in trip_data["batches"]]
        assert "BATCH-COLD-01" in batch_codes
        assert "BATCH-COLD-02" in batch_codes

        # Kiểm tra sự kiện khởi hành được ghi vào Hash Chain của 2 lô
        events = (
            db_session.query(ChainEvent)
            .filter(ChainEvent.batch_id.in_([data["batch1"].id, data["batch2"].id]))
            .all()
        )
        assert len(events) >= 2
        assert any("Khởi hành chuyến xe lạnh" in e.event_data for e in events)

    def test_s41_ingest_telemetry_ignore_older_timestamps(self, client: TestClient, db_session):
        """User Story S-41: Nhận mảng dữ liệu nhiệt độ và bỏ qua các bản ghi có timestamp cũ hơn bản ghi mới nhất."""
        data = self._setup_entities(db_session)
        headers = {"Authorization": f"Bearer {data['token_carrier']}"}

        # 1. Tạo chuyến xe
        trip_res = client.post(
            "/api/v1/cold-chain/trips",
            json={"vehicle_code": "REEFER-T1", "batch_ids": [data["batch1"].id]},
            headers=headers,
        )
        trip_id = trip_res.json()["id"]

        now = datetime.now(UTC)
        t0 = (now - timedelta(hours=2)).isoformat()
        t1 = (now - timedelta(hours=1, minutes=30)).isoformat()
        t2 = (now - timedelta(hours=1)).isoformat()

        # Đợt 1: Gửi 3 điểm đo hợp lệ (t0 < t1 < t2)
        batch1_readings = [
            {"trip_id": trip_id, "timestamp": t0, "temperature": 4.5},
            {"trip_id": trip_id, "timestamp": t1, "temperature": 5.0},
            {"trip_id": trip_id, "timestamp": t2, "temperature": 4.8},
        ]
        res1 = client.post("/api/v1/cold-chain/telemetry", json=batch1_readings, headers=headers)
        assert res1.status_code == status.HTTP_200_OK
        assert res1.json()["accepted_count"] == 3
        assert res1.json()["ignored_count"] == 0

        # Đợt 2: Gửi lại điểm t1 (cũ hơn t2) và điểm mới t3
        t3 = now.isoformat()
        batch2_readings = [
            {"trip_id": trip_id, "timestamp": t1, "temperature": 5.2},  # CŨ -> BỎ QUA
            {"trip_id": trip_id, "timestamp": t3, "temperature": 5.1},  # MỚI -> NHẬN
        ]
        res2 = client.post("/api/v1/cold-chain/telemetry", json=batch2_readings, headers=headers)
        assert res2.status_code == status.HTTP_200_OK
        assert res2.json()["accepted_count"] == 1
        assert res2.json()["ignored_count"] == 1

    def test_s43_temporary_fluctuation_under_30_minutes_not_violated(self, client: TestClient, db_session):
        """User Story S-43: Nhiệt độ vượt ngưỡng nhất thời (dưới 30 phút, ví dụ mở cửa xe 15 phút) KHÔNG bị coi là vi phạm."""
        data = self._setup_entities(db_session)
        headers = {"Authorization": f"Bearer {data['token_carrier']}"}

        trip_res = client.post(
            "/api/v1/cold-chain/trips",
            json={"vehicle_code": "REEFER-DOOR-OPEN", "batch_ids": [data["batch1"].id], "max_temperature": 8.0},
            headers=headers,
        )
        trip_id = trip_res.json()["id"]

        now = datetime.now(UTC)
        # Giả lập mở cửa xe trong 15 phút: nhiệt độ tăng lên 14°C, sau đó đóng cửa hạ về 4°C
        readings = [
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=0)).isoformat(), "temperature": 4.0},
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=5)).isoformat(), "temperature": 12.0},  # Vượt ngưỡng
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=15)).isoformat(), "temperature": 14.5},  # Đỉnh
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=20)).isoformat(), "temperature": 10.0},  # Vượt 15p
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=25)).isoformat(), "temperature": 4.0},   # Trở lại bình thường
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=60)).isoformat(), "temperature": 4.2},
        ]

        resp = client.post("/api/v1/cold-chain/telemetry", json=readings, headers=headers)
        assert resp.status_code == status.HTTP_200_OK
        # Vì chỉ vượt ngưỡng 15 phút (< 30 phút), không có vi phạm nào được kích hoạt
        assert len(resp.json()["violations_detected"]) == 0

        # Kiểm tra bảng cold_chain_violations trong DB phải rỗng
        violations = db_session.query(ColdChainViolation).filter_by(trip_id=trip_id).all()
        assert len(violations) == 0

    def test_s43_s45_continuous_violation_over_30_minutes_triggers_alert_and_hash_chain(
        self, client: TestClient, db_session
    ):
        """
        User Story S-43 & S-45:
        - Nhiệt độ vượt ngưỡng liên tục trên 30 phút (ví dụ 40 phút) -> Kích hoạt sự kiện vi phạm chuỗi lạnh.
        - Tự động ghi vi phạm vào Hash Chain của TOÀN BỘ các lô hàng trên chuyến xe.
        """
        data = self._setup_entities(db_session)
        headers = {"Authorization": f"Bearer {data['token_carrier']}"}

        trip_res = client.post(
            "/api/v1/cold-chain/trips",
            json={
                "vehicle_code": "REEFER-FAIL-COOLING",
                "batch_ids": [data["batch1"].id, data["batch2"].id],
                "max_temperature": 8.0,
            },
            headers=headers,
        )
        trip_id = trip_res.json()["id"]

        now = datetime.now(UTC)
        # Giả lập hỏng máy lạnh: nhiệt độ vượt 8°C liên tục từ phút 10 đến phút 50 (kéo dài 40 phút > 30 phút)
        readings = [
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=0)).isoformat(), "temperature": 4.0},
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=10)).isoformat(), "temperature": 9.5},   # Bắt đầu vượt
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=25)).isoformat(), "temperature": 15.0},  # Đỉnh 15°C
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=40)).isoformat(), "temperature": 14.0},
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=50)).isoformat(), "temperature": 11.0},  # Kết thúc đợt (40p)
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=55)).isoformat(), "temperature": 5.0},   # Sửa xong máy lạnh
        ]

        resp = client.post("/api/v1/cold-chain/telemetry", json=readings, headers=headers)
        assert resp.status_code == status.HTTP_200_OK
        res_data = resp.json()

        # Hệ thống phải phát hiện đúng 1 sự kiện vi phạm
        assert len(res_data["violations_detected"]) == 1
        v = res_data["violations_detected"][0]
        assert v["duration_minutes"] == 40.0
        assert v["peak_temperature"] == 15.0
        assert v["hash_recorded"] is True

        # S-45: Kiểm tra Hash Chain của CẢ HAI lô hàng (batch1 và batch2) đều được ghi sự kiện vi phạm
        events_batch1 = (
            db_session.query(ChainEvent)
            .filter(ChainEvent.batch_id == data["batch1"].id, ChainEvent.event_type == "COLD_CHAIN_VIOLATION")
            .all()
        )
        events_batch2 = (
            db_session.query(ChainEvent)
            .filter(ChainEvent.batch_id == data["batch2"].id, ChainEvent.event_type == "COLD_CHAIN_VIOLATION")
            .all()
        )
        assert len(events_batch1) >= 1
        assert len(events_batch2) >= 1
        assert "VI PHẠM CHUỖI LẠNH" in events_batch1[0].event_data.upper()
        assert "VI PHẠM CHUỖI LẠNH" in events_batch2[0].event_data.upper()

    def test_s43_merge_two_violations_under_5_minutes_gap(self, client: TestClient, db_session):
        """
        User Story S-43: Hai lần vượt ngưỡng cách nhau dưới 5 phút thì tự động GỘP THÀNH 1 LẦN VI PHẠM DUY NHẤT.
        Ví dụ:
        - Đợt 1: vượt ngưỡng 20 phút (phút 0 -> 20).
        - Nhiệt độ hạ xuống bình thường trong 3 phút (phút 20 -> 23 < 5 phút).
        - Đợt 2: vượt ngưỡng tiếp 15 phút (phút 23 -> 38).
        Tổng cộng gộp lại = 38 phút (>= 30 phút) -> Kích hoạt 1 vi phạm duy nhất!
        """
        data = self._setup_entities(db_session)
        headers = {"Authorization": f"Bearer {data['token_carrier']}"}

        trip_res = client.post(
            "/api/v1/cold-chain/trips",
            json={"vehicle_code": "REEFER-MERGE-TEST", "batch_ids": [data["batch1"].id], "max_temperature": 8.0},
            headers=headers,
        )
        trip_id = trip_res.json()["id"]

        now = datetime.now(UTC)
        readings = [
            # Đợt 1: Phút 0 -> Phút 20 (20 phút vượt ngưỡng, đỉnh 12.0)
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=0)).isoformat(), "temperature": 9.0},
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=10)).isoformat(), "temperature": 12.0},
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=20)).isoformat(), "temperature": 9.5},
            # Khoảng nghỉ: Chỉ 3 phút hạ về 6°C (cách nhau < 5 phút)
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=22)).isoformat(), "temperature": 6.0},
            # Đợt 2: Phút 23 -> Phút 38 (15 phút vượt ngưỡng tiếp, đỉnh 16.0)
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=23)).isoformat(), "temperature": 10.0},
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=30)).isoformat(), "temperature": 16.0},
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=38)).isoformat(), "temperature": 9.0},
            # Sau phút 38 trở lại bình thường
            {"trip_id": trip_id, "timestamp": (now + timedelta(minutes=45)).isoformat(), "temperature": 4.0},
        ]

        resp = client.post("/api/v1/cold-chain/telemetry", json=readings, headers=headers)
        assert resp.status_code == status.HTTP_200_OK
        res_data = resp.json()

        # Hệ thống gộp thành đúng 1 vi phạm duy nhất (vì khoảng cách 3 phút < 5 phút)
        assert len(res_data["violations_detected"]) == 1
        v = res_data["violations_detected"][0]
        # Thời lượng tính từ phút 0 đến phút 38 = 38 phút (>= 30 phút)
        assert v["duration_minutes"] == 38.0
        assert v["peak_temperature"] == 16.0
