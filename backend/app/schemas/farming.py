from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FarmingLogBase(BaseModel):
    plot_id: int
    activity_type: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    materials_used: str | None = Field(default=None, max_length=255)
    activity_date: str = Field(..., min_length=1, max_length=20)


class FarmingLogCreate(FarmingLogBase):
    pass


class FarmingLogResponse(FarmingLogBase):
    id: int
    supervisor_id: int | None
    organization_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FieldIncidentBase(BaseModel):
    plot_id: int
    incident_type: str = Field(..., min_length=1, max_length=100)
    severity: str = Field(default="medium", pattern="^(low|medium|high)$")
    description: str = Field(..., min_length=1, max_length=500)


class FieldIncidentCreate(FieldIncidentBase):
    pass


class FieldIncidentResolve(BaseModel):
    action_taken: str = Field(..., min_length=1, max_length=500)


class FieldIncidentResponse(FieldIncidentBase):
    id: int
    action_taken: str | None
    status: str
    reported_by_id: int | None
    organization_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
