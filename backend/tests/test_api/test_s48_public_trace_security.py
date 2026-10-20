from datetime import UTC, datetime

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.batch_relation import BatchRelation, BatchRelationType
from app.models.cold_chain import TransportTrip, TripBatch, TripStatus
from app.models.land_plot import LandPlot
from app.models.organization import Organization
from app.services.hash_chain_service import record_chain_event


def test_public_batch_trace_success(client: TestClient, db_session: Session):
    """
    AC 1: Người tiêu dùng không cần đăng nhập vẫn có thể tra cứu mã lô hợp lệ qua QR / mã tem.
    AC 3: Trả về các thông tin công khai: Tên sản phẩm, Tên vùng trồng, Tỉnh/thành, Ngày thu hoạch,
          và các mốc hành trình chuỗi cung ứng chính dựa trên sự kiện thực trong DB.
    """
    # 1. Tạo tổ chức và lô hàng
    org = Organization(name="HTX Rau Sạch Đà Lạt", code="HTX-DL-01")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    batch = Batch(
        batch_code="BATCH-S48-TOMATO-01",
        product_name="Cà Chua Cherry Hữu Cơ (VietGAP)",
        organization_id=org.id,
    )
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    # Thêm các sự kiện thực tế trong DB
    t1 = datetime(2026, 10, 15, 7, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 10, 16, 9, 30, 0, tzinfo=UTC)
    t3 = datetime(2026, 10, 17, 14, 0, 0, tzinfo=UTC)

    record_chain_event(
        db=db_session,
        batch_id=batch.id,
        event_type="BATCH_INITIALIZED",
        event_data={"plot": "Vườn Cà Chua A1", "certification": "VietGAP"},
        organization_id=org.id,
        timestamp=t1,
    )
    record_chain_event(
        db=db_session,
        batch_id=batch.id,
        event_type="HARVESTED",
        event_data={"crop": "Cà chua chín mọng"},
        organization_id=org.id,
        timestamp=t2,
    )
    record_chain_event(
        db=db_session,
        batch_id=batch.id,
        event_type="PROCESSING",
        event_data={"step": "Phân loại Grade A"},
        organization_id=org.id,
        timestamp=t3,
    )
    db_session.commit()

    # 2. Gọi API công khai (không truyền Header Authorization)
    response = client.get("/api/v1/batches/public/BATCH-S48-TOMATO-01")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["batch_code"] == "BATCH-S48-TOMATO-01"
    assert data["product_name"] == "Cà Chua Cherry Hữu Cơ (VietGAP)"
    assert data["farm_name"] == "HTX Rau Sạch Đà Lạt"
    assert "province" in data
    assert data["harvest_date"] == "2026-10-16"
    assert data["certification"] == "VietGAP"
    assert "journey_milestones" in data
    assert len(data["journey_milestones"]) == 3
    assert data["is_safe_phi"] is True


def test_public_batch_trace_no_internal_data_leakage(
    client: TestClient, db_session: Session
):
    """
    AC 4 (S-48 & E-08): Tuyệt đối không trả về và không làm lộ:
    - Khối lượng lô / sản lượng
    - Giá bán / doanh thu / chi phí
    - Tên riêng đối tác trung gian / logistics bảo mật kinh doanh
    - Bất kỳ thông tin tài chính hoặc nội bộ nào
    """
    org = Organization(name="Nông Trường Mộc Châu", code="NT-MC-01")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    batch = Batch(
        batch_code="BATCH-SECURE-MC-02",
        product_name="Dâu Tây Giống Nhật",
        organization_id=org.id,
        initial_quantity=500.0,
        remaining_quantity=450.0,
    )
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    response = client.get("/api/v1/batches/public/BATCH-SECURE-MC-02")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Danh sách các trường nhạy cảm TUYỆT ĐỐI KHÔNG ĐƯỢC XUẤT HIỆN
    forbidden_keys = [
        "quantity",
        "qty",
        "weight",
        "price",
        "unit_price",
        "revenue",
        "cost",
        "profit",
        "organization_id",
        "partner_name",
        "buyer",
        "buyer_id",
        "supplier",
        "supplier_id",
        "intermediary_name",
        "transport_partner_id",
        "carrier_name",
    ]

    for key in forbidden_keys:
        assert key not in data, (
            f"LỖI BẢO MẬT: Phát hiện trường nhạy cảm '{key}' bị rò rỉ trong API tra cứu công khai!"
        )

    # Kiểm tra trong các mốc hành trình cũng không để lộ dữ liệu nhạy cảm
    for milestone in data.get("journey_milestones", []):
        for key in forbidden_keys:
            assert key not in milestone


