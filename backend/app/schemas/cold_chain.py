from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TripCreateRequest(BaseModel):
    """Yêu cầu tạo chuyến vận chuyển lạnh (User Story S-40)."""

    vehicle_code: str = Field(..., min_length=2, max_length=100, description="Mã thùng lạnh hoặc xe lạnh")
    batch_ids: list[int] = Field(..., min_length=1, description="Danh sách ID các lô hàng đang chở")
    trip_code: str | None = Field(None, max_length=50, description="Mã chuyến (tự sinh nếu không truyền)")
    carrier_org_id: int | None = Field(None, description="ID đơn vị vận chuyển lạnh (mặc định lấy theo user)")
    driver_name: str | None = Field(None, max_length=100, description="Tên tài xế phụ trách")
    min_temperature: float = Field(2.0, description="Ngưỡng nhiệt độ tối thiểu (°C)")
    max_temperature: float = Field(8.0, description="Ngưỡng nhiệt độ tối đa cho phép (°C)")


class TripBatchItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    batch_id: int
    batch_code: str
    product_name: str


class ColdChainViolationItem(BaseModel):
    """Thông tin chi tiết một sự kiện vi phạm chuỗi lạnh (S-43, S-45)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_id: int
    started_at: datetime
    ended_at: datetime
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_minutes: float
    peak_temperature: float
    threshold: float
    violation_type: str
    status: str
    hash_recorded: bool
    created_at: datetime


class TelemetryReadingItem(BaseModel):
    """Dữ liệu một điểm đo nhiệt độ cảm biến."""

    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    temperature: float


class TelemetryReadingInput(BaseModel):
    """Một bản ghi đo nhiệt độ gửi từ cảm biến IoT (S-41)."""

    trip_id: int
    timestamp: datetime
    temperature: float


class TransportTripResponse(BaseModel):
    """Thông tin tổng quan chuyến vận chuyển lạnh."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_code: str
    vehicle_code: str
    license_plate: str | None = None
    carrier_org_id: int
    carrier_org_name: str | None = None
    carrier_name: str | None = None
    driver_name: str | None = None
    min_temperature: float
    max_temperature: float
    status: str
    start_time: datetime
    end_time: datetime | None = None
    created_at: datetime
    batches: list[TripBatchItem] = []
    violations_count: int = 0
    violation_count: int = 0
    readings_count: int = 0


class TransportTripDetailResponse(TransportTripResponse):
    """Chi tiết chuyến xe gồm toàn bộ danh sách vi phạm và các điểm nhiệt độ gần nhất."""

    violations: list[ColdChainViolationItem] = []
    recent_telemetry: list[TelemetryReadingItem] = []
    telemetry: list[TelemetryReadingItem] = []


class TelemetryIngestResponse(BaseModel):
    """Kết quả tiếp nhận dữ liệu cảm biến (S-41, S-43, S-45)."""

    accepted_count: int
    ignored_count: int
    message: str
    violations_detected: list[ColdChainViolationItem] = []


class ScenarioSimulationRequest(BaseModel):
    """Yêu cầu chạy kịch bản giả lập cảm biến nhiệt độ (S-42)."""

    reset_previous_telemetry: bool = Field(
        True,
        description="Xóa dữ liệu telemetry và vi phạm cũ của chuyến để quan sát kịch bản độc lập",
    )


class ScenarioSimulationResponse(BaseModel):
    """Kết quả chạy Script Giả lập Cảm biến theo 5 kịch bản mẫu (S-42)."""

    model_config = ConfigDict(from_attributes=True)

    scenario_id: int
    scenario_name: str
    trip_id: int
    trip_code: str
    vehicle_code: str
    readings_injected: int
    violations_count: int
    violations: list[ColdChainViolationItem] = []
    is_violated: bool
    description: str
    rule_explanation: str
    hash_chain_updated: bool

