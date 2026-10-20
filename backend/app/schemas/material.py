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


class BatchMaterialLogCreate(BaseModel):
    material_name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(default="pesticide", max_length=50)  # pesticide, fertilizer, bio_pesticide
    dosage: str = Field(..., min_length=1, max_length=100)
    applied_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")  # YYYY-MM-DD
    isolation_days: int = Field(default=7, ge=0)
    applied_by: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
    material_id: int | None = None


class BatchMaterialLogResponse(BaseModel):
    id: int
    batch_id: int
    material_id: int | None
    material_name: str
    category: str
    dosage: str
    applied_date: str
    isolation_days: int
    safe_harvest_date: str
    applied_by: str | None
    notes: str | None
    organization_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BatchPHICheckResponse(BaseModel):
    batch_id: int
    batch_code: str
    is_safe_to_harvest: bool
    tested_harvest_date: str
    max_safe_harvest_date: str | None
    days_remaining: int
    status: str  # compliant, violating, no_pesticide_applied
    message: str
    material_logs: list[BatchMaterialLogResponse]

