from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.models.user import User, UserRole
from app.repositories.security_log_repository import SecurityLogRepository
from app.schemas.security_log import SecurityLogResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/security-logs", response_model=list[SecurityLogResponse])
def get_security_logs(
    _admin_or_inspector: Annotated[
        User,
        Depends(
            require_roles(
                UserRole.ADMIN.value,
                UserRole.SYSTEM_ADMIN.value,
                UserRole.INSPECTOR.value,
            )
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
):
    """
    Xem danh sách nhật ký cảnh báo an ninh & lần thử truy cập chéo tổ chức.
    Chỉ dành cho Quản trị viên (Admin) hoặc Cán bộ kiểm tra (Inspector).
    """
    return SecurityLogRepository.list_logs(db, skip=skip, limit=limit)
