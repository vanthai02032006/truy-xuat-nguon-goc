from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HandoverBase(BaseModel):
    batch_id: int
    to_org_id: int
    temperature: str | float | None = None
    notes: str | None = None


class HandoverCreate(HandoverBase):
    pass


class HandoverRejectRequest(BaseModel):
    reject_reason: str = Field(
        ...,
        min_length=10,
        description="Bắt buộc nhập lý do từ chối bàn giao tối thiểu 10 ký tự (User Story S-16)",
    )


class HandoverResponse(BaseModel):
    id: int
    batch_id: int
    from_org_id: int
    to_org_id: int
    status: str
    reject_reason: str | None = None
    temperature: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    batch_code: str | None = None
    product_name: str | None = None
    from_org_name: str | None = None
    to_org_name: str | None = None
    batch_status: str | None = None
    has_cold_chain_violation: bool = False
    cold_chain_warning: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ChainEventResponse(BaseModel):
    id: int
    batch_id: int
    event_type: str
    event_data: str
    organization_id: int | None = None
    previous_hash: str
    current_hash: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationSimpleResponse(BaseModel):
    id: int
    name: str
    code: str | None = None

    model_config = ConfigDict(from_attributes=True)
