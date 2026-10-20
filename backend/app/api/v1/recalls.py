from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.recall import (
    RecallConfirmIsolationRequest,
    RecallCreateRequest,
    RecallListResponse,
    RecallResponse,
)
from app.services.recall_service import RecallService

router = APIRouter(prefix="/recalls", tags=["recalls"])


@router.post("", response_model=RecallResponse, status_code=status.HTTP_201_CREATED)
def trigger_recall(
    payload: RecallCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Kích hoạt Mở Lệnh Thu Hồi Khẩn Cấp (User Story S-33, S-34, S-35, S-38):
    1. Kiểm tra phân quyền: Cán bộ kiểm tra (Inspector) hoặc Quản trị của tổ chức đang giữ lô.
    2. Lý do thu hồi bắt buộc tối thiểu 20 ký tự.
    3. Tự động khoanh vùng toàn bộ cây con cháu hậu duệ qua mọi tầng tách/gộp bằng BFS downstream.
    4. Thống kê chi tiết khối lượng nông sản còn trong kho/trên kệ vs đã bán cho người tiêu dùng.
    5. Khóa tức thì quyền Bàn giao, Tách lô và Gộp lô đối với tất cả các lô bị khoanh vùng.
    6. Tạo danh sách hành động cần xác nhận cô lập cho từng tổ chức liên quan.
    7. Ghi nhận sự kiện vào chuỗi Hash Chain bất biến.
    """
    return RecallService.trigger_recall(db=db, user=current_user, payload=payload)


@router.get("", response_model=RecallListResponse)
def list_recalls(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status_filter: str | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """
    Lấy danh sách các lệnh thu hồi nông sản khẩn cấp (S-36, S-37):
    - Cán bộ kiểm tra và Quản trị hệ thống xem toàn bộ.
    - Tổ chức khác chỉ xem các lệnh do mình mở hoặc có lô của mình bị ảnh hưởng.
    """
    items, total = RecallService.list_recalls(
        db=db,
        user=current_user,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )
    return RecallListResponse(
        total=total,
        items=items,
        page=(skip // limit) + 1,
        page_size=limit,
    )


@router.get("/{recall_id}", response_model=RecallResponse)
def get_recall_detail(
    recall_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Xem chi tiết lệnh thu hồi khẩn cấp (S-34, S-35, S-37):
    - Thông tin tổng quan lệnh, lý do, mức độ.
    - Thống kê kg tồn kho/trên kệ vs kg đã bán.
    - Danh sách toàn bộ các lô con cháu bị khoanh vùng.
    - Tiến độ xác nhận cô lập của các tổ chức (ví dụ 3/5 đã xong).
    """
    return RecallService.get_recall_detail(
        db=db, recall_id=recall_id, user=current_user
    )


@router.post("/{recall_id}/confirm-isolation", response_model=RecallResponse)
def confirm_isolation(
    recall_id: int,
    payload: RecallConfirmIsolationRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Quy trình xử lý thu hồi (User Story S-36, S-37):
    - Tổ chức có lô bị ảnh hưởng xác nhận đã cô lập/thu hồi phần hàng thuộc quyền quản lý của mình.
    - Cập nhật trạng thái tiến độ xử lý và ghi nhận sự kiện Hash Chain.
    - Tự động hoàn tất lệnh nếu tất cả tổ chức liên quan đã xác nhận xử lý xong 100%.
    """
    return RecallService.confirm_organization_isolation(
        db=db,
        recall_id=recall_id,
        user=current_user,
        payload=payload,
    )
