from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BatchBase(BaseModel):
    batch_code: str
    product_name: str


class BatchCreate(BatchBase):
    organization_id: int | None = None


class BatchResponse(BatchBase):
    id: int
    organization_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
