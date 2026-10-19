from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TransactionBase(BaseModel):
    transaction_type: str = Field(
        ..., pattern="^(revenue|expense)$"
    )  # revenue, expense
    category: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    description: str | None = Field(default=None, max_length=255)
    transaction_date: str = Field(..., min_length=1, max_length=20)


class TransactionCreate(TransactionBase):
    pass


class TransactionResponse(TransactionBase):
    id: int
    organization_id: int
    created_by_id: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinancialSummaryResponse(BaseModel):
    organization_id: int
    total_revenue: float
    total_expense: float
    net_profit: float
    transaction_count: int
