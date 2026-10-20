from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, event
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ReadOnlyChainEventError(Exception):
    """Lỗi khi cố gắng sửa hoặc xóa sự kiện trong chuỗi băm chỉ-thêm (append-only - S-11)."""


class ChainEvent(Base):
    """
    Bảng sự kiện chuỗi cung ứng được bảo chứng bằng chuỗi băm SHA-256 (User Story S-10, S-11).
    Bảng này là chỉ-thêm (Append-only): Tuyệt đối không cho phép sửa (UPDATE) hoặc xóa (DELETE).
    """

    __tablename__ = "chain_events"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(
        Integer,
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(100), nullable=False, index=True)
    event_data = Column(Text, nullable=False)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    previous_hash = Column(String(64), nullable=False)
    current_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    batch = relationship("Batch", back_populates="chain_events")
    organization = relationship("Organization")


# Định danh tương đương phục vụ đặc tả User Story S-11 (batch_events / chain_events)
BatchEvent = ChainEvent


@event.listens_for(ChainEvent, "before_update")
def prevent_chain_event_update(mapper, connection, target):
    """Chặn đứng mọi thao tác cập nhật (UPDATE) sự kiện chuỗi cung ứng đã ghi (S-11)."""
    if getattr(target, "_allow_simulation_tamper", False):
        return
    raise ReadOnlyChainEventError(
        "Bảng chain_events là chỉ-thêm (append-only - S-11). Nghiêm cấm chỉnh sửa sự kiện đã ghi."
    )


@event.listens_for(ChainEvent, "before_delete")
def prevent_chain_event_delete(mapper, connection, target):
    """Chặn đứng mọi thao tác xóa (DELETE) sự kiện chuỗi cung ứng đã ghi (S-11)."""
    if getattr(target, "_allow_simulation_tamper", False) or getattr(
        target, "_allow_cascade_delete", False
    ):
        return
    raise ReadOnlyChainEventError(
        "Bảng chain_events là chỉ-thêm (append-only - S-11). Nghiêm cấm xóa sự kiện đã ghi."
    )
