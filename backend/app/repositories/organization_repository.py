from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.organization import Organization


class OrganizationRepository:
    @staticmethod
    def get_by_id(db: Session, org_id: int) -> Organization | None:
        return db.query(Organization).filter(Organization.id == org_id).first()

    @staticmethod
    def get_by_code(db: Session, code: str) -> Organization | None:
        return db.query(Organization).filter(Organization.code == code).first()

    @staticmethod
    def create(db: Session, organization: Organization) -> Organization:
        db.add(organization)
        db.commit()
        db.refresh(organization)
        return organization

    @staticmethod
    def list_all(db: Session) -> list[Organization]:
        return db.query(Organization).all()
