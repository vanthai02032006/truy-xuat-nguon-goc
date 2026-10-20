from __future__ import annotations

import enum

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class BatchRelationType(str, enum.Enum):
    SPLIT = "SPLIT"
    MERGE = "MERGE"


class BatchRelation(Base):
    """
    Bảng quan hệ batch_relations (User Story S-17, S-18, S-19):
    - Lưu trữ quan hệ cha - con giữa các lô hàng khi Tách lô (Split) hoặc Gộp lô (Merge).
    - Lưu khối lượng chuyển đổi (quantity).
    - Phục vụ việc dựng đồ thị phả hệ nguồn gốc chuỗi cung ứng (Genealogy Tree).
    """

    __tablename__ = "batch_relations"

    id = Column(Integer, primary_key=True, index=True)
    parent_batch_id = Column(
        Integer,
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    child_batch_id = Column(
        Integer,
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type = Column(
        String(20),
        nullable=False,
        index=True,
    )
    quantity = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    parent_batch = relationship(
        "Batch",
        foreign_keys=[parent_batch_id],
        back_populates="child_relations",
    )
    child_batch = relationship(
        "Batch",
        foreign_keys=[child_batch_id],
        back_populates="parent_relations",
    )
