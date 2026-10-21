from __future__ import annotations

from datetime import datetime
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models.batch import Batch
from app.models.chain_event import ChainEvent
from app.models.cold_chain import TransportTrip, TripStatus
from app.models.organization import Organization
from app.models.user import User, UserRole


def get_auth_headers(user_email: str, role: str, org_id: int | None) -> dict[str, str]:
    token = create_access_token(subject=user_email, role=role, organization_id=org_id)
    return {"Authorization": f"Bearer {token}"}


class TestFourBugFixesRBAC:
    """
    Bộ kiểm thử cho 4 lỗi logic nghiệp vụ và phân quyền:
    Lỗi 1: Lộ dữ liệu giữa các tổ chức ở endpoint /chain-events (S-05, S-23)
    Lỗi 2: Lô đã bán hết (consumed / sold_out) vẫn tạo được phiếu bàn giao (S-29)
    Lỗi 3: Ai cũng thấy chuyến xe lạnh và quyền Gửi IoT (Phân quyền đơn vị vận chuyển)
    Lỗi 4: Nhật ký an ninh hệ thống S-31 chỉ dành cho Admin, chặn các vai trò khác (HTTP 403)
    """

    @pytest.fixture
    def setup_data(self, db_session: Session):
        org_farm = Organization(id=801, name="Trang Trại Rau Củ Sạch", code="ORG-FARM-801")
        org_carrier_1 = Organization(id=802, name="Hãng Xe Lạnh Việt Nhật", code="ORG-CARRIER-802")
        org_carrier_2 = Organization(id=803, name="Hãng Xe Lạnh Phương Nam", code="ORG-CARRIER-803")
        org_retailer = Organization(id=804, name="Siêu Thị BioMart", code="ORG-RETAIL-804")

        db_session.add_all([org_farm, org_carrier_1, org_carrier_2, org_retailer])
        db_session.flush()

        user_admin = User(
            id=901,
            email="admin@system.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Quản Trị Viên",
            role=UserRole.SYSTEM_ADMIN.value,
            organization_id=None,
            is_active=True,
        )
        user_inspector = User(
            id=902,
            email="inspector@chicuctt.gov.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Thanh Tra Viên",
            role=UserRole.INSPECTOR.value,
            organization_id=None,
            is_active=True,
        )
        user_farm = User(
            id=903,
            email="farmer@farm801.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Chủ Trang Trại",
            role=UserRole.FARM.value,
            organization_id=org_farm.id,
            is_active=True,
        )
        user_carrier_1 = User(
            id=904,
            email="carrier1@logistics802.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Điều Phối Xe Lạnh 1",
            role="carrier",
            organization_id=org_carrier_1.id,
            is_active=True,
        )
        user_carrier_2 = User(
            id=905,
            email="carrier2@logistics803.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Điều Phối Xe Lạnh 2",
            role="carrier",
            organization_id=org_carrier_2.id,
            is_active=True,
        )
        user_retailer = User(
            id=906,
            email="manager@biomart804.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Quản Lý Siêu Thị",
            role=UserRole.RETAILER.value,
            organization_id=org_retailer.id,
            is_active=True,
        )

        db_session.add_all([
            user_admin, user_inspector, user_farm, user_carrier_1, user_carrier_2, user_retailer
        ])
        db_session.flush()

        # Batch 1: Thuộc Farm
        batch_farm = Batch(
            id=8011,
            batch_code="BATCH-FARM-8011",
            product_name="Dâu Tây Đà Lạt",
            organization_id=org_farm.id,
            initial_quantity=500.0,
            remaining_quantity=500.0,
            status="active",
        )
        # Batch 2: Thuộc Retailer đã bán hết (consumed)
        batch_consumed = Batch(
            id=8012,
            batch_code="BATCH-RETAIL-CONSUMED",
            product_name="Xà Lách Thủy Canh",
            organization_id=org_retailer.id,
            initial_quantity=200.0,
            remaining_quantity=0.0,
            status="consumed",
        )
        # Batch 3: Thuộc Retailer số lượng còn lại bằng 0 nhưng status sold_out
        batch_sold_out = Batch(
            id=8013,
            batch_code="BATCH-RETAIL-SOLDOUT",
            product_name="Cà Chua Beef",
            organization_id=org_retailer.id,
            initial_quantity=100.0,
            remaining_quantity=0.0,
            status="sold_out",
        )
        # Batch 4: Thuộc Retailer đang active nhưng số lượng còn lại bằng 0
        batch_zero_qty = Batch(
            id=8014,
            batch_code="BATCH-RETAIL-ZERO",
            product_name="Ớt Chuông Chuẩn VietGAP",
            organization_id=org_retailer.id,
            initial_quantity=100.0,
            remaining_quantity=0.0,
            status="active",
        )
        # Batch 5: Thuộc Carrier 2 (riêng tư của carrier 2 & retailer)
        batch_unrelated = Batch(
            id=8015,
            batch_code="BATCH-CARRIER2-SECRET",
            product_name="Nấm Hương Hữu Cơ",
            organization_id=org_carrier_2.id,
            initial_quantity=300.0,
            remaining_quantity=300.0,
            status="active",
        )

        db_session.add_all([batch_farm, batch_consumed, batch_sold_out, batch_zero_qty, batch_unrelated])
        db_session.flush()

        # Chain Events:
        # Event 1: Farm thu hoạch
        ev_farm = ChainEvent(
            id=8001,
            batch_id=batch_farm.id,
            organization_id=org_farm.id,
            event_type="HARVEST",
            event_data='{"action": "Thu hoạch nông sản"}',
            previous_hash="0" * 64,
            current_hash="hash_8001",
        )
        # Event 2: Carrier 1 vận chuyển
        ev_carrier_1 = ChainEvent(
            id=8002,
            batch_id=batch_farm.id,
            organization_id=org_carrier_1.id,
            event_type="COLD_CHAIN_ALERT",
            event_data='{"action": "Cảnh báo chuỗi lạnh xe 1"}',
            previous_hash="hash_8001",
            current_hash="hash_8002",
        )
        # Event 3: Lô mật của Carrier 2 (hoàn toàn không liên quan đến Farm)
        ev_carrier_2 = ChainEvent(
            id=8003,
            batch_id=batch_unrelated.id,
            organization_id=org_carrier_2.id,
            event_type="CARRIER_SECRET",
            event_data='{"action": "Vi phạm chuỗi lạnh xe 2"}',
            previous_hash="0" * 64,
            current_hash="hash_8003",
        )

        db_session.add_all([ev_farm, ev_carrier_1, ev_carrier_2])
        db_session.flush()

        # Cold chain trips:
        trip_1 = TransportTrip(
            id=8051,
            trip_code="TRIP-CARRIER1-01",
            carrier_org_id=org_carrier_1.id,
            driver_name="Tài Xế Hãng 1",
            vehicle_code="29H-111.11",
            min_temperature=2.0,
            max_temperature=8.0,
            status=TripStatus.IN_TRANSIT.value,
        )
        trip_2 = TransportTrip(
            id=8052,
            trip_code="TRIP-CARRIER2-02",
            carrier_org_id=org_carrier_2.id,
            driver_name="Tài Xế Hãng 2",
            vehicle_code="51D-222.22",
            min_temperature=0.0,
            max_temperature=4.0,
            status=TripStatus.IN_TRANSIT.value,
        )

        db_session.add_all([trip_1, trip_2])
        db_session.commit()

        return {
            "users": {
                "admin": user_admin,
                "inspector": user_inspector,
                "farm": user_farm,
                "carrier_1": user_carrier_1,
                "carrier_2": user_carrier_2,
                "retailer": user_retailer,
            },
            "orgs": {
                "farm": org_farm,
                "carrier_1": org_carrier_1,
                "carrier_2": org_carrier_2,
                "retailer": org_retailer,
            },
            "batches": {
                "farm": batch_farm,
                "consumed": batch_consumed,
                "sold_out": batch_sold_out,
                "zero_qty": batch_zero_qty,
                "unrelated": batch_unrelated,
            },
            "trips": {
                "trip_1": trip_1,
                "trip_2": trip_2,
            },
        }

    # =========================================================================
    # LỖI 1: LỘ DỮ LIỆU GIỮA CÁC TỔ CHỨC Ở ENDPOINT /chain-events (S-05, S-23)
    # =========================================================================
    def test_chain_events_data_isolation(self, client: TestClient, setup_data):
        """
        Quản trị viên và Thanh tra thấy toàn bộ sự kiện.
        Nông hộ chỉ thấy sự kiện thuộc lô của mình hoặc tổ chức mình,
        KHÔNG thấy sự kiện của lô không liên quan (Carrier 2 secret).
        """
        users = setup_data["users"]
        orgs = setup_data["orgs"]

        # 1. Admin thấy toàn bộ
        hdr_admin = get_auth_headers(users["admin"].email, users["admin"].role, None)
        res_admin = client.get("/api/v1/chain-events", headers=hdr_admin)
        assert res_admin.status_code == status.HTTP_200_OK
        admin_event_ids = [e["id"] for e in res_admin.json()]
        assert 8001 in admin_event_ids
        assert 8002 in admin_event_ids
        assert 8003 in admin_event_ids

        # 2. Thanh tra (Inspector) thấy toàn bộ để phục vụ kiểm toán
        hdr_insp = get_auth_headers(users["inspector"].email, users["inspector"].role, None)
        res_insp = client.get("/api/v1/chain-events", headers=hdr_insp)
        assert res_insp.status_code == status.HTTP_200_OK
        insp_event_ids = [e["id"] for e in res_insp.json()]
        assert 8001 in insp_event_ids
        assert 8002 in insp_event_ids
        assert 8003 in insp_event_ids

        # 3. Nông hộ (Farm): Thấy sự kiện của lô mình sở hữu (8001, 8002),
        # KHÔNG THẤY sự kiện của lô không liên quan (8003)
        hdr_farm = get_auth_headers(users["farm"].email, users["farm"].role, orgs["farm"].id)
        res_farm = client.get("/api/v1/chain-events", headers=hdr_farm)
        assert res_farm.status_code == status.HTTP_200_OK
        farm_event_ids = [e["id"] for e in res_farm.json()]
        assert 8001 in farm_event_ids
        assert 8003 not in farm_event_ids, "Sự kiện của tổ chức/lô hàng không liên quan bị lộ cho Farm!"

        # 4. Carrier 2: Thấy sự kiện 8003 của mình, không thấy 8001 của Farm
        hdr_c2 = get_auth_headers(users["carrier_2"].email, users["carrier_2"].role, orgs["carrier_2"].id)
        res_c2 = client.get("/api/v1/chain-events", headers=hdr_c2)
        assert res_c2.status_code == status.HTTP_200_OK
        c2_event_ids = [e["id"] for e in res_c2.json()]
        assert 8003 in c2_event_ids
        assert 8001 not in c2_event_ids

    # =========================================================================
    # LỖI 2: LÔ ĐÃ BÁN HẾT VẪN TẠO ĐƯỢC PHIẾU BÀN GIAO (S-29)
    # =========================================================================
    def test_block_handover_for_consumed_or_zero_qty_batch(self, client: TestClient, setup_data):
        """
        Lô có status in ('consumed', 'sold_out') hoặc remaining_quantity <= 0
        bị chặn tạo phiếu bàn giao với HTTP 400.
        """
        users = setup_data["users"]
        orgs = setup_data["orgs"]
        batches = setup_data["batches"]

        hdr_retailer = get_auth_headers(users["retailer"].email, users["retailer"].role, orgs["retailer"].id)

        # 1. Thử tạo phiếu bàn giao cho lô consumed
        res_consumed = client.post(
            "/api/v1/handovers",
            headers=hdr_retailer,
            json={
                "batch_id": batches["consumed"].id,
                "to_org_id": orgs["farm"].id,
                "temperature": 5.0,
                "notes": "Bàn giao thử lô đã tiêu thụ",
            },
        )
        assert res_consumed.status_code == status.HTTP_400_BAD_REQUEST
        assert "Lô hàng đã tiêu thụ hết (bán hết)" in res_consumed.json()["detail"]

        # 2. Thử tạo phiếu bàn giao cho lô sold_out
        res_sold_out = client.post(
            "/api/v1/handovers",
            headers=hdr_retailer,
            json={
                "batch_id": batches["sold_out"].id,
                "to_org_id": orgs["farm"].id,
                "temperature": 5.0,
                "notes": "Bàn giao thử lô sold_out",
            },
        )
        assert res_sold_out.status_code == status.HTTP_400_BAD_REQUEST
        assert "Lô hàng đã tiêu thụ hết (bán hết)" in res_sold_out.json()["detail"]

        # 3. Thử tạo phiếu bàn giao cho lô có remaining_quantity <= 0 (kể cả khi status là active)
        res_zero = client.post(
            "/api/v1/handovers",
            headers=hdr_retailer,
            json={
                "batch_id": batches["zero_qty"].id,
                "to_org_id": orgs["farm"].id,
                "temperature": 5.0,
                "notes": "Bàn giao thử lô hết khối lượng",
            },
        )
        assert res_zero.status_code == status.HTTP_400_BAD_REQUEST
        assert "Lô hàng đã tiêu thụ hết (bán hết)" in res_zero.json()["detail"]

    # =========================================================================
    # LỖI 3: PHÂN QUYỀN CHUYẾN XE LẠNH VÀ GỬI IOT (ĐƠN VỊ VẬN CHUYỂN)
    # =========================================================================
    def test_trips_carrier_isolation_and_iot_permissions(self, client: TestClient, setup_data):
        """
        - Carrier chỉ thấy chuyến xe do chính tổ chức mình phụ trách.
        - Admin và Inspector thấy toàn bộ.
        - Non-carrier (Farm) bị từ chối khi tạo chuyến xe hoặc gửi IoT/telemetry.
        - Carrier không được truy cập chi tiết chuyến xe của Carrier khác.
        """
        users = setup_data["users"]
        orgs = setup_data["orgs"]
        trips = setup_data["trips"]
        batches = setup_data["batches"]

        # 1. Carrier 1 chỉ thấy trip 1, không thấy trip 2
        hdr_c1 = get_auth_headers(users["carrier_1"].email, users["carrier_1"].role, orgs["carrier_1"].id)
        res_c1 = client.get("/api/v1/cold-chain/trips", headers=hdr_c1)
        assert res_c1.status_code == status.HTTP_200_OK
        c1_trip_ids = [t["id"] for t in res_c1.json()]
        assert trips["trip_1"].id in c1_trip_ids
        assert trips["trip_2"].id not in c1_trip_ids, "Carrier 1 thấy chuyến xe của Carrier 2!"

        # 2. Carrier 2 chỉ thấy trip 2, không thấy trip 1
        hdr_c2 = get_auth_headers(users["carrier_2"].email, users["carrier_2"].role, orgs["carrier_2"].id)
        res_c2 = client.get("/api/v1/cold-chain/trips", headers=hdr_c2)
        assert res_c2.status_code == status.HTTP_200_OK
        c2_trip_ids = [t["id"] for t in res_c2.json()]
        assert trips["trip_2"].id in c2_trip_ids
        assert trips["trip_1"].id not in c2_trip_ids

        # 3. Admin & Inspector thấy cả 2 trips
        hdr_admin = get_auth_headers(users["admin"].email, users["admin"].role, None)
        res_admin = client.get("/api/v1/cold-chain/trips", headers=hdr_admin)
        assert res_admin.status_code == status.HTTP_200_OK
        admin_trip_ids = [t["id"] for t in res_admin.json()]
        assert trips["trip_1"].id in admin_trip_ids
        assert trips["trip_2"].id in admin_trip_ids

        # 4. Carrier 1 cố tình truy cập chi tiết chuyến xe của Carrier 2 -> 403 Forbidden
        res_cross_detail = client.get(f"/api/v1/cold-chain/trips/{trips['trip_2'].id}", headers=hdr_c1)
        assert res_cross_detail.status_code == status.HTTP_403_FORBIDDEN

        # 5. Farm cố tình tạo chuyến xe lạnh -> 403 Forbidden
        hdr_farm = get_auth_headers(users["farm"].email, users["farm"].role, orgs["farm"].id)
        res_farm_create = client.post(
            "/api/v1/cold-chain/trips",
            headers=hdr_farm,
            json={
                "vehicle_code": "49A-999.99",
                "batch_ids": [batches["farm"].id],
                "trip_code": "TRIP-FARM-ILLEGAL",
                "carrier_org_id": orgs["farm"].id,
                "driver_name": "Nông dân lái xe",
                "min_temperature": 2.0,
                "max_temperature": 8.0,
            },
        )
        assert res_farm_create.status_code == status.HTTP_403_FORBIDDEN

        # 6. Farm cố tình gửi IoT / chạy kịch bản giả lập sensor -> 403 Forbidden
        res_farm_iot = client.post(
            f"/api/v1/cold-chain/trips/{trips['trip_1'].id}/simulate-scenario/1",
            headers=hdr_farm,
            json={"reset_previous_telemetry": True},
        )
        assert res_farm_iot.status_code == status.HTTP_403_FORBIDDEN

    # =========================================================================
    # LỖI 4: NHẬT KÝ AN NINH HỆ THỐNG S-31 CHỈ DÀNH CHO ADMIN
    # =========================================================================
    def test_audit_security_logs_admin_only(self, client: TestClient, setup_data):
        """
        Chỉ Admin được xem /audit/security-logs (HTTP 200).
        Các vai trò khác (Farm, Carrier, Inspector) đều bị chặn 403 Forbidden.
        """
        users = setup_data["users"]
        orgs = setup_data["orgs"]

        # 1. Admin truy cập thành công
        hdr_admin = get_auth_headers(users["admin"].email, users["admin"].role, None)
        res_admin = client.get("/api/v1/audit/security-logs", headers=hdr_admin)
        assert res_admin.status_code == status.HTTP_200_OK

        # 2. Inspector bị chặn (HTTP 403)
        hdr_insp = get_auth_headers(users["inspector"].email, users["inspector"].role, None)
        res_insp = client.get("/api/v1/audit/security-logs", headers=hdr_insp)
        assert res_insp.status_code == status.HTTP_403_FORBIDDEN

        # 3. Farm bị chặn (HTTP 403)
        hdr_farm = get_auth_headers(users["farm"].email, users["farm"].role, orgs["farm"].id)
        res_farm = client.get("/api/v1/audit/security-logs", headers=hdr_farm)
        assert res_farm.status_code == status.HTTP_403_FORBIDDEN

        # 4. Carrier bị chặn (HTTP 403)
        hdr_carrier = get_auth_headers(users["carrier_1"].email, users["carrier_1"].role, orgs["carrier_1"].id)
        res_carrier = client.get("/api/v1/audit/security-logs", headers=hdr_carrier)
        assert res_carrier.status_code == status.HTTP_403_FORBIDDEN
