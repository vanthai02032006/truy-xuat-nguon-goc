from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FarmerCreateRequest(BaseModel):
    """Yêu cầu đăng ký nông hộ mới kèm định danh cá nhân."""

    full_name: str = Field(..., min_length=2, max_length=150, description="Họ và tên nông hộ")
    phone: str = Field(..., min_length=8, max_length=50, description="Số điện thoại liên hệ")
    id_card: str | None = Field(None, max_length=50, description="Số CCCD / CMND")
    detail_address: str = Field(..., min_length=3, max_length=255, description="Địa chỉ cư trú chi tiết")
    province: str = Field("Lâm Đồng", max_length=100, description="Tỉnh / Thành phố vùng trồng")
    organization_id: int | None = Field(None, description="Tổ chức / HTX quản lý (mặc định theo user)")
    farmer_ref_id: str | None = Field(None, max_length=50, description="Mã tham chiếu bí danh (tự sinh nếu để trống)")


class FarmerResponse(BaseModel):
    """Thông tin hiển thị của nông hộ."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    farmer_ref_id: str
    full_name: str | None = None
    phone: str | None = None
    id_card: str | None = None
    detail_address: str | None = None
    province: str
    organization_id: int
    organization_name: str | None = None
    is_anonymized: bool
    anonymized_at: datetime | None = None
    anonymize_reason: str | None = None
    display_name: str
    created_at: datetime


class FarmerAnonymizeRequest(BaseModel):
    """Yêu cầu xóa / ẩn danh dữ liệu cá nhân theo Nghị định 13/2023/NĐ-CP."""

    reason: str = Field(
        "Yêu cầu xóa dữ liệu cá nhân theo Điều 16 Nghị định 13/2023/NĐ-CP",
        min_length=10,
        max_length=255,
        description="Lý do xóa hoặc ẩn danh dữ liệu",
    )


class FarmerAnonymizeResponse(BaseModel):
    """Kết quả xóa dữ liệu định danh cá nhân mà không làm đứt chuỗi Hash (S-56)."""

    success: bool
    farmer_ref_id: str
    message: str
    is_anonymized: bool
    anonymized_at: datetime
    batches_checked_count: int
    chain_integrity_valid: bool
    integrity_message: str
