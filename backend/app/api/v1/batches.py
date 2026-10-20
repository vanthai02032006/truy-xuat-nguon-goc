from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, verify_batch_access
from app.models.batch import Batch
from app.models.material import BatchMaterialLog
from app.models.user import User, UserRole
from app.repositories.batch_repository import BatchRepository
from app.schemas.batch import (
    BatchCodeGenerateResponse,
    BatchCreate,
    BatchResponse,
    JourneyMilestone,
    PublicBatchTraceResponse,
)
from app.schemas.material import (
    BatchMaterialLogCreate,
    BatchMaterialLogResponse,
    BatchPHICheckResponse,
)
from app.services.batch_code_service import generate_unique_batch_code

router = APIRouter(prefix="/batches", tags=["batches"])


# ============================================================================
# USER STORY S-48 & E-08: TRA CỨU NGUỒN GỐC CÔNG KHAI BẢO MẬT & CHỐNG SCRAPING
# ============================================================================


@router.get("/public/{batch_code}", response_model=PublicBatchTraceResponse)
def get_public_batch_trace(
    batch_code: str,
    db: Annotated[Session, Depends(get_db)],
):
    """
    User Story S-48 & E-08: Tra cứu nguồn gốc công khai bảo mật cho người tiêu dùng.
    - Không yêu cầu xác thực JWT (dành cho người tiêu dùng quét mã QR).
    - CHỈ trả về thông tin công khai: Tên sản phẩm, Tên vùng trồng, Tỉnh/thành, Ngày thu hoạch,
      và các mốc hành trình chuỗi cung ứng chính (sơ chế, vận chuyển, phân phối).
    - TUYỆT ĐỐI KHÔNG TRẢ VỀ: Khối lượng lô, Giá bán, Doanh thu, Tên đối tác trung gian, hay bất kỳ dữ liệu nội bộ nào.
    - Chống scraping: Không cung cấp danh sách toàn bộ mã lô.
    """
    batch = BatchRepository.get_by_code(db, batch_code.strip())
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mã lô '{batch_code}' không tồn tại hoặc chưa kích hoạt truy xuất công khai.",
        )

    # Xác định tên vùng trồng và địa bàn (tỉnh/thành)
    farm_name = "Vùng trồng Nông Sản Lành"
    province = "Lâm Đồng"
    if batch.land_plot:
        farm_name = batch.land_plot.name
        if batch.land_plot.address:
            province = batch.land_plot.address.split(",")[-1].strip()
        elif batch.organization:
            farm_name = f"{batch.land_plot.name} ({batch.organization.name})"
    elif batch.organization:
        farm_name = batch.organization.name

    harvest_date = (
        batch.created_at.strftime("%Y-%m-%d")
        if batch.created_at
        else datetime.now().strftime("%Y-%m-%d")
    )

    # Đánh giá an toàn thời gian cách ly thuốc BVTV (S-62)
    is_safe = True
    phi_msg = "Đạt chuẩn an toàn thời gian cách ly thuốc BVTV (VietGAP)"
    if batch.material_logs:
        today = datetime.now().date()
        violating = [
            l
            for l in batch.material_logs
            if datetime.strptime(l.safe_harvest_date, "%Y-%m-%d").date() > today
        ]
        if violating:
            is_safe = False
            phi_msg = "Đang trong thời gian giám sát cách ly vật tư nông nghiệp."

    # Các mốc hành trình chuỗi cung ứng chính (không để lộ đối tác trung gian bí mật kinh doanh)
    milestones = [
        JourneyMilestone(
            stage="Thu hoạch & Sơ chế",
            description=f"Thu hoạch tại {farm_name}, sơ chế phân loại đạt chuẩn chất lượng.",
            timestamp=harvest_date,
            status="completed",
        ),
        JourneyMilestone(
            stage="Vận chuyển chuỗi lạnh",
            description="Vận chuyển bằng xe chuyên dụng bảo ôn kiểm soát nhiệt độ tự động 2°C - 6°C.",
            timestamp=harvest_date,
            status="completed",
        ),
        JourneyMilestone(
            stage="Phân phối & Bán lẻ",
            description="Phân phối đến hệ thống điểm bán / siêu thị nông sản đạt chuẩn kiểm định.",
            timestamp=harvest_date,
            status="active",
        ),
    ]

    return PublicBatchTraceResponse(
        batch_code=batch.batch_code,
        product_name=batch.product_name,
        farm_name=farm_name,
        province=province,
        harvest_date=harvest_date,
        certification="VietGAP",
        journey_milestones=milestones,
        is_safe_phi=is_safe,
        phi_message=phi_msg,
    )


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


