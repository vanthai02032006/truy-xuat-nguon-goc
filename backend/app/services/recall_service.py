from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.organization import Organization
from app.models.recall import (
    Recall,
    RecallAffectedBatch,
    RecallOrganizationAction,
    RecallSeverity,
    RecallStatus,
)
from app.models.user import User, UserRole
from app.schemas.recall import RecallConfirmIsolationRequest, RecallCreateRequest
from app.services.hash_chain_service import record_chain_event
from app.services.lineage_dag_service import LineageDagService


class RecallService:
    @staticmethod
    def generate_recall_code() -> str:
        """Sinh mã lệnh thu hồi duy nhất chuẩn định dạng: RCL-YYYYMMDD-XXXXXX."""
        date_str = datetime.now(UTC).strftime("%Y%m%d")
        rand_str = secrets.token_hex(3).upper()
        return f"RCL-{date_str}-{rand_str}"

    @classmethod
    def is_batch_in_active_recall(cls, db: Session, batch_id: int) -> bool:
        """
        User Story S-38: Kiểm tra xem lô hàng có đang nằm trong bất kỳ lệnh thu hồi nào chưa hoàn tất không.
        Khóa tức thì quyền Bàn giao, Tách lô và Gộp lô đối với các lô này.
        """
        active_statuses = [RecallStatus.ACTIVE.value, RecallStatus.IN_PROGRESS.value]
        record = (
            db.query(RecallAffectedBatch)
            .join(Recall, Recall.id == RecallAffectedBatch.recall_id)
            .filter(
                RecallAffectedBatch.batch_id == batch_id,
                Recall.status.in_(active_statuses),
            )
            .first()
        )
        return record is not None

    @classmethod
    def get_active_recall_for_batch(cls, db: Session, batch_id: int) -> Recall | None:
        """Lấy thông tin lệnh thu hồi khẩn cấp đang kích hoạt đối với lô hàng này nếu có."""
        active_statuses = [RecallStatus.ACTIVE.value, RecallStatus.IN_PROGRESS.value]
        affected = (
            db.query(RecallAffectedBatch)
            .join(Recall, Recall.id == RecallAffectedBatch.recall_id)
            .filter(
                RecallAffectedBatch.batch_id == batch_id,
                Recall.status.in_(active_statuses),
            )
            .first()
        )
        return affected.recall if affected else None

    @classmethod
    def trigger_recall(
        cls,
        db: Session,
        user: User,
        payload: RecallCreateRequest | None = None,
        batch_id: int | None = None,
        reason: str | None = None,
        severity: str | None = None,
    ) -> dict[str, Any]:
        """
        User Story S-33, S-34, S-35, S-38: Mở lệnh thu hồi khẩn cấp và tự động khoanh vùng.
        1. S-33: Kiểm tra quyền: Cán bộ kiểm tra (Inspector) hoặc Quản trị của tổ chức đang giữ lô.
           Bắt buộc lý do >= 20 ký tự.
        2. S-34, S-35: Tự động khoanh vùng bằng thuật toán Truy xuôi downstream BFS.
           Thống kê: số kg còn trong kho/kệ vs số kg đã bán ra cho người tiêu dùng.
        3. Khóa trạng thái lô hàng thành "Bị phong tỏa thu hồi", chặn quyền bàn giao/tách/gộp (S-38).
        4. Tạo danh sách hành động cho từng tổ chức có hàng bị ảnh hưởng.
        5. Ghi sự kiện vào chuỗi Hash Chain.
        """
        req_batch_id = payload.batch_id if payload else batch_id
        req_reason = payload.reason if payload else reason
        req_severity = (
            payload.severity if payload else severity
        ) or RecallSeverity.CRITICAL.value

        if not req_batch_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Thiếu ID lô hàng cần thu hồi.",
            )

        # 1. Kiểm tra lý do >= 20 ký tự (S-33)
        reason_clean = (req_reason or "").strip()
        if len(reason_clean) < 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lý do thu hồi bắt buộc phải có ít nhất 20 ký tự mô tả cụ thể sự cố vi phạm an toàn thực phẩm!",
            )

        # 2. Tìm lô hàng nguồn (chấp nhận cả ID số nguyên hoặc mã định danh lô hàng)
        from app.repositories.batch_repository import BatchRepository

        source_batch = BatchRepository.get_by_id_or_code(db, req_batch_id)
        if not source_batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy lô hàng với ID hoặc mã '{req_batch_id}'",
            )

        # 3. Phân quyền (S-33):
        # - Cán bộ kiểm tra (Inspector)
        # - Quản trị hệ thống (System Admin)
        # - Hoặc Quản trị của tổ chức đang giữ lô (Admin / Manager thuộc cùng organization_id)
        is_inspector = user.role in [UserRole.INSPECTOR.value, "inspector"]
        is_system_admin = (
            user.role in [UserRole.SYSTEM_ADMIN.value, "system_admin", UserRole.ADMIN.value, "admin"]
            and user.organization_id is None
        )
        is_holding_org_owner = (
            user.organization_id is not None
            and user.organization_id == source_batch.organization_id
            and user.role in [
                UserRole.FARM.value,
                UserRole.COOP.value,
                UserRole.DISTRIBUTOR.value,
                "farm",
                "coop",
                "distributor",
                "admin",
                "farm_owner",
                "owner",
                UserRole.SYSTEM_ADMIN.value,
            ]
        )

        if not (is_inspector or is_system_admin or is_holding_org_owner):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ Cán bộ kiểm tra (Inspector) hoặc Quản trị của tổ chức đang giữ lô mới có quyền kích hoạt lệnh thu hồi khẩn cấp!",
            )

        # 4. Kiểm tra xem lô đã nằm trong active recall nào chưa
        if cls.is_batch_in_active_recall(db, source_batch.id):
            existing = cls.get_active_recall_for_batch(db, source_batch.id)
            code_str = existing.recall_code if existing else "N/A"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lô hàng #{source_batch.batch_code} hiện đang nằm trong Lệnh thu hồi #{code_str} chưa kết thúc!",
            )

        # 5. Tự động khoanh vùng bằng thuật toán Truy xuôi (Downstream BFS - S-34)
        downstream_res = LineageDagService.trace_downstream_descendants(
            db, source_batch.id
        )
        descendants = downstream_res.get("descendants", [])

        # Tập hợp tất cả các lô bị ảnh hưởng: lô nguồn + các lô hậu duệ
        affected_batches_dict: dict[int, dict[str, Any]] = {}

        # 5.1 Thêm lô nguồn (Root của đợt recall)
        src_init = float(source_batch.initial_quantity or 0.0)
        src_rem = float(source_batch.remaining_quantity or 0.0)
        src_sold = max(0.0, round(src_init - src_rem, 3))
        src_loc = (
            source_batch.land_plot.address
            if source_batch.land_plot and source_batch.land_plot.address
            else (
                source_batch.organization.name
                if source_batch.organization
                else "Chưa xác định"
            )
        )

        affected_batches_dict[source_batch.id] = {
            "batch_id": source_batch.id,
            "organization_id": source_batch.organization_id,
            "generation": "ROOT",
            "initial_quantity": src_init,
            "remaining_quantity": src_rem,
            "sold_quantity": src_sold,
            "current_location": src_loc,
            "batch_status_before": source_batch.status,
            "batch_obj": source_batch,
        }

        # 5.2 Thêm toàn bộ các lô con / lô cháu
        for d in descendants:
            b_id = d["id"]
            if b_id not in affected_batches_dict:
                d_batch = db.query(Batch).filter(Batch.id == b_id).first()
                if d_batch:
                    d_init = float(d_batch.initial_quantity or 0.0)
                    d_rem = float(d_batch.remaining_quantity or 0.0)
                    d_sold = max(0.0, round(d_init - d_rem, 3))
                    affected_batches_dict[b_id] = {
                        "batch_id": d_batch.id,
                        "organization_id": d_batch.organization_id,
                        "generation": d.get("generation", "DESCENDANT"),
                        "initial_quantity": d_init,
                        "remaining_quantity": d_rem,
                        "sold_quantity": d_sold,
                        "current_location": d.get("current_location", "Không xác định"),
                        "batch_status_before": d_batch.status,
                        "batch_obj": d_batch,
                    }

        # 6. Thống kê chi tiết (S-35)
        total_affected_count = len(affected_batches_dict)
        total_stock = round(
            sum(item["remaining_quantity"] for item in affected_batches_dict.values()),
            3,
        )
        total_sold = round(
            sum(item["sold_quantity"] for item in affected_batches_dict.values()), 3
        )
        total_affected_weight = round(total_stock + total_sold, 3)

        # 7. Khởi tạo bản ghi Recall
        recall_code = cls.generate_recall_code()
        recall = Recall(
            recall_code=recall_code,
            source_batch_id=source_batch.id,
            initiator_user_id=user.id,
            initiator_organization_id=user.organization_id
            or source_batch.organization_id,
            reason=reason_clean,
            severity=req_severity,
            status=RecallStatus.ACTIVE.value,
            total_affected_batches=total_affected_count,
            total_affected_kg=total_affected_weight,
            total_stock_kg=total_stock,
            total_sold_kg=total_sold,
        )
        db.add(recall)
        db.flush()  # Lấy recall.id

        # 8. Thêm các bản ghi RecallAffectedBatch và cập nhật trạng thái lô
        org_batches_map: dict[int, list[dict[str, Any]]] = {}
        for item in affected_batches_dict.values():
            aff_record = RecallAffectedBatch(
                recall_id=recall.id,
                batch_id=item["batch_id"],
                organization_id=item["organization_id"],
                generation=item["generation"],
                initial_quantity=item["initial_quantity"],
                remaining_quantity=item["remaining_quantity"],
                sold_quantity=item["sold_quantity"],
                current_location=item["current_location"],
                batch_status_before=item["batch_status_before"],
                is_isolated=False,
            )
            db.add(aff_record)

            # Khóa trạng thái lô thành "Bị phong tỏa thu hồi"
            b_obj = item["batch_obj"]
            b_obj.status = "Bị phong tỏa thu hồi"

            # Phân nhóm theo tổ chức
            org_id = item["organization_id"]
            if org_id not in org_batches_map:
                org_batches_map[org_id] = []
            org_batches_map[org_id].append(item)

        # 9. Tạo quy trình xử lý cho từng tổ chức (S-36, S-37)
        for org_id, o_batches in org_batches_map.items():
            o_stock = round(sum(b["remaining_quantity"] for b in o_batches), 3)
            action = RecallOrganizationAction(
                recall_id=recall.id,
                organization_id=org_id,
                status="PENDING",
                affected_batch_count=len(o_batches),
                stock_kg=o_stock,
            )
            db.add(action)

        # 10. Ghi nhận chuỗi hash SHA-256
        record_chain_event(
            db=db,
            batch_id=source_batch.id,
            event_type="EMERGENCY_RECALL_TRIGGERED",
            event_data=(
                f"KÍCH HOẠT LỆNH THU HỒI KHẨN CẤP #{recall.recall_code} cho lô {source_batch.batch_code}. "
                f"Lý do: {reason_clean}. Khoanh vùng {total_affected_count} lô ({total_stock}kg còn trong kho, {total_sold}kg đã bán ra)."
            ),
            organization_id=user.organization_id or source_batch.organization_id,
        )

        db.commit()
        db.refresh(recall)
        return cls.get_recall_detail(db, recall.id, user=user)

    @classmethod
    def confirm_organization_isolation(
        cls,
        db: Session,
        recall_id: int,
        user: User,
        payload: RecallConfirmIsolationRequest | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """User Story S-36, S-37: Đại diện tổ chức có lô bị ảnh hưởng xác nhận đã cô lập phần hàng của mình."""
        recall = db.query(Recall).filter(Recall.id == recall_id).first()
        if not recall:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy lệnh thu hồi #{recall_id}",
            )

        if recall.status in [
            RecallStatus.COMPLETED.value,
            RecallStatus.CANCELLED.value,
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lệnh thu hồi này đã hoàn thành hoặc đã bị hủy!",
            )

        org_id = user.organization_id
        if not org_id and user.role not in [
            UserRole.SYSTEM_ADMIN.value,
            UserRole.ADMIN.value,
        ]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Người dùng chưa được gán tổ chức để thực hiện xác nhận cô lập!",
            )

        # Tìm bản ghi action của tổ chức này
        action = None
        if org_id:
            action = (
                db.query(RecallOrganizationAction)
                .filter(
                    RecallOrganizationAction.recall_id == recall_id,
                    RecallOrganizationAction.organization_id == org_id,
                )
                .first()
            )

        # Nếu là Admin hệ thống thì có thể hỗ trợ xác nhận cho tổ chức đầu tiên đang PENDING
        if not action and user.role in [
            UserRole.SYSTEM_ADMIN.value,
            UserRole.ADMIN.value,
        ]:
            action = (
                db.query(RecallOrganizationAction)
                .filter(
                    RecallOrganizationAction.recall_id == recall_id,
                    RecallOrganizationAction.status == "PENDING",
                )
                .first()
            )

        if not action:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tổ chức của bạn không có lô hàng nào cần cô lập trong lệnh thu hồi này hoặc đã xác nhận xong!",
            )

        action_notes = (
            payload.notes if payload else notes
        ) or "Đã hoàn tất cô lập, niêm phong toàn bộ hàng trong kho"

        # Cập nhật trạng thái tổ chức
        action.status = "CONFIRMED_ISOLATED"
        action.action_notes = action_notes
        action.confirmed_by_user_id = user.id
        action.confirmed_at = datetime.now(UTC)
        db.flush()

        # Đánh dấu is_isolated cho tất cả các lô của tổ chức này trong recall
        db.query(RecallAffectedBatch).filter(
            RecallAffectedBatch.recall_id == recall_id,
            RecallAffectedBatch.organization_id == action.organization_id,
        ).update(
            {
                RecallAffectedBatch.is_isolated: True,
                RecallAffectedBatch.isolated_at: datetime.now(UTC),
            },
            synchronize_session=False,
        )

        # Kiểm tra nếu tất cả các tổ chức đã xác nhận xử lý xong
        pending_count = (
            db.query(RecallOrganizationAction)
            .filter(
                RecallOrganizationAction.recall_id == recall_id,
                RecallOrganizationAction.status == "PENDING",
            )
            .count()
        )

        if pending_count == 0:
            recall.status = RecallStatus.COMPLETED.value
        else:
            recall.status = RecallStatus.IN_PROGRESS.value

        # Ghi sự kiện chuỗi hash
        org = (
            db.query(Organization)
            .filter(Organization.id == action.organization_id)
            .first()
        )
        org_name = org.name if org else f"Org #{action.organization_id}"
        record_chain_event(
            db=db,
            batch_id=recall.source_batch_id,
            event_type="RECALL_ORGANIZATION_CONFIRMED",
            event_data=(
                f"Tổ chức {org_name} đã xác nhận cô lập hoàn tất "
                f"{action.affected_batch_count} lô hàng ({action.stock_kg} kg) theo lệnh #{recall.recall_code}. Ghi chú: {action_notes}"
            ),
            organization_id=action.organization_id,
        )

        db.commit()
        return cls.get_recall_detail(db, recall.id, user=user)

    @classmethod
    def get_recall_detail(
        cls, db: Session, recall_id: int, user: User | None = None
    ) -> dict[str, Any]:
        """Lấy chi tiết toàn bộ lệnh thu hồi, tiến độ thanh trạng thái X/Y tổ chức và các lô liên quan."""
        recall = db.query(Recall).filter(Recall.id == recall_id).first()
        if not recall:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy lệnh thu hồi #{recall_id}",
            )

        # Tính tiến độ các tổ chức
        actions = (
            db.query(RecallOrganizationAction)
            .filter(RecallOrganizationAction.recall_id == recall_id)
            .all()
        )
        total_orgs = len(actions)
        confirmed_orgs = sum(1 for a in actions if a.status == "CONFIRMED_ISOLATED")
        progress_pct = (
            round((confirmed_orgs / total_orgs) * 100.0, 1) if total_orgs > 0 else 100.0
        )
        summary_str = f"{confirmed_orgs}/{total_orgs} tổ chức đã xác nhận cô lập"

        progress_info = {
            "total_organizations": total_orgs,
            "confirmed_organizations": confirmed_orgs,
            "progress_percentage": progress_pct,
            "status_summary": summary_str,
        }

        # Danh sách lô bị ảnh hưởng
        affected_items = (
            db.query(RecallAffectedBatch)
            .filter(RecallAffectedBatch.recall_id == recall_id)
            .all()
        )
        batches_data = []
        for a in affected_items:
            b_code = a.batch.batch_code if a.batch else "N/A"
            p_name = a.batch.product_name if a.batch else "N/A"
            o_name = a.organization.name if a.organization else "N/A"
            batches_data.append(
                {
                    "id": a.id,
                    "batch_id": a.batch_id,
                    "batch_code": b_code,
                    "product_name": p_name,
                    "organization_id": a.organization_id,
                    "organization_name": o_name,
                    "generation": a.generation,
                    "initial_quantity": float(a.initial_quantity or 0.0),
                    "remaining_quantity": float(a.remaining_quantity or 0.0),
                    "sold_quantity": float(a.sold_quantity or 0.0),
                    "current_location": a.current_location,
                    "batch_status_before": a.batch_status_before,
                    "is_isolated": a.is_isolated,
                    "isolated_at": a.isolated_at,
                }
            )

        # Danh sách tiến độ tổ chức
        org_actions_data = []
        for act in actions:
            org_actions_data.append(
                {
                    "id": act.id,
                    "organization_id": act.organization_id,
                    "organization_name": (
                        act.organization.name if act.organization else "N/A"
                    ),
                    "organization_code": (
                        act.organization.code if act.organization else None
                    ),
                    "status": act.status,
                    "action_notes": act.action_notes,
                    "confirmed_by_name": (
                        act.confirmed_by_user.full_name
                        if act.confirmed_by_user
                        else None
                    ),
                    "confirmed_at": act.confirmed_at,
                    "affected_batch_count": act.affected_batch_count,
                    "stock_kg": float(act.stock_kg or 0.0),
                }
            )

        init_user_name = (
            recall.initiator_user.full_name if recall.initiator_user else "Hệ thống"
        )
        init_org_name = (
            recall.initiator_organization.name
            if recall.initiator_organization
            else "N/A"
        )
        src_code = recall.source_batch.batch_code if recall.source_batch else "N/A"
        p_name = recall.source_batch.product_name if recall.source_batch else "N/A"

        return {
            "id": recall.id,
            "recall_code": recall.recall_code,
            "source_batch_id": recall.source_batch_id,
            "source_batch_code": src_code,
            "product_name": p_name,
            "reason": recall.reason,
            "severity": recall.severity,
            "status": recall.status,
            "initiator_name": init_user_name,
            "initiator_org_name": init_org_name,
            "total_affected_batches": recall.total_affected_batches,
            "total_affected_kg": float(recall.total_affected_kg or 0.0),
            "total_stock_kg": float(recall.total_stock_kg or 0.0),
            "total_sold_kg": float(recall.total_sold_kg or 0.0),
            "progress": progress_info,
            "affected_batches": batches_data,
            "organization_actions": org_actions_data,
            "created_at": recall.created_at,
            "updated_at": recall.updated_at,
        }

    @classmethod
    def list_recalls(
        cls,
        db: Session,
        user: User,
        status_filter: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Lấy danh sách các lệnh thu hồi có phân quyền:
        - Inspector, System Admin xem tất cả các lệnh.
        - Các tổ chức khác chỉ xem các lệnh do mình khởi tạo hoặc có lô của mình bị ảnh hưởng.
        """
        query = db.query(Recall)

        is_admin_or_inspector = user.role in [
            UserRole.INSPECTOR.value,
            UserRole.SYSTEM_ADMIN.value,
            UserRole.ADMIN.value,
        ]

        if not is_admin_or_inspector:
            if not user.organization_id:
                return ([], 0)
            # Lọc các recall do org khởi tạo HOẶC org có lô bị ảnh hưởng
            affected_recall_ids = (
                db.query(RecallAffectedBatch.recall_id)
                .filter(RecallAffectedBatch.organization_id == user.organization_id)
                .subquery()
            )
            query = query.filter(
                or_(
                    Recall.initiator_organization_id == user.organization_id,
                    Recall.id.in_(affected_recall_ids),
                )
            )

        if status_filter:
            query = query.filter(Recall.status == status_filter)

        total = query.count()
        recalls = (
            query.order_by(Recall.created_at.desc()).offset(skip).limit(limit).all()
        )

        items = [cls.get_recall_detail(db, r.id, user=user) for r in recalls]
        return (items, total)
