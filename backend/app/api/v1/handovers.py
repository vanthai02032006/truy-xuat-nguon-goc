from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.batch import Batch
from app.models.chain_event import ChainEvent
from app.models.handover import Handover, HandoverStatus
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.repositories.security_log_repository import SecurityLogRepository
from app.schemas.handover import (
    ChainEventResponse,
    HandoverCreate,
    HandoverRejectRequest,
    HandoverResponse,
    OrganizationSimpleResponse,
)
from app.services.hash_chain_service import record_chain_event

router = APIRouter(prefix="/handovers", tags=["handovers"])


def _to_handover_response(h: Handover) -> HandoverResponse:
    """Helper chuyển đổi model Handover thành schema response đầy đủ thông tin."""
    return HandoverResponse(
        id=h.id,
        batch_id=h.batch_id,
        from_org_id=h.from_org_id,
        to_org_id=h.to_org_id,
        status=h.status,
        reject_reason=h.reject_reason,
        temperature=str(h.temperature) if h.temperature is not None else None,
        created_at=h.created_at,
        updated_at=h.updated_at,
        batch_code=h.batch.batch_code if h.batch else None,
        product_name=h.batch.product_name if h.batch else None,
        from_org_name=h.from_org.name if h.from_org else f"Tổ chức #{h.from_org_id}",
        to_org_name=h.to_org.name if h.to_org else f"Tổ chức #{h.to_org_id}",
        batch_status=h.batch.status if h.batch else None,
    )


