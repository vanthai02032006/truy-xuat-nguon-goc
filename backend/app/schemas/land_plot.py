from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LandPlotBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Tên thửa đất")
    area: float = Field(..., description="Diện tích thửa đất (phải lớn hơn 0)")
    unit: str = Field(default="m2", max_length=50, description="Đơn vị tính diện tích")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Vĩ độ toạ độ GPS")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Kinh độ toạ độ GPS")
    address: str | None = Field(
        default=None, max_length=255, description="Địa chỉ hoặc mô tả vị trí"
    )

    @field_validator("area")
    @classmethod
    def validate_area(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(
                "Diện tích thửa đất phải lớn hơn 0 (không được âm hoặc bằng 0)."
            )
        return v


class LandPlotCreate(LandPlotBase):
    organization_id: int | None = None


class LandPlotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    area: float | None = Field(default=None)
    unit: str | None = Field(default=None, max_length=50)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    address: str | None = Field(default=None, max_length=255)

    @field_validator("area")
    @classmethod
    def validate_area(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError(
                "Diện tích thửa đất phải lớn hơn 0 (không được âm hoặc bằng 0)."
            )
        return v


class LandPlotResponse(BaseModel):
    id: int
    name: str
    area: float
    unit: str
    latitude: float
    longitude: float
    address: str | None
    organization_id: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
