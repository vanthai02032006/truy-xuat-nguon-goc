from collections import deque
from typing import Any

from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.batch_relation import BatchRelation


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
