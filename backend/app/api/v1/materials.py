from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.api.deps import (
    get_db,
    require_farm_owner_or_admin,
    require_field_supervisor_or_above,
)
from app.models.material import Material, MaterialRequest
from app.models.user import User
from app.schemas.material import (
    MaterialCreate,
    MaterialRequestCreate,
    MaterialRequestReject,
    MaterialRequestResponse,
    MaterialResponse,
)

router = APIRouter(prefix="/materials", tags=["Materials & Inventory"])


@router.get("", response_model=list[MaterialResponse])
def list_materials(
    current_user: Annotated[User, Depends(require_field_supervisor_or_above)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
):
    """Lấy danh sách vật tư / kho của nông trại."""
    query = db.query(Material)
    if current_user.organization_id is not None:
        query = query.filter(Material.organization_id == current_user.organization_id)
    return query.offset(skip).limit(limit).all()


@router.post("", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
def create_material(
    material_in: MaterialCreate,
    current_user: Annotated[User, Depends(require_farm_owner_or_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    """Tạo mới danh mục vật tư trong kho (Chủ nông trại hoặc Quản trị viên)."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Người dùng chưa được gán vào tổ chức/nông trại.",
        )
    material = Material(
        name=material_in.name,
        code=material_in.code,
        category=material_in.category,
        quantity_in_stock=material_in.quantity_in_stock,
        unit=material_in.unit,
        min_threshold=material_in.min_threshold,
        organization_id=current_user.organization_id,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


@router.get("/requests", response_model=list[MaterialRequestResponse])
def list_material_requests(
    current_user: Annotated[User, Depends(require_field_supervisor_or_above)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
):
    """Danh sách đề xuất cấp phát vật tư nông nghiệp."""
    query = db.query(MaterialRequest)
    if current_user.organization_id is not None:
        query = query.filter(
            MaterialRequest.organization_id == current_user.organization_id
        )
    if status_filter:
        query = query.filter(MaterialRequest.status == status_filter)
    return query.order_by(MaterialRequest.id.desc()).offset(skip).limit(limit).all()


@router.post(
    "/requests",
    response_model=MaterialRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_material_request(
    request_in: MaterialRequestCreate,
    current_user: Annotated[User, Depends(require_field_supervisor_or_above)],
    db: Annotated[Session, Depends(get_db)],
):
    """Giám sát nông trại tạo đề xuất cấp phát vật tư canh tác."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Người dùng chưa được gán vào tổ chức/nông trại.",
        )
    mat_request = MaterialRequest(
        material_name=request_in.material_name,
        quantity=request_in.quantity,
        unit=request_in.unit,
        purpose=request_in.purpose,
        urgency=request_in.urgency,
        status="pending",
        requester_id=current_user.id,
        organization_id=current_user.organization_id,
    )
    db.add(mat_request)
    db.commit()
    db.refresh(mat_request)
    return mat_request


@router.post("/requests/{request_id}/approve", response_model=MaterialRequestResponse)
def approve_material_request(
    request_id: int,
    current_user: Annotated[User, Depends(require_farm_owner_or_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    """Chủ nông trại duyệt đề xuất vật tư."""
    mat_request = (
        db.query(MaterialRequest).filter(MaterialRequest.id == request_id).first()
    )
    if not mat_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy đề xuất vật tư với ID {request_id}",
        )
    if (
        current_user.organization_id
        and mat_request.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền thao tác trên đề xuất của nông trại khác.",
        )
    if mat_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Đề xuất đã ở trạng thái '{mat_request.status}', không thể duyệt lại.",
        )

    mat_request.status = "approved"
    mat_request.approver_id = current_user.id
    mat_request.reviewed_at = func.now()
    db.commit()
    db.refresh(mat_request)
    return mat_request


@router.post("/requests/{request_id}/reject", response_model=MaterialRequestResponse)
def reject_material_request(
    request_id: int,
    reject_in: MaterialRequestReject,
    current_user: Annotated[User, Depends(require_farm_owner_or_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    """Chủ nông trại từ chối đề xuất vật tư kèm lý do."""
    mat_request = (
        db.query(MaterialRequest).filter(MaterialRequest.id == request_id).first()
    )
    if not mat_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy đề xuất vật tư với ID {request_id}",
        )
    if (
        current_user.organization_id
        and mat_request.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền thao tác trên đề xuất của nông trại khác.",
        )
    if mat_request.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Đề xuất đã ở trạng thái '{mat_request.status}', không thể từ chối.",
        )

    mat_request.status = "rejected"
    mat_request.rejection_reason = reject_in.reason
    mat_request.approver_id = current_user.id
    mat_request.reviewed_at = func.now()
    db.commit()
    db.refresh(mat_request)
    return mat_request
