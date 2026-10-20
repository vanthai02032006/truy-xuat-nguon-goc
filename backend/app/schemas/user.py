from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    email: str
    full_name: str
    role: str = "member"
    organization_id: int | None = None


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    failed_attempts: int = 0
    locked_until: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    organization_id: int | None
    user_email: str
    full_name: str | None = None


class SimulateLockoutRequest(BaseModel):
    email: str


class LockoutStatusResponse(BaseModel):
    email: str
    failed_attempts: int
    is_locked: bool
    remaining_minutes: int | None = None
    locked_until: datetime | None = None

