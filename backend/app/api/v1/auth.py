from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import Token, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(
    login_data: UserLogin,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Đăng nhập hệ thống bằng email và mật khẩu (S-04).
    Mật khẩu được xác thực bằng argon2id.
    Tạo JWT token và set cookie HttpOnly Secure.
    """
    user = UserRepository.get_by_email(db, login_data.email)
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản hiện đang bị khóa.",
        )

    access_token = create_access_token(
        subject=user.email,
        role=user.role,
        organization_id=user.organization_id,
    )

    # Đặt cookie phiên có cờ HttpOnly (S-04 NFR)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        organization_id=user.organization_id,
        user_email=user.email,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    """Xem thông tin tài khoản hiện tại."""
    return current_user