@router.post("", response_model=HandoverResponse, status_code=status.HTTP_201_CREATED)
def create_handover(
    payload: HandoverCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Tạo lệnh bàn giao lô hàng sang tổ chức tiếp nhận (User Story S-15):
    - Tổ chức A khởi tạo bàn giao sang tổ chức B.
    - Lô chuyển sang trạng thái "chờ xác nhận".
    - Tổ chức A vẫn tạm thời giữ quyền sở hữu.
    - Chặn không cho tạo lệnh bàn giao thứ hai khi đang có lệnh chờ.
    """
    if current_user.role == UserRole.INSPECTOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cán bộ kiểm tra chỉ có quyền xem dữ liệu (chế độ chỉ đọc).",
        )

    batch = db.query(Batch).filter(Batch.id == payload.batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lô hàng không tồn tại.",
        )

    # 1. Kiểm tra quyền sở hữu hiện tại: Chỉ tổ chức đang giữ lô mới được tạo bàn giao
    if (
        current_user.role not in [UserRole.SYSTEM_ADMIN.value, UserRole.ADMIN.value]
        and batch.organization_id != current_user.organization_id
    ):
        client_ip = request.client.host if request.client else "unknown"
        SecurityLogRepository.log_attempt(
            db=db,
            user_id=current_user.id,
            user_email=current_user.email,
            user_org_id=current_user.organization_id,
            attempt_type="cross_tenant_access_denied",
            target_resource="batch",
            target_id=str(batch.id),
            target_org_id=batch.organization_id,
            endpoint=request.url.path,
            method=request.method,
            ip_address=client_ip,
            description=(
                f"Người dùng {current_user.email} (Tổ chức {current_user.organization_id}) "
                f"cố tình tạo lệnh bàn giao trên lô #{batch.id} của Tổ chức {batch.organization_id}."
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền bàn giao lô hàng của tổ chức khác.",
        )

    # S-38: Khóa tức thì quyền Bàn giao đối với các lô nằm trong danh sách lệnh thu hồi
    from app.services.recall_service import RecallService

    if RecallService.is_batch_in_active_recall(db, batch.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lô hàng #{batch.batch_code} đang nằm trong Lệnh thu hồi khẩn cấp (S-38), nghiêm cấm bàn giao luân chuyển!",
        )

    # 2. Không cho phép tự bàn giao cho chính mình
    if payload.to_org_id == current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể bàn giao lô hàng cho chính tổ chức của mình.",
        )

    # 3. Kiểm tra tổ chức nhận có tồn tại không
    target_org = (
        db.query(Organization).filter(Organization.id == payload.to_org_id).first()
    )
    if not target_org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tổ chức nhận bàn giao không tồn tại trong hệ thống.",
        )

    # 4. Chặn không cho tạo lệnh bàn giao thứ hai khi đang có lệnh chờ xác nhận (S-15)
    existing_pending = (
        db.query(Handover)
        .filter(
            Handover.batch_id == batch.id,
            Handover.status == HandoverStatus.PENDING.value,
        )
        .first()
    )
    if existing_pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lô hàng đang có một lệnh bàn giao chờ xác nhận.",
        )

    # 5. Cập nhật trạng thái lô hàng thành "chờ xác nhận", A vẫn giữ quyền sở hữu
    batch.status = "chờ xác nhận"

    handover = Handover(
        batch_id=batch.id,
        from_org_id=current_user.organization_id,
        to_org_id=payload.to_org_id,
        status=HandoverStatus.PENDING.value,
        temperature=str(payload.temperature)
        if payload.temperature is not None
        else None,
    )
    db.add(handover)
    db.flush()

    # 6. Ghi nhận sự kiện khởi tạo bàn giao vào chuỗi Hash SHA-256
    record_chain_event(
        db=db,
        batch_id=batch.id,
        event_type="HANDOVER_CREATED",
        event_data=(
            f"Khởi tạo lệnh bàn giao lô {batch.batch_code} từ Org #{current_user.organization_id} "
            f"sang Org #{payload.to_org_id}. Nhiệt độ ghi nhận: {payload.temperature or 'N/A'}"
        ),
        organization_id=current_user.organization_id,
    )

    db.commit()
    db.refresh(handover)
    return _to_handover_response(handover)


@router.get("", response_model=list[HandoverResponse])
def get_handovers(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    direction: str = Query("all", description="'incoming', 'outgoing', hoặc 'all'"),
    handover_status: str | None = Query(
        None, alias="status", description="PENDING, ACCEPTED, REJECTED"
    ),
):
    """
    Lấy danh sách các lệnh bàn giao (S-15, S-16):
    - direction=incoming: Danh sách các lô được bàn giao tới (chờ tôi xác nhận).
    - direction=outgoing: Danh sách các lô tổ chức tôi đã bàn giao đi.
    """
    query = db.query(Handover)

    # Phân quyền: Cán bộ kiểm tra và Quản trị viên xem được tất cả
    is_admin_or_inspector = current_user.role in [
        UserRole.INSPECTOR.value,
        UserRole.SYSTEM_ADMIN.value,
        UserRole.ADMIN.value,
    ]

    if not is_admin_or_inspector:
        if direction == "incoming":
            query = query.filter(Handover.to_org_id == current_user.organization_id)
        elif direction == "outgoing":
            query = query.filter(Handover.from_org_id == current_user.organization_id)
        else:
            query = query.filter(
                or_(
                    Handover.from_org_id == current_user.organization_id,
                    Handover.to_org_id == current_user.organization_id,
                )
            )

    if handover_status:
        query = query.filter(Handover.status == handover_status.upper())

    handovers = query.order_by(Handover.created_at.desc()).all()
    return [_to_handover_response(h) for h in handovers]


@router.get("/candidate-orgs", response_model=list[OrganizationSimpleResponse])
def get_candidate_organizations(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Lấy danh sách các tổ chức khác trong chuỗi cung ứng để chọn đơn vị nhận bàn giao."""
    query = db.query(Organization)
    if current_user.organization_id:
        query = query.filter(Organization.id != current_user.organization_id)
    orgs = query.order_by(Organization.name.asc()).all()
    return [OrganizationSimpleResponse(id=o.id, name=o.name, code=o.code) for o in orgs]


@router.get("/{handover_id}", response_model=HandoverResponse)
def get_handover_detail(
    handover_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Xem chi tiết một lệnh bàn giao."""
    handover = db.query(Handover).filter(Handover.id == handover_id).first()
    if not handover:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lệnh bàn giao không tồn tại.",
        )

    is_admin_or_inspector = current_user.role in [
        UserRole.INSPECTOR.value,
        UserRole.SYSTEM_ADMIN.value,
        UserRole.ADMIN.value,
    ]
    if not is_admin_or_inspector and (
        handover.from_org_id != current_user.organization_id
        and handover.to_org_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập lệnh bàn giao của tổ chức khác.",
        )

    return _to_handover_response(handover)


@router.post("/{handover_id}/accept", response_model=HandoverResponse)
def accept_handover(
    handover_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Xác nhận tiếp nhận lô hàng (User Story S-16):
    - Chuyển quyền giữ lô (batches.organization_id) sang tổ chức B.
    - Ghi một sự kiện xác nhận vào chuỗi hash trong cùng một Database Transaction.
    """
    if current_user.role == UserRole.INSPECTOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cán bộ kiểm tra chỉ có quyền xem dữ liệu (chế độ chỉ đọc).",
        )

    handover = db.query(Handover).filter(Handover.id == handover_id).first()
    if not handover:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lệnh bàn giao không tồn tại.",
        )

    if handover.status != HandoverStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lệnh bàn giao không ở trạng thái chờ xác nhận (hiện tại: {handover.status}).",
        )

    # Chỉ tổ chức bên nhận (to_org_id) mới được quyền xác nhận
    if handover.to_org_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ tổ chức tiếp nhận mới có quyền xác nhận bàn giao.",
        )

    # Thực thi nguyên tử trong cùng 1 Database Transaction:
    handover.status = HandoverStatus.ACCEPTED.value

    batch = db.query(Batch).filter(Batch.id == handover.batch_id).first()
    if batch:
        # Chuyển quyền giữ lô sang tổ chức B
        batch.organization_id = handover.to_org_id
        batch.status = "active"

    # Ghi sự kiện xác nhận vào chuỗi hash SHA-256
    record_chain_event(
        db=db,
        batch_id=handover.batch_id,
        event_type="HANDOVER_ACCEPTED",
        event_data=(
            f"Tổ chức #{handover.to_org_id} đã xác nhận tiếp nhận quyền quản lý lô hàng "
            f"#{handover.batch_id} từ Tổ chức #{handover.from_org_id}."
        ),
        organization_id=handover.to_org_id,
    )

    db.commit()
    db.refresh(handover)
    return _to_handover_response(handover)


