import json
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    ADMIN_ROLES,
    INSPECTOR_ROLES,
    get_current_user,
    get_db,
    verify_batch_access,
)
from app.core.config import settings
from app.models.batch import Batch
from app.models.batch_relation import BatchRelation, BatchRelationType
from app.models.chain_event import ChainEvent
from app.models.cold_chain import TransportTrip, TripBatch, TripStatus
from app.models.handover import Handover, HandoverStatus
from app.models.land_plot import LandPlot
from app.models.material import BatchMaterialLog
from app.models.product import Product
from app.models.user import User, UserRole
from app.repositories.batch_repository import BatchRepository
from app.schemas.batch import (
    BatchCodeGenerateResponse,
    BatchCreate,
    BatchResponse,
    FarmOriginInfo,
    JourneyMilestone,
    PublicBatchTraceResponse,
)
from app.schemas.batch_relation import (
    BatchLineageResponse,
    BatchMergeRequest,
    BatchMergeResponse,
    BatchRelationResponse,
    BatchSplitRequest,
    BatchSplitResponse,
)
from app.schemas.inspection_dossier import InspectionDossierResponse
from app.schemas.lineage_dag import (
    DagGraphResponse,
    DescendantsResponse,
    RootOriginsResponse,
    SeedLineageDagResponse,
)
from app.schemas.material import (
    BatchMaterialLogCreate,
    BatchMaterialLogResponse,
    BatchPHICheckResponse,
)
from app.services.batch_code_service import generate_unique_batch_code
from app.services.hash_chain_service import record_chain_event
from app.services.inspection_dossier_service import InspectionDossierService
from app.services.lineage_dag_service import LineageCycleError, LineageDagService
from app.services.recall_service import RecallService

router = APIRouter(prefix="/batches", tags=["batches"])


# ============================================================================
# USER STORY S-48 & E-08: TRA CỨU NGUỒN GỐC CÔNG KHAI BẢO MẬT & CHỐNG SCRAPING
# ============================================================================


