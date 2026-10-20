from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BatchBase(BaseModel):
    product_name: str
    land_plot_id: int | None = None
    initial_quantity: float = Field(default=100.0, ge=0)
    remaining_quantity: float = Field(default=100.0, ge=0)
    unit: str = "kg"


class BatchCreate(BatchBase):
    batch_code: str | None = None
    organization_id: int | None = None


class BatchCodeGenerateResponse(BaseModel):
    batch_code: str


class BatchResponse(BatchBase):
    id: int
    batch_code: str
    organization_id: int
    status: str = "active"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# USER STORY S-48 & E-08: TRANG TRA CỨU CÔNG KHAI BẢO MẬT & CHỐNG SCRAPING
# Tuyệt đối không chứa: Khối lượng lô, Giá bán, Doanh thu, Tên đối tác trung gian
# ============================================================================


class JourneyMilestone(BaseModel):
    stage: str
    description: str
    timestamp: str | None = None
    status: str = "completed"


class PublicBatchTraceResponse(BaseModel):
    batch_code: str
    product_name: str
    farm_name: str
    province: str
    harvest_date: str
    certification: str = "VietGAP"
    journey_milestones: list[JourneyMilestone] = []
    is_safe_phi: bool = True
    phi_message: str = "Đạt chuẩn an toàn thời gian cách ly thuốc BVTV (VietGAP)"

    model_config = ConfigDict(from_attributes=True)
