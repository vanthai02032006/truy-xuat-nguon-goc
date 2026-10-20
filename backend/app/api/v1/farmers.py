from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.farmer import (
    FarmerAnonymizeRequest,
    FarmerAnonymizeResponse,
    FarmerCreateRequest,
    FarmerResponse,
)
from app.services.farmer_service import FarmerService

router = APIRouter(prefix="/farmers", tags=["farmers"])


@router.post("", response_model=FarmerResponse, status_code=status.HTTP_201_CREATED)
def create_farmer(
    payload: FarmerCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Đăng ký hồ sơ nông hộ có định danh cá nhân (S-56):
    - Tách thông tin định danh cá nhân (Họ tên, SĐT, CCCD, Địa chỉ) ra bảng farmer_identities riêng.
    - Sinh mã tham chiếu bí danh (farmer_ref_id) để dùng trong chuỗi Hash SHA-256.
    """
    return FarmerService.create_farmer(db=db, user=current_user, payload=payload)


@router.get("", response_model=list[FarmerResponse])
def list_farmers(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    """
    Lấy danh sách các nông hộ:
    - Nếu đã xóa PII (is_anonymized = True): hiển thị tên 'Nông hộ ẩn danh (FMR-...)',
      thông tin SĐT/CCCD/Địa chỉ bị xóa bỏ theo Nghị định 13/2023/NĐ-CP.
    """
    return FarmerService.list_farmers(db=db, user=current_user, skip=skip, limit=limit)


@router.get("/{farmer_ref_id}", response_model=FarmerResponse)
def get_farmer_detail(
    farmer_ref_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Xem chi tiết hồ sơ nông hộ theo mã tham chiếu bí danh."""
    return FarmerService.get_farmer_by_ref(db=db, farmer_ref_id=farmer_ref_id)


@router.post("/{farmer_ref_id}/anonymize", response_model=FarmerAnonymizeResponse)
def anonymize_farmer(
    farmer_ref_id: str,
    payload: FarmerAnonymizeRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    User Story S-56: Xóa / Ẩn danh dữ liệu định danh cá nhân của nông hộ (Nghị định 13/2023/NĐ-CP).
    - Xóa toàn bộ PII (Họ tên, SĐT, CCCD, Địa chỉ chi tiết) trong bảng farmer_identities.
    - Chuỗi Hash SHA-256 của mọi lô hàng liên quan không bị thay đổi vì chỉ lưu farmer_ref_id.
    - Kiểm tra lại toàn vẹn SHA-256 (S-12) vẫn báo HỢP LỆ 100%.
    """
    return FarmerService.anonymize_farmer(
        db=db,
        user=current_user,
        farmer_ref_id=farmer_ref_id,
        reason=payload.reason,
    )