@router.get("/public/{batch_code}", response_model=PublicBatchTraceResponse)
@router.get("/public/batches/{batch_code}", response_model=PublicBatchTraceResponse)
def get_public_batch_trace(
    batch_code: str,
    db: Annotated[Session, Depends(get_db)],
):
    """
    User Story S-47, S-48 & Epic E-08: Tra cứu nguồn gốc công khai bảo mật cho người tiêu dùng.
    - Không yêu cầu xác thực JWT (dành cho người tiêu dùng quét mã QR).
    - CHỈ trả về thông tin công khai trong Allowlist S-48: Tên sản phẩm, Tên vùng trồng, Tỉnh/thành,
      Ngày thu hoạch, Chứng nhận (nếu có căn cứ DB), và các mốc hành trình chuỗi cung ứng thực tế.
    - TUYỆT ĐỐI KHÔNG TRẢ VỀ: Khối lượng lô, Giá bán, Doanh thu, Tên đối tác trung gian, hay bất kỳ dữ liệu nội bộ nào.
    - Hỗ trợ lô hàng được tách/gộp nhiều tầng (Multi-tier lineage): Thể hiện đầy đủ tất cả vùng trồng gốc (origins).
    - Tự động phát hiện chu trình (cycle detection) trong đồ thị phả hệ và dừng an toàn.
    - Không tạo mốc giả hoặc chứng nhận giả: Chỉ hiển thị dữ liệu thực có trong database.
    """
    batch = BatchRepository.get_by_code(db, batch_code.strip())
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mã lô '{batch_code}' không tồn tại hoặc chưa kích hoạt truy xuất công khai.",
        )

    # 1. Truy vết nguồn gốc phả hệ nhiều tầng (Multi-tier Lineage & Cycle Detection - S-47)
    visited_batch_ids: set[int] = set()
    queue: list[Batch] = [batch]
    all_related_batches: list[Batch] = []

    origins: list[FarmOriginInfo] = []
    seen_origin_keys: set[tuple[str, str]] = set()

    def _extract_farm_info(b: Batch) -> FarmOriginInfo | None:
        f_name = None
        prov = None
        plot_name = None

        farmer_ref = b.farmer_ref_id or (b.land_plot.farmer_ref_id if b.land_plot else None)
        if farmer_ref:
            from app.models.farmer import FarmerIdentity
            farmer_obj = db.query(FarmerIdentity).filter(FarmerIdentity.farmer_ref_id == farmer_ref).first()
            if farmer_obj and farmer_obj.is_anonymized:
                f_name = f"Vùng trồng nông hộ ẩn danh ({farmer_ref})"
                prov = farmer_obj.province or "Chưa có thông tin địa phương"
            elif farmer_obj:
                f_name = farmer_obj.full_name or "Vùng trồng nông hộ"
                prov = farmer_obj.province or "Chưa có thông tin địa phương"

        if not f_name and b.land_plot:
            f_name = b.land_plot.name
            plot_name = b.land_plot.name
            if b.land_plot.address:
                prov = b.land_plot.address.split(",")[-1].strip()
            elif b.organization:
                f_name = f"{b.land_plot.name} ({b.organization.name})"
                prov = "Chưa có thông tin địa phương"

        if not f_name and b.organization:
            f_name = b.organization.name
            prov = "Chưa có thông tin địa phương"

        if f_name:
            return FarmOriginInfo(
                farm_name=f_name,
                province=prov or "Chưa có thông tin địa phương",
                land_plot_name=plot_name,
            )
        return None

    while queue:
        curr = queue.pop(0)
        if curr.id in visited_batch_ids:
            # Phát hiện chu trình (Cycle detection) -> Dừng an toàn để ngăn vòng lặp vô hạn
            continue
        visited_batch_ids.add(curr.id)
        all_related_batches.append(curr)

        parent_relations = (
            db.query(BatchRelation)
            .filter(BatchRelation.child_batch_id == curr.id)
            .all()
        )

        if not parent_relations:
            # Lô gốc (Root Origin)
            origin_info = _extract_farm_info(curr)
            if origin_info:
                key = (origin_info.farm_name, origin_info.province)
                if key not in seen_origin_keys:
                    seen_origin_keys.add(key)
                    origins.append(origin_info)
        else:
            for rel in parent_relations:
                if rel.parent_batch_id not in visited_batch_ids:
                    p_batch = db.query(Batch).filter(Batch.id == rel.parent_batch_id).first()
                    if p_batch:
                        queue.append(p_batch)

    # Nếu lô không có cha và không có plot gốc ở loop, fallback về chính nó
    if not origins:
        fallback_origin = _extract_farm_info(batch)
        if fallback_origin:
            origins.append(fallback_origin)

    if origins:
        if len(origins) == 1:
            farm_name = origins[0].farm_name
            province = origins[0].province
        else:
            farm_name = "; ".join(o.farm_name for o in origins)
            valid_provinces = list(dict.fromkeys(
                o.province for o in origins if o.province != "Chưa có thông tin địa phương"
            ))
            province = ", ".join(valid_provinces) if valid_provinces else "Chưa có thông tin địa phương"
    else:
        farm_name = "Chưa có thông tin vùng trồng"
        province = "Chưa có thông tin địa phương"

    # 2. Xác định ngày thu hoạch thực tế từ database
    all_chain_events = (
        db.query(ChainEvent)
        .filter(ChainEvent.batch_id.in_(visited_batch_ids))
        .order_by(ChainEvent.created_at.asc(), ChainEvent.id.asc())
        .all()
    )

    harvest_date = None
    for ev in all_chain_events:
        if ev.event_type.upper() in ["HARVESTED", "HARVEST"]:
            harvest_date = ev.created_at.strftime("%Y-%m-%d")
            break
    if not harvest_date and batch.created_at:
        harvest_date = batch.created_at.strftime("%Y-%m-%d")
    elif not harvest_date:
        harvest_date = "Chưa có thông tin ngày thu hoạch"

    # 3. Xác định chứng nhận chất lượng (VietGAP, GlobalGAP, Organic...) có bằng chứng thực tế
    certification = "Chưa có thông tin chứng nhận"
    for ce in all_chain_events:
        ev_type = (ce.event_type or "").upper()
        ev_data_str = str(ce.event_data or "")
        ev_data_lower = ev_data_str.lower()
        if "VIETGAP" in ev_type or "vietgap" in ev_data_lower:
            certification = "VietGAP"
            break
        elif "GLOBALGAP" in ev_type or "globalgap" in ev_data_lower:
            certification = "GlobalGAP"
            break
        elif "ORGANIC" in ev_type or "hữu cơ" in ev_data_lower or "organic" in ev_data_lower:
            certification = "Hữu cơ (Organic)"
            break
        elif "CERTIFICATION" in ev_type:
            try:
                parsed = json.loads(ev_data_str)
                if isinstance(parsed, dict) and "certification" in parsed:
                    certification = str(parsed["certification"])
                    break
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

    if certification == "Chưa có thông tin chứng nhận":
        prod_obj = db.query(Product).filter(Product.name == batch.product_name).first()
        if prod_obj and prod_obj.description:
            desc_lower = prod_obj.description.lower()
            if "vietgap" in desc_lower:
                certification = "VietGAP"
            elif "globalgap" in desc_lower:
                certification = "GlobalGAP"
            elif "hữu cơ" in desc_lower or "organic" in desc_lower:
                certification = "Hữu cơ (Organic)"

    # 4. Đánh giá an toàn thời gian cách ly thuốc BVTV (S-62)
    all_material_logs: list[BatchMaterialLog] = []
    for b_item in all_related_batches:
        if b_item.material_logs:
            all_material_logs.extend(b_item.material_logs)

    is_safe = True
    if all_material_logs:
        today = datetime.now().date()
        violating = []
        for l in all_material_logs:
            try:
                safe_dt = datetime.strptime(l.safe_harvest_date, "%Y-%m-%d").date()
                if safe_dt > today:
                    violating.append(l)
            except (ValueError, TypeError):
                continue
        if violating:
            is_safe = False
            phi_msg = "Đang trong thời gian giám sát cách ly vật tư nông nghiệp."
        else:
            phi_msg = (
                f"Đạt chuẩn an toàn thời gian cách ly thuốc BVTV ({certification})"
                if certification != "Chưa có thông tin chứng nhận"
                else "Đạt chuẩn an toàn thời gian cách ly thuốc BVTV."
            )
    else:
        is_safe = True
        phi_msg = "Chưa ghi nhận nhật ký sử dụng vật tư nông nghiệp"

    # 5. Các mốc hành trình chuỗi cung ứng thực tế (Không tự tạo nội dung giả)
    milestones: list[JourneyMilestone] = []
    seen_milestones: set[tuple[str, str]] = set()

    def _add_milestone(stage: str, description: str, dt: datetime | None, status_str: str = "completed"):
        ts_str = dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None
        key = (stage, ts_str or "")
        if key not in seen_milestones:
            seen_milestones.add(key)
            milestones.append(
                JourneyMilestone(
                    stage=stage,
                    description=description,
                    timestamp=ts_str,
                    status=status_str,
                )
            )

    # 5.1. Mốc từ chuỗi sự kiện ChainEvent
    for ce in all_chain_events:
        etype = ce.event_type.upper()
        if etype in ["BATCH_INITIALIZED", "BATCH_CREATED"]:
            _add_milestone(
                stage="Khởi tạo lô hàng",
                description=f"Khởi tạo lô hàng tại {farm_name}.",
                dt=ce.created_at,
            )
        elif etype in ["HARVESTED", "HARVEST"]:
            _add_milestone(
                stage="Thu hoạch",
                description=f"Thu hoạch nông sản tại {farm_name}.",
                dt=ce.created_at,
            )
        elif etype in ["PROCESSING", "PREPROCESSING", "SORTING"]:
            _add_milestone(
                stage="Sơ chế & Phân loại",
                description="Sơ chế, phân loại và kiểm tra chất lượng ban đầu.",
                dt=ce.created_at,
            )
        elif etype in ["PACKAGING", "PACKING"]:
            _add_milestone(
                stage="Đóng gói",
                description="Đóng gói bao bì và niêm phong lô hàng.",
                dt=ce.created_at,
            )
        elif etype in ["COLD_STORAGE"]:
            _add_milestone(
                stage="Lưu kho lạnh",
                description="Bảo quản trong kho lạnh kiểm soát nhiệt độ.",
                dt=ce.created_at,
            )
        elif etype in ["BATCH_SPLIT"]:
            _add_milestone(
                stage="Phân tách lô hàng",
                description="Phân tách lô hàng phục vụ phân phối chuỗi cung ứng.",
                dt=ce.created_at,
            )
        elif etype in ["BATCH_MERGED"]:
            _add_milestone(
                stage="Gộp lô hàng",
                description="Gộp nông sản từ các nguồn gốc đạt chuẩn chất lượng.",
                dt=ce.created_at,
            )
        elif etype in ["HANDOVER_INITIATED"]:
            _add_milestone(
                stage="Bắt đầu vận chuyển",
                description="Bắt đầu vận chuyển trong chuỗi cung ứng.",
                dt=ce.created_at,
            )
        elif etype in ["HANDOVER_ACCEPTED", "TRANSFERRED"]:
            _add_milestone(
                stage="Bàn giao chuỗi cung ứng",
                description="Hoàn tất bàn giao tiếp nhận giữa các chặng trong chuỗi cung ứng.",
                dt=ce.created_at,
            )
        elif etype in ["RECALL_APPLIED"]:
            _add_milestone(
                stage="Thu hồi khẩn cấp",
                description="Lô hàng đang trong diện giám sát hoặc xử lý thu hồi.",
                dt=ce.created_at,
                status_str="active",
            )
        elif etype in ["INSPECTION", "QUALITY_CHECK"]:
            _add_milestone(
                stage="Kiểm tra chất lượng",
                description="Kiểm tra và xác nhận chất lượng nông sản.",
                dt=ce.created_at,
            )

    # 5.2. Mốc từ chuyến vận chuyển chuỗi lạnh (TransportTrip)
    trips = (
        db.query(TransportTrip)
        .join(TripBatch, TripBatch.trip_id == TransportTrip.id)
        .filter(TripBatch.batch_id.in_(visited_batch_ids))
        .order_by(TransportTrip.start_time.asc())
        .all()
    )
    for trip in trips:
        readings = trip.telemetry_readings
        if readings:
            min_t = min(r.temperature for r in readings)
            max_t = max(r.temperature for r in readings)
            desc_temp = f" (nhiệt độ thực đo: {min_t:.1f}°C - {max_t:.1f}°C)"
        else:
            desc_temp = f" (dải nhiệt độ cài đặt: {trip.min_temperature:.1f}°C - {trip.max_temperature:.1f}°C)"

        t_status = "completed" if trip.status == TripStatus.COMPLETED.value else "active"
        t_dt = trip.end_time or trip.start_time or trip.created_at
        _add_milestone(
            stage="Vận chuyển chuỗi lạnh",
            description=f"Vận chuyển bằng xe chuyên dụng bảo quản lạnh{desc_temp}.",
            dt=t_dt,
            status_str=t_status,
        )

    # 5.3. Mốc từ biên bản bàn giao (Handover)
    handovers = (
        db.query(Handover)
        .filter(Handover.batch_id.in_(visited_batch_ids))
        .order_by(Handover.created_at.asc())
        .all()
    )
    for h in handovers:
        h_dt = h.updated_at if h.status == HandoverStatus.ACCEPTED.value else h.created_at
        h_temp = f" (nhiệt độ ghi nhận: {h.temperature})" if h.temperature else ""
        if h.status == HandoverStatus.ACCEPTED.value:
            _add_milestone(
                stage="Bàn giao chuỗi cung ứng",
                description=f"Hoàn thành bàn giao tiếp nhận trong chuỗi cung ứng{h_temp}.",
                dt=h_dt,
                status_str="completed",
            )
        elif h.status == HandoverStatus.PENDING.value:
            _add_milestone(
                stage="Bàn giao chuỗi cung ứng",
                description=f"Đang chờ tiếp nhận trong chuỗi cung ứng{h_temp}.",
                dt=h_dt,
                status_str="active",
            )

    # Sắp xếp các mốc thời gian tăng dần
    milestones.sort(key=lambda m: m.timestamp or "")

    return PublicBatchTraceResponse(
        batch_code=batch.batch_code,
        product_name=batch.product_name,
        farm_name=farm_name,
        province=province,
        harvest_date=harvest_date,
        certification=certification,
        journey_milestones=milestones,
        is_safe_phi=is_safe,
        phi_message=phi_msg,
        origins=origins,
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
    if current_user.role in [UserRole.INSPECTOR.value, UserRole.SYSTEM_ADMIN.value, "inspector", "system_admin", "admin"]:
        # Cán bộ kiểm tra & Quản trị hệ thống: Thấy được lô của mọi tổ chức (organization_id=None)
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

    farmer_ref = batch_in.farmer_ref_id
    if not farmer_ref and batch_in.land_plot_id:
        plot = db.query(LandPlot).filter(LandPlot.id == batch_in.land_plot_id).first()
        if plot and plot.farmer_ref_id:
            farmer_ref = plot.farmer_ref_id

    new_batch = Batch(
        batch_code=final_batch_code,
        product_name=batch_in.product_name,
        organization_id=target_org_id,
        land_plot_id=batch_in.land_plot_id,
        farmer_ref_id=farmer_ref,
        initial_quantity=batch_in.initial_quantity,
        remaining_quantity=batch_in.remaining_quantity,
        unit=batch_in.unit,
    )
    try:
        db.add(new_batch)
        db.flush()

        # Ghi nhận sự kiện khởi tạo lô hàng vào chuỗi Hash SHA-256 trong CÙNG TRANSACTION (S-10, S-11)
        # Chỉ chứa farmer_ref_id, không chứa PII (S-56)
        event_data = {
            "action": "BATCH_INITIALIZED",
            "batch_code": new_batch.batch_code,
            "product_name": new_batch.product_name,
            "quantity": new_batch.initial_quantity,
            "unit": new_batch.unit,
        }
        if farmer_ref:
            event_data["farmer_ref_id"] = farmer_ref

        record_chain_event(
            db=db,
            batch_id=new_batch.id,
            event_type="BATCH_INITIALIZED",
            event_data=event_data,
            organization_id=target_org_id,
        )
        db.commit()
        db.refresh(new_batch)
        return new_batch
    except Exception:
        db.rollback()
        raise


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_batch(
    batch: Annotated[Batch, Depends(verify_batch_access)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Xóa lô hàng thuộc tổ chức của mình.
    AC 4: Cán bộ kiểm tra không được xóa (chế độ chỉ đọc).
    S-11 / An toàn dữ liệu: Ngăn chặn xóa lô kéo theo cascade xóa các sự kiện đã ghi trong chuỗi hash.
    """
    if current_user.role == UserRole.INSPECTOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cán bộ kiểm tra chỉ có quyền xem dữ liệu (chế độ chỉ đọc).",
        )

    from app.models.chain_event import ChainEvent
    has_events = db.query(ChainEvent).filter(ChainEvent.batch_id == batch.id).first()
    if has_events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lô hàng '{batch.batch_code}' đã ghi nhận sự kiện trong chuỗi hash bất biến (S-11). Nghiêm cấm xóa lô hàng để ngăn chặn cascade làm mất hoặc đứt gãy lịch sử truy xuất nguồn gốc.",
        )

    BatchRepository.delete(db, batch)


# ============================================================================
# USER STORY S-17, S-18, S-19: TÁCH LÔ (SPLIT) VÀ GỘP LÔ (MERGE) HÀNG NÔNG SẢN
# ============================================================================


@router.post(
    "/merge",
    response_model=BatchMergeResponse,
    status_code=status.HTTP_201_CREATED,
)
def merge_batches(
    payload: BatchMergeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    User Story S-19: Gộp nhiều lô hàng có CÙNG loại sản phẩm thành 1 lô mới.
    - Khóa các dòng lô mẹ theo thứ tự ID cố định (ORDER BY id ASC) để tránh deadlock.
    - Kiểm tra các lô mẹ có cùng loại sản phẩm.
    - Trừ số lượng tương ứng ở các lô mẹ.
    - Tạo lô mới có khối lượng bằng tổng lượng gộp.
    - Lưu vết quan hệ MERGE vào bảng batch_relations.
    - Ghi nhận sự kiện chuỗi hash SHA-256 trong cùng transaction.
    """
    if current_user.role == UserRole.INSPECTOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cán bộ kiểm tra chỉ có quyền xem dữ liệu (chế độ chỉ đọc).",
        )

    # 1. Tránh deadlock: Sắp xếp các batch_id theo thứ tự tăng dần cố định
    sorted_sources = sorted(payload.sources, key=lambda s: s.batch_id)
    sorted_ids = [s.batch_id for s in sorted_sources]

    if len(set(sorted_ids)) != len(sorted_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Danh sách lô gộp chứa mã lô trùng lặp.",
        )

    # 2. Khóa các dòng lô mẹ theo thứ tự ID cố định (SELECT ... FOR UPDATE ORDER BY id ASC)
    parents = (
        db.query(Batch)
        .filter(Batch.id.in_(sorted_ids))
        .order_by(Batch.id.asc())
        .with_for_update()
        .all()
    )

    if len(parents) != len(sorted_ids):
        missing_ids = set(sorted_ids) - {p.id for p in parents}
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy các lô hàng có ID: {list(missing_ids)}.",
        )

    parent_map = {p.id: p for p in parents}

    # 3. Kiểm tra phân quyền: Tất cả các lô phải thuộc tổ chức của current_user
    for p in parents:
        if (
            current_user.role not in [UserRole.SYSTEM_ADMIN.value, UserRole.ADMIN.value]
            and p.organization_id != current_user.organization_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bạn không có quyền thao tác trên lô #{p.id} ({p.batch_code}) của tổ chức khác.",
            )
        if p.status == "chờ xác nhận":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lô {p.batch_code} đang trong trạng thái chờ bàn giao, không thể gộp lô.",
            )
        if RecallService.is_batch_in_active_recall(db, p.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lô {p.batch_code} đang nằm trong danh sách lệnh thu hồi khẩn cấp, đã bị khóa quyền Gộp lô theo S-38.",
            )

    # 4. Kiểm tra CÙNG LOẠI SẢN PHẨM (S-19 tiêu chí chấp nhận)
    product_names = {p.product_name.strip().lower() for p in parents}
    if len(product_names) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Chỉ được gộp các lô có CÙNG loại sản phẩm! "
                f"Các sản phẩm hiện tại: {', '.join(p.product_name for p in parents)}."
            ),
        )

    # 5. Kiểm tra khối lượng và trừ số lượng tương ứng ở các lô mẹ
    total_merged_qty = 0.0
    for src in sorted_sources:
        p = parent_map[src.batch_id]
        if src.quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Khối lượng gộp từ lô {p.batch_code} phải lớn hơn 0.",
            )
        if src.quantity > p.remaining_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Khối lượng yêu cầu gộp từ lô {p.batch_code} ({src.quantity} {p.unit}) "
                    f"vượt quá khối lượng còn lại ({p.remaining_quantity} {p.unit})."
                ),
            )
        p.remaining_quantity = round(p.remaining_quantity - src.quantity, 3)
        total_merged_qty += src.quantity

    total_merged_qty = round(total_merged_qty, 3)
    base_parent = parents[0]

    # 6. Tạo lô mới đại diện cho lô đã gộp
    merged_code = generate_unique_batch_code(db)
    merged_batch = Batch(
        batch_code=merged_code,
        product_name=base_parent.product_name,
        organization_id=current_user.organization_id,
        land_plot_id=base_parent.land_plot_id,
        status="active",
        initial_quantity=total_merged_qty,
        remaining_quantity=total_merged_qty,
        unit=base_parent.unit,
    )
    db.add(merged_batch)
    db.flush()

    # 7. Lưu bảng quan hệ batch_relations (loại MERGE)
    for src in sorted_sources:
        p = parent_map[src.batch_id]
        rel = BatchRelation(
            parent_batch_id=p.id,
            child_batch_id=merged_batch.id,
            relation_type=BatchRelationType.MERGE.value,
            quantity=src.quantity,
            notes=payload.notes,
        )
        db.add(rel)

        # Ghi sự kiện hash cho từng lô mẹ
        record_chain_event(
            db=db,
            batch_id=p.id,
            event_type="BATCH_MERGE_PARENT",
            event_data=(
                f"Trích {src.quantity} {p.unit} để gộp vào lô mới {merged_batch.batch_code}. "
                f"Khối lượng còn lại: {p.remaining_quantity} {p.unit}"
            ),
            organization_id=current_user.organization_id,
        )

    # Ghi sự kiện hash cho lô gộp mới
    src_codes_str = ", ".join(
        f"{parent_map[s.batch_id].batch_code} ({s.quantity} {parent_map[s.batch_id].unit})"
        for s in sorted_sources
    )
    record_chain_event(
        db=db,
        batch_id=merged_batch.id,
        event_type="BATCH_MERGE_CREATED",
        event_data=(
            f"Tạo lô mới từ việc gộp các lô [{src_codes_str}]. "
            f"Tổng khối lượng gộp: {total_merged_qty} {merged_batch.unit}"
        ),
        organization_id=current_user.organization_id,
    )

    db.commit()
    db.refresh(merged_batch)
    for p in parents:
        db.refresh(p)

    return BatchMergeResponse(
        merged_batch=merged_batch,
        source_batches=parents,
        total_merged_quantity=total_merged_qty,
    )


