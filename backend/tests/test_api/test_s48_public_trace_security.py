from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.land_plot import LandPlot
from app.models.organization import Organization


def test_public_batch_trace_success(client: TestClient, db_session: Session):
    """
    AC 1: Người tiêu dùng không cần đăng nhập vẫn có thể tra cứu mã lô hợp lệ qua QR / mã tem.
    AC 3: Trả về các thông tin công khai: Tên sản phẩm, Tên vùng trồng, Tỉnh/thành, Ngày thu hoạch,
          và các mốc hành trình chuỗi cung ứng chính.
    """
    # 1. Tạo tổ chức và lô hàng
    org = Organization(name="HTX Rau Sạch Đà Lạt", code="HTX-DL-01")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    batch = Batch(
        batch_code="BATCH-S48-TOMATO-01",
        product_name="Cà Chua Cherry Hữu Cơ",
        organization_id=org.id,
    )
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    # 2. Gọi API công khai (không truyền Header Authorization)
    response = client.get("/api/v1/batches/public/BATCH-S48-TOMATO-01")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["batch_code"] == "BATCH-S48-TOMATO-01"
    assert data["product_name"] == "Cà Chua Cherry Hữu Cơ"
    assert data["farm_name"] == "HTX Rau Sạch Đà Lạt"
    assert "province" in data
    assert "harvest_date" in data
    assert data["certification"] == "VietGAP"
    assert "journey_milestones" in data
    assert len(data["journey_milestones"]) >= 3
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