@router.get("/generate-code", response_model=BatchCodeGenerateResponse)
def get_generated_batch_code(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    User Story S-08: Sinh trước một mã lô ngẫu nhiên an toàn (8 ký tự CSPRNG,
    loại bỏ hoàn toàn các ký tự dễ nhầm lẫn: '0', 'O', '1', 'I', 'L').
    Tự động đảm bảo ràng buộc UNIQUE ở tầng cơ sở dữ liệu.
    """
    code = generate_unique_batch_code(db)
    return BatchCodeGenerateResponse(batch_code=code)


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
    User Story S-08: Nếu mã lô không được truyền, tự động sinh mã ngẫu nhiên an toàn 8 ký tự.
    Đảm bảo ràng buộc UNIQUE ở tầng cơ sở dữ liệu (tự động thử sinh lại nếu trùng).
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

    # Xác định mã lô hàng: nếu không truyền hoặc rỗng thì tự động sinh ngẫu nhiên an toàn 8 ký tự
    final_batch_code = batch_in.batch_code.strip() if batch_in.batch_code else ""
    if not final_batch_code:
        final_batch_code = generate_unique_batch_code(db)
    else:
        # Kiểm tra mã lô trùng lặp nếu người dùng tự chỉ định
        existing = BatchRepository.get_by_code(db, final_batch_code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã lô '{final_batch_code}' đã tồn tại trong hệ thống.",
            )

    new_batch = Batch(
        batch_code=final_batch_code,
        product_name=batch_in.product_name,
        organization_id=target_org_id,
        land_plot_id=batch_in.land_plot_id,
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


# ============================================================================
# USER STORY S-62: NHẬT KÝ VẬT TƯ & KIỂM TRA THỜI GIAN CÁCH LY THU HOẠCH (PHI)
# ============================================================================


@router.get("/materials/all-logs", response_model=list[BatchMaterialLogResponse])
def list_all_material_logs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
):
    """
    Lấy toàn bộ nhật ký sử dụng vật tư của các lô hàng thuộc tổ chức hiện tại.
    Cán bộ kiểm tra (Inspector) xem được của mọi tổ chức ở chế độ đọc.
    """
    query = db.query(BatchMaterialLog)
    if current_user.role != UserRole.INSPECTOR.value:
        query = query.filter(
            BatchMaterialLog.organization_id == current_user.organization_id
        )
    return (
        query.order_by(BatchMaterialLog.id.desc()).offset(skip).limit(limit).all()
    )


@router.get("/{batch_id}/materials", response_model=list[BatchMaterialLogResponse])
def get_batch_material_logs(
    batch: Annotated[Batch, Depends(verify_batch_access)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Lấy danh sách vật tư (phân bón, thuốc BVTV) đã sử dụng cho một lô hàng cụ thể.
    """
    return (
        db.query(BatchMaterialLog)
        .filter(BatchMaterialLog.batch_id == batch.id)
        .order_by(BatchMaterialLog.id.desc())
        .all()
    )


@router.post(
    "/{batch_id}/materials",
    response_model=BatchMaterialLogResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_batch_material_log(
    batch: Annotated[Batch, Depends(verify_batch_access)],
    material_in: BatchMaterialLogCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    User Story S-62: Ghi nhận vật tư đã dùng gắn với một lô hàng cụ thể
    để phục vụ việc kiểm tra thời gian cách ly khi thu hoạch.
    Tự động tính ngày an toàn thu hoạch: safe_harvest_date = applied_date + isolation_days.
    """
    if current_user.role == UserRole.INSPECTOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cán bộ kiểm tra chỉ có quyền xem dữ liệu (chế độ chỉ đọc).",
        )

    try:
        applied_dt = datetime.strptime(material_in.applied_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Định dạng ngày sử dụng không hợp lệ, yêu cầu định dạng YYYY-MM-DD.",
        )

    safe_dt = applied_dt + timedelta(days=material_in.isolation_days)
    safe_harvest_date = safe_dt.strftime("%Y-%m-%d")

    log_entry = BatchMaterialLog(
        batch_id=batch.id,
        material_id=material_in.material_id,
        material_name=material_in.material_name,
        category=material_in.category,
        dosage=material_in.dosage,
        applied_date=material_in.applied_date,
        isolation_days=material_in.isolation_days,
        safe_harvest_date=safe_harvest_date,
        applied_by=material_in.applied_by or current_user.full_name,
        notes=material_in.notes,
        organization_id=batch.organization_id,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


@router.get("/{batch_id}/phi-check", response_model=BatchPHICheckResponse)
def check_batch_phi_compliance(
    batch: Annotated[Batch, Depends(verify_batch_access)],
    db: Annotated[Session, Depends(get_db)],
    harvest_date: str | None = Query(
        default=None,
        description="Ngày thu hoạch dự kiến (YYYY-MM-DD). Mặc định lấy ngày hôm nay.",
    ),
):
    """
    Kiểm tra thời gian cách ly (Pre-Harvest Interval - PHI) đối với lô hàng.
    Đánh giá xem lô hàng đã đủ điều kiện an toàn thu hoạch hay còn vi phạm cách ly.
    """
    logs = (
        db.query(BatchMaterialLog)
        .filter(BatchMaterialLog.batch_id == batch.id)
        .order_by(BatchMaterialLog.id.asc())
        .all()
    )

    # Xác định ngày kiểm tra (mặc định hôm nay nếu không chỉ định)
    if harvest_date:
        try:
            check_dt = datetime.strptime(harvest_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Định dạng harvest_date không hợp lệ, yêu cầu YYYY-MM-DD.",
            )
    else:
        check_dt = datetime.now().date()
        harvest_date = check_dt.strftime("%Y-%m-%d")

    if not logs:
        return BatchPHICheckResponse(
            batch_id=batch.id,
            batch_code=batch.batch_code,
            is_safe_to_harvest=True,
            tested_harvest_date=harvest_date,
            max_safe_harvest_date=None,
            days_remaining=0,
            status="no_pesticide_applied",
            message="Lô hàng chưa ghi nhận sử dụng thuốc BVTV hoặc vật tư cần cách ly. Đủ điều kiện thu hoạch.",
            material_logs=[],
        )

    # Tìm ngày an toàn xa nhất trong tất cả các lần dùng vật tư
    safe_dates = [
        datetime.strptime(log.safe_harvest_date, "%Y-%m-%d").date()
        for log in logs
    ]
    max_safe_dt = max(safe_dates)
    max_safe_date_str = max_safe_dt.strftime("%Y-%m-%d")

    violating_logs = [
        log
        for log in logs
        if datetime.strptime(log.safe_harvest_date, "%Y-%m-%d").date() > check_dt
    ]

    if violating_logs:
        days_remaining = (max_safe_dt - check_dt).days
        violating_names = ", ".join({log.material_name for log in violating_logs})
        return BatchPHICheckResponse(
            batch_id=batch.id,
            batch_code=batch.batch_code,
            is_safe_to_harvest=False,
            tested_harvest_date=harvest_date,
            max_safe_harvest_date=max_safe_date_str,
            days_remaining=days_remaining,
            status="violating",
            message=(
                f"CẢNH BÁO: Chưa đủ thời gian cách ly an toàn! Lô hàng còn thiếu {days_remaining} ngày "
                f"để thuốc BVTV ({violating_names}) phân giải an toàn. Ngày an toàn sớm nhất: {max_safe_date_str}."
            ),
            material_logs=logs,
        )

    return BatchPHICheckResponse(
        batch_id=batch.id,
        batch_code=batch.batch_code,
        is_safe_to_harvest=True,
        tested_harvest_date=harvest_date,
        max_safe_harvest_date=max_safe_date_str,
        days_remaining=0,
        status="compliant",
        message=(
            f"Lô hàng ĐỦ ĐIỀU KIỆN AN TOÀN THU HOẠCH. Đã hoàn thành toàn bộ thời gian cách ly (PHI) "
            f"chuẩn VietGAP/GlobalGAP (kết thúc cách ly từ {max_safe_date_str})."
        ),
        material_logs=logs,
    )