@router.post("/{handover_id}/reject", response_model=HandoverResponse)
def reject_handover(
    handover_id: int,
    payload: HandoverRejectRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Từ chối tiếp nhận lô hàng (User Story S-16):
    - Bắt buộc nhập lý do (tối thiểu 10 ký tự).
    - Lô vẫn thuộc quyền giữ của tổ chức A.
    - Ghi nhận sự kiện từ chối kèm lý do vào chuỗi hash trong cùng một Database Transaction.
    """
    if current_user.role == UserRole.INSPECTOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cán bộ kiểm tra chỉ có quyền xem dữ liệu (chế độ chỉ đọc).",
        )

    # Kiểm tra tính hợp lệ của lý do từ chối (tối thiểu 10 ký tự)
    reason = payload.reject_reason.strip() if payload.reject_reason else ""
    if len(reason) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lý do từ chối phải có tối thiểu 10 ký tự.",
        )

    handover = db.query(Handover).filter(Handover.id == handover_id).first()
    if not handover:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lệnh bàn giao không tồn tại.",
        )

    if handover.status != HandoverStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lệnh bàn giao không ở trạng thái chờ xác nhận (hiện tại: {handover.status}).",
        )

    # Chỉ tổ chức bên nhận mới có quyền từ chối
    if handover.to_org_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ tổ chức tiếp nhận mới có quyền từ chối bàn giao.",
        )

    # Thực thi nguyên tử trong cùng 1 Database Transaction:
    handover.status = HandoverStatus.REJECTED.value
    handover.reject_reason = reason

    batch = db.query(Batch).filter(Batch.id == handover.batch_id).first()
    if batch:
        # Lô vẫn thuộc quyền sở hữu của tổ chức A
        batch.organization_id = handover.from_org_id
        batch.status = "active"

    # Ghi nhận sự kiện từ chối kèm lý do vào chuỗi hash SHA-256
    record_chain_event(
        db=db,
        batch_id=handover.batch_id,
        event_type="HANDOVER_REJECTED",
        event_data=(
            f"Tổ chức #{handover.to_org_id} từ chối tiếp nhận lô #{handover.batch_id} "
            f"từ Tổ chức #{handover.from_org_id}. Lý do: {reason}"
        ),
        organization_id=handover.to_org_id,
    )

    db.commit()
    db.refresh(handover)
    return _to_handover_response(handover)


@router.get("/batches/{batch_id}/chain-events", response_model=list[ChainEventResponse])
def get_batch_chain_events(
    batch_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Tra cứu chuỗi sự kiện hash SHA-256 của một lô hàng cụ thể (S-10, S-12)."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lô hàng không tồn tại.",
        )

    # Áp dụng quy tắc canView(org, batch) theo chuẩn S-23 & Task T-54
    from app.services.batch_access_service import can_view_batch

    allowed, _reason, cutoff_time = can_view_batch(
        org_id=current_user.organization_id,
        batch=batch,
        db=db,
        user_role=current_user.role,
    )
    if not allowed:
        client_ip = request.client.host if request.client else "unknown"
        SecurityLogRepository.log_attempt(
            db=db,
            user_id=current_user.id,
            user_email=current_user.email,
            user_org_id=current_user.organization_id,
            attempt_type="cross_tenant_access_denied",
            target_resource="batch",
            target_id=str(batch.id),
            target_org_id=batch.organization_id,
            endpoint=request.url.path,
            method=request.method,
            ip_address=client_ip,
            description=(
                f"Người dùng {current_user.email} (Tổ chức {current_user.organization_id}) "
                f"cố tình gọi API truy cập dòng thời gian lô #{batch.id} của Tổ chức {batch.organization_id} (không thuộc phả hệ)."
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập dữ liệu của tổ chức khác.",
        )

    query = db.query(ChainEvent).filter(ChainEvent.batch_id == batch_id)
    if cutoff_time is not None:
        # Điều kiện c: chỉ xem lịch sử các sự kiện tính tới thời điểm bàn giao đi
        query = query.filter(ChainEvent.created_at <= cutoff_time)

    return query.order_by(ChainEvent.id.asc()).all()
