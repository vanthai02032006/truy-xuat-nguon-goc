from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.batch import Batch
from app.models.user import User, UserRole
from app.repositories.security_log_repository import SecurityLogRepository
from app.services.hash_chain_service import (
    simulate_tamper_attack,
    verify_chain_integrity,
)

router = APIRouter(prefix="/chain-events", tags=["chain-events"])

INSPECTOR_ADMIN_ROLES = {
    UserRole.INSPECTOR.value,
    UserRole.ADMIN.value,
    UserRole.SYSTEM_ADMIN.value,
    "inspector",
    "admin",
    "system_admin",
}


class SimulateTamperRequest(BaseModel):
    batch_id: int | None = None
    batch_code: str | None = None
    action: str = Field(
        ...,
        description="Loại mô phỏng: 'tamper_data' (sửa lén SQL), 'delete_event' (xóa sự kiện giữa chuỗi), 'reset' (khôi phục)",
    )
    event_id: int | None = None
    tamper_value: str | None = None


@router.get("")
@router.get("/")
def list_chain_events(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    batch_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    """
    Lấy danh sách các mắt xích sự kiện băm SHA-256 từ cơ sở dữ liệu thật (S-05, S-23):
    - Admin / Inspector: Xem toàn bộ sự kiện phục vụ kiểm toán / thanh tra.
    - Tổ chức khác (farm, cooperative, carrier, retailer):
      Chỉ xem các sự kiện thuộc quyền sở hữu của tổ chức đó (event.organization_id == current_user.organization_id)
      HOẶC sự kiện thuộc chuỗi lịch sử của các lô hàng mà tổ chức đó đang giữ hoặc từng sở hữu/tiếp nhận (S-23).
    - Ngăn chặn hoàn toàn rò rỉ dữ liệu giữa các tổ chức không liên quan.
    """
    from collections import deque
    from sqlalchemy import and_, func, or_
    from app.models.batch_relation import BatchRelation
    from app.models.chain_event import ChainEvent
    from app.models.handover import Handover, HandoverStatus

    query = db.query(ChainEvent)

    is_admin_or_inspector = current_user.role in INSPECTOR_ADMIN_ROLES
    if not is_admin_or_inspector:
        org_id = current_user.organization_id
        if not org_id:
            return []

        # 1. Các lô mà tổ chức hiện đang trực tiếp nắm giữ (Điều kiện a)
        held_batch_ids = {
            b_id for (b_id,) in db.query(Batch.id).filter(Batch.organization_id == org_id).all()
        }

        # 2. Các lô tổ tiên của các lô đang nắm giữ (Điều kiện b: BFS ngược)
        ancestor_ids: set[int] = set()
        if held_batch_ids:
            queue: deque[int] = deque(held_batch_ids)
            visited: set[int] = set(held_batch_ids)
            while queue:
                curr_id = queue.popleft()
                parent_relations = (
                    db.query(BatchRelation.parent_batch_id)
                    .filter(BatchRelation.child_batch_id == curr_id)
                    .all()
                )
                for (p_id,) in parent_relations:
                    ancestor_ids.add(p_id)
                    if p_id not in visited:
                        visited.add(p_id)
                        queue.append(p_id)

        # 3. Các lô tổ chức từng tiếp nhận thành công (to_org_id)
        received_batch_ids = {
            b_id
            for (b_id,) in db.query(Handover.batch_id)
            .filter(
                Handover.to_org_id == org_id,
                Handover.status == HandoverStatus.ACCEPTED.value,
            )
            .all()
        }

        # 4. Các lô tổ chức từng nắm giữ và đã bàn giao đi trong quá khứ (Điều kiện c: chỉ xem tới cutoff_time)
        past_handovers = (
            db.query(
                Handover.batch_id,
                func.coalesce(func.max(Handover.updated_at), func.max(Handover.created_at)).label("cutoff"),
            )
            .filter(
                Handover.from_org_id == org_id,
                Handover.status == HandoverStatus.ACCEPTED.value,
            )
            .group_by(Handover.batch_id)
            .all()
        )

        full_access_batch_ids = held_batch_ids | ancestor_ids | received_batch_ids
        conditions = [ChainEvent.organization_id == org_id]
        if full_access_batch_ids:
            conditions.append(ChainEvent.batch_id.in_(full_access_batch_ids))

        for p_batch_id, cutoff in past_handovers:
            if p_batch_id not in full_access_batch_ids and cutoff is not None:
                conditions.append(
                    and_(ChainEvent.batch_id == p_batch_id, ChainEvent.created_at <= cutoff)
                )

        query = query.filter(or_(*conditions))

    if batch_id:
        query = query.filter(ChainEvent.batch_id == batch_id)

    events = query.order_by(ChainEvent.id.desc()).limit(limit).all()
    return [
        {
            "id": e.id,
            "batch_id": e.batch_id,
            "event_type": e.event_type,
            "event_data": e.event_data,
            "organization_id": e.organization_id,
            "previous_hash": e.previous_hash,
            "current_hash": e.current_hash,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "batch_code": e.batch.batch_code if e.batch else None,
            "org_name": e.organization.name if e.organization else f"Tổ chức #{e.organization_id}",
        }
        for e in events
    ]


@router.get("/verify")
def verify_batch_chain(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    batch_id: int | None = Query(default=None, description="ID của lô hàng cần kiểm tra"),
    batch_code: str | None = Query(default=None, description="Mã lô hàng cần kiểm tra"),
) -> dict[str, Any]:
    """
    User Story S-12, Task T-29:
    Kiểm tra tính toàn vẹn chuỗi Hash SHA-256 cho Cán bộ kiểm tra & Quản trị hệ thống.
    - Phát hiện sự kiện bị sửa lén trực tiếp trong CSDL (mã băm không khớp).
    - Phát hiện đứt gãy liên kết chuỗi (previous_hash không khớp).
    - Đánh dấu nghi vấn mọi sự kiện nằm phía sau vị trí bị xâm phạm.
    """
    if not batch_id and not batch_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng cung cấp ít nhất 'batch_id' hoặc 'batch_code'.",
        )

    target_batch = None
    if batch_id:
        target_batch = db.query(Batch).filter(Batch.id == batch_id).first()
    elif batch_code:
        target_batch = (
            db.query(Batch).filter(Batch.batch_code == batch_code.strip()).first()
        )

    if not target_batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lô hàng tương ứng để kiểm tra chuỗi hash.",
        )

    if current_user.role not in INSPECTOR_ADMIN_ROLES:
        from app.services.batch_access_service import can_view_batch

        allowed, _, _ = can_view_batch(
            org_id=current_user.organization_id,
            batch=target_batch,
            db=db,
            user_role=current_user.role,
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không có quyền truy cập dữ liệu của tổ chức khác.",
            )

    return verify_chain_integrity(db, batch_id=target_batch.id)


