from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    category = Column(
        String(50), nullable=False, default="fertilizer"
    )  # fertilizer, pesticide, seed, tool
    quantity_in_stock = Column(Float, nullable=False, default=0.0)
    unit = Column(String(50), nullable=False, default="kg")
    min_threshold = Column(Float, nullable=False, default=10.0)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    organization = relationship("Organization")


class MaterialRequest(Base):
    __tablename__ = "material_requests"

    id = Column(Integer, primary_key=True, index=True)
    material_name = Column(String(200), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False, default="kg")
    purpose = Column(String(255), nullable=True)
    urgency = Column(
        String(50), nullable=False, default="normal"
    )  # normal, high, critical
    status = Column(
        String(50), nullable=False, default="pending"
    )  # pending, approved, rejected, fulfilled
    requester_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approver_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rejection_reason = Column(String(255), nullable=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization")
    requester = relationship("User", foreign_keys=[requester_id])
    approver = relationship("User", foreign_keys=[approver_id])


class BatchMaterialLog(Base):
    """
    User Story S-62: Ghi nhận vật tư (phân bón, thuốc BVTV) đã dùng gắn với một lô hàng cụ thể
    để phục vụ việc kiểm tra thời gian cách ly khi thu hoạch.
    """

    __tablename__ = "batch_material_logs"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(
        Integer,
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    material_id = Column(
        Integer,
        ForeignKey("materials.id", ondelete="SET NULL"),
        nullable=True,
    )
    material_name = Column(String(200), nullable=False)
    category = Column(
        String(50), nullable=False, default="pesticide"
    )  # pesticide, fertilizer, bio_pesticide
    dosage = Column(
        String(100), nullable=False
    )  # ví dụ: "50ml/bình 16L", "10kg/1000m2"
    applied_date = Column(String(20), nullable=False)  # YYYY-MM-DD
    isolation_days = Column(Integer, nullable=False, default=7)  # Số ngày cách ly (PHI)
    safe_harvest_date = Column(
        String(20), nullable=False
    )  # Ngày an toàn thu hoạch: YYYY-MM-DD
    applied_by = Column(String(100), nullable=True)  # Người thực hiện
    notes = Column(String(500), nullable=True)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    batch = relationship("Batch", back_populates="material_logs")
    material = relationship("Material")
    organization = relationship("Organization")
