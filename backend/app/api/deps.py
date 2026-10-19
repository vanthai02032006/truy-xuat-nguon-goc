from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import decode_access_token
from app.models.batch import Batch
from app.models.user import User, UserRole
from app.repositories.batch_repository import BatchRepository
from app.repositories.security_log_repository import SecurityLogRepository
from app.repositories.user_repository import UserRepository


def get_db() -> Generator[Session, None, None]:
    """Dependency cung cấp session cơ sở dữ liệu cho mỗi request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    authorization: Annotated[str | None, Header()] = None,
    access_token: Annotated[str | None, Cookie()] = None,
) -> User:
    """
    Xác thực người dùng từ Bearer token hoặc HttpOnly Cookie.
    Nếu không có token hoặc token không hợp lệ -> Trả về 401 Unauthorized.
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    elif access_token:
        token = access_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu xác thực danh tính. Vui lòng đăng nhập.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_email = payload["sub"]
    user = UserRepository.get_by_email(db, user_email)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản không tồn tại hoặc đã bị khóa.",
        )

    return user


def require_roles(*allowed_roles: str):
    """
    Dependency kiểm tra vai trò người dùng (RBAC).
    Nếu vai trò không khớp -> Trả về 403 Forbidden.
    """

    def role_checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Quyền truy cập bị từ chối. Yêu cầu vai trò trong {allowed_roles}.",
            )
        return current_user

    return role_checker


def check_default_deny(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """
    AC 3: Giả sử một route mới được thêm mà quên khai báo quyền,
    Khi gọi route đó, Thì bị từ chối — mặc định là chặn (Default Deny).
    """
    route = request.scope.get("endpoint")
    declared_perms = getattr(route, "_declared_permissions", None)
    if declared_perms is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Route chưa được khai báo quyền truy cập — mặc định là chặn.",
        )


def enforce_route_permission(required_permission: str | list[str]):
    """
    Decorator gán và khai báo quyền rõ ràng cho route.
    """
    perms = (
        [required_permission]
        if isinstance(required_permission, str)
        else required_permission
    )

    def decorator(func):
        func._declared_permissions = perms
        return func

    return decorator


def verify_batch_access(
    batch_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> Batch:
    """
    Kiểm tra quyền truy cập lô hàng chéo tổ chức và cán bộ kiểm tra:
    - AC 2: Gọi thẳng API với mã bản ghi của tổ chức khác -> Trả về 403 và ghi nhật ký lần thử.
    - AC 4: Cán bộ kiểm tra (inspector) -> Thấy được lô của mọi tổ chức nhưng chỉ ở chế độ đọc.
    """
    batch = BatchRepository.get_by_id(db, batch_id)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy lô hàng với ID {batch_id}",
        )

    client_ip = request.client.host if request.client else "unknown"

    # Trường hợp là cán bộ kiểm tra (Inspector)
    if current_user.role == UserRole.INSPECTOR.value:
        if request.method not in ["GET", "HEAD", "OPTIONS"]:
            SecurityLogRepository.log_attempt(
                db=db,
                user_id=current_user.id,
                user_email=current_user.email,
                user_org_id=current_user.organization_id,
                attempt_type="inspector_write_violation",
                target_resource="batch",
                target_id=str(batch.id),
                target_org_id=batch.organization_id,
                endpoint=request.url.path,
                method=request.method,
                ip_address=client_ip,
                description="Cán bộ kiểm tra cố gắng thực hiện thao tác ghi/sửa/xóa (chỉ được phép đọc).",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cán bộ kiểm tra chỉ có quyền xem dữ liệu (chế độ chỉ đọc).",
            )
        return batch

    # Trường hợp là thành viên / quản trị tổ chức (Member / Admin)
    # Kiểm tra xem lô hàng có thuộc tổ chức của user hay không (AC 2)
    if batch.organization_id != current_user.organization_id:
        SecurityLogRepository.log_attempt(
            db=db,
            user_id=current_user.id,
            user_email=current_user.email,
            user_org_id=current_user.organization_id,
            attempt_type="cross_tenant_access_denied",
            target_resource="batch",
            target_id=str(batch.id),
            target_org_id=batch.organization_id,
            endpoint=request.url.path,
            method=request.method,
            ip_address=client_ip,
            description=(
                f"Người dùng {current_user.email} (Tổ chức {current_user.organization_id}) "
                f"cố tình gọi thẳng API truy cập lô #{batch.id} của Tổ chức {batch.organization_id}."
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập dữ liệu của tổ chức khác.",
        )

    return batch
