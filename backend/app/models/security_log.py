from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class SecurityLog(Base):
    __tablename__ = "security_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    user_email = Column(String(255), nullable=True)
    user_org_id = Column(Integer, nullable=True, index=True)
    attempt_type = Column(
        String(100), nullable=False
    )  # ví dụ: "cross_tenant_access_attempt"
    target_resource = Column(String(100), nullable=False)  # ví dụ: "batch"
    target_id = Column(String(100), nullable=True)
    target_org_id = Column(Integer, nullable=True, index=True)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(20), nullable=False)
    ip_address = Column(String(100), nullable=True)
    description = Column(String(500), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