@router.post("/simulate-tamper")
def simulate_chain_tamper(
    payload: SimulateTamperRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    request: Request,
) -> dict[str, Any]:
    """
    User Story S-12, Task T-29, T-30:
    Mô phỏng sửa lén SQL hoặc Xóa sự kiện giữa chuỗi để kiểm thử thuật toán chống gian lận.
    CHỈ Cán bộ kiểm tra (Inspector) và Quản trị hệ thống (Admin) mới có quyền chạy API này.
    """
    if current_user.role not in INSPECTOR_ADMIN_ROLES:
        client_ip = request.client.host if request.client else "unknown"
        SecurityLogRepository.log_attempt(
            db=db,
            user_id=current_user.id,
            user_email=current_user.email,
            user_org_id=current_user.organization_id,
            attempt_type="unauthorized_tamper_simulation",
            target_resource="chain_events",
            target_id=str(payload.batch_id or payload.batch_code or "unknown"),
            target_org_id=None,
            endpoint=request.url.path,
            method="POST",
            ip_address=client_ip,
            description="Người dùng không phải Inspector/Admin cố tình gọi API mô phỏng can thiệp chuỗi hash.",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Cán bộ kiểm tra (Inspector) và Quản trị hệ thống (Admin) mới có quyền chạy mô phỏng.",
        )

    target_batch_id = payload.batch_id
    if not target_batch_id and payload.batch_code:
        batch_obj = (
            db.query(Batch).filter(Batch.batch_code == payload.batch_code.strip()).first()
        )
        if batch_obj:
            target_batch_id = batch_obj.id

    if not target_batch_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng cung cấp batch_id hoặc batch_code hợp lệ để mô phỏng.",
        )

    result = simulate_tamper_attack(
        db=db,
        batch_id=target_batch_id,
        action=payload.action,
        event_id=payload.event_id,
        tamper_value=payload.tamper_value,
    )
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Mô phỏng thất bại."),
        )

    return result


@router.put("/{event_id}")
def update_event_forbidden(
    event_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    User Story S-11: Bảng batch_events/chain_events là CHỈ-THÊM (append-only).
    Không có bất kỳ API nào cho phép UPDATE sự kiện đã ghi.
    """
    client_ip = request.client.host if request.client else "unknown"
    SecurityLogRepository.log_attempt(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        user_org_id=current_user.organization_id,
        attempt_type="append_only_violation_update",
        target_resource="chain_events",
        target_id=str(event_id),
        target_org_id=None,
        endpoint=request.url.path,
        method="PUT",
        ip_address=client_ip,
        description="Cố tình gọi API sửa sự kiện chuỗi băm (vi phạm nguyên tắc append-only S-11).",
    )
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Bảng chain_events là chỉ-thêm (append-only - S-11). Tuyệt đối không cho phép chỉnh sửa sự kiện đã ghi.",
    )


@router.delete("/{event_id}")
def delete_event_forbidden(
    event_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    User Story S-11: Bảng batch_events/chain_events là CHỈ-THÊM (append-only).
    Không có bất kỳ API nào cho phép DELETE sự kiện đã ghi.
    """
    client_ip = request.client.host if request.client else "unknown"
    SecurityLogRepository.log_attempt(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        user_org_id=current_user.organization_id,
        attempt_type="append_only_violation_delete",
        target_resource="chain_events",
        target_id=str(event_id),
        target_org_id=None,
        endpoint=request.url.path,
        method="DELETE",
        ip_address=client_ip,
        description="Cố tình gọi API xóa sự kiện chuỗi băm (vi phạm nguyên tắc append-only S-11).",
    )
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Bảng chain_events là chỉ-thêm (append-only - S-11). Tuyệt đối không cho phép xóa sự kiện đã ghi.",
    )
