from __future__ import annotations

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class RecallStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class RecallSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"


class Recall(Base):
    """User Story S-33, S-34, S-35: Lệnh thu hồi khẩn cấp lô hàng nông sản (Epic E-06)."""

    __tablename__ = "recalls"

    id = Column(Integer, primary_key=True, index=True)
    recall_code = Column(String(50), unique=True, nullable=False, index=True)
    source_batch_id = Column(
        Integer,
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    initiator_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    initiator_organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason = Column(String(1000), nullable=False)  # Bắt buộc >= 20 ký tự
    severity = Column(String(50), default=RecallSeverity.CRITICAL.value, nullable=False)
    status = Column(
        String(50), default=RecallStatus.ACTIVE.value, nullable=False, index=True
    )
    total_affected_batches = Column(Integer, default=0, nullable=False)
    total_affected_kg = Column(Float, default=0.0, nullable=False)
    total_stock_kg = Column(Float, default=0.0, nullable=False)
    total_sold_kg = Column(Float, default=0.0, nullable=False)
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

    source_batch = relationship("Batch", foreign_keys=[source_batch_id])
    initiator_user = relationship("User", foreign_keys=[initiator_user_id])
    initiator_organization = relationship(
        "Organization", foreign_keys=[initiator_organization_id]
    )

    affected_items = relationship(
        "RecallAffectedBatch",
        back_populates="recall",
        cascade="all, delete-orphan",
    )
    organization_actions = relationship(
        "RecallOrganizationAction",
        back_populates="recall",
        cascade="all, delete-orphan",
    )


class RecallAffectedBatch(Base):
    """User Story S-34, S-35: Các lô con/cháu bị khoanh vùng trong lệnh thu hồi."""

    __tablename__ = "recall_affected_batches"

    id = Column(Integer, primary_key=True, index=True)
    recall_id = Column(
        Integer,
        ForeignKey("recalls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    batch_id = Column(
        Integer,
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    generation = Column(String(20), default="ROOT", nullable=False)
    initial_quantity = Column(Float, default=0.0, nullable=False)
    remaining_quantity = Column(Float, default=0.0, nullable=False)
    sold_quantity = Column(Float, default=0.0, nullable=False)
    current_location = Column(String(255), nullable=True)
    batch_status_before = Column(String(50), nullable=True)
    is_isolated = Column(Boolean, default=False, nullable=False)
    isolated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    recall = relationship("Recall", back_populates="affected_items")
    batch = relationship("Batch")
    organization = relationship("Organization")


class RecallOrganizationAction(Base):
    """User Story S-36, S-37: Quản lý quy trình xử lý & xác nhận cô lập của từng tổ chức."""

    __tablename__ = "recall_organization_actions"

    id = Column(Integer, primary_key=True, index=True)
    recall_id = Column(
        Integer,
        ForeignKey("recalls.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        String(50), default="PENDING", nullable=False, index=True
    )  # PENDING, CONFIRMED_ISOLATED
    action_notes = Column(String(500), nullable=True)
    confirmed_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    affected_batch_count = Column(Integer, default=0, nullable=False)
    stock_kg = Column(Float, default=0.0, nullable=False)

    recall = relationship("Recall", back_populates="organization_actions")
    organization = relationship("Organization")
    confirmed_by_user = relationship("User")