def test_public_batch_trace_with_land_plot(client: TestClient, db_session: Session):
    """
    Kiểm tra tra cứu lô hàng đã liên kết với thửa đất vùng trồng (Land Plot)
    thì hiển thị đúng tên vùng trồng và địa phương (tỉnh/thành).
    """
    org = Organization(name="HTX Nông Nghiệp Thắng Lợi", code="HTX-TL-02")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    plot = LandPlot(
        name="Thửa Đất Số 5 - Vùng Trồng Hữu Cơ",
        area=2.5,
        unit="ha",
        latitude=11.9404,
        longitude=108.4583,
        address="Xã Tu Tra, Huyện Đơn Dương, Tỉnh Lâm Đồng",
        organization_id=org.id,
    )
    db_session.add(plot)
    db_session.commit()
    db_session.refresh(plot)

    batch = Batch(
        batch_code="BATCH-PLOT-TL-03",
        product_name="Dưa Lưới Fuji",
        organization_id=org.id,
        land_plot_id=plot.id,
    )
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    response = client.get("/api/v1/batches/public/BATCH-PLOT-TL-03")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["farm_name"] == "Thửa Đất Số 5 - Vùng Trồng Hữu Cơ"
    assert data["province"] == "Tỉnh Lâm Đồng"


def test_public_batch_trace_not_found(client: TestClient):
    """
    Tra cứu mã lô không tồn tại trong hệ thống -> Trả về 404 Not Found rõ ràng.
    """
    response = client.get("/api/v1/batches/public/BATCH-NONEXISTENT-99999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "không tồn tại" in response.json()["detail"]


def test_anti_scraping_no_public_batch_listing(client: TestClient):
    """
    E-08 (Anti-Scraping): Đối thủ không thể cào / quét toàn bộ danh sách mã lô:
    - Không tồn tại endpoint công khai để lấy danh sách mã lô.
    - Gọi GET /api/v1/batches mà không có auth token thì bị chặn 401 Unauthorized.
    """
    # 1. Gọi endpoint danh sách lô hàng nội bộ mà không có JWT -> 401
    response = client.get("/api/v1/batches")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # 2. Kiểm tra không có endpoint /api/v1/batches/public/ cho phép list
    resp_list = client.get("/api/v1/batches/public")
    assert resp_list.status_code in [
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_405_METHOD_NOT_ALLOWED,
    ]


# ============================================================================
# CÁC TEST MỚI BỔ SUNG CHO S-47 VÀ S-48 THEO YÊU CẦU
# ============================================================================


def test_public_batch_trace_multiple_milestones_with_db_timestamps(
    client: TestClient, db_session: Session
):
    """
    Yêu cầu 1 & 6: Lô thông thường có nhiều mốc với thời gian lấy từ database:
    - Mỗi mốc hành trình phải dùng thời gian tương ứng với bản ghi nguồn.
    - Thao tác vận chuyển chuỗi lạnh lấy từ TransportTrip và phản ánh nhiệt độ thực.
    """
    org = Organization(name="HTX Nông Sản An Toàn", code="HTX-ANTOAN")
    carrier_org = Organization(name="Đơn Vị Logistics Lạnh", code="ORG-COLD-LOG")
    db_session.add_all([org, carrier_org])
    db_session.commit()

    plot = LandPlot(
        name="Vườn Măng Cụt Cầu Đất",
        area=1.8,
        unit="ha",
        latitude=11.9,
        longitude=108.4,
        address="Xã Xuân Trường, Thành phố Đà Lạt, Tỉnh Lâm Đồng",
        organization_id=org.id,
    )
    db_session.add(plot)
    db_session.commit()

    batch = Batch(
        batch_code="BATCH-MILESTONES-REAL-01",
        product_name="Măng Cụt Lục Bình",
        organization_id=org.id,
        land_plot_id=plot.id,
    )
    db_session.add(batch)
    db_session.commit()

    # 1. Sự kiện gieo trồng / khởi tạo
    t_init = datetime(2026, 9, 1, 8, 0, 0, tzinfo=UTC)
    record_chain_event(
        db=db_session,
        batch_id=batch.id,
        event_type="BATCH_INITIALIZED",
        event_data={"plot": "Vườn Măng Cụt Cầu Đất"},
        organization_id=org.id,
        timestamp=t_init,
    )

    # 2. Sự kiện thu hoạch
    t_harvest = datetime(2026, 9, 20, 6, 30, 0, tzinfo=UTC)
    record_chain_event(
        db=db_session,
        batch_id=batch.id,
        event_type="HARVESTED",
        event_data={"note": "Thu hoạch quả đạt độ chín 85%"},
        organization_id=org.id,
        timestamp=t_harvest,
    )

    # 3. Sự kiện sơ chế
    t_proc = datetime(2026, 9, 20, 10, 0, 0, tzinfo=UTC)
    record_chain_event(
        db=db_session,
        batch_id=batch.id,
        event_type="PROCESSING",
        event_data={"note": "Làm sạch và phân loại"},
        organization_id=org.id,
        timestamp=t_proc,
    )

    # 4. Chuyến xe lạnh
    t_trip_start = datetime(2026, 9, 21, 5, 0, 0, tzinfo=UTC)
    t_trip_end = datetime(2026, 9, 21, 11, 30, 0, tzinfo=UTC)
    trip = TransportTrip(
        trip_code="TRIP-COLD-MC-01",
        vehicle_code="XE-LANH-49A",
        carrier_org_id=carrier_org.id,
        min_temperature=4.0,
        max_temperature=8.0,
        status=TripStatus.COMPLETED.value,
        start_time=t_trip_start,
        end_time=t_trip_end,
    )
    db_session.add(trip)
    db_session.flush()

    tb = TripBatch(trip_id=trip.id, batch_id=batch.id)
    db_session.add(tb)
    db_session.commit()

    # Gọi API
    response = client.get(f"/api/v1/batches/public/{batch.batch_code}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["batch_code"] == "BATCH-MILESTONES-REAL-01"
    assert data["harvest_date"] == "2026-09-20"

    milestones = data["journey_milestones"]
    assert len(milestones) == 4

    # Kiểm tra thời gian từng mốc khớp với database
    stages = [m["stage"] for m in milestones]
    assert "Khởi tạo lô hàng" in stages
    assert "Thu hoạch" in stages
    assert "Sơ chế & Phân loại" in stages
    assert "Vận chuyển chuỗi lạnh" in stages

    m_harvest = next(m for m in milestones if m["stage"] == "Thu hoạch")
    assert "2026-09-20 06:30:00" in m_harvest["timestamp"]

    m_trip = next(m for m in milestones if m["stage"] == "Vận chuyển chuỗi lạnh")
    assert "2026-09-21 11:30:00" in m_trip["timestamp"]
    assert "4.0°C - 8.0°C" in m_trip["description"]


def test_public_batch_trace_merged_batch_shows_all_root_origins(
    client: TestClient, db_session: Session
):
    """
    Yêu cầu 3 & 6: Lô gộp từ nhiều vùng trồng thể hiện đầy đủ các nguồn gốc:
    - Batch C được gộp từ Batch A (Thửa 1 - Lâm Đồng) và Batch B (Thửa 2 - Đắk Lắk).
    - Trang công khai phải thể hiện tất cả vùng trồng gốc và địa phương có liên quan.
    """
    org1 = Organization(name="HTX Rau Đà Lạt", code="HTX-DL-MERGE")
    org2 = Organization(name="HTX Cà Phê Buôn Ma Thuột", code="HTX-BMT-MERGE")
    db_session.add_all([org1, org2])
    db_session.commit()

    plot1 = LandPlot(
        name="Thửa Số 1 - Đà Lạt",
        area=1.0,
        unit="ha",
        latitude=11.9,
        longitude=108.4,
        address="Phường 7, Đà Lạt, Tỉnh Lâm Đồng",
        organization_id=org1.id,
    )
    plot2 = LandPlot(
        name="Thửa Số 2 - Cư M'gar",
        area=2.0,
        unit="ha",
        latitude=12.7,
        longitude=108.1,
        address="Xã Ea Tul, Huyện Cư M'gar, Tỉnh Đắk Lắk",
        organization_id=org2.id,
    )
    db_session.add_all([plot1, plot2])
    db_session.commit()

    batch_a = Batch(
        batch_code="BATCH-PARENT-A",
        product_name="Nông Sản Hỗn Hợp",
        organization_id=org1.id,
        land_plot_id=plot1.id,
    )
    batch_b = Batch(
        batch_code="BATCH-PARENT-B",
        product_name="Nông Sản Hỗn Hợp",
        organization_id=org2.id,
        land_plot_id=plot2.id,
    )
    batch_c = Batch(
        batch_code="BATCH-CHILD-C-MERGED",
        product_name="Nông Sản Hỗn Hợp Gộp",
        organization_id=org1.id,
        land_plot_id=None,  # Lô gộp không gắn trực tiếp 1 thửa
    )
    db_session.add_all([batch_a, batch_b, batch_c])
    db_session.commit()

    # Tạo quan hệ gộp (Merge Relations)
    rel1 = BatchRelation(
        parent_batch_id=batch_a.id,
        child_batch_id=batch_c.id,
        relation_type=BatchRelationType.MERGE.value,
        quantity=50.0,
    )
    rel2 = BatchRelation(
        parent_batch_id=batch_b.id,
        child_batch_id=batch_c.id,
        relation_type=BatchRelationType.MERGE.value,
        quantity=50.0,
    )
    db_session.add_all([rel1, rel2])
    db_session.commit()

    # Gọi API công khai của lô gộp Batch C
    response = client.get(f"/api/v1/batches/public/{batch_c.batch_code}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Kiểm tra origins có đầy đủ 2 vùng trồng gốc
    origins = data.get("origins", [])
    assert len(origins) == 2
    origin_names = [o["farm_name"] for o in origins]
    assert "Thửa Số 1 - Đà Lạt" in origin_names
    assert "Thửa Số 2 - Cư M'gar" in origin_names

    # farm_name và province tổng hợp thể hiện đầy đủ
    assert "Thửa Số 1 - Đà Lạt" in data["farm_name"]
    assert "Thửa Số 2 - Cư M'gar" in data["farm_name"]
    assert "Tỉnh Lâm Đồng" in data["province"]
    assert "Tỉnh Đắk Lắk" in data["province"]


def test_public_batch_trace_empty_batch_has_no_fake_milestones_and_no_fake_vietgap(
    client: TestClient, db_session: Session
):
    """
    Yêu cầu 2 & 6: Lô không có dữ liệu công đoạn thì KHÔNG xuất hiện mốc giả,
    không tự ý khẳng định chứng nhận VietGAP nếu database không có bằng chứng.
    """
    org = Organization(name="Cơ Sở Trồng Trọt Mới", code="ORG-NEW-FARM")
    db_session.add(org)
    db_session.commit()

    # Tạo lô hàng hoàn toàn trống: không có ChainEvent, không có Trip, không có Handover
    batch = Batch(
        batch_code="BATCH-EMPTY-NO-FAKE-01",
        product_name="Rau Củ Tươi Thông Thường",
        organization_id=org.id,
    )
    db_session.add(batch)
    db_session.commit()

    response = client.get(f"/api/v1/batches/public/{batch.batch_code}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Không có mốc công đoạn giả
    assert data["journey_milestones"] == [], (
        "LỖI: Lô hàng không có dữ liệu công đoạn nhưng lại xuất hiện mốc giả!"
    )

    # Không tự khẳng định VietGAP khi không có bằng chứng
    assert data["certification"] == "Chưa có thông tin chứng nhận"
    assert "Chưa ghi nhận nhật ký sử dụng vật tư nông nghiệp" in data["phi_message"]


def test_public_batch_trace_lineage_cycle_detection_stops_safely(
    client: TestClient, db_session: Session
):
    """
    Yêu cầu 3 & 6: Lô có dữ liệu bị lỗi hoặc chu trình (Cycle) trong batch_relations
    không gây vòng lặp vô hạn và dừng an toàn.
    """
    org = Organization(name="HTX Thử Nghiệm Chu Trình", code="HTX-CYCLE")
    db_session.add(org)
    db_session.commit()

    batch_x = Batch(
        batch_code="BATCH-CYCLE-X",
        product_name="Dưa Chuột Baby",
        organization_id=org.id,
    )
    batch_y = Batch(
        batch_code="BATCH-CYCLE-Y",
        product_name="Dưa Chuột Baby",
        organization_id=org.id,
    )
    db_session.add_all([batch_x, batch_y])
    db_session.commit()

    # Cố tình tạo chu trình: X là cha của Y, Y là cha của X
    rel_x_to_y = BatchRelation(
        parent_batch_id=batch_x.id,
        child_batch_id=batch_y.id,
        relation_type=BatchRelationType.MERGE.value,
        quantity=10.0,
    )
    rel_y_to_x = BatchRelation(
        parent_batch_id=batch_y.id,
        child_batch_id=batch_x.id,
        relation_type=BatchRelationType.MERGE.value,
        quantity=10.0,
    )
    db_session.add_all([rel_x_to_y, rel_y_to_x])
    db_session.commit()

    # Gọi API: phải kết thúc thành công (200 OK) mà không bị RecursionError hay treo vô hạn
    response = client.get(f"/api/v1/batches/public/{batch_x.batch_code}")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["batch_code"] == "BATCH-CYCLE-X"
