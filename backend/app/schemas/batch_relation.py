from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.batch import BatchResponse


class BatchSplitItem(BaseModel):
    quantity: float = Field(..., gt=0, description="Khối lượng của lô con mới")
    notes: str | None = None


class BatchSplitRequest(BaseModel):
    splits: list[BatchSplitItem] = Field(
        ..., min_length=1, description="Danh sách các lô con cần tách ra từ lô mẹ"
    )
    notes: str | None = None


class BatchSplitResponse(BaseModel):
    parent_batch: BatchResponse
    child_batches: list[BatchResponse]
    total_split_quantity: float


class MergeSourceItem(BaseModel):
    batch_id: int | str = Field(..., description="ID hoặc Mã của lô nguồn cần gộp")
    quantity: float = Field(
        ..., gt=0, description="Khối lượng trích xuất từ lô này để gộp"
    )


class BatchMergeRequest(BaseModel):
    sources: list[MergeSourceItem] = Field(
        ...,
        min_length=2,
        description="Tối thiểu 2 lô nguồn có cùng loại sản phẩm để gộp",
    )
    notes: str | None = None


class BatchMergeResponse(BaseModel):
    merged_batch: BatchResponse
    source_batches: list[BatchResponse]
    total_merged_quantity: float


class BatchRelationResponse(BaseModel):
    id: int
    parent_batch_id: int
    child_batch_id: int
    parent_batch_code: str | None = None
    child_batch_code: str | None = None
    relation_type: str
    quantity: float
    notes: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchLineageResponse(BaseModel):
    batch: BatchResponse
    parents: list[BatchRelationResponse] = []
    children: list[BatchRelationResponse] = []
