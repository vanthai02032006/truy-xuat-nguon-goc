from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.cold_chain import (
    ScenarioSimulationRequest,
    ScenarioSimulationResponse,
    TelemetryIngestResponse,
    TelemetryReadingInput,
    TransportTripDetailResponse,
    TransportTripResponse,
    TripCreateRequest,
)
from app.services.cold_chain_service import ColdChainService

router = APIRouter(prefix="/cold-chain", tags=["cold-chain"])


@router.post("/trips", response_model=TransportTripResponse, status_code=status.HTTP_201_CREATED)
def create_trip(
    payload: TripCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Tạo Chuyến vận chuyển lạnh (User Story S-40):
    - Gồm: Mã chuyến, Mã thùng lạnh/xe lạnh, Danh sách các lô hàng đang chở.
    - Phân quyền: Đơn vị vận chuyển lạnh (Transporter) hoặc Quản trị hệ thống.
    - Tự động ghi sự kiện khởi hành vào Hash Chain cho toàn bộ các lô hàng trên chuyến xe.
    """
    return ColdChainService.create_trip(db=db, user=current_user, payload=payload)


@router.get("/trips", response_model=list[TransportTripResponse])
def list_trips(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    status_filter: str | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """
    Lấy danh sách các chuyến vận chuyển lạnh (S-40):
    - Lọc theo trạng thái (IN_TRANSIT, COMPLETED, CANCELLED).
    - Cô lập theo tổ chức: Đơn vị vận chuyển chỉ xem các chuyến của tổ chức mình.
    """
    return ColdChainService.list_trips(
        db=db,
        user=current_user,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )


@router.get("/trips/{trip_id}", response_model=TransportTripDetailResponse)
def get_trip_detail(
    trip_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Xem chi tiết chuyến vận chuyển lạnh (S-40, S-43):
    - Danh sách các lô hàng đang chở.
    - Danh sách các sự kiện vi phạm nhiệt độ chuỗi lạnh (> 30 phút).
    - Chuỗi dữ liệu đo nhiệt độ gần nhất từ cảm biến.
    """
    return ColdChainService.get_trip_detail(db=db, trip_id=trip_id)


@router.post("/telemetry", response_model=TelemetryIngestResponse, status_code=status.HTTP_200_OK)
def ingest_telemetry(
    readings: list[TelemetryReadingInput],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Endpoint nhận dữ liệu cảm biến nhiệt độ chuỗi lạnh (User Stories S-41, S-43, S-45):
    1. Nhận mảng dữ liệu nhiệt độ: { trip_id, timestamp, temperature }.
    2. Bỏ qua các bản ghi có timestamp cũ hơn bản ghi mới nhất đã lưu (S-41).
    3. Thuật toán phát hiện vi phạm có độ trễ 30 phút (S-43):
       - Vượt ngưỡng nhất thời (dưới 30 phút) KHÔNG bị coi là vi phạm.
       - Chỉ khi vượt ngưỡng LIÊN TỤC TRÊN 30 PHÚT mới kích hoạt sự kiện vi phạm.
       - Hai lần vượt ngưỡng cách nhau dưới 5 phút thì tự động gộp thành 1 lần vi phạm duy nhất.
    4. Tự động ghi nhận vi phạm vào Hash Chain của toàn bộ các lô hàng trên chuyến xe (S-45).
    """
    return ColdChainService.ingest_telemetry(db=db, readings=readings, user=current_user)


@router.post(
    "/trips/{trip_id}/simulate-scenario/{scenario_id}",
    response_model=ScenarioSimulationResponse,
    status_code=status.HTTP_200_OK,
)
def simulate_trip_scenario(
    trip_id: int,
    scenario_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    payload: ScenarioSimulationRequest | None = None,
):
    """
    Công cụ chạy Script Giả lập Cảm biến theo 5 kịch bản mẫu (User Story S-42):
    - Kịch bản 1: Không vượt ngưỡng (ổn định 2°C - 8°C).
    - Kịch bản 2: Vượt ngưỡng 10 phút (mở cửa xe tạm thời) -> KHÔNG tính là vi phạm.
    - Kịch bản 3: Vượt ngưỡng liên tục 45 phút (> 30 phút) -> Tính 1 vi phạm.
    - Kịch bản 4: Hai lần vượt cách nhau dưới 5 phút -> Gộp thành 1 vi phạm.
    - Kịch bản 5: Vượt qua nửa đêm (cross-midnight).
    - Khi phát hiện vi phạm, tự động ghi sự kiện vi phạm vào chuỗi hash của mọi lô trên xe (S-45).
    """
    reset_prev = payload.reset_previous_telemetry if payload else True
    return ColdChainService.simulate_scenario(
        db=db,
        trip_id=trip_id,
        scenario_id=scenario_id,
        reset_previous_telemetry=reset_prev,
        user=current_user,
    )

