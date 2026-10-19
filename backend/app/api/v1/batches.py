from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, verify_batch_access
from app.models.batch import Batch
from app.models.user import User, UserRole
from app.repositories.batch_repository import BatchRepository
from app.schemas.batch import BatchCreate, BatchResponse

router = APIRouter(prefix="/batches", tags=["batches"])


@router.get("", response_model=list[BatchResponse])
def list_batches(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
):
    """
    AC 1: Giả sử tôi đã đăng nhập, Khi xem bất kỳ danh sách nào,
          Thì chỉ thấy bản ghi thuộc tổ chức tôi.
    AC 4: Giả sử tôi là cán bộ kiểm tra, Khi xem,
          Thì thấy được lô của mọi tổ chức nhưng chỉ ở chế độ đọc.
    NFR: Lọc theo tổ chức ở tầng truy vấn (Database Query), không lọc ở giao diện.
    """
    if current_user.role == UserRole.INSPECTOR.value:
        # Cán bộ kiểm tra: Thấy được lô của mọi tổ chức (organization_id=None)
        return BatchRepository.list_batches(
            db, organization_id=None, skip=skip, limit=limit
        )

    # Thành viên / quản trị tổ chức:
    # Truy vấn trực tiếp bằng WHERE organization_id = :org_id ở tầng database
    return BatchRepository.list_batches(
        db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{batch_id}", response_model=BatchResponse)
def get_batch_detail(
    batch: Annotated[Batch, Depends(verify_batch_access)],
):
    """
    AC 2: Giả sử tôi gọi thẳng API với mã bản ghi của tổ chức khác bằng công cụ dòng lệnh,
          Khi máy chủ nhận yêu cầu, Thì trả về 403 và ghi nhật ký lần thử.
    AC 4: Cán bộ kiểm tra được xem lô của bất kỳ tổ chức nào ở chế độ đọc.
    """
    return batch


@router.post("", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
def create_batch(
    batch_in: BatchCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Tạo lô hàng mới gắn với tổ chức của user hiện tại.
    AC 4: Cán bộ kiểm tra (Inspector) chỉ ở chế độ đọc, bị từ chối khi cố tạo mới (403).
    """
    if current_user.role == UserRole.INSPECTOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cán bộ kiểm tra chỉ có quyền xem dữ liệu (chế độ chỉ đọc).",
        )

    # Đảm bảo lô hàng luôn gắn với tổ chức của người dùng tạo nó
    target_org_id = current_user.organization_id
    if not target_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản người dùng chưa được liên kết với bất kỳ tổ chức nào.",
        )

    # Kiểm tra mã lô trùng lặp
    existing = BatchRepository.get_by_code(db, batch_in.batch_code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mã lô '{batch_in.batch_code}' đã tồn tại trong hệ thống.",
        )

    new_batch = Batch(
        batch_code=batch_in.batch_code,
        product_name=batch_in.product_name,
        organization_id=target_org_id,
    )
    return BatchRepository.create(db, new_batch)


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_batch(
    batch: Annotated[Batch, Depends(verify_batch_access)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Xóa lô hàng thuộc tổ chức của mình.
    AC 4: Cán bộ kiểm tra không được xóa (chế độ chỉ đọc).
    """
    if current_user.role == UserRole.INSPECTOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cán bộ kiểm tra chỉ có quyền xem dữ liệu (chế độ chỉ đọc).",
        )

    BatchRepository.delete(db, batch)
