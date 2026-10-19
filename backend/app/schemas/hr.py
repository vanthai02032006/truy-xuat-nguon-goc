from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WorkerBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=200)
    worker_type: str = Field(default="seasonal", max_length=50)
    phone: str | None = Field(default=None, max_length=20)


class WorkerCreate(WorkerBase):
    daily_rate: float = Field(default=250000.0, ge=0)


class WorkerResponse(WorkerBase):
    id: int
    daily_rate: float | None = None  # Ẩn với vai trò Supervisor
    organization_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DailyTaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    plot_id: int | None = None
    worker_id: int | None = None
    task_date: str = Field(..., min_length=1, max_length=20)


class DailyTaskCreate(DailyTaskBase):
    pass


class DailyTaskResponse(DailyTaskBase):
    id: int
    supervisor_id: int | None
    status: str
    organization_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TimesheetCreate(BaseModel):
    worker_id: int
    date: str = Field(..., min_length=1, max_length=20)
    hours_worked: float = Field(default=8.0, ge=0)
    output_quantity: float = Field(default=0.0, ge=0)
    output_unit: str = Field(default="kg", max_length=50)


class TimesheetResponse(BaseModel):
    id: int
    worker_id: int
    date: str
    hours_worked: float
    output_quantity: float
    output_unit: str
    status: str
    supervisor_id: int | None
    approver_id: int | None
    organization_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PayrollSummary(BaseModel):
    organization_id: int
    total_workers: int
    total_hours_worked: float
    total_estimated_wage: float
