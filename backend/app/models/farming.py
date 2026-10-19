from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class FarmingLog(Base):
    __tablename__ = "farming_logs"

    id = Column(Integer, primary_key=True, index=True)
    plot_id = Column(
        Integer,
        ForeignKey("land_plots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activity_type = Column(
        String(100), nullable=False
    )  # watering, fertilizing, spraying, pruning, harvesting
    description = Column(String(500), nullable=True)
    materials_used = Column(String(255), nullable=True)
    activity_date = Column(String(20), nullable=False)
    supervisor_id = Column(
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
    plot = relationship("LandPlot")
    supervisor = relationship("User")


class FieldIncident(Base):
    __tablename__ = "field_incidents"

    id = Column(Integer, primary_key=True, index=True)
    plot_id = Column(
        Integer,
        ForeignKey("land_plots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_type = Column(
        String(100), nullable=False
    )  # pest, disease, weather, equipment
    severity = Column(String(50), nullable=False, default="medium")  # low, medium, high
    description = Column(String(500), nullable=False)
    action_taken = Column(String(500), nullable=True)
    status = Column(
        String(50), nullable=False, default="reported"
    )  # reported, resolving, resolved
    reported_by_id = Column(
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
    plot = relationship("LandPlot")
    reported_by = relationship("User")
