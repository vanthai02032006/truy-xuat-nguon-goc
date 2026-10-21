import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    get_db,
    verify_land_plot_access,
)
from app.models.land_plot import LandPlot
from app.models.organization import Organization
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
    if current_user.role in [UserRole.INSPECTOR.value, UserRole.SYSTEM_ADMIN.value, "inspector", "system_admin", "admin"]:
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
    if current_user.role in [UserRole.INSPECTOR.value, "inspector"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cán bộ kiểm tra chỉ có quyền xem dữ liệu (chế độ chỉ đọc).",
        )

    # 2. Kiểm tra vai trò được phép khai báo thửa đất
    allowed_roles = {
        UserRole.FARM.value,
        UserRole.SYSTEM_ADMIN.value,
        "farm",
        "system_admin",
        "admin",
        "farm_owner",
        "farmer",
        "vung_trong",
        "supervisor",
        "owner",
        "member",
    }
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Chỉ tài khoản vai trò vùng trồng/nông trại mới có quyền khai báo thửa đất (vai trò hiện tại: {current_user.role}).",
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
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Xóa thửa đất (Chỉ Chủ nông trại hoặc Quản trị viên hệ thống có quyền)."""
    allowed_roles = {
        UserRole.SYSTEM_ADMIN.value,
        UserRole.FARM.value,
        "system_admin",
        "admin",
        "farm",
        "farm_owner",
        "owner",
    }
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Chủ nông trại hoặc Quản trị viên mới có quyền xóa thửa đất.",
        )
    LandPlotRepository.delete(db, plot)


class LandPlotCsvImportRequest(BaseModel):
    csv_content: str = Field(..., description="Nội dung tệp CSV chứa danh sách thửa đất")


class LandPlotCsvImportResponse(BaseModel):
    imported_count: int
    skipped_count: int
    total_rows: int
    errors: list[str] = []


@router.post("/import-csv", response_model=LandPlotCsvImportResponse)
async def import_land_plots_csv(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    User Story S-32: Nhập danh sách thửa đất từ tệp CSV.
    - Cột: name (tên thửa), address (địa chỉ), area (diện tích ha), latitude, longitude.
    - Thuộc về organization_id của người dùng hiện tại (hoặc farm được chỉ định).
    """
    if current_user.role in [UserRole.INSPECTOR.value, "inspector"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cán bộ kiểm tra chỉ có quyền xem (Read-only), không được phép thêm thửa đất.",
        )

    content_type = request.headers.get("content-type", "")
    lines = ""
    if "application/json" in content_type:
        try:
            body = await request.json()
            lines = (body.get("csv_content") or "").strip()
        except Exception:  # noqa: BLE001
            lines = ""
    elif "multipart/form-data" in content_type:
        try:
            raw = await request.body()
            parts = raw.split(b"\r\n\r\n", 1)
            if len(parts) == 2:
                csv_bytes = parts[1].rsplit(b"\r\n--", 1)[0]
                lines = csv_bytes.decode("utf-8", errors="replace").strip()
            else:
                lines = raw.decode("utf-8", errors="replace").strip()
        except Exception:  # noqa: BLE001
            lines = ""
    else:
        try:
            body = await request.json()
            lines = (body.get("csv_content") or "").strip()
        except Exception:  # noqa: BLE001
            raw = await request.body()
            lines = raw.decode("utf-8", errors="replace").strip()

    if not lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nội dung CSV không được để trống.",
        )

    f = io.StringIO(lines)
    reader = csv.DictReader(f)
    imported = 0
    skipped = 0
    total = 0
    errors = []

    target_org_id = current_user.organization_id
    if not target_org_id:
        farm_org = db.query(Organization).filter(Organization.code.ilike("%FARM%")).first()
        if not farm_org:
            farm_org = db.query(Organization).first()
        if farm_org:
            target_org_id = farm_org.id

    if not target_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hệ thống chưa có tổ chức nào để liên kết thửa đất.",
        )

    for idx, row in enumerate(reader, start=2):
        total += 1
        clean_row = {str(k).strip().lower(): str(v).strip() for k, v in row.items() if k}
        name = clean_row.get("name") or clean_row.get("tên thửa") or clean_row.get("tên")
        address = clean_row.get("address") or clean_row.get("địa chỉ") or "Lâm Đồng, Việt Nam"
        area_str = clean_row.get("area") or clean_row.get("diện tích") or "1.0"
        lat_str = clean_row.get("latitude") or clean_row.get("vĩ độ") or "11.94"
        lng_str = clean_row.get("longitude") or clean_row.get("kinh độ") or "108.45"

        if not name:
            errors.append(f"Dòng {idx}: Thiếu tên thửa đất.")
            skipped += 1
            continue

        if "variety" in clean_row or "default_unit" in clean_row:
            errors.append(f"Dòng {idx} ({name}): Tệp này có cấu trúc danh mục sản phẩm, vui lòng chọn loại dữ liệu 'Danh Mục Sản Phẩm'.")
            skipped += 1
            continue

        try:
            area = float(area_str)
            if area <= 0:
                raise ValueError("Diện tích phải > 0")
        except ValueError:
            errors.append(f"Dòng {idx} ({name}): Diện tích '{area_str}' không hợp lệ.")
            skipped += 1
            continue

        try:
            lat = float(lat_str)
            lng = float(lng_str)
        except ValueError:
            lat = 11.94
            lng = 108.45

        existing = (
            db.query(LandPlot)
            .filter(LandPlot.name == name, LandPlot.organization_id == target_org_id)
            .first()
        )
        if existing:
            skipped += 1
            continue

        new_plot = LandPlot(
            name=name,
            address=address,
            area=area,
            latitude=lat,
            longitude=lng,
            organization_id=target_org_id,
        )
        db.add(new_plot)
        imported += 1

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lỗi khi lưu thửa đất vào CSDL: {exc!s}",
        ) from exc

    return LandPlotCsvImportResponse(
        imported_count=imported,
        skipped_count=skipped,
        total_rows=total,
        errors=errors,
    )

