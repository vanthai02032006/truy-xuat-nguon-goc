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


class TripStatus(str, enum.Enum):
    IN_TRANSIT = "IN_TRANSIT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ViolationType(str, enum.Enum):
    HIGH_TEMPERATURE = "HIGH_TEMPERATURE"
    FREEZING = "FREEZING"


class TransportTrip(Base):
    """User Story S-40: Quản lý chuyến vận chuyển hàng nông sản bảo quản lạnh (Epic E-07)."""

    __tablename__ = "transport_trips"

    id = Column(Integer, primary_key=True, index=True)
    trip_code = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_code = Column(String(100), nullable=False, index=True)  # Biển số xe / mã thùng lạnh
    carrier_org_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    driver_name = Column(String(100), nullable=True)
    min_temperature = Column(Float, default=2.0, nullable=False)
    max_temperature = Column(Float, default=8.0, nullable=False)
    status = Column(
        String(50), default=TripStatus.IN_TRANSIT.value, nullable=False, index=True
    )
    start_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    carrier_organization = relationship("Organization")
    trip_batches = relationship(
        "TripBatch", back_populates="trip", cascade="all, delete-orphan"
    )
    telemetry_readings = relationship(
        "TemperatureTelemetry",
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="TemperatureTelemetry.timestamp.asc()",
    )
    violations = relationship(
        "ColdChainViolation",
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="ColdChainViolation.started_at.asc()",
    )


class TripBatch(Base):
    """Liên kết giữa chuyến xe lạnh và danh sách các lô hàng đang chở (S-40)."""

    __tablename__ = "trip_batches"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(
        Integer,
        ForeignKey("transport_trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    batch_id = Column(
        Integer,
        ForeignKey("batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    trip = relationship("TransportTrip", back_populates="trip_batches")
    batch = relationship("Batch")


class TemperatureTelemetry(Base):
    """User Story S-41: Nhật ký cảm biến nhiệt độ chuỗi lạnh theo thời gian."""

    __tablename__ = "temperature_telemetry"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(
        Integer,
        ForeignKey("transport_trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    temperature = Column(Float, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    trip = relationship("TransportTrip", back_populates="telemetry_readings")


class ColdChainViolation(Base):
    """User Story S-43, S-45: Sự kiện vi phạm chuỗi lạnh có độ trễ 30 phút và cảnh báo hash chain."""

    __tablename__ = "cold_chain_violations"

    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(
        Integer,
        ForeignKey("transport_trips.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Float, nullable=False)
    peak_temperature = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    violation_type = Column(
        String(50), default=ViolationType.HIGH_TEMPERATURE.value, nullable=False
    )
    status = Column(String(50), default="DETECTED", nullable=False, index=True)
    hash_recorded = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    trip = relationship("TransportTrip", back_populates="violations")
