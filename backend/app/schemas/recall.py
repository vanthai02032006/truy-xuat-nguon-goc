from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RecallCreateRequest(BaseModel):
    batch_id: int = Field(..., description="ID của lô hàng phát hiện sự cố cần thu hồi")
    reason: str = Field(
        ...,
        min_length=20,
        description="Lý do thu hồi bắt buộc tối thiểu 20 ký tự mô tả chi tiết sự cố",
    )
    severity: str | None = Field(
        default="CRITICAL",
        description="Mức độ nghiêm trọng: CRITICAL, HIGH, MEDIUM",
    )


class RecallAffectedBatchItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    batch_code: str
    product_name: str
    organization_id: int
    organization_name: str
    generation: str
    initial_quantity: float
    remaining_quantity: float
    sold_quantity: float
    current_location: str | None = None
    batch_status_before: str | None = None
    is_isolated: bool
    isolated_at: datetime | None = None


class RecallOrgProgressItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    organization_name: str
    organization_code: str | None = None
    status: str  # PENDING, CONFIRMED_ISOLATED
    action_notes: str | None = None
    confirmed_by_name: str | None = None
    confirmed_at: datetime | None = None
    affected_batch_count: int
    stock_kg: float


class RecallProgressInfo(BaseModel):
    total_organizations: int
    confirmed_organizations: int
    progress_percentage: float
    status_summary: str  # e.g. "3/5 tổ chức đã cô lập"


class RecallResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recall_code: str
    source_batch_id: int
    source_batch_code: str
    product_name: str
    reason: str
    severity: str
    status: str
    initiator_name: str
    initiator_org_name: str
    total_affected_batches: int
    total_affected_kg: float
    total_stock_kg: float
    total_sold_kg: float
    progress: RecallProgressInfo
    affected_batches: list[RecallAffectedBatchItem] = []
    organization_actions: list[RecallOrgProgressItem] = []
    created_at: datetime
    updated_at: datetime | None = None


class RecallConfirmIsolationRequest(BaseModel):
    notes: str | None = Field(
        default="Đã hoàn tất cô lập, niêm phong toàn bộ hàng trong kho",
        description="Ghi chú xác nhận biện pháp xử lý cô lập",
    )


class RecallListResponse(BaseModel):
    items: list[RecallResponse]
    total: int
