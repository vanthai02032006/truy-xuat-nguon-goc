from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.batch import Batch


class BatchRepository:
    @staticmethod
    def get_by_id(db: Session, batch_id: int) -> Batch | None:
        """Lấy thông tin lô hàng theo ID."""
        return db.query(Batch).filter(Batch.id == batch_id).first()

    @staticmethod
    def get_by_code(db: Session, batch_code: str) -> Batch | None:
        """Lấy thông tin lô hàng theo mã lô."""
        return db.query(Batch).filter(Batch.batch_code == batch_code).first()

    @staticmethod
    def list_batches(
        db: Session,
        organization_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Batch]:
        """
        NFR / Task T-12: Lọc theo tổ chức ở tầng truy vấn (SQL WHERE clause),
        tuyệt đối không lọc ở giao diện hay tầng ứng dụng sau khi fetch toàn bộ.
        """
        from app.services.batch_access_service import apply_tenant_filter

        query = apply_tenant_filter(db.query(Batch), Batch, organization_id)
        return query.order_by(Batch.id.desc()).offset(skip).limit(limit).all()


    @staticmethod
    def create(db: Session, batch: Batch, auto_commit: bool = True) -> Batch:
        db.add(batch)
        if auto_commit:
            db.commit()
            db.refresh(batch)
        else:
            db.flush()
        return batch

    @staticmethod
    def delete(db: Session, batch: Batch) -> None:
        db.delete(batch)
        db.commit()
