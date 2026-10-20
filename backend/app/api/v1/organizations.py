from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.deps import ADMIN_ROLES, INSPECTOR_ROLES, get_current_user, get_db
from app.models.batch import Batch
from app.models.organization import OrganizationLocation
from app.models.user import User
from app.services.hash_chain_service import record_chain_event

router = APIRouter(prefix="/organizations", tags=["organizations"])


class LocationCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200, description="Tên cửa hàng hoặc kho con")
    address: str | None = Field(None, max_length=255, description="Địa chỉ cửa hàng/kho")
    location_type: str = Field("STORE", description="Loại địa điểm: STORE, WAREHOUSE, OUTLET")


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    name: str
    address: str | None = None
    location_type: str


class TransferLocationRequest(BaseModel):
    location_id: int = Field(..., description="ID địa điểm/cửa hàng tiếp nhận lô hàng")
    notes: str | None = Field(None, description="Ghi chú điều chuyển")


@router.get("/locations", response_model=list[LocationResponse])
def list_organization_locations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    organization_id: int | None = Query(None, description="Lọc theo ID tổ chức"),
):
    """
    User Story S-30: Danh mục địa điểm / cửa hàng trực thuộc tổ chức.
    - Quản trị viên và Cán bộ kiểm tra xem được toàn bộ.
    - Mỗi tổ chức bình thường chỉ xem các địa điểm trực thuộc tổ chức mình.
    """
    query = db.query(OrganizationLocation)
    if current_user.role not in (ADMIN_ROLES | INSPECTOR_ROLES):
        query = query.filter(OrganizationLocation.organization_id == current_user.organization_id)
    elif organization_id is not None:
        query = query.filter(OrganizationLocation.organization_id == organization_id)

    return query.all()


@router.post("/locations", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
def create_organization_location(
    payload: LocationCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    User Story S-30: Khai báo cửa hàng / kho con mới cho tổ chức.
    - Chặn Cán bộ kiểm tra (chỉ đọc).
    """
    if current_user.role in INSPECTOR_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cán bộ kiểm tra chỉ có quyền xem (Read-only), không được phép thêm địa điểm.",
        )

    org_id = current_user.organization_id or 40
    loc = OrganizationLocation(
        organization_id=org_id,
        name=payload.name.strip(),
        address=payload.address.strip() if payload.address else None,
        location_type=payload.location_type.upper(),
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


def _resolve_batch_by_id_or_code(db: Session, identifier: str | int) -> Batch | None:
    raw = str(identifier).strip()
    if raw.isdigit():
        b = db.query(Batch).filter(Batch.id == int(raw)).first()
        if b:
            return b
    return db.query(Batch).filter(Batch.batch_code == raw).first()


@router.post("/batches/{batch_id}/transfer-location")
def transfer_batch_to_location(
    batch_id: str,
    payload: TransferLocationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    User Story S-30: Điều chuyển lô hàng về cửa hàng / kho con cụ thể và ghi nhận Hash Chain bất biến.
    """
    if current_user.role in INSPECTOR_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cán bộ kiểm tra chỉ có quyền xem (Read-only).",
        )

    batch = _resolve_batch_by_id_or_code(db, batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy lô hàng '{batch_id}'",
        )

    is_admin = current_user.role in ADMIN_ROLES
    if not is_admin and batch.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền thao tác trên lô hàng của tổ chức khác.",
        )

    loc = db.query(OrganizationLocation).filter(OrganizationLocation.id == payload.location_id).first()
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy địa điểm/cửa hàng #{payload.location_id}",
        )

    record_chain_event(
        db=db,
        batch_id=batch.id,
        event_type="BATCH_STORE_ASSIGNED",
        event_data={
            "location_id": loc.id,
            "store_name": loc.name,
            "address": loc.address,
            "notes": payload.notes or "Điều chuyển lô về quầy kệ cửa hàng",
            "message": f"Lô {batch.batch_code} đã được điều chuyển về {loc.name} ({loc.address or 'N/A'})",
        },
        organization_id=batch.organization_id,
    )
    db.commit()

    return {
        "status": "ok",
        "batch_id": batch.id,
        "batch_code": batch.batch_code,
        "location_id": loc.id,
        "location_name": loc.name,
        "message": f"Đã chuyển lô {batch.batch_code} về {loc.name} thành công và ghi nhận Hash Chain.",
    }
