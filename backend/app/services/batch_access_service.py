from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Query, Session

from app.models.batch import Batch
from app.models.batch_relation import BatchRelation
from app.models.chain_event import ChainEvent
from app.models.handover import Handover, HandoverStatus
from app.models.organization import Organization
from app.models.user import UserRole


def apply_tenant_filter(query: Query, model_class: Any, organization_id: int | None) -> Query:
    """
    Task T-12: Gắn điều kiện lọc WHERE organization_id = current_org_id ở tầng truy vấn SQL.
    Tuyệt đối không fetch toàn bộ rồi lọc trên RAM/giao diện.
    Nếu organization_id is None (Inspector / System Admin), không gắn điều kiện lọc.
    """
    if organization_id is not None and hasattr(model_class, "organization_id"):
        return query.filter(model_class.organization_id == organization_id)
    return query


def tenant_query(db: Session, model_class: Any, organization_id: int | None) -> Query:
    """
    Task T-12: Hàm truy vấn nền tự động gắn điều kiện lọc WHERE organization_id = current_org_id.
    """
    return apply_tenant_filter(db.query(model_class), model_class, organization_id)


def can_view_batch(
    org_id: int | Organization | None,
    batch: Batch | int,
    db: Session,
    user_role: str | None = None,
) -> tuple[bool, str, datetime | None]:
    """
    Quy tắc xem lịch sử tổ tiên xuyên tổ chức theo User Story S-23 và Task T-54:
    Một tổ chức ĐƯỢC PHÉP xem thông tin và dòng thời gian của một lô nếu thỏa 1 trong 3 điều kiện:
      a) Tổ chức đang giữ lô đó (batch.organization_id == org_id).
      b) Lô đó là TỔ TIÊN (qua các bước tách/gộp/bàn giao trước đó) của một lô mà tổ chức đang giữ
         (để nhà phân phối xem được vùng trồng và HTX sơ chế đã làm gì).
      c) Tổ chức từng giữ lô đó trong quá khứ (nhưng chỉ được xem lịch sử các sự kiện tính tới
         thời điểm bàn giao đi, KHÔNG được thấy các bước phát sinh sau khi đã bàn giao cho bên khác).

    Nếu gọi API xem một lô khác của tổ chức đối tác mà KHÔNG liên quan phả hệ tới lô mình đang giữ
    -> trả về HTTP 403 Forbidden.

    Returns:
      (allowed: bool, reason: str, cutoff_time: datetime | None)
    """
    if hasattr(org_id, "id"):
        org_id = org_id.id
    # 0. Cán bộ kiểm tra (Inspector) và Quản trị hệ thống (System Admin) được phép đọc dữ liệu toàn chuỗi
    if user_role in [
        UserRole.INSPECTOR.value,
        UserRole.SYSTEM_ADMIN.value,
        UserRole.ADMIN.value,
        "inspector",
        "system_admin",
        "admin",
    ]:
        return True, "INSPECTOR_OR_ADMIN", None

    # Lấy đối tượng Batch từ DB nếu truyền batch_id
    if isinstance(batch, int):
        batch_obj = db.query(Batch).filter(Batch.id == batch).first()
        if not batch_obj:
            return False, "BATCH_NOT_FOUND", None
    else:
        batch_obj = batch

    if org_id is None:
        return False, "NO_ORGANIZATION", None

    # Điều kiện a: Tổ chức đang trực tiếp giữ lô đó
    if batch_obj.organization_id == org_id:
        return True, "CURRENT_HOLDER", None

    # Điều kiện b: Lô đó là TỔ TIÊN của một lô mà tổ chức đang giữ
    # Lấy tập hợp tất cả các lô hàng mà tổ chức hiện đang giữ
    held_batches = (
        db.query(Batch.id)
        .filter(Batch.organization_id == org_id)
        .all()
    )
    held_batch_ids = {b_id for (b_id,) in held_batches}

    if held_batch_ids:
        # Duyệt đồ thị BFS theo chiều xuôi (cha -> con) từ batch_obj.id
        # Nếu chạm tới bất kỳ lô nào thuộc held_batch_ids -> batch_obj là tổ tiên của lô mà org đang giữ!
        queue: deque[int] = deque([batch_obj.id])
        visited: set[int] = {batch_obj.id}
        while queue:
            curr_id = queue.popleft()
            child_relations = (
                db.query(BatchRelation.child_batch_id)
                .filter(BatchRelation.parent_batch_id == curr_id)
                .all()
            )
            for (child_id,) in child_relations:
                if child_id in held_batch_ids:
                    return True, "ANCESTOR_OF_HELD_BATCH", None
                if child_id not in visited:
                    visited.add(child_id)
                    queue.append(child_id)

    # Điều kiện c: Tổ chức từng giữ lô đó trong quá khứ
    # Kiểm tra trong bảng handovers xem có lệnh bàn giao ACCEPTED nào mà from_org_id == org_id không
    past_handover = (
        db.query(Handover)
        .filter(
            Handover.batch_id == batch_obj.id,
            Handover.from_org_id == org_id,
            Handover.status == HandoverStatus.ACCEPTED.value,
        )
        .order_by(Handover.updated_at.desc(), Handover.id.desc())
        .first()
    )
    if past_handover:
        # Thời điểm bàn giao đi: chỉ được xem các sự kiện tính tới thời điểm này
        cutoff_time = past_handover.updated_at or past_handover.created_at
        return True, "PAST_HOLDER", cutoff_time

    # Không thỏa mãn bất kỳ điều kiện nào trong 3 quy tắc trên
    return False, "NOT_RELATED", None


def canView(
    org: int | Organization | None,
    batch: int | Batch,
    db: Session | None = None,
    user_role: str | None = None,
) -> bool:
    """
    Hàm canView(org, batch) theo chuẩn User Story S-23 và Task T-54.
    Trả về True nếu thỏa 1 trong 3 điều kiện (đang giữ, là tổ tiên, hoặc từng giữ).
    """
    org_id = org.id if hasattr(org, "id") else org
    if db is None:
        from app.core.database import SessionLocal

        with SessionLocal() as session:
            allowed, _, _ = can_view_batch(org_id, batch, session, user_role=user_role)
            return allowed
    allowed, _, _ = can_view_batch(org_id, batch, db, user_role=user_role)
    return allowed


def get_viewable_chain_events(
    batch_id: int,
    org_id: int | None,
    db: Session,
    user_role: str | None = None,
) -> list[ChainEvent]:
    """
    Lấy danh sách các sự kiện hash chain của lô hàng được phép xem theo S-23:
    Nếu tổ chức từng giữ lô trong quá khứ (Điều kiện c) -> chỉ xem các sự kiện tính tới thời điểm bàn giao đi.
    """
    allowed, _reason, cutoff_time = can_view_batch(org_id, batch_id, db, user_role)
    if not allowed:
        return []

    query = db.query(ChainEvent).filter(ChainEvent.batch_id == batch_id)
    if cutoff_time is not None:
        query = query.filter(ChainEvent.created_at <= cutoff_time)

    return query.order_by(ChainEvent.id.asc()).all()