@router.post(
    "/{batch_id}/split",
    response_model=BatchSplitResponse,
    status_code=status.HTTP_201_CREATED,
)
def split_batch(
    batch_id: int | str,
    payload: BatchSplitRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    User Story S-17 & S-18: Tách lô nông sản thành nhiều lô con.
    - Khóa dòng lô mẹ bằng SELECT ... FOR UPDATE để chống race condition.
    - Tổng khối lượng các lô con không được vượt quá khối lượng còn lại của lô mẹ.
    - Mỗi lô con có mã lô mới (sinh an toàn), kế thừa sản phẩm và thửa gốc từ lô mẹ.
    - Khối lượng còn lại của lô mẹ bị trừ tương ứng.
    - Lưu vết vào bảng batch_relations (loại SPLIT).
    - Ghi nhận sự kiện chuỗi hash SHA-256 trong cùng transaction.
    """
    if current_user.role == UserRole.INSPECTOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cán bộ kiểm tra chỉ có quyền xem dữ liệu (chế độ chỉ đọc).",
        )

    # Khóa dòng lô mẹ với SELECT ... FOR UPDATE chống race condition (S-17, S-18)
    resolved_batch = _resolve_batch_by_id_or_code(db, batch_id)
    if not resolved_batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lô hàng '{batch_id}' không tồn tại.",
        )
    parent = db.query(Batch).filter(Batch.id == resolved_batch.id).with_for_update().first()

    # Kiểm tra phân quyền: Chỉ tổ chức đang giữ quyền sở hữu mới được tách lô
    if (
        current_user.role not in [UserRole.SYSTEM_ADMIN.value, UserRole.ADMIN.value]
        and parent.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền thực hiện thao tác trên lô hàng của tổ chức khác.",
        )

    # Không cho tách lô khi lô đang trong trạng thái chờ xác nhận bàn giao
    if parent.status == "chờ xác nhận":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lô hàng đang trong quá trình bàn giao chờ xác nhận, không thể tách lô.",
        )

    # Chặn lan rộng S-38: Khóa quyền Tách lô đối với lô đang nằm trong lệnh thu hồi
    if RecallService.is_batch_in_active_recall(db, parent.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lô {parent.batch_code} đang nằm trong danh sách lệnh thu hồi khẩn cấp, đã bị khóa quyền Tách lô theo S-38.",
        )

    total_split_qty = sum(item.quantity for item in payload.splits)
    if total_split_qty <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tổng khối lượng tách phải lớn hơn 0.",
        )

    if total_split_qty > parent.remaining_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Tổng khối lượng các lô con ({total_split_qty} {parent.unit}) "
                f"vượt quá khối lượng còn lại của lô mẹ ({parent.remaining_quantity} {parent.unit})."
            ),
        )

    # Trừ khối lượng còn lại của lô mẹ
    parent.remaining_quantity = round(parent.remaining_quantity - total_split_qty, 3)

    child_batches: list[Batch] = []

    for item in payload.splits:
        child_code = generate_unique_batch_code(db)
        child = Batch(
            batch_code=child_code,
            product_name=parent.product_name,
            organization_id=parent.organization_id,
            land_plot_id=parent.land_plot_id,
            status="active",
            initial_quantity=item.quantity,
            remaining_quantity=item.quantity,
            unit=parent.unit,
        )
        db.add(child)
        db.flush()  # Sinh child.id
        child_batches.append(child)

        rel = BatchRelation(
            parent_batch_id=parent.id,
            child_batch_id=child.id,
            relation_type=BatchRelationType.SPLIT.value,
            quantity=item.quantity,
            notes=item.notes or payload.notes,
        )
        db.add(rel)

        # Ghi nhận mắt xích hash cho lô con
        record_chain_event(
            db=db,
            batch_id=child.id,
            event_type="BATCH_SPLIT_CREATED",
            event_data=(
                f"Lô con {child.batch_code} ({item.quantity} {child.unit}) "
                f"được tách ra từ lô mẹ {parent.batch_code} (#{parent.id})"
            ),
            organization_id=current_user.organization_id,
        )

    # Ghi nhận mắt xích hash cho lô mẹ
    child_codes_str = ", ".join(c.batch_code for c in child_batches)
    record_chain_event(
        db=db,
        batch_id=parent.id,
        event_type="BATCH_SPLIT_PARENT",
        event_data=(
            f"Tách {len(child_batches)} lô con [{child_codes_str}] "
            f"với tổng khối lượng {total_split_qty} {parent.unit}. "
            f"Khối lượng còn lại: {parent.remaining_quantity} {parent.unit}"
        ),
        organization_id=current_user.organization_id,
    )

    db.commit()
    db.refresh(parent)
    for c in child_batches:
        db.refresh(c)

    return BatchSplitResponse(
        parent_batch=parent,
        child_batches=child_batches,
        total_split_quantity=total_split_qty,
    )


@router.get("/{batch_id}/lineage", response_model=BatchLineageResponse)
def get_batch_lineage(
    batch_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Truy vấn đồ thị phả hệ (Genealogy Tree) nguồn gốc lô hàng (S-17, S-18, S-19):
    - Các lô cha/mẹ tạo nên lô này (qua split hoặc merge).
    - Các lô con được sinh ra từ lô này (qua split hoặc merge).
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lô hàng #{batch_id} không tồn tại.",
        )

    is_admin_or_inspector = current_user.role in [
        UserRole.INSPECTOR.value,
        UserRole.SYSTEM_ADMIN.value,
        UserRole.ADMIN.value,
    ]
    if (
        not is_admin_or_inspector
        and batch.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xem thông tin lô hàng của tổ chức khác.",
        )

    # Truy vấn quan hệ cha: lô này là child_batch_id
    parent_rels = (
        db.query(BatchRelation)
        .filter(BatchRelation.child_batch_id == batch.id)
        .order_by(BatchRelation.id.asc())
        .all()
    )
    parents_data = [
        BatchRelationResponse(
            id=r.id,
            parent_batch_id=r.parent_batch_id,
            child_batch_id=r.child_batch_id,
            parent_batch_code=r.parent_batch.batch_code if r.parent_batch else None,
            child_batch_code=r.child_batch.batch_code if r.child_batch else None,
            relation_type=r.relation_type,
            quantity=r.quantity,
            notes=r.notes,
            created_at=r.created_at,
        )
        for r in parent_rels
    ]

    # Truy vấn quan hệ con: lô này là parent_batch_id
    child_rels = (
        db.query(BatchRelation)
        .filter(BatchRelation.parent_batch_id == batch.id)
        .order_by(BatchRelation.id.asc())
        .all()
    )
    children_data = [
        BatchRelationResponse(
            id=r.id,
            parent_batch_id=r.parent_batch_id,
            child_batch_id=r.child_batch_id,
            parent_batch_code=r.parent_batch.batch_code if r.parent_batch else None,
            child_batch_code=r.child_batch.batch_code if r.child_batch else None,
            relation_type=r.relation_type,
            quantity=r.quantity,
            notes=r.notes,
            created_at=r.created_at,
        )
        for r in child_rels
    ]

    return BatchLineageResponse(
        batch=batch,
        parents=parents_data,
        children=children_data,
    )


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
    if (
        current_user.role not in [UserRole.INSPECTOR.value, UserRole.SYSTEM_ADMIN.value, "inspector", "system_admin", "admin"]
        and current_user.organization_id is not None
    ):
        query = query.filter(
            BatchMaterialLog.organization_id == current_user.organization_id
        )
    return query.order_by(BatchMaterialLog.id.desc()).offset(skip).limit(limit).all()


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
        datetime.strptime(log.safe_harvest_date, "%Y-%m-%d").date() for log in logs
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


# ============================================================================
# USER STORY S-21, S-26, S-27: THUẬT TOÁN ĐỒ THỊ DAG PHẢ HỆ LÔ HÀNG NÔNG SẢN
# ============================================================================


def _resolve_batch_by_id_or_code(db: Session, identifier: str | int) -> Batch | None:
    raw = str(identifier).strip()
    if raw.isdigit():
        b = db.query(Batch).filter(Batch.id == int(raw)).first()
        if b:
            return b
    return db.query(Batch).filter(Batch.batch_code == raw).first()


@router.get("/{batch_id}/origins", response_model=RootOriginsResponse)
def get_batch_root_origins(
    batch_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    User Story S-21: Truy ngược nguồn gốc bằng BFS.
    - Duyệt ngược theo chiều con -> cha từ bảng batch_relations.
    - Chống vòng lặp vô hạn bằng visited_set và kiểm tra chu trình.
    - Trả về danh sách toàn bộ các lô thu hoạch gốc ban đầu cùng tên vùng trồng và thửa đất tương ứng.
    """
    batch = _resolve_batch_by_id_or_code(db, batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lô hàng '{batch_id}' không tồn tại.",
        )

    is_admin_or_inspector = current_user.role in [
        UserRole.INSPECTOR.value,
        UserRole.SYSTEM_ADMIN.value,
        UserRole.ADMIN.value,
    ]
    if (
        not is_admin_or_inspector
        and batch.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy vấn phả hệ của lô hàng thuộc tổ chức khác.",
        )

    try:
        data = LineageDagService.trace_upstream_roots(db, batch.id)
        return RootOriginsResponse(
            target_batch_id=data["target_batch_id"],
            target_batch_code=data["target_batch_code"],
            root_count=data["root_count"],
            roots=data["roots"],
        )
    except LineageCycleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{batch_id}/descendants", response_model=DescendantsResponse)
def get_batch_descendants(
    batch_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    User Story S-26, S-27: Truy xuôi hậu duệ bằng BFS.
    - Duyệt theo chiều cha -> con từ bảng batch_relations để liệt kê mọi lô con, cháu, lô gộp.
    - Trả về: Tổ chức hiện đang giữ, Địa điểm/cửa hàng hiện tại, Khối lượng còn lại và Trạng thái (kho/hết).
    """
    batch = _resolve_batch_by_id_or_code(db, batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lô hàng '{batch_id}' không tồn tại.",
        )

    is_admin_or_inspector = current_user.role in [
        UserRole.INSPECTOR.value,
        UserRole.SYSTEM_ADMIN.value,
        UserRole.ADMIN.value,
    ]
    if (
        not is_admin_or_inspector
        and batch.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy vấn hậu duệ của lô hàng thuộc tổ chức khác.",
        )

    try:
        data = LineageDagService.trace_downstream_descendants(db, batch.id)
        return DescendantsResponse(
            source_batch_id=data["source_batch_id"],
            source_batch_code=data["source_batch_code"],
            descendant_count=data["descendant_count"],
            descendants=data["descendants"],
        )
    except LineageCycleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{batch_id}/dag-graph", response_model=DagGraphResponse)
def get_batch_dag_graph(
    batch_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Tổng hợp Đồ thị DAG phục vụ vẽ sơ đồ phả hệ trực quan 3 chiều:
    - Tổ tiên và Lô gốc bên trái.
    - Lô hiện tại ở giữa.
    - Toàn bộ hậu duệ bên phải.
    """
    batch = _resolve_batch_by_id_or_code(db, batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lô hàng '{batch_id}' không tồn tại.",
        )

    is_admin_or_inspector = current_user.role in [
        UserRole.INSPECTOR.value,
        UserRole.SYSTEM_ADMIN.value,
        UserRole.ADMIN.value,
    ]
    if (
        not is_admin_or_inspector
        and batch.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy vấn đồ thị DAG của lô hàng thuộc tổ chức khác.",
        )

    try:
        data = LineageDagService.get_dag_graph_structure(db, batch.id)
        return DagGraphResponse(
            focus_batch=data["focus_batch"],
            roots=data["roots"],
            ancestors=data["ancestors"],
            descendants=data["descendants"],
            nodes=data["nodes"],
            edges=data["edges"],
        )
    except LineageCycleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/seed-lineage-dag",
    response_model=SeedLineageDagResponse,
    status_code=status.HTTP_201_CREATED,
)
def seed_lineage_dag(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    User Story S-22 / S-39 / E-05 / E-06:
    Nạp bộ dữ liệu mẫu phả hệ 3-4 tầng với ít nhất 12 lô qua 3+ tổ chức,
    có đầy đủ Tách lô và Gộp lô, đi kèm đáp án đếm tay để đối chiếu.
    """
    data = LineageDagService.seed_lineage_dataset(db)
    return SeedLineageDagResponse(**data)


@router.post(
    "/seed-full-database",
    status_code=status.HTTP_201_CREATED,
)
def seed_full_database(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    force_reset: bool = Query(False, description="Chỉ được phép bật ở development/testing"),
):
    """
    Nạp dữ liệu mẫu demo:
    - Bắt buộc vai trò Quản trị viên hệ thống (system_admin).
    - Vô hiệu hóa hoàn toàn ở môi trường production và staging.
    - Mặc định force_reset=False để đảm bảo an toàn, không xóa dữ liệu đang có.
    """
    if settings.APP_ENV in ("production", "staging"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tính năng nạp dữ liệu mẫu bị vô hiệu hóa ở môi trường production và staging.",
        )
    if current_user.role not in (UserRole.SYSTEM_ADMIN.value, "system_admin", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Quản trị viên hệ thống (system_admin) mới có quyền gọi nạp dữ liệu mẫu.",
        )

    from app.services.database_seeder import run_full_database_seed

    return run_full_database_seed(db, force_reset=force_reset)



@router.get("/{batch_id}/inspection-dossier", response_model=InspectionDossierResponse)
def get_batch_inspection_dossier(
    batch_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    User Story S-52, S-53: Xuất hồ sơ kiểm tra truy xuất nguồn gốc (PDF / Bản in).
    - Dành cho Cán bộ kiểm tra (Inspector), Quản trị viên hoặc tổ chức có thẩm quyền.
    - Bao gồm: Thông tin lô, Dòng thời gian sự kiện, Phả hệ tổ tiên & hậu duệ,
      Vi phạm chuỗi lạnh, Lệnh thu hồi (nếu có),
      Kết quả kiểm tra toàn vẹn chuỗi Hash SHA-256 tại thời điểm xuất và Terminal Hash.
    """
    # Quyền truy cập: Cán bộ kiểm tra và Admin xem được mọi lô; các bên khác chỉ xem lô thuộc tổ chức mình
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lô hàng #{batch_id} không tồn tại.",
        )

    is_admin_or_inspector = current_user.role in [
        UserRole.INSPECTOR.value,
        UserRole.SYSTEM_ADMIN.value,
        UserRole.ADMIN.value,
    ]
    if (
        not is_admin_or_inspector
        and batch.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xuất hồ sơ kiểm tra của lô hàng thuộc tổ chức khác.",
        )

    return InspectionDossierService.generate_dossier(
        db=db,
        batch_id=batch_id,
        inspector_user=current_user,
    )


@router.post("/{batch_id}/consume", response_model=BatchResponse)
def mark_batch_consumed(
    batch_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    User Story S-29: Đánh dấu lô đã bán hết cho người tiêu dùng.
    - Dành cho Nhà phân phối / Chuỗi bán lẻ hoặc Quản trị hệ thống.
    - Chuyển remaining_quantity về 0.0 và status = 'CONSUMED'.
    - Ghi nhận sự kiện vào chuỗi Hash Chain bất biến.
    """
    batch = _resolve_batch_by_id_or_code(db, batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lô hàng '{batch_id}' không tồn tại.",
        )

    if current_user.role in INSPECTOR_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cán bộ kiểm tra chỉ có quyền đọc (Read-only), không được phép cập nhật trạng thái lô hàng.",
        )

    is_admin = current_user.role in ADMIN_ROLES
    if not is_admin and batch.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền thao tác trên lô hàng thuộc tổ chức khác.",
        )

    if RecallService.is_batch_in_active_recall(db, batch.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lô hàng đang nằm trong lệnh thu hồi khẩn cấp, không thể bán ra thị trường!",
        )

    sold_qty = batch.remaining_quantity
    batch.remaining_quantity = 0.0
    batch.status = "CONSUMED"
    db.flush()

    record_chain_event(
        db=db,
        batch_id=batch.id,
        event_type="BATCH_CONSUMED",
        event_data={
            "action": "CONSUMED_ALL",
            "sold_quantity": sold_qty,
            "unit": batch.unit,
            "status": "CONSUMED",
            "message": f"Lô {batch.batch_code} ({batch.product_name}) đã bán hết cho người tiêu dùng tại điểm bán lẻ.",
        },
        organization_id=batch.organization_id,
    )
    db.commit()
    db.refresh(batch)
    return batch



