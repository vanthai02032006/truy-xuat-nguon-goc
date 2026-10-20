"""Test Suite kiểm thử thuật toán đồ thị phả hệ DAG (Directed Acyclic Graph)
nông sản theo User Story S-21, S-26, S-27:

1. S-21: Truy ngược nguồn gốc bằng BFS (Ancestry tracing to roots):
   - Duyệt ngược con -> cha.
   - Sử dụng visited_set và kiểm tra phát hiện chu trình (Cycle Detection).
   - Trả về toàn bộ các lô thu hoạch gốc kèm tên vùng trồng và thửa đất tương ứng.

2. S-26, S-27: Truy xuôi hậu duệ bằng BFS (Descendant tracing):
   - Duyệt xuôi cha -> con từ lô gốc.
   - Liệt kê mọi lô con, cháu, kể cả các lô gộp trộn nguồn khác.
   - Trả về tổ chức hiện giữ, địa điểm/cửa hàng hiện tại, khối lượng còn lại, trạng thái (kho/hết).

3. Đồ thị DAG phả hệ đa chiều (3 cột trực quan).
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.batch import Batch
from app.models.batch_relation import BatchRelation, BatchRelationType
from app.models.land_plot import LandPlot
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.services.lineage_dag_service import LineageCycleError, LineageDagService


def get_auth_headers(email: str, role: str, org_id: int) -> dict:
    token = create_access_token(subject=email, role=role, organization_id=org_id)
    return {"Authorization": f"Bearer {token}"}


class TestLineageDagAlgorithms:
    @pytest.fixture
    def dag_seed_data(self, db_session: Session) -> dict:
        """Tạo mạng lưới phả hệ nhiều thế hệ (Roots -> Split -> Merge -> Split):

        - Lô Gốc 1 (Root 1: Cà chua Beef, 1000 kg, Thửa A1, Org Farm A)
        - Lô Gốc 2 (Root 2: Cà chua Cherry, 500 kg, Thửa B2, Org Farm B)
        - Thế hệ 1:
          + Root 1 tách thành: Child 1A (400 kg) và Child 1B (600 kg)
        - Thế hệ 2:
          + Child 1B (300 kg) gộp với Root 2 (200 kg) -> Merged M1 (500 kg, Org Co-op)
        - Thế hệ 3:
          + Merged M1 tách thành: Grandchild M1-Retail (200 kg, Org Retailer, còn 0kg - đã bán hết)
            và Grandchild M1-Stock (300 kg, còn 150 kg - trong kho)
        """
        # Tạo Organizations
        org_farm_a = Organization(name="HTX Nông Nghiệp Thắng Lợi", code="ORG_FARM_A")
        org_farm_b = Organization(name="Trang Trại Hữu Cơ Đà Lạt", code="ORG_FARM_B")
        org_coop = Organization(name="HTX Sơ Chế Chế Biến Lành", code="ORG_COOP")
        org_retail = Organization(name="Chuỗi Siêu Thị BioMart", code="ORG_RETAIL")
        org_other = Organization(name="Doanh Nghiệp Độc Lập Khác", code="ORG_OTHER")
        db_session.add_all([org_farm_a, org_farm_b, org_coop, org_retail, org_other])
        db_session.commit()

        # Tạo Users
        user_farm_a = User(
            email="farmer_a@example.com",
            hashed_password="fakehash",
            full_name="Nguyễn Nông Dân A",
            role=UserRole.FARM.value,
            organization_id=org_farm_a.id,
            is_active=True,
        )
        user_inspector = User(
            email="inspector_dag@example.com",
            hashed_password="fakehash",
            full_name="Thanh Tra Viên Chi Cục",
            role=UserRole.INSPECTOR.value,
            organization_id=org_farm_a.id,
            is_active=True,
        )
        user_other = User(
            email="other_org@example.com",
            hashed_password="fakehash",
            full_name="Người Dùng Tổ Chức Khác",
            role=UserRole.FARM.value,
            organization_id=org_other.id,
            is_active=True,
        )
        db_session.add_all([user_farm_a, user_inspector, user_other])
        db_session.commit()

        # Tạo Land Plots
        plot_a1 = LandPlot(
            name="Thửa A1 - Nhà Kính Cà Chua",
            area=5000.0,
            unit="m2",
            latitude=11.9404,
            longitude=108.4583,
            address="Xã Đạ Sar, Huyện Lạc Dương, Lâm Đồng",
            organization_id=org_farm_a.id,
        )
        plot_b2 = LandPlot(
            name="Thửa B2 - Vườn Sinh Thái",
            area=3000.0,
            unit="m2",
            latitude=11.9512,
            longitude=108.4621,
            address="Thôn Đa Lộc, TP Đà Lạt, Lâm Đồng",
            organization_id=org_farm_b.id,
        )
        db_session.add_all([plot_a1, plot_b2])
        db_session.commit()

        # 1. ROOT BATCHES
        root_1 = Batch(
            batch_code="ROOT-TOM-01",
            product_name="Cà chua Beef Hữu Cơ",
            organization_id=org_farm_a.id,
            land_plot_id=plot_a1.id,
            initial_quantity=1000.0,
            remaining_quantity=0.0,
            unit="kg",
            status="Đã xuất hết",
        )
        root_2 = Batch(
            batch_code="ROOT-CHERRY-02",
            product_name="Cà chua Cherry Vàng",
            organization_id=org_farm_b.id,
            land_plot_id=plot_b2.id,
            initial_quantity=500.0,
            remaining_quantity=300.0,
            unit="kg",
            status="Đang lưu kho",
        )
        db_session.add_all([root_1, root_2])
        db_session.commit()

        # 2. GENERATION 1: SPLIT ROOT 1 -> 1A, 1B
        child_1a = Batch(
            batch_code="CHILD-TOM-1A",
            product_name="Cà chua Beef Hữu Cơ",
            organization_id=org_farm_a.id,
            land_plot_id=plot_a1.id,
            initial_quantity=400.0,
            remaining_quantity=400.0,
            unit="kg",
            status="Đang lưu kho",
        )
        child_1b = Batch(
            batch_code="CHILD-TOM-1B",
            product_name="Cà chua Beef Hữu Cơ",
            organization_id=org_farm_a.id,
            land_plot_id=plot_a1.id,
            initial_quantity=600.0,
            remaining_quantity=300.0,
            unit="kg",
            status="Đang lưu kho",
        )
        db_session.add_all([child_1a, child_1b])
        db_session.commit()

        rel_split_1a = BatchRelation(
            parent_batch_id=root_1.id,
            child_batch_id=child_1a.id,
            relation_type=BatchRelationType.SPLIT.value,
            quantity=400.0,
        )
        rel_split_1b = BatchRelation(
            parent_batch_id=root_1.id,
            child_batch_id=child_1b.id,
            relation_type=BatchRelationType.SPLIT.value,
            quantity=600.0,
        )
        db_session.add_all([rel_split_1a, rel_split_1b])
        db_session.commit()

        # 3. GENERATION 2: MERGE (Child 1B + Root 2 -> Merged M1)
        merged_m1 = Batch(
            batch_code="MERGE-TOM-M1",
            product_name="Cà chua Phối Trộn Sơ Chế",
            organization_id=org_coop.id,
            initial_quantity=500.0,
            remaining_quantity=0.0,
            unit="kg",
            status="Đã chuyển tiếp",
        )
        db_session.add(merged_m1)
        db_session.commit()

        rel_merge_1 = BatchRelation(
            parent_batch_id=child_1b.id,
            child_batch_id=merged_m1.id,
            relation_type=BatchRelationType.MERGE.value,
            quantity=300.0,
        )
        rel_merge_2 = BatchRelation(
            parent_batch_id=root_2.id,
            child_batch_id=merged_m1.id,
            relation_type=BatchRelationType.MERGE.value,
            quantity=200.0,
        )
        db_session.add_all([rel_merge_1, rel_merge_2])
        db_session.commit()

        # 4. GENERATION 3: SPLIT M1 -> Grandchild M1-Retail & Grandchild M1-Stock
        grandchild_retail = Batch(
            batch_code="GCHILD-M1-RETAIL",
            product_name="Cà chua Phối Trộn Sơ Chế",
            organization_id=org_retail.id,
            initial_quantity=200.0,
            remaining_quantity=0.0,  # Đã bán hết
            unit="kg",
            status="Điểm bán lẻ",
        )
        grandchild_stock = Batch(
            batch_code="GCHILD-M1-STOCK",
            product_name="Cà chua Phối Trộn Sơ Chế",
            organization_id=org_coop.id,
            initial_quantity=300.0,
            remaining_quantity=150.0,  # Còn trong kho
            unit="kg",
            status="Đang lưu kho",
        )
        db_session.add_all([grandchild_retail, grandchild_stock])
        db_session.commit()

        rel_split_gc1 = BatchRelation(
            parent_batch_id=merged_m1.id,
            child_batch_id=grandchild_retail.id,
            relation_type=BatchRelationType.SPLIT.value,
            quantity=200.0,
        )
        rel_split_gc2 = BatchRelation(
            parent_batch_id=merged_m1.id,
            child_batch_id=grandchild_stock.id,
            relation_type=BatchRelationType.SPLIT.value,
            quantity=300.0,
        )
        db_session.add_all([rel_split_gc1, rel_split_gc2])
        db_session.commit()

        return {
            "org_farm_a": org_farm_a,
            "org_farm_b": org_farm_b,
            "org_coop": org_coop,
            "org_retail": org_retail,
            "org_other": org_other,
            "user_farm_a": user_farm_a,
            "user_inspector": user_inspector,
            "user_other": user_other,
            "plot_a1": plot_a1,
            "plot_b2": plot_b2,
            "root_1": root_1,
            "root_2": root_2,
            "child_1a": child_1a,
            "child_1b": child_1b,
            "merged_m1": merged_m1,
            "grandchild_retail": grandchild_retail,
            "grandchild_stock": grandchild_stock,
        }

    # =========================================================================
    # 1. USER STORY S-21: THUẬT TOÁN TRUY NGƯỢC NGUỒN GỐC (UPSTREAM BFS)
    # =========================================================================

    def test_s21_trace_upstream_roots_success(
        self, client: TestClient, db_session: Session, dag_seed_data: dict
    ):
        """Từ lô cháu `GCHILD-M1-RETAIL`:
        - Truy ngược nguồn gốc bằng BFS.
        - Tìm ra chính xác 2 lô thu hoạch gốc: ROOT-TOM-01 và ROOT-CHERRY-02.
        - Trả về đúng tên vùng trồng (HTX Thắng Lợi, Trang Trại Đà Lạt) và thửa đất (Thửa A1, Thửa B2).
        """
        gc_retail = dag_seed_data["grandchild_retail"]
        inspector = dag_seed_data["user_inspector"]
        headers = get_auth_headers(
            inspector.email, inspector.role, dag_seed_data["org_farm_a"].id
        )

        resp = client.get(
            f"/api/v1/batches/{gc_retail.id}/origins",
            headers=headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()

        assert data["target_batch_id"] == gc_retail.id
        assert data["target_batch_code"] == gc_retail.batch_code
        assert data["root_count"] == 2

        root_codes = {r["batch_code"] for r in data["roots"]}
        assert root_codes == {"ROOT-TOM-01", "ROOT-CHERRY-02"}

        # Kiểm tra thông tin vùng trồng và thửa đất của từng lô gốc
        root_1_info = next(r for r in data["roots"] if r["batch_code"] == "ROOT-TOM-01")
        assert root_1_info["farm_name"] == "HTX Nông Nghiệp Thắng Lợi"
        assert root_1_info["land_plot_name"] == "Thửa A1 - Nhà Kính Cà Chua"
        assert "Lạc Dương" in root_1_info["land_plot_address"]
        assert root_1_info["generation_depth"] == 3  # GC -> M1 -> 1B -> Root1

        root_2_info = next(
            r for r in data["roots"] if r["batch_code"] == "ROOT-CHERRY-02"
        )
        assert root_2_info["farm_name"] == "Trang Trại Hữu Cơ Đà Lạt"
        assert root_2_info["land_plot_name"] == "Thửa B2 - Vườn Sinh Thái"
        assert root_2_info["generation_depth"] == 2  # GC -> M1 -> Root2

    def test_s21_trace_upstream_single_line_parent(
        self, client: TestClient, db_session: Session, dag_seed_data: dict
    ):
        """Từ lô con `CHILD-TOM-1A` (chỉ có 1 lô cha gốc):
        - Truy ngược ra duy nhất 1 lô gốc ROOT-TOM-01.
        """
        child_1a = dag_seed_data["child_1a"]
        farmer_a = dag_seed_data["user_farm_a"]
        headers = get_auth_headers(
            farmer_a.email, farmer_a.role, dag_seed_data["org_farm_a"].id
        )

        resp = client.get(
            f"/api/v1/batches/{child_1a.id}/origins",
            headers=headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["root_count"] == 1
        assert data["roots"][0]["batch_code"] == "ROOT-TOM-01"

    def test_s21_cycle_detection_in_upstream_trace(
        self, client: TestClient, db_session: Session, dag_seed_data: dict
    ):
        """Cố tình tạo chu trình (cycle) vòng lặp vô hạn trong database (A -> B -> C -> A):
        - Thuật toán BFS phải bắt được chu trình bằng visited/path check.
        - Service ném `LineageCycleError`.
        - Endpoint trả về HTTP 400 Bad Request.
        """
        # Tạo chu trình: GCHILD-M1-RETAIL (con) lại trỏ làm cha của ROOT-TOM-01!
        cycle_rel = BatchRelation(
            parent_batch_id=dag_seed_data["grandchild_retail"].id,
            child_batch_id=dag_seed_data["root_1"].id,
            relation_type=BatchRelationType.SPLIT.value,
            quantity=50.0,
        )
        db_session.add(cycle_rel)
        db_session.commit()

        # Kiểm tra service trực tiếp ném LineageCycleError
        with pytest.raises(LineageCycleError) as exc_info:
            LineageDagService.trace_upstream_roots(
                db_session, dag_seed_data["grandchild_retail"].id
            )
        assert "chu trình" in str(exc_info.value).lower()

        # Kiểm tra API endpoint trả về HTTP 400
        inspector = dag_seed_data["user_inspector"]
        headers = get_auth_headers(
            inspector.email, inspector.role, dag_seed_data["org_farm_a"].id
        )
        resp = client.get(
            f"/api/v1/batches/{dag_seed_data['grandchild_retail'].id}/origins",
            headers=headers,
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert "chu trình" in resp.json()["detail"].lower()

    # =========================================================================
    # 2. USER STORY S-26, S-27: THUẬT TOÁN TRUY XUÔI HẬU DUỆ (DOWNSTREAM BFS)
    # =========================================================================

    def test_s26_s27_trace_downstream_descendants_success(
        self, client: TestClient, db_session: Session, dag_seed_data: dict
    ):
        """Từ lô thu hoạch gốc `ROOT-TOM-01`:
        - Truy xuôi bằng BFS tìm tất cả hậu duệ.
        - Liệt kê đủ: CHILD-TOM-1A, CHILD-TOM-1B, MERGE-TOM-M1 (lô gộp), GCHILD-M1-RETAIL, GCHILD-M1-STOCK.
        - Kiểm tra tổ chức hiện giữ, khối lượng còn lại, địa điểm và trạng thái (kho/hết).
        """
        root_1 = dag_seed_data["root_1"]
        farmer_a = dag_seed_data["user_farm_a"]
        headers = get_auth_headers(
            farmer_a.email, farmer_a.role, dag_seed_data["org_farm_a"].id
        )

        resp = client.get(
            f"/api/v1/batches/{root_1.id}/descendants",
            headers=headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()

        assert data["source_batch_id"] == root_1.id
        assert data["source_batch_code"] == root_1.batch_code
        assert data["descendant_count"] == 5

        descendant_codes = [d["batch_code"] for d in data["descendants"]]
        assert "CHILD-TOM-1A" in descendant_codes
        assert "CHILD-TOM-1B" in descendant_codes
        assert "MERGE-TOM-M1" in descendant_codes
        assert "GCHILD-M1-RETAIL" in descendant_codes
        assert "GCHILD-M1-STOCK" in descendant_codes

        # Kiểm tra chi tiết lô cháu GCHILD-M1-RETAIL
        d_retail = next(
            d for d in data["descendants"] if d["batch_code"] == "GCHILD-M1-RETAIL"
        )
        assert d_retail["holding_organization"]["name"] == "Chuỗi Siêu Thị BioMart"
        assert d_retail["remaining_quantity"] == 0.0
        assert d_retail["is_depleted"] is True  # Đã bán hết
        assert d_retail["status"] == "Điểm bán lẻ"

        # Kiểm tra chi tiết lô cháu GCHILD-M1-STOCK
        d_stock = next(
            d for d in data["descendants"] if d["batch_code"] == "GCHILD-M1-STOCK"
        )
        assert d_stock["holding_organization"]["name"] == "HTX Sơ Chế Chế Biến Lành"
        assert d_stock["remaining_quantity"] == 150.0
        assert d_stock["is_depleted"] is False  # Còn trong kho
        assert d_stock["status"] == "Đang lưu kho"

    def test_s26_s27_trace_descendants_merged_batch_source(
        self, client: TestClient, db_session: Session, dag_seed_data: dict
    ):
        """Từ lô gốc 2 `ROOT-CHERRY-02`:
        - Truy xuôi hậu duệ xem các lô con cháu:
        - Phải tìm thấy `MERGE-TOM-M1`, `GCHILD-M1-RETAIL`, `GCHILD-M1-STOCK`.
        """
        root_2 = dag_seed_data["root_2"]
        inspector = dag_seed_data["user_inspector"]
        headers = get_auth_headers(
            inspector.email, inspector.role, dag_seed_data["org_farm_a"].id
        )

        resp = client.get(
            f"/api/v1/batches/{root_2.id}/descendants",
            headers=headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        descendant_codes = [d["batch_code"] for d in data["descendants"]]
        assert "MERGE-TOM-M1" in descendant_codes
        assert "GCHILD-M1-RETAIL" in descendant_codes
        assert "GCHILD-M1-STOCK" in descendant_codes
        assert "CHILD-TOM-1A" not in descendant_codes

    # =========================================================================
    # 3. ĐỒ THỊ DAG PHẢ HỆ ĐA CHIỀU (3 CỘT: ROOTS - FOCUS - DESCENDANTS)
    # =========================================================================

    def test_dag_graph_structure_endpoint(
        self, client: TestClient, db_session: Session, dag_seed_data: dict
    ):
        """Kiểm tra endpoint tổng hợp cấu trúc đồ thị DAG:
        - Tiêu điểm ở giữa (Focus Batch): MERGE-TOM-M1.
        - Bên trái (Roots & Ancestors): ROOT-1, ROOT-2, CHILD-1B.
        - Bên phải (Descendants): GCHILD-M1-RETAIL, GCHILD-M1-STOCK.
        - Cạnh (Edges): Các mối quan hệ chuyển đổi có khối lượng.
        """
        m1 = dag_seed_data["merged_m1"]
        inspector = dag_seed_data["user_inspector"]
        headers = get_auth_headers(
            inspector.email, inspector.role, dag_seed_data["org_farm_a"].id
        )

        resp = client.get(
            f"/api/v1/batches/{m1.id}/dag-graph",
            headers=headers,
        )
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()

        assert data["focus_batch"]["id"] == m1.id
        assert data["focus_batch"]["batch_code"] == m1.batch_code
        assert data["focus_batch"]["node_type"] == "FOCUS"

        # Kiểm tra danh sách roots bên trái
        root_codes = {r["batch_code"] for r in data["roots"]}
        assert "ROOT-TOM-01" in root_codes
        assert "ROOT-CHERRY-02" in root_codes

        # Kiểm tra danh sách descendants bên phải
        desc_codes = {d["batch_code"] for d in data["descendants"]}
        assert "GCHILD-M1-RETAIL" in desc_codes
        assert "GCHILD-M1-STOCK" in desc_codes

        # Kiểm tra danh sách edges
        assert len(data["edges"]) >= 4

    # =========================================================================
    # 4. BẢO MẬT MULTI-TENANT & QUYỀN TRUY VẤN
    # =========================================================================

    def test_multi_tenant_isolation_on_dag_endpoints(
        self, client: TestClient, db_session: Session, dag_seed_data: dict
    ):
        """User của tổ chức khác không có quyền xem thông tin của lô không thuộc quản lý -> 403 Forbidden."""
        root_1 = dag_seed_data["root_1"]
        user_other = dag_seed_data["user_other"]
        headers_other = get_auth_headers(
            user_other.email, user_other.role, dag_seed_data["org_other"].id
        )

        # Origins
        resp1 = client.get(
            f"/api/v1/batches/{root_1.id}/origins",
            headers=headers_other,
        )
        assert resp1.status_code == status.HTTP_403_FORBIDDEN

        # Descendants
        resp2 = client.get(
            f"/api/v1/batches/{root_1.id}/descendants",
            headers=headers_other,
        )
        assert resp2.status_code == status.HTTP_403_FORBIDDEN

        # DAG Graph
        resp3 = client.get(
            f"/api/v1/batches/{root_1.id}/dag-graph",
            headers=headers_other,
        )
        assert resp3.status_code == status.HTTP_403_FORBIDDEN
