from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.land_plot import LandPlot


class LandPlotRepository:
    @staticmethod
    def get_by_id(db: Session, plot_id: int) -> LandPlot | None:
        """Lấy thông tin thửa đất theo ID."""
        return db.query(LandPlot).filter(LandPlot.id == plot_id).first()

    @staticmethod
    def list_plots(
        db: Session,
        organization_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[LandPlot]:
        """
        NFR: Lọc thửa đất theo tổ chức ở tầng truy vấn (SQL WHERE clause),
        tuyệt đối không lọc ở giao diện hay tầng ứng dụng sau khi fetch toàn bộ.
        """
        query = db.query(LandPlot)
        if organization_id is not None:
            query = query.filter(LandPlot.organization_id == organization_id)
        return query.order_by(LandPlot.id.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def create(db: Session, plot: LandPlot) -> LandPlot:
        db.add(plot)
        db.commit()
        db.refresh(plot)
        return plot

    @staticmethod
    def update(db: Session, plot: LandPlot, update_data: dict) -> LandPlot:
        for field, value in update_data.items():
            if value is not None and hasattr(plot, field):
                setattr(plot, field, value)
        db.commit()
        db.refresh(plot)
        return plot

    @staticmethod
    def delete(db: Session, plot: LandPlot) -> None:
        db.delete(plot)
        db.commit()
