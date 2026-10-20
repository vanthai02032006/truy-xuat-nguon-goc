from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class FarmerIdentity(Base):
    """
    User Story S-56 & Nghị định 13/2023/NĐ-CP:
    Tách biệt dữ liệu định danh cá nhân của nông hộ (PII - Personally Identifiable Information)
    ra khỏi bảng sự kiện chuỗi khối (chain_events / batch_events).
    
    Nội dung lưu trong chuỗi hash chỉ sử dụng mã tham chiếu bí danh `farmer_ref_id`.
    Khi nông hộ thực hiện quyền xóa dữ liệu cá nhân theo NĐ 13/2023/NĐ-CP:
    - Bảng farmer_identities sẽ ẩn danh hóa / xóa thông tin PII (Họ tên, SĐT, CCCD, Địa chỉ).
    - Chuỗi Hash SHA-256 của các lô hàng không đổi một ký tự nào -> Toàn vẹn 100%.
    """

    __tablename__ = "farmer_identities"

    id = Column(Integer, primary_key=True, index=True)
    farmer_ref_id = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(150), nullable=True)
    phone = Column(String(50), nullable=True)
    id_card = Column(String(50), nullable=True)  # CMND / CCCD
    detail_address = Column(String(255), nullable=True)  # Thôn/Xóm, số nhà chi tiết
    province = Column(String(100), default="Lâm Đồng", nullable=False)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_anonymized = Column(Boolean, default=False, nullable=False, index=True)
    anonymized_at = Column(DateTime(timezone=True), nullable=True)
    anonymize_reason = Column(String(255), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
    )

    organization = relationship("Organization")
