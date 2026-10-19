from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import check_default_deny, enforce_route_permission, get_current_user
from app.models.user import User

router = APIRouter(prefix="/protected", tags=["protected"])


@router.get("/declared-perm")
@enforce_route_permission(["read:sample"])
def get_with_declared_permission(
    current_user: Annotated[User, Depends(get_current_user)],
    _deny_check: Annotated[None, Depends(check_default_deny)],
):
    """Route có khai báo quyền hợp lệ -> Truy cập thành công."""
    return {
        "status": "ok",
        "message": "Truy cập thành công vào route có khai báo quyền rõ ràng.",
        "user": current_user.email,
    }


@router.get("/unconfigured-route")
def get_without_declared_permission(
    current_user: Annotated[User, Depends(get_current_user)],
    _deny_check: Annotated[None, Depends(check_default_deny)],
):
    """
    AC 3: Giả sử một route mới được thêm mà quên khai báo quyền,
    Khi gọi route đó, Thì bị từ chối — mặc định là chặn.
    """
    return {"message": "Không bao giờ chạy tới đây vì bị chặn mặc định"}
