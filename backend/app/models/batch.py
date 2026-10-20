from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_code = Column(String(100), unique=True, nullable=False, index=True)
    product_name = Column(String(200), nullable=False)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    land_plot_id = Column(
        Integer,
        ForeignKey("land_plots.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    farmer_ref_id = Column(String(50), nullable=True, index=True)
    status = Column(
        String(50),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
    )
    initial_quantity = Column(
        Float,
        nullable=False,
        default=100.0,
        server_default="100.0",
    )
    remaining_quantity = Column(
        Float,
        nullable=False,
        default=100.0,
        server_default="100.0",
    )
    unit = Column(
        String(20),
        nullable=False,
        default="kg",
        server_default="kg",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    organization = relationship("Organization")
    land_plot = relationship("LandPlot", back_populates="batches")
    material_logs = relationship(
        "BatchMaterialLog", back_populates="batch", cascade="all, delete-orphan"
    )
    handovers = relationship(
        "Handover", back_populates="batch", cascade="all, delete-orphan"
    )
    chain_events = relationship(
        "ChainEvent", back_populates="batch", cascade="all, delete-orphan"
    )
    child_relations = relationship(
        "BatchRelation",
        foreign_keys="BatchRelation.parent_batch_id",
        back_populates="parent_batch",
        cascade="all, delete-orphan",
    )
    parent_relations = relationship(
        "BatchRelation",
        foreign_keys="BatchRelation.child_batch_id",
        back_populates="child_batch",
        cascade="all, delete-orphan",
    )
