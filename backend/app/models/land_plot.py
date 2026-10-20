from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class LandPlot(Base):
    __tablename__ = "land_plots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    area = Column(Float, nullable=False)  # Diện tích đất (> 0)
    unit = Column(String(50), default="m2", nullable=False)
    latitude = Column(Float, nullable=False)  # Toạ độ vĩ độ (số thực)
    longitude = Column(Float, nullable=False)  # Toạ độ kinh độ (số thực)
    address = Column(String(255), nullable=True)
    farmer_ref_id = Column(String(50), nullable=True, index=True)
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
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True,
    )

    organization = relationship("Organization")
    batches = relationship("Batch", back_populates="land_plot")
