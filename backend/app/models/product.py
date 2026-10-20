from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class Product(Base):
    """
    Bảng danh mục sản phẩm dùng chung cho toàn hệ thống (User Story S-07, Task T-16).
    Không lọc theo organization_id: Mọi tổ chức đều dùng chung danh mục này.
    """

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), unique=True, nullable=False, index=True)
    unit = Column(String(20), nullable=False)  # Đơn vị tính đóng: 'kg', 'tấn', 'thùng'
    description = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
