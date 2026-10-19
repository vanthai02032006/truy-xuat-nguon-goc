from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MaterialBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=50)
    category: str = Field(default="fertilizer", max_length=50)
    quantity_in_stock: float = Field(default=0.0, ge=0)
    unit: str = Field(default="kg", max_length=50)
    min_threshold: float = Field(default=10.0, ge=0)


class MaterialCreate(MaterialBase):
    pass


class MaterialResponse(MaterialBase):
    id: int
    organization_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaterialRequestCreate(BaseModel):
    material_name: str = Field(..., min_length=1, max_length=200)
    quantity: float = Field(..., gt=0)
    unit: str = Field(default="kg", max_length=50)
    purpose: str | None = Field(default=None, max_length=255)
    urgency: str = Field(default="normal", max_length=50)  # normal, high, critical


class MaterialRequestReject(BaseModel):
    reason: str = Field(..., min_length=1, max_length=255)


class MaterialRequestResponse(BaseModel):
    id: int
    material_name: str
    quantity: float
    unit: str
    purpose: str | None
    urgency: str
    status: str
    requester_id: int | None
    approver_id: int | None
    rejection_reason: str | None
    organization_id: int
    created_at: datetime
    reviewed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
