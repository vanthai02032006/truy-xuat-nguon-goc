from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ProductUnit(str, Enum):
    """
    Danh sách đóng các đơn vị tính hợp lệ (User Story S-07, Task T-16).
    Tuyệt đối không cho phép nhập chữ tự do ngoài các giá trị này.
    """

    KG = "kg"
    TON = "tấn"
    BOX = "thùng"


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Tên sản phẩm nông sản")
    unit: ProductUnit = Field(..., description="Đơn vị tính bắt buộc từ danh sách đóng: kg, tấn, thùng")
    description: str | None = Field(default=None, max_length=1000, description="Mô tả chi tiết sản phẩm")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    unit: ProductUnit | None = None
    description: str | None = Field(default=None, max_length=1000)


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
