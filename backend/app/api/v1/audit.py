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
    _admin_user: Annotated[
        User,
        Depends(
            require_roles(
                UserRole.SYSTEM_ADMIN.value,
                "system_admin",
                "admin",
            )
        ),
    ],
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
):
    """
    Xem danh sách nhật ký cảnh báo an ninh & lần thử truy cập chéo tổ chức (S-31).
    Chỉ dành riêng cho Quản trị viên hệ thống (system_admin).
    Cán bộ kiểm tra (Inspector) và các vai trò tổ chức khác bị chặn (HTTP 403 Forbidden).
    """
    return SecurityLogRepository.list_logs(db, skip=skip, limit=limit)
