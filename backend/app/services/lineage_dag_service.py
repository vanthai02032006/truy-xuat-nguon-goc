from collections import deque
from typing import Any

from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.batch_relation import BatchRelation, BatchRelationType
from app.models.land_plot import LandPlot
from app.models.organization import Organization


class LineageCycleError(ValueError):
    """Ném ra khi phát hiện chu trình (vòng lặp vô hạn) trong đồ thị phả hệ lô hàng (Directed Acyclic Graph violation)."""


class LineageDagService:
    """Service thực thi các thuật toán duyệt đồ thị DAG cho phả hệ lô nông sản.

    - S-21: Truy ngược nguồn gốc (Ancestry tracing to roots) bằng BFS.
    - S-26, S-27: Truy xuôi hậu duệ (Descendant tracing) bằng BFS.
    - Sơ đồ trực quan: Tổng hợp cấu trúc DAG đa chiều (Left: Roots/Ancestors, Center: Focus, Right: Descendants).
    """

    @staticmethod
    def trace_upstream_roots(db: Session, batch_id: int) -> dict[str, Any]:
        """User Story S-21: Truy ngược nguồn gốc bằng BFS.

        - Đầu vào: mã lô hoặc ID lô bất kỳ.
        - Thuật toán: Dùng Breadth-First Search (BFS) duyệt ngược theo chiều con -> cha từ bảng `batch_relations`.
        - Bắt buộc có tập `visited_set` và kiểm tra chu trình: Nếu phát hiện chu trình thì ném `LineageCycleError`.
        - Trả về: Danh sách toàn bộ các lô thu hoạch gốc ban đầu cùng tên vùng trồng và thửa đất tương ứng.
        """
        focus_batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not focus_batch:
            raise ValueError(f"Không tìm thấy lô hàng với ID {batch_id}")

        # Hàng đợi BFS: (current_batch_id, path_from_target, depth)
        queue: deque = deque([(batch_id, [batch_id], 0)])
        visited_nodes: set[int] = set()
        root_batches_map: dict[int, dict[str, Any]] = {}
        ancestor_nodes_map: dict[int, dict[str, Any]] = {}

        while queue:
            curr_id, path, depth = queue.popleft()
            visited_nodes.add(curr_id)

            # Tìm các lô cha trực tiếp của curr_id
            parent_relations = (
                db.query(BatchRelation)
                .filter(BatchRelation.child_batch_id == curr_id)
                .all()
            )

            if not parent_relations:
                # Không có cha -> Đây là Lô Thu Hoạch Gốc (Root Batch)
                b_obj = db.query(Batch).filter(Batch.id == curr_id).first()
                if b_obj and b_obj.id not in root_batches_map:
                    farm_name = (
                        b_obj.organization.name
                        if b_obj.organization
                        else "Chưa xác định"
                    )
                    plot_name = (
                        b_obj.land_plot.name if b_obj.land_plot else "Chưa xác định"
                    )
                    plot_address = b_obj.land_plot.address if b_obj.land_plot else None

                    root_batches_map[b_obj.id] = {
                        "id": b_obj.id,
                        "batch_code": b_obj.batch_code,
                        "product_name": b_obj.product_name,
                        "farm_name": farm_name,
                        "land_plot_id": b_obj.land_plot_id,
                        "land_plot_name": plot_name,
                        "land_plot_address": plot_address,
                        "harvest_date": b_obj.created_at,
                        "initial_quantity": b_obj.initial_quantity,
                        "remaining_quantity": b_obj.remaining_quantity,
                        "unit": b_obj.unit or "kg",
                        "generation_depth": depth,
                    }
            else:
                for rel in parent_relations:
                    parent_id = rel.parent_batch_id

                    # Kiểm tra Chu trình (Cycle Detection):
                    # Nếu parent_id đã xuất hiện trên đường đi hiện tại -> đồ thị có chu trình!
                    if parent_id in path:
                        cycle_path = " -> ".join(map(str, path + [parent_id]))
                        raise LineageCycleError(
                            f"Phát hiện chu trình vòng lặp bất thường trong phả hệ lô hàng! Lô {parent_id} đã xuất hiện trên đường đi: {cycle_path}"
                        )

                    parent_batch = db.query(Batch).filter(Batch.id == parent_id).first()
                    if (
                        parent_batch
                        and parent_batch.id not in ancestor_nodes_map
                        and parent_batch.id != batch_id
                    ):
                        ancestor_nodes_map[parent_batch.id] = {
                            "id": parent_batch.id,
                            "batch_code": parent_batch.batch_code,
                            "product_name": parent_batch.product_name,
                            "node_type": "ANCESTOR",
                            "holding_org_name": (
                                parent_batch.organization.name
                                if parent_batch.organization
                                else "N/A"
                            ),
                            "remaining_quantity": parent_batch.remaining_quantity,
                            "unit": parent_batch.unit or "kg",
                            "status": parent_batch.status,
                            "is_depleted": (
                                parent_batch.remaining_quantity is not None
                                and parent_batch.remaining_quantity <= 0
                            ),
                        }

                    queue.append((parent_id, path + [parent_id], depth + 1))

        # Sắp xếp các lô gốc theo khoảng cách thế hệ
        roots_list = sorted(
            root_batches_map.values(),
            key=lambda r: (r["generation_depth"], r["id"]),
        )

        return {
            "target_batch_id": focus_batch.id,
            "target_batch_code": focus_batch.batch_code,
            "root_count": len(roots_list),
            "roots": roots_list,
            "ancestor_nodes": list(ancestor_nodes_map.values()),
        }

    @staticmethod
    def trace_downstream_descendants(db: Session, batch_id: int) -> dict[str, Any]:
        """User Story S-26, S-27: Truy xuôi hậu duệ bằng BFS.

        - Đầu vào: mã lô thu hoạch gốc (hoặc bất kỳ lô nào cần truy vết).
        - Thuật toán BFS duyệt theo chiều cha -> con để liệt kê mọi lô con, lô cháu, kể cả các lô gộp có sản phẩm từ nguồn khác trộn vào.
        - Trả về: Danh sách đầy đủ mọi lô hậu duệ kèm theo:
          + Tổ chức hiện đang giữ
          + Địa điểm / cửa hàng hiện tại
          + Khối lượng còn lại
          + Trạng thái (còn trong kho hay đã bán/xuất hết)
        """
        source_batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not source_batch:
            raise ValueError(f"Không tìm thấy lô hàng với ID {batch_id}")

        queue: deque = deque([(batch_id, [batch_id], 0)])
        visited_nodes: set[int] = set()
        descendants_list: list[dict[str, Any]] = []
        seen_child_ids: set[int] = set()

        while queue:
            curr_id, path, depth = queue.popleft()
            visited_nodes.add(curr_id)

            # Lấy tất cả quan hệ con mà curr_id là cha
            child_relations = (
                db.query(BatchRelation)
                .filter(BatchRelation.parent_batch_id == curr_id)
                .all()
            )

            for rel in child_relations:
                child_id = rel.child_batch_id

                # Kiểm tra chu trình xuôi
                if child_id in path:
                    cycle_path = " -> ".join(map(str, path + [child_id]))
                    raise LineageCycleError(
                        f"Phát hiện chu trình vòng lặp xuôi trong đồ thị phả hệ lô hàng! Lô {child_id} đã nằm trên đường đi: {cycle_path}"
                    )

                child_batch = db.query(Batch).filter(Batch.id == child_id).first()
                if child_batch:
                    # Xác định địa điểm / cửa hàng hiện tại
                    location = "Chưa xác định"
                    if child_batch.land_plot and child_batch.land_plot.address:
                        location = f"{child_batch.land_plot.name} ({child_batch.land_plot.address})"
                    elif child_batch.organization:
                        location = f"Cơ sở / Kho {child_batch.organization.name}"

                    org_info = {
                        "id": (
                            child_batch.organization.id
                            if child_batch.organization
                            else None
                        ),
                        "name": (
                            child_batch.organization.name
                            if child_batch.organization
                            else "N/A"
                        ),
                        "code": (
                            child_batch.organization.code
                            if child_batch.organization
                            else "N/A"
                        ),
                    }

                    is_depleted = (
                        child_batch.remaining_quantity is not None
                        and child_batch.remaining_quantity <= 0
                    )

                    descendant_entry = {
                        "id": child_batch.id,
                        "batch_code": child_batch.batch_code,
                        "product_name": child_batch.product_name,
                        "generation": f"F{depth + 1}",
                        "generation_level": depth + 1,
                        "relation_type": rel.relation_type,
                        "quantity_transferred": rel.quantity,
                        "holding_organization": org_info,
                        "current_location": location,
                        "initial_quantity": child_batch.initial_quantity,
                        "remaining_quantity": child_batch.remaining_quantity,
                        "unit": child_batch.unit or "kg",
                        "status": child_batch.status or "Đang lưu kho",
                        "is_depleted": is_depleted,
                        "parent_batch_id": curr_id,
                    }

                    # Mỗi quan hệ chuyển đổi được ghi nhận
                    descendants_list.append(descendant_entry)
                    seen_child_ids.add(child_id)

                    queue.append((child_id, path + [child_id], depth + 1))

        return {
            "source_batch_id": source_batch.id,
            "source_batch_code": source_batch.batch_code,
            "descendant_count": len(descendants_list),
            "descendants": descendants_list,
        }

    @classmethod
    def get_dag_graph_structure(cls, db: Session, batch_id: int) -> dict[str, Any]:
        """Tổng hợp cấu trúc đồ thị DAG hoàn chỉnh cho giao diện sơ đồ cây phả hệ trực quan:

        - Lô hiện tại ở giữa (Focus Batch).
        - Tổ tiên & Lô thu hoạch gốc ở bên trái (Roots & Ancestors).
        - Toàn bộ hậu duệ ở bên phải (Descendants).
        - Các cạnh chuyển đổi (Edges) kèm khối lượng và loại quan hệ (SPLIT/MERGE).
        """
        focus_batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not focus_batch:
            raise ValueError(f"Không tìm thấy lô hàng với ID {batch_id}")

        # 1. Lấy dữ liệu ngược (Roots & Ancestors)
        upstream_data = cls.trace_upstream_roots(db, batch_id)

        # 2. Lấy dữ liệu xuôi (Descendants)
        downstream_data = cls.trace_downstream_descendants(db, batch_id)

        # 3. Tạo Focus Node
        focus_location = "Chưa xác định"
        if focus_batch.land_plot and focus_batch.land_plot.address:
            focus_location = (
                f"{focus_batch.land_plot.name} ({focus_batch.land_plot.address})"
            )
        elif focus_batch.organization:
            focus_location = f"Cơ sở {focus_batch.organization.name}"

        is_focus_depleted = (
            focus_batch.remaining_quantity is not None
            and focus_batch.remaining_quantity <= 0
        )

        focus_node = {
            "id": focus_batch.id,
            "batch_code": focus_batch.batch_code,
            "product_name": focus_batch.product_name,
            "node_type": "FOCUS",
            "holding_org_name": (
                focus_batch.organization.name if focus_batch.organization else "N/A"
            ),
            "location": focus_location,
            "remaining_quantity": focus_batch.remaining_quantity,
            "unit": focus_batch.unit or "kg",
            "status": focus_batch.status,
            "is_depleted": is_focus_depleted,
        }

        # 4. Tập hợp tất cả các node trong DAG (loại trừ trùng lặp)
        all_nodes_dict: dict[int, dict[str, Any]] = {focus_batch.id: focus_node}

        # Thêm roots
        for r in upstream_data["roots"]:
            if r["id"] not in all_nodes_dict:
                all_nodes_dict[r["id"]] = {
                    "id": r["id"],
                    "batch_code": r["batch_code"],
                    "product_name": r["product_name"],
                    "node_type": "ROOT",
                    "holding_org_name": r["farm_name"],
                    "location": r["land_plot_address"] or r["land_plot_name"],
                    "remaining_quantity": r["remaining_quantity"],
                    "unit": r["unit"],
                    "status": "Lô thu hoạch gốc",
                    "is_depleted": (
                        r["remaining_quantity"] is not None
                        and r["remaining_quantity"] <= 0
                    ),
                }

        # Thêm ancestors
        for a in upstream_data["ancestor_nodes"]:
            if a["id"] not in all_nodes_dict:
                all_nodes_dict[a["id"]] = a

        # Thêm descendants
        for d in downstream_data["descendants"]:
            if d["id"] not in all_nodes_dict:
                all_nodes_dict[d["id"]] = {
                    "id": d["id"],
                    "batch_code": d["batch_code"],
                    "product_name": d["product_name"],
                    "node_type": "DESCENDANT",
                    "holding_org_name": d["holding_organization"]["name"],
                    "location": d["current_location"],
                    "remaining_quantity": d["remaining_quantity"],
                    "unit": d["unit"],
                    "status": d["status"],
                    "is_depleted": d["is_depleted"],
                }

        # 5. Tập hợp các cạnh (Edges) giữa các node có trong all_nodes_dict
        all_batch_ids = set(all_nodes_dict.keys())
        edges_db = (
            db.query(BatchRelation)
            .filter(
                BatchRelation.parent_batch_id.in_(all_batch_ids),
                BatchRelation.child_batch_id.in_(all_batch_ids),
            )
            .all()
        )

        edges_list = [
            {
                "source_batch_id": e.parent_batch_id,
                "target_batch_id": e.child_batch_id,
                "relation_type": e.relation_type,
                "quantity": e.quantity,
            }
            for e in edges_db
        ]

        return {
            "focus_batch": focus_node,
            "roots": upstream_data["roots"],
            "ancestors": upstream_data["ancestor_nodes"],
            "descendants": downstream_data["descendants"],
            "nodes": list(all_nodes_dict.values()),
            "edges": edges_list,
        }

    @classmethod
    def seed_lineage_dataset(cls, db: Session) -> dict[str, Any]:
        """
        User Story S-22 / S-39 / Epic E-05 / Epic E-06:
        Nạp bộ dữ liệu mẫu phả hệ 3-4 tầng với ít nhất 12 lô qua 3+ tổ chức,
        bao gồm cả Tách lô và Gộp lô, đi kèm đáp án đếm tay để đối chiếu.
        """
        seed_codes = [
            "ROOT-TOM-01",
            "ROOT-CHERRY-02",
            "ROOT-ROMA-03",
            "CHILD-TOM-1A",
            "CHILD-TOM-1B",
            "CHILD-ROMA-3A",
            "CHILD-ROMA-3B",
            "MERGE-TOM-M1",
            "MERGE-MIX-M2",
            "RETAIL-M1-STORE-01",
            "RETAIL-M1-STORE-02",
            "RETAIL-M2-SUPERMARKET",
            "STOCK-COOP-BACKUP",
        ]

        # 1. Dọn dẹp dữ liệu cũ nếu đã tồn tại để tránh xung đột khóa
        existing_batches = db.query(Batch).filter(Batch.batch_code.in_(seed_codes)).all()
        if existing_batches:
            existing_ids = [b.id for b in existing_batches]
            # Xóa các quan hệ phả hệ cũ
            db.query(BatchRelation).filter(
                (BatchRelation.parent_batch_id.in_(existing_ids))
                | (BatchRelation.child_batch_id.in_(existing_ids))
            ).delete(synchronize_session=False)

            # Dọn dẹp các lệnh thu hồi liên quan nếu có
            from app.models.recall import (
                Recall,
                RecallAffectedBatch,
                RecallOrganizationAction,
            )

            db.query(RecallAffectedBatch).filter(
                RecallAffectedBatch.batch_id.in_(existing_ids)
            ).delete(synchronize_session=False)

            linked_recalls = (
                db.query(Recall).filter(Recall.source_batch_id.in_(existing_ids)).all()
            )
            for r in linked_recalls:
                db.query(RecallOrganizationAction).filter(
                    RecallOrganizationAction.recall_id == r.id
                ).delete(synchronize_session=False)
                db.delete(r)

            # Dọn dẹp Chain Events liên quan
            from app.models.chain_event import ChainEvent

            db.query(ChainEvent).filter(
                ChainEvent.batch_id.in_(existing_ids)
            ).delete(synchronize_session=False)

            # Xóa các batch cũ
            for b in existing_batches:
                db.delete(b)
            db.flush()

        # 2. Khởi tạo/Tìm 4 tổ chức trong chuỗi cung ứng
        def get_or_create_org(name: str, code: str) -> Organization:
            org = db.query(Organization).filter(Organization.code == code).first()
            if not org:
                org = Organization(name=name, code=code)
                db.add(org)
                db.flush()
            return org

        org_farm_a = get_or_create_org("HTX Nông Nghiệp Thắng Lợi", "ORG_FARM_A")
        org_farm_b = get_or_create_org("Trang Trại Hữu Cơ Đà Lạt", "ORG_FARM_B")
        org_coop = get_or_create_org("HTX Sơ Chế Chế Biến Lành", "ORG_COOP")
        org_retail = get_or_create_org("Chuỗi Siêu Thị BioMart", "ORG_RETAIL")

        # 3. Khởi tạo/Tìm thửa đất vùng trồng
        def get_or_create_plot(
            name: str, org_id: int, address: str, lat: float = 11.9404, lng: float = 108.4583
        ) -> LandPlot:
            plot = (
                db.query(LandPlot)
                .filter(LandPlot.name == name, LandPlot.organization_id == org_id)
                .first()
            )
            if not plot:
                plot = LandPlot(
                    name=name,
                    area=5000.0,
                    unit="m2",
                    latitude=lat,
                    longitude=lng,
                    address=address,
                    organization_id=org_id,
                )
                db.add(plot)
                db.flush()
            return plot

        plot_a1 = get_or_create_plot(
            "Thửa A1 - Nhà Kính Cà Chua",
            org_farm_a.id,
            "Xã Đạ Sar, Huyện Lạc Dương, Lâm Đồng",
            lat=11.9404,
            lng=108.4583,
        )
        plot_b2 = get_or_create_plot(
            "Thửa B2 - Vườn Sinh Thái",
            org_farm_b.id,
            "Thôn Đa Lộc, TP Đà Lạt, Lâm Đồng",
            lat=11.9512,
            lng=108.4621,
        )


        # 4. Khởi tạo 13 Lô hàng qua 4 tầng:
        # Tầng 1: Lô Thu Hoạch Gốc (3 lô)
        root_1 = Batch(
            batch_code="ROOT-TOM-01",
            product_name="Cà chua Beef Hữu Cơ",
            organization_id=org_farm_a.id,
            land_plot_id=plot_a1.id,
            initial_quantity=1200.0,
            remaining_quantity=0.0,
            unit="kg",
            status="Đã xuất hết",
        )
        root_2 = Batch(
            batch_code="ROOT-CHERRY-02",
            product_name="Cà chua Cherry Vàng",
            organization_id=org_farm_b.id,
            land_plot_id=plot_b2.id,
            initial_quantity=800.0,
            remaining_quantity=200.0,
            unit="kg",
            status="Đang lưu kho",
        )
        root_3 = Batch(
            batch_code="ROOT-ROMA-03",
            product_name="Cà chua Mận Roma",
            organization_id=org_farm_a.id,
            land_plot_id=plot_a1.id,
            initial_quantity=600.0,
            remaining_quantity=0.0,
            unit="kg",
            status="Đã xuất hết",
        )
        db.add_all([root_1, root_2, root_3])
        db.flush()

        # Tầng 2: Tách lô tại Vùng trồng (4 lô con)
        child_1a = Batch(
            batch_code="CHILD-TOM-1A",
            product_name="Cà chua Beef Hữu Cơ",
            organization_id=org_farm_a.id,
            land_plot_id=plot_a1.id,
            initial_quantity=500.0,
            remaining_quantity=300.0,
            unit="kg",
            status="Đang lưu kho",
        )
        child_1b = Batch(
            batch_code="CHILD-TOM-1B",
            product_name="Cà chua Beef Hữu Cơ",
            organization_id=org_farm_a.id,
            land_plot_id=plot_a1.id,
            initial_quantity=700.0,
            remaining_quantity=100.0,
            unit="kg",
            status="Đang lưu kho",
        )
        child_3a = Batch(
            batch_code="CHILD-ROMA-3A",
            product_name="Cà chua Mận Roma",
            organization_id=org_farm_a.id,
            land_plot_id=plot_a1.id,
            initial_quantity=300.0,
            remaining_quantity=0.0,
            unit="kg",
            status="Đã chuyển sơ chế",
        )
        child_3b = Batch(
            batch_code="CHILD-ROMA-3B",
            product_name="Cà chua Mận Roma",
            organization_id=org_farm_a.id,
            land_plot_id=plot_a1.id,
            initial_quantity=300.0,
            remaining_quantity=300.0,
            unit="kg",
            status="Đang lưu kho",
        )
        db.add_all([child_1a, child_1b, child_3a, child_3b])
        db.flush()

        # Tầng 3: Gộp lô tại HTX Sơ Chế Chế Biến Lành (2 lô gộp)
        merge_m1 = Batch(
            batch_code="MERGE-TOM-M1",
            product_name="Cà chua Phối Trộn Sơ Chế",
            organization_id=org_coop.id,
            initial_quantity=1200.0,
            remaining_quantity=0.0,
            unit="kg",
            status="Đã phân phối hết",
        )
        merge_m2 = Batch(
            batch_code="MERGE-MIX-M2",
            product_name="Cà chua Salad Cao Cấp",
            organization_id=org_coop.id,
            initial_quantity=500.0,
            remaining_quantity=0.0,
            unit="kg",
            status="Đã phân phối hết",
        )
        db.add_all([merge_m1, merge_m2])
        db.flush()

        # Tầng 4: Phân phối & Bán lẻ tại Chuỗi Siêu thị BioMart & Dự trữ (4 lô)
        retail_01 = Batch(
            batch_code="RETAIL-M1-STORE-01",
            product_name="Cà chua Phối Trộn Sơ Chế",
            organization_id=org_retail.id,
            initial_quantity=400.0,
            remaining_quantity=0.0,  # Đã bán hết tại Siêu thị BioMart Quận 1
            unit="kg",
            status="Điểm bán lẻ",
        )
        retail_02 = Batch(
            batch_code="RETAIL-M1-STORE-02",
            product_name="Cà chua Phối Trộn Sơ Chế",
            organization_id=org_retail.id,
            initial_quantity=600.0,
            remaining_quantity=150.0,  # Còn 150 kg tại kệ BioMart Cầu Giấy
            unit="kg",
            status="Đang bày bán",
        )
        retail_03 = Batch(
            batch_code="RETAIL-M2-SUPERMARKET",
            product_name="Cà chua Salad Cao Cấp",
            organization_id=org_retail.id,
            initial_quantity=500.0,
            remaining_quantity=80.0,  # Còn 80 kg tại kệ BioMart Thủ Đức
            unit="kg",
            status="Đang bày bán",
        )
        stock_backup = Batch(
            batch_code="STOCK-COOP-BACKUP",
            product_name="Cà chua Phối Trộn Sơ Chế",
            organization_id=org_coop.id,
            initial_quantity=200.0,
            remaining_quantity=200.0,  # Còn 200 kg trong kho lạnh HTX
            unit="kg",
            status="Đang lưu kho",
        )
        db.add_all([retail_01, retail_02, retail_03, stock_backup])
        db.flush()

        # 5. Khởi tạo 12 quan hệ phả hệ (Tách & Gộp)
        relations = [
            # Tầng 1 -> Tầng 2: SPLIT
            BatchRelation(
                parent_batch_id=root_1.id,
                child_batch_id=child_1a.id,
                relation_type=BatchRelationType.SPLIT.value,
                quantity=500.0,
                notes="Tách 500kg sang lô con 1A",
            ),
            BatchRelation(
                parent_batch_id=root_1.id,
                child_batch_id=child_1b.id,
                relation_type=BatchRelationType.SPLIT.value,
                quantity=700.0,
                notes="Tách 700kg sang lô con 1B giao HTX",
            ),
            BatchRelation(
                parent_batch_id=root_3.id,
                child_batch_id=child_3a.id,
                relation_type=BatchRelationType.SPLIT.value,
                quantity=300.0,
                notes="Tách 300kg sang lô con 3A giao HTX",
            ),
            BatchRelation(
                parent_batch_id=root_3.id,
                child_batch_id=child_3b.id,
                relation_type=BatchRelationType.SPLIT.value,
                quantity=300.0,
                notes="Tách 300kg sang lô con 3B lưu kho Farm",
            ),
            # Tầng 2 -> Tầng 3: MERGE
            BatchRelation(
                parent_batch_id=child_1b.id,
                child_batch_id=merge_m1.id,
                relation_type=BatchRelationType.MERGE.value,
                quantity=600.0,
                notes="Gộp 600kg từ lô con 1B của Farm A",
            ),
            BatchRelation(
                parent_batch_id=root_2.id,
                child_batch_id=merge_m1.id,
                relation_type=BatchRelationType.MERGE.value,
                quantity=600.0,
                notes="Gộp 600kg từ lô gốc Cherry của Farm B",
            ),
            BatchRelation(
                parent_batch_id=child_3a.id,
                child_batch_id=merge_m2.id,
                relation_type=BatchRelationType.MERGE.value,
                quantity=300.0,
                notes="Gộp 300kg cà chua Roma",
            ),
            BatchRelation(
                parent_batch_id=child_1a.id,
                child_batch_id=merge_m2.id,
                relation_type=BatchRelationType.MERGE.value,
                quantity=200.0,
                notes="Gộp 200kg cà chua Beef",
            ),
            # Tầng 3 -> Tầng 4: SPLIT
            BatchRelation(
                parent_batch_id=merge_m1.id,
                child_batch_id=retail_01.id,
                relation_type=BatchRelationType.SPLIT.value,
                quantity=400.0,
                notes="Tách 400kg giao Siêu thị BioMart Quận 1",
            ),
            BatchRelation(
                parent_batch_id=merge_m1.id,
                child_batch_id=retail_02.id,
                relation_type=BatchRelationType.SPLIT.value,
                quantity=600.0,
                notes="Tách 600kg giao Siêu thị BioMart Cầu Giấy",
            ),
            BatchRelation(
                parent_batch_id=merge_m1.id,
                child_batch_id=stock_backup.id,
                relation_type=BatchRelationType.SPLIT.value,
                quantity=200.0,
                notes="Trích 200kg dự trữ kho lạnh HTX",
            ),
            BatchRelation(
                parent_batch_id=merge_m2.id,
                child_batch_id=retail_03.id,
                relation_type=BatchRelationType.SPLIT.value,
                quantity=500.0,
                notes="Tách 500kg giao BioMart Thủ Đức",
            ),
        ]
        db.add_all(relations)
        db.flush()

        # 6. Ghi nhận Chain Event cho từng lô để đảm bảo chuỗi hash chuẩn T-24/S-10
        from app.services.hash_chain_service import record_chain_event

        all_seeded_batches = [
            root_1,
            root_2,
            root_3,
            child_1a,
            child_1b,
            child_3a,
            child_3b,
            merge_m1,
            merge_m2,
            retail_01,
            retail_02,
            retail_03,
            stock_backup,
        ]
        for b in all_seeded_batches:
            record_chain_event(
                db=db,
                batch_id=b.id,
                event_type="BATCH_SEED_INITIALIZED",
                event_data=f"Khởi tạo lô {b.batch_code} ({b.initial_quantity} {b.unit})",
                organization_id=b.organization_id,
            )

        db.commit()

        # Refresh toàn bộ đối tượng
        for b in all_seeded_batches:
            db.refresh(b)

        sample_list = [
            {
                "id": b.id,
                "batch_code": b.batch_code,
                "product_name": b.product_name,
                "organization_name": b.organization.name if b.organization else "N/A",
                "organization_id": b.organization_id,
                "initial_quantity": b.initial_quantity,
                "remaining_quantity": b.remaining_quantity,
                "unit": b.unit,
                "status": b.status,
            }
            for b in all_seeded_batches
        ]

        # Đáp án đếm tay đối chiếu (Hand-counted Answer Key)
        answer_key = {
            "focus_merge_m1": {
                "batch_id": merge_m1.id,
                "batch_code": "MERGE-TOM-M1",
                "upstream_roots_count": 2,
                "upstream_roots": ["ROOT-TOM-01", "ROOT-CHERRY-02"],
                "upstream_parents_count": 2,
                "upstream_parents": ["CHILD-TOM-1B", "ROOT-CHERRY-02"],
                "downstream_descendants_count": 3,
                "downstream_descendants": [
                    "RETAIL-M1-STORE-01",
                    "RETAIL-M1-STORE-02",
                    "STOCK-COOP-BACKUP",
                ],
                "shelf_stock_remaining_kg": 350.0,  # 150kg Cầu Giấy + 200kg Kho HTX
                "consumed_sold_kg": 850.0,          # 400kg Q1 + 450kg Cầu Giấy
                "total_batch_weight_kg": 1200.0,
            },
            "focus_root_tom_01": {
                "batch_id": root_1.id,
                "batch_code": "ROOT-TOM-01",
                "upstream_roots_count": 1,
                "upstream_roots": ["ROOT-TOM-01"],
                "downstream_descendants_count": 8,
                "downstream_descendants": [
                    "CHILD-TOM-1A",
                    "CHILD-TOM-1B",
                    "MERGE-TOM-M1",
                    "MERGE-MIX-M2",
                    "RETAIL-M1-STORE-01",
                    "RETAIL-M1-STORE-02",
                    "RETAIL-M2-SUPERMARKET",
                    "STOCK-COOP-BACKUP",
                ],
            },
            "recall_scenario_m1": {
                "trigger_batch_id": merge_m1.id,
                "trigger_batch_code": "MERGE-TOM-M1",
                "reason": "Phát hiện dư lượng kim loại nặng vượt ngưỡng quy chuẩn an toàn VietGAP tại đợt kiểm nghiệm độc lập",
                "affected_batches_count": 4,  # MERGE-TOM-M1 + 3 hậu duệ
                "affected_batch_codes": [
                    "MERGE-TOM-M1",
                    "RETAIL-M1-STORE-01",
                    "RETAIL-M1-STORE-02",
                    "STOCK-COOP-BACKUP",
                ],
                "affected_organizations_count": 2,  # HTX Sơ Chế + Chuỗi Siêu Thị BioMart
                "affected_organizations": [
                    "HTX Sơ Chế Chế Biến Lành",
                    "Chuỗi Siêu Thị BioMart",
                ],
                "total_affected_kg": 1200.0,
                "total_stock_kg": 350.0,
                "total_sold_kg": 850.0,
            },
        }

        return {
            "message": "Nạp bộ dữ liệu mẫu phả hệ 3-4 tầng (Seed S-22 / S-39) thành công!",
            "total_batches": len(all_seeded_batches),
            "total_organizations": 4,
            "total_relations": len(relations),
            "sample_batches": sample_list,
            "answer_key": answer_key,
        }

