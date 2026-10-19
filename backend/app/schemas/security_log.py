from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SecurityLogResponse(BaseModel):
    id: int
    user_id: int | None
    user_email: str | None
    user_org_id: int | None
    attempt_type: str
    target_resource: str
    target_id: str | None
    target_org_id: int | None
    endpoint: str
    method: str
    ip_address: str | None
    description: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
