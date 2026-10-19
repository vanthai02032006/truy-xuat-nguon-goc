from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    verify_land_plot_access,
)
from app.models.land_plot import LandPlot
from app.models.user import User, UserRole
from app.repositories.land_plot_repository import LandPlotRepository
from app.schemas.land_plot import (
    LandPlotCreate,
    LandPlotResponse,
    LandPlotUpdate,
)

router = APIRouter(prefix="/land-plots", tags=["land-plots"])


@router.get("", response_model=list[LandPlotResponse])
def list_land_plots(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
):
    """
    AC 3: Giả sử tôi xem danh sách thửa, Khi tải trang,
          Thì chỉ thấy thửa của tổ chức mình.
    Cán bộ kiểm tra (Inspector): Xem được thửa của mọi tổ chức ở chế độ đọc.
    NFR: Lọc theo tổ chức ở tầng truy vấn (Database Query), không lọc ở giao diện.
    """
    if current_user.role == UserRole.INSPECTOR.value:
        return LandPlotRepository.list_plots(
            db, organization_id=None, skip=skip, limit=limit
        )

    return LandPlotRepository.list_plots(
        db,
        organization_id=current_user.organization_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{plot_id}", response_model=LandPlotResponse)
def get_land_plot_detail(
    plot: Annotated[LandPlot, Depends(verify_land_plot_access)],
):
    """
    Xem chi tiết thửa đất:
    - Nếu gọi sang thửa của tổ chức khác -> Trả về 403 và ghi nhật ký lần thử (S-05/S-06).
    - Cán bộ kiểm tra được xem thửa của mọi tổ chức ở chế độ đọc.
    """
    return plot


@router.post("", response_model=LandPlotResponse, status_code=status.HTTP_201_CREATED)
def create_land_plot(
    plot_in: LandPlotCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    AC 1: Giả sử đã đăng nhập bằng vai trò vùng trồng,
          Khi khai báo thửa với tên, diện tích và toạ độ hợp lệ,
          Thì thửa được lưu và thuộc tổ chức của tôi.
    AC 2: Giả sử tôi nhập diện tích âm hoặc bằng 0,
          Khi lưu, Thì bị chặn kèm thông báo rõ lý do.
    """
    # 1. Cán bộ kiểm tra không được phép tạo/sửa dữ liệu (chỉ đọc)
    if current_user.role == UserRole.INSPECTOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cán bộ kiểm tra chỉ có quyền xem dữ liệu (chế độ chỉ đọc).",
        )

    # 2. Kiểm tra vai trò được phép khai báo thửa đất (vùng trồng / nông dân / quản trị / thành viên HTX)
    allowed_roles = [
        UserRole.FARMER.value,
        UserRole.VUNG_TRONG.value,
        UserRole.ADMIN.value,
        UserRole.MEMBER.value,
    ]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Chỉ tài khoản vai trò vùng trồng mới có quyền khai báo thửa đất (vai trò hiện tại: {current_user.role}).",
        )

    # 3. Kiểm tra tổ chức của người dùng
    target_org_id = current_user.organization_id
    if not target_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tài khoản người dùng chưa được liên kết với bất kỳ tổ chức vùng trồng nào.",
        )

    # 4. AC 2: Kiểm tra diện tích âm hoặc bằng 0
    if plot_in.area <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Diện tích thửa đất phải lớn hơn 0 (không được âm hoặc bằng 0).",
        )

    # 5. Khởi tạo thửa đất mới gắn chặt với tổ chức của user
    new_plot = LandPlot(
        name=plot_in.name,
        area=plot_in.area,
        unit=plot_in.unit or "m2",
        latitude=float(plot_in.latitude),
        longitude=float(plot_in.longitude),
        address=plot_in.address,
        organization_id=target_org_id,
    )
    return LandPlotRepository.create(db, new_plot)


@router.put("/{plot_id}", response_model=LandPlotResponse)
def update_land_plot(
    plot_in: LandPlotUpdate,
    plot: Annotated[LandPlot, Depends(verify_land_plot_access)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    AC 4: Giả sử tôi sửa tên thửa, Khi lưu,
          Thì lô đã gắn với thửa vẫn trỏ đúng thửa đó.
    AC 2: Cập nhật diện tích âm hoặc bằng 0 cũng bị chặn với lý do rõ ràng.
    """
    if plot_in.area is not None and plot_in.area <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Diện tích thửa đất phải lớn hơn 0 (không được âm hoặc bằng 0).",
        )

    update_dict = plot_in.model_dump(exclude_unset=True)
    return LandPlotRepository.update(db, plot, update_dict)


@router.delete("/{plot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_land_plot(
    plot: Annotated[LandPlot, Depends(verify_land_plot_access)],
    db: Annotated[Session, Depends(get_db)],
):
    """Xóa thửa đất."""
    LandPlotRepository.delete(db, plot)
