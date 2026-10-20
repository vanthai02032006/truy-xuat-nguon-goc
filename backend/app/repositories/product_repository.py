from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.product import Product


class ProductRepository:
    """Repository thao tác dữ liệu bảng products dùng chung toàn hệ thống."""

    @staticmethod
    def get(db: Session, product_id: int) -> Product | None:
        return db.query(Product).filter(Product.id == product_id).first()

    @staticmethod
    def get_by_name(db: Session, name: str) -> Product | None:
        clean_name = name.strip()
        return (
            db.query(Product)
            .filter(func.lower(Product.name) == func.lower(clean_name))
            .first()
        )

    @staticmethod
    def list(
        db: Session, skip: int = 0, limit: int = 100, query: str | None = None
    ) -> list[Product]:
        q = db.query(Product)
        if query:
            clean_q = f"%{query.strip().lower()}%"
            q = q.filter(func.lower(Product.name).like(clean_q))
        return q.order_by(Product.name.asc()).offset(skip).limit(limit).all()

    @staticmethod
    def create(db: Session, product: Product) -> Product:
        db.add(product)
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def update(db: Session, product: Product) -> Product:
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def delete(db: Session, product: Product) -> None:
        db.delete(product)
        db.commit()
