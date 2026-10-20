from __future__ import annotations

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.land_plot import LandPlot
from app.models.product import Product
from app.services.database_seeder import run_full_database_seed, seed_database_if_empty
from app.services.hash_chain_service import verify_chain_integrity


def test_database_seeder_full_coverage(db_session: Session, client: TestClient):
    """
    Kiểm thử script seed database:
    1. Nạp thành công sản phẩm, thửa đất, 13 lô hàng, chuỗi hash SHA-256 thật.
    2. Toàn bộ 13 lô hàng đều có chuỗi băm hợp lệ 100% khi chạy verify_chain_integrity.
    3. Tra cứu công khai /api/v1/batches/public/{batch_code} và /public/batches/{batch_code} đều trả về HTTP 200.
    """
    # Chạy seeder trên session DB
    result = run_full_database_seed(db_session, force_reset=True)
    assert result["status"] == "success"
    assert result["total_batches"] >= 12

    # Kiểm tra danh mục sản phẩm
    products = db_session.query(Product).all()
    assert len(products) >= 5

    # Kiểm tra thửa đất
    plots = db_session.query(LandPlot).all()
    assert len(plots) >= 3

    # Kiểm tra tất cả các lô hàng đều có tính toàn vẹn 100%
    batches = db_session.query(Batch).all()
    assert len(batches) >= 12

    for b in batches:
        # Kiểm tra tính toàn vẹn chuỗi Hash SHA-256
        integrity = verify_chain_integrity(db_session, batch_id=b.id)
        assert integrity["valid"] is True, f"Lô {b.batch_code} bị lỗi chuỗi hash: {integrity}"

        # Kiểm tra API tra cứu công khai bằng mã lô tại các định dạng URL
        resp = client.get(f"/api/v1/batches/public/{b.batch_code}")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["batch_code"] == b.batch_code
        assert "product_name" in data
        assert "journey_milestones" in data

        # Kiểm tra route /public/batches/{batch_code}
        resp_root = client.get(f"/public/batches/{b.batch_code}")
        assert resp_root.status_code == status.HTTP_200_OK
        assert resp_root.json()["batch_code"] == b.batch_code

        # Kiểm tra route /api/v1/public/batches/{batch_code}
        resp_v1_pub = client.get(f"/api/v1/public/batches/{b.batch_code}")
        assert resp_v1_pub.status_code == status.HTTP_200_OK

    # Kiểm tra lại hàm seed_database_if_empty khi DB đã có dữ liệu -> Bỏ qua
    res_skip = seed_database_if_empty(db_session)
    assert res_skip["status"] == "skipped"

    # Kiểm tra endpoint POST /api/v1/batches/seed-full-database
    from app.core.security import create_access_token

    admin_token = create_access_token(
        subject="sysadmin@nongsanlanh.gov.vn",
        role="system_admin",
        organization_id=None,
    )
    resp_seed = client.post(
        "/api/v1/batches/seed-full-database",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_seed.status_code == status.HTTP_201_CREATED
    assert resp_seed.json()["status"] in ("success", "skipped")

    # Kiểm tra endpoint GET /api/v1/chain-events
    resp_events = client.get(
        "/api/v1/chain-events",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp_events.status_code == status.HTTP_200_OK
    assert len(resp_events.json()) > 0
