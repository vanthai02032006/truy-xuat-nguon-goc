from __future__ import annotations

import pytest
from app.core.security import create_access_token, get_password_hash
from app.models.batch import Batch
from app.models.batch_relation import BatchRelation, BatchRelationType
from app.models.chain_event import ChainEvent
from app.models.land_plot import LandPlot
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.services.hash_chain_service import verify_chain_integrity
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def get_auth_headers(user_email: str, role: str, org_id: int | None) -> dict[str, str]:
    token = create_access_token(subject=user_email, role=role, organization_id=org_id)
    return {"Authorization": f"Bearer {token}"}


class TestS17S18S19SplitMerge:
    @pytest.fixture
    def split_merge_seed(self, db_session: Session) -> dict:
        """Khởi tạo dữ liệu kiểm thử độc lập cho User Story S-17, S-18, S-19."""
        # 1. Hai tổ chức
        org_a = Organization(
            id=101, name="Hợp tác xã Nông trại Xanh", code="ORG-FARM-XANH"
        )
        org_b = Organization(
            id=102, name="Doanh nghiệp Bán lẻ Vinamart", code="ORG-RETAIL-VINA"
        )
        db_session.add_all([org_a, org_b])
        db_session.flush()

        # 2. Thửa đất
        plot = LandPlot(
            id=201,
            name="Thửa đất A1 - Đồi Cà Chua",
            area=5000.0,
            latitude=11.75,
            longitude=108.45,
            address="Đức Trọng, Lâm Đồng",
            organization_id=org_a.id,
        )
        db_session.add(plot)
        db_session.flush()

        # 3. Người dùng
        user_a = User(
            id=301,
            email="farmer_a@xanhfarm.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Nguyễn Văn A (Farm)",
            role=UserRole.FARM.value,
            organization_id=org_a.id,
            is_active=True,
        )
        user_b = User(
            id=302,
            email="manager_b@vinamart.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Trần Thị B (Retail)",
            role=UserRole.RETAILER.value,
            organization_id=org_b.id,
            is_active=True,
        )
        inspector = User(
            id=303,
            email="inspector@kiemdinh.gov.vn",
            hashed_password=get_password_hash("pass123"),
            full_name="Vũ Cán Bộ Kiểm Tra",
            role=UserRole.INSPECTOR.value,
            organization_id=None,
            is_active=True,
        )
        db_session.add_all([user_a, user_b, inspector])
        db_session.flush()

        # 4. Các lô hàng ban đầu
        # Lô 1 của Org A: 100 kg Cà chua Beef
        batch_parent = Batch(
            id=401,
            batch_code="B-TOM-100KG",
            product_name="Cà chua Beef Đà Lạt",
            organization_id=org_a.id,
            land_plot_id=plot.id,
            status="active",
            initial_quantity=100.0,
            remaining_quantity=100.0,
            unit="kg",
        )
        # Lô 2 của Org A: Đang chờ xác nhận bàn giao
        batch_pending = Batch(
            id=402,
            batch_code="B-TOM-PENDING",
            product_name="Cà chua Beef Đà Lạt",
            organization_id=org_a.id,
            land_plot_id=plot.id,
            status="chờ xác nhận",
            initial_quantity=50.0,
            remaining_quantity=50.0,
            unit="kg",
        )
        # Lô 3 & 4 của Org A: Dưa lưới Huỳnh Long (chuẩn bị để gộp)
        batch_melon_1 = Batch(
            id=403,
            batch_code="B-MELON-01",
            product_name="Dưa lưới Huỳnh Long",
            organization_id=org_a.id,
            land_plot_id=plot.id,
            status="active",
            initial_quantity=40.0,
            remaining_quantity=40.0,
            unit="kg",
        )
        batch_melon_2 = Batch(
            id=404,
            batch_code="B-MELON-02",
            product_name="Dưa lưới Huỳnh Long",
            organization_id=org_a.id,
            land_plot_id=plot.id,
            status="active",
            initial_quantity=60.0,
            remaining_quantity=60.0,
            unit="kg",
        )
        # Lô 5 của Org A: Dâu tây New Zealand (khác loại sản phẩm)
        batch_berry = Batch(
            id=405,
            batch_code="B-BERRY-01",
            product_name="Dâu tây New Zealand",
            organization_id=org_a.id,
            land_plot_id=plot.id,
            status="active",
            initial_quantity=30.0,
            remaining_quantity=30.0,
            unit="kg",
        )

        db_session.add_all(
            [
                batch_parent,
                batch_pending,
                batch_melon_1,
                batch_melon_2,
                batch_berry,
            ]
        )
        db_session.commit()

        return {
            "org_a": org_a,
            "org_b": org_b,
            "plot": plot,
            "user_a": user_a,
            "user_b": user_b,
            "inspector": inspector,
            "batch_parent": batch_parent,
            "batch_pending": batch_pending,
            "batch_melon_1": batch_melon_1,
            "batch_melon_2": batch_melon_2,
            "batch_berry": batch_berry,
        }

    # =========================================================================
    # 1. TIÊU CHÍ S-17 & S-18: TÁCH LÔ NÔNG SẢN (SPLIT)
    # =========================================================================

    def test_split_batch_success(
        self, client: TestClient, db_session: Session, split_merge_seed: dict
    ):
        """
        Tách lô mẹ 100 kg thành 2 lô con (35 kg và 40 kg):
        - Tổng khối lượng tách = 75 kg.
        - Khối lượng còn lại của lô mẹ giảm còn 25 kg.
        - Sinh ra 2 lô con mới kế thừa sản phẩm và thửa đất.
        - Lưu vết quan hệ cha-con vào bảng batch_relations (SPLIT).
        - Ghi nhận sự kiện chuỗi hash cho cả mẹ và các con.
        """
        headers_a = get_auth_headers(
            split_merge_seed["user_a"].email,
            split_merge_seed["user_a"].role,
            split_merge_seed["org_a"].id,
        )

        payload = {
            "splits": [
                {"quantity": 35.0, "notes": "Đóng thùng loại 1 xuất khẩu"},
                {"quantity": 40.0, "notes": "Đóng thùng loại 2 siêu thị"},
            ],
            "notes": "Tách lô sau khi phân loại tại xưởng",
        }

        resp = client.post(
            f"/api/v1/batches/{split_merge_seed['batch_parent'].id}/split",
            json=payload,
            headers=headers_a,
        )
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()

        assert data["total_split_quantity"] == 75.0
        assert data["parent_batch"]["remaining_quantity"] == 25.0
        assert len(data["child_batches"]) == 2

        child_1 = data["child_batches"][0]
        child_2 = data["child_batches"][1]

        # Kiểm tra kế thừa sản phẩm và thửa đất
        assert child_1["product_name"] == "Cà chua Beef Đà Lạt"
        assert child_1["land_plot_id"] == split_merge_seed["plot"].id
        assert child_1["initial_quantity"] == 35.0
        assert child_1["remaining_quantity"] == 35.0
        assert child_1["unit"] == "kg"
        assert child_1["batch_code"] != split_merge_seed["batch_parent"].batch_code

        assert child_2["initial_quantity"] == 40.0
        assert child_2["remaining_quantity"] == 40.0

        # Kiểm tra Database
        db_session.expire_all()
        parent_db = (
            db_session.query(Batch)
            .filter_by(id=split_merge_seed["batch_parent"].id)
            .first()
        )
        assert parent_db.remaining_quantity == 25.0

        # Kiểm tra bảng batch_relations
        relations = (
            db_session.query(BatchRelation)
            .filter_by(parent_batch_id=parent_db.id)
            .all()
        )
        assert len(relations) == 2
        for r in relations:
            assert r.relation_type == BatchRelationType.SPLIT.value
            assert r.quantity in [35.0, 40.0]

        # Kiểm tra Chuỗi Hash
        chain_parent = (
            db_session.query(ChainEvent).filter_by(batch_id=parent_db.id).all()
        )
        assert any(e.event_type == "BATCH_SPLIT_PARENT" for e in chain_parent)
        assert verify_chain_integrity(db_session, parent_db.id)["valid"] is True

    def test_split_batch_exceeding_remaining_quantity(
        self, client: TestClient, db_session: Session, split_merge_seed: dict
    ):
        """Tổng khối lượng các lô con vượt quá khối lượng còn lại của lô mẹ -> 400 Bad Request."""
        headers_a = get_auth_headers(
            split_merge_seed["user_a"].email,
            split_merge_seed["user_a"].role,
            split_merge_seed["org_a"].id,
        )

        # Lô mẹ 100 kg, cố tình tách 60 kg + 45 kg = 105 kg
        payload = {
            "splits": [
                {"quantity": 60.0},
                {"quantity": 45.0},
            ]
        }
        resp = client.post(
            f"/api/v1/batches/{split_merge_seed['batch_parent'].id}/split",
            json=payload,
            headers=headers_a,
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "vượt quá khối lượng còn lại của lô mẹ" in resp.json()["detail"]

        # Đảm bảo khối lượng lô mẹ không bị trừ
        db_session.expire_all()
        parent = (
            db_session.query(Batch)
            .filter_by(id=split_merge_seed["batch_parent"].id)
            .first()
        )
        assert parent.remaining_quantity == 100.0

    def test_split_batch_blocked_when_pending_handover(
        self, client: TestClient, db_session: Session, split_merge_seed: dict
    ):
        """Lô hàng đang ở trạng thái 'chờ xác nhận' bàn giao thì không được phép tách lô."""
        headers_a = get_auth_headers(
            split_merge_seed["user_a"].email,
            split_merge_seed["user_a"].role,
            split_merge_seed["org_a"].id,
        )
        payload = {"splits": [{"quantity": 10.0}]}
        resp = client.post(
            f"/api/v1/batches/{split_merge_seed['batch_pending'].id}/split",
            json=payload,
            headers=headers_a,
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "đang trong quá trình bàn giao chờ xác nhận" in resp.json()["detail"]

    def test_split_batch_forbidden_cross_tenant(
        self, client: TestClient, db_session: Session, split_merge_seed: dict
    ):
        """Tổ chức B không thể thực hiện tách lô thuộc sở hữu của tổ chức A."""
        headers_b = get_auth_headers(
            split_merge_seed["user_b"].email,
            split_merge_seed["user_b"].role,
            split_merge_seed["org_b"].id,
        )
        payload = {"splits": [{"quantity": 10.0}]}
        resp = client.post(
            f"/api/v1/batches/{split_merge_seed['batch_parent'].id}/split",
            json=payload,
            headers=headers_b,
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    # =========================================================================
    # 2. TIÊU CHÍ S-19: GỘP LÔ NÔNG SẢN CÙNG SẢN PHẨM (MERGE) & TRÁNH DEADLOCK
    # =========================================================================

    def test_merge_batches_success(
        self, client: TestClient, db_session: Session, split_merge_seed: dict
    ):
        """
        Gộp 2 lô Dưa lưới Huỳnh Long:
        - Lô 1 (40 kg): trích 25 kg -> còn 15 kg
        - Lô 2 (60 kg): trích 45 kg -> còn 15 kg
        - Tổng khối lượng lô gộp mới = 70 kg.
        - Khóa các dòng theo thứ tự ID cố định tránh deadlock.
        - Tạo bản ghi quan hệ MERGE và ghi chuỗi hash.
        """
        headers_a = get_auth_headers(
            split_merge_seed["user_a"].email,
            split_merge_seed["user_a"].role,
            split_merge_seed["org_a"].id,
        )

        payload = {
            "sources": [
                {
                    "batch_id": split_merge_seed["batch_melon_2"].id,
                    "quantity": 45.0,
                },
                {
                    "batch_id": split_merge_seed["batch_melon_1"].id,
                    "quantity": 25.0,
                },
            ],
            "notes": "Gộp 2 sọt dưa lưới đạt size VIP chuẩn siêu thị",
        }

        resp = client.post("/api/v1/batches/merge", json=payload, headers=headers_a)
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()

        assert data["total_merged_quantity"] == 70.0
        merged = data["merged_batch"]
        assert merged["product_name"] == "Dưa lưới Huỳnh Long"
        assert merged["initial_quantity"] == 70.0
        assert merged["remaining_quantity"] == 70.0

        # Kiểm tra Database: Các lô mẹ đã bị trừ tương ứng
        db_session.expire_all()
        m1 = (
            db_session.query(Batch)
            .filter_by(id=split_merge_seed["batch_melon_1"].id)
            .first()
        )
        m2 = (
            db_session.query(Batch)
            .filter_by(id=split_merge_seed["batch_melon_2"].id)
            .first()
        )
        assert m1.remaining_quantity == 15.0
        assert m2.remaining_quantity == 15.0

        # Kiểm tra bảng batch_relations
        relations = (
            db_session.query(BatchRelation).filter_by(child_batch_id=merged["id"]).all()
        )
        assert len(relations) == 2
        for r in relations:
            assert r.relation_type == BatchRelationType.MERGE.value
            assert r.quantity in [25.0, 45.0]

    def test_merge_batches_different_products_rejected(
        self, client: TestClient, db_session: Session, split_merge_seed: dict
    ):
        """Cố tình gộp 2 lô khác loại sản phẩm (Dưa lưới và Dâu tây) -> 400 Bad Request."""
        headers_a = get_auth_headers(
            split_merge_seed["user_a"].email,
            split_merge_seed["user_a"].role,
            split_merge_seed["org_a"].id,
        )
        payload = {
            "sources": [
                {
                    "batch_id": split_merge_seed["batch_melon_1"].id,
                    "quantity": 10.0,
                },
                {
                    "batch_id": split_merge_seed["batch_berry"].id,
                    "quantity": 10.0,
                },
            ]
        }
        resp = client.post("/api/v1/batches/merge", json=payload, headers=headers_a)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "CÙNG loại sản phẩm" in resp.json()["detail"]

    def test_merge_batches_exceeding_source_quantity_rejected(
        self, client: TestClient, db_session: Session, split_merge_seed: dict
    ):
        """Khối lượng trích xuất vượt quá khối lượng còn lại của lô mẹ -> 400 Bad Request."""
        headers_a = get_auth_headers(
            split_merge_seed["user_a"].email,
            split_merge_seed["user_a"].role,
            split_merge_seed["org_a"].id,
        )
        payload = {
            "sources": [
                {
                    "batch_id": split_merge_seed["batch_melon_1"].id,
                    "quantity": 50.0,
                },  # Chỉ có 40 kg
                {
                    "batch_id": split_merge_seed["batch_melon_2"].id,
                    "quantity": 10.0,
                },
            ]
        }
        resp = client.post("/api/v1/batches/merge", json=payload, headers=headers_a)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "vượt quá khối lượng còn lại" in resp.json()["detail"]

    # =========================================================================
    # 3. TIÊU CHÍ ĐỒ THỊ PHẢ HỆ (GENEALOGY GRAPH LINEAGE)
    # =========================================================================

    def test_batch_lineage_graph(
        self, client: TestClient, db_session: Session, split_merge_seed: dict
    ):
        """
        Kiểm tra API truy vấn đồ thị phả hệ /lineage:
        - Tách lô mẹ -> lô con mang quan hệ cha.
        - Lô con kiểm tra lineage thấy parents chứa lô mẹ.
        - Lô mẹ kiểm tra lineage thấy children chứa các lô con.
        """
        headers_a = get_auth_headers(
            split_merge_seed["user_a"].email,
            split_merge_seed["user_a"].role,
            split_merge_seed["org_a"].id,
        )

        # 1. Tách lô mẹ
        split_resp = client.post(
            f"/api/v1/batches/{split_merge_seed['batch_parent'].id}/split",
            json={"splits": [{"quantity": 20.0}, {"quantity": 30.0}]},
            headers=headers_a,
        )
        child_id = split_resp.json()["child_batches"][0]["id"]

        # 2. Truy vấn phả hệ của lô con -> Phải thấy cha là batch_parent
        child_lineage = client.get(
            f"/api/v1/batches/{child_id}/lineage", headers=headers_a
        )
        assert child_lineage.status_code == status.HTTP_200_OK
        data_c = child_lineage.json()
        assert len(data_c["parents"]) == 1
        assert (
            data_c["parents"][0]["parent_batch_id"]
            == split_merge_seed["batch_parent"].id
        )
        assert data_c["parents"][0]["relation_type"] == "SPLIT"
        assert data_c["parents"][0]["quantity"] == 20.0

        # 3. Truy vấn phả hệ của lô mẹ -> Phải thấy 2 children
        parent_lineage = client.get(
            f"/api/v1/batches/{split_merge_seed['batch_parent'].id}/lineage",
            headers=headers_a,
        )
        assert parent_lineage.status_code == status.HTTP_200_OK
        data_p = parent_lineage.json()
        assert len(data_p["children"]) == 2

    # =========================================================================
    # 4. KIỂM TRA PHÂN QUYỀN INSPECTOR (CHỈ ĐỌC, CHẶN GHI)
    # =========================================================================

    def test_inspector_cannot_split_or_merge(
        self, client: TestClient, db_session: Session, split_merge_seed: dict
    ):
        """Cán bộ kiểm tra (Inspector) xem được lineage nhưng bị chặn gọi split / merge (403)."""
        headers_insp = get_auth_headers(
            split_merge_seed["inspector"].email,
            split_merge_seed["inspector"].role,
            None,
        )

        # Inspector xem lineage -> 200 OK
        resp_view = client.get(
            f"/api/v1/batches/{split_merge_seed['batch_parent'].id}/lineage",
            headers=headers_insp,
        )
        assert resp_view.status_code == status.HTTP_200_OK

        # Inspector cố tình tách lô -> 403 Forbidden
        resp_split = client.post(
            f"/api/v1/batches/{split_merge_seed['batch_parent'].id}/split",
            json={"splits": [{"quantity": 10.0}]},
            headers=headers_insp,
        )
        assert resp_split.status_code == status.HTTP_403_FORBIDDEN

        # Inspector cố tình gộp lô -> 403 Forbidden
        resp_merge = client.post(
            "/api/v1/batches/merge",
            json={
                "sources": [
                    {
                        "batch_id": split_merge_seed["batch_melon_1"].id,
                        "quantity": 10.0,
                    },
                    {
                        "batch_id": split_merge_seed["batch_melon_2"].id,
                        "quantity": 10.0,
                    },
                ]
            },
            headers=headers_insp,
        )
        assert resp_merge.status_code == status.HTTP_403_FORBIDDEN
