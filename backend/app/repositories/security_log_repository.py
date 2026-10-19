from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.security_log import SecurityLog

logger = logging.getLogger("security.audit")


class SecurityLogRepository:
    @staticmethod
    def log_attempt(
        db: Session,
        user_id: int | None,
        user_email: str | None,
        user_org_id: int | None,
        attempt_type: str,
        target_resource: str,
        target_id: str | None,
        target_org_id: int | None,
        endpoint: str,
        method: str,
        ip_address: str | None,
        description: str,
    ) -> SecurityLog:
        """
        Ghi nhật ký lần thử truy cập tài nguyên trái phép / chéo tổ chức:
        1. Ghi nhận vào bảng security_logs trong cơ sở dữ liệu.
        2. Ghi ra log hệ thống (logger.warning) phục vụ SIEM / giám sát an ninh.
        """
        logger.warning(
            "CẢNH BÁO BẢO MẬT: %s | User: %s (ID: %s, Org: %s) -> Mục tiêu: %s (ID: %s, Org: %s) tại %s [%s] | Chi tiết: %s",
            attempt_type,
            user_email or "Anonymous",
            user_id,
            user_org_id,
            target_resource,
            target_id,
            target_org_id,
            endpoint,
            method,
            description,
        )

        log_entry = SecurityLog(
            user_id=user_id,
            user_email=user_email,
            user_org_id=user_org_id,
            attempt_type=attempt_type,
            target_resource=target_resource,
            target_id=str(target_id) if target_id is not None else None,
            target_org_id=target_org_id,
            endpoint=endpoint,
            method=method,
            ip_address=ip_address,
            description=description,
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @staticmethod
    def list_logs(
        db: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SecurityLog]:
        return (
            db.query(SecurityLog)
            .order_by(SecurityLog.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
