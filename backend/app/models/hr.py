from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Worker(Base):
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(200), nullable=False)
    worker_type = Column(
        String(50), nullable=False, default="seasonal"
    )  # seasonal, permanent
    phone = Column(String(20), nullable=True)
    daily_rate = Column(
        Float, nullable=False, default=250000.0
    )  # Thù lao/ngày (ẩn với Supervisor)
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


class DailyTask(Base):
    __tablename__ = "daily_tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    plot_id = Column(
        Integer, ForeignKey("land_plots.id", ondelete="SET NULL"), nullable=True
    )
    worker_id = Column(
        Integer, ForeignKey("workers.id", ondelete="SET NULL"), nullable=True
    )
    supervisor_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status = Column(
        String(50), nullable=False, default="assigned"
    )  # assigned, in_progress, completed
    task_date = Column(String(20), nullable=False)
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
    worker = relationship("Worker")
    supervisor = relationship("User")


class Timesheet(Base):
    __tablename__ = "timesheets"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(
        Integer, ForeignKey("workers.id", ondelete="CASCADE"), nullable=False
    )
    date = Column(String(20), nullable=False)
    hours_worked = Column(Float, nullable=False, default=8.0)
    output_quantity = Column(Float, nullable=False, default=0.0)
    output_unit = Column(String(50), nullable=False, default="kg")
    status = Column(
        String(50), nullable=False, default="submitted"
    )  # submitted, approved
    supervisor_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approver_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
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
    worker = relationship("Worker")
    supervisor = relationship("User", foreign_keys=[supervisor_id])
    approver = relationship("User", foreign_keys=[approver_id])
