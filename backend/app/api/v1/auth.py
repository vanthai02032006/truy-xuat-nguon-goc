from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    LockoutStatusResponse,
    SimulateLockoutRequest,
    Token,
    UserLogin,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_dt(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


DEMO_USERS_CONFIG = [
    {
        "id": 101,
        "email": "manager@nongtraixanh.vn",
        "full_name": "Nguyễn Văn Nông (Vùng trồng)",
        "role": UserRole.FARM.value,
        "org_id": 10,
        "org_name": "HTX Nông Nghiệp Thắng Lợi",
        "org_code": "FARM-TL",
    },
    {
        "id": 102,
        "email": "operator@sochebaoloc.vn",
        "full_name": "Trần Thị Sơ Chế (HTX Sơ chế)",
        "role": UserRole.COOP.value,
        "org_id": 20,
        "org_name": "HTX Sơ Chế Bảo Lộc",
        "org_code": "COOP-BL",
    },
    {
        "id": 103,
        "email": "driver@coldexpress.vn",
        "full_name": "Lê Vận Tải (Đơn vị vận chuyển lạnh)",
        "role": UserRole.LOGISTICS.value,
        "org_id": 30,
        "org_name": "Công Ty Vận Tải Lạnh Express",
        "org_code": "LOG-EXP",
    },
    {
        "id": 104,
        "email": "store@biomart.vn",
        "full_name": "Phạm Bán Lẻ (Nhà phân phối / Bán lẻ)",
        "role": UserRole.DISTRIBUTOR.value,
        "org_id": 40,
        "org_name": "Hệ Thống Bán Lẻ BioMart",
        "org_code": "RET-BIO",
    },
    {
        "id": 105,
        "email": "inspector.safe@kiemdinh.gov.vn",
        "full_name": "Đoàn Thanh Tra Chất Lượng (Cán bộ kiểm tra)",
        "role": UserRole.INSPECTOR.value,
        "org_id": None,
        "org_name": None,
        "org_code": None,
    },
    {
        "id": 106,
        "email": "sysadmin@nongsanlanh.gov.vn",
        "full_name": "Quản Trị Hệ Thống Toàn Nền Tảng",
        "role": UserRole.SYSTEM_ADMIN.value,
        "org_id": None,
        "org_name": None,
        "org_code": None,
    },
]


def ensure_supply_chain_demo_users(db: Session):
    """Đảm bảo 6 tài khoản mẫu tương ứng 6 vai trò luôn có sẵn trong DB để demo."""
    for cfg in DEMO_USERS_CONFIG:
        if cfg["org_id"] and cfg["org_name"]:
            org = db.query(Organization).filter(Organization.id == cfg["org_id"]).first()
            if not org:
                org = Organization(
                    id=cfg["org_id"],
                    name=cfg["org_name"],
                    code=cfg["org_code"],
                )
                db.add(org)
                try:
                    db.flush()
                except SQLAlchemyError:
                    db.rollback()

        u = db.query(User).filter(User.email == cfg["email"]).first()
        if not u:
            new_u = User(
                email=cfg["email"],
                hashed_password=get_password_hash("pass123"),
                full_name=cfg["full_name"],
                role=cfg["role"],
                organization_id=cfg["org_id"],
                is_active=True,
                failed_attempts=0,
                locked_until=None,
            )
            db.add(new_u)
            try:
                db.commit()
            except SQLAlchemyError:
                db.rollback()
        else:
            if u.role != cfg["role"]:
                u.role = cfg["role"]
                try:
                    db.commit()
                except SQLAlchemyError:
                    db.rollback()


@router.post("/login", response_model=Token)
def login(
    login_data: UserLogin,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Đăng nhập hệ thống bằng email và mật khẩu (S-04 / T-08 / T-09 / T-10).
    - Mật khẩu được băm và xác thực bằng thuật toán argon2id.
    - Sai email hoặc sai mật khẩu trả về CÙNG MỘT câu thông báo lỗi duy nhất:
      'Email hoặc mật khẩu không chính xác.'
    - Đếm failed_attempts. Sau 5 lần sai liên tiếp, khóa tạm 15 phút.
    - Ở lần thứ 6 (chưa hết 15 phút), KỂ CẢ NHẬP ĐÚNG MẬT KHẨU vẫn từ chối và thông báo số phút còn lại.
    - Khi đăng nhập thành công (hoặc sau khi hết 15 phút), đặt lại failed_attempts = 0.
    - Cookie phiên có cờ HttpOnly và Secure.
    """
    ensure_supply_chain_demo_users(db)

    now = datetime.now(UTC)
    user = UserRepository.get_by_email(db, login_data.email)

    if user:
        locked_until = _normalize_dt(user.locked_until)
        # 1. Kiểm tra tài khoản có đang bị khóa tạm thời không
        if locked_until and locked_until > now:
            remaining_seconds = int((locked_until - now).total_seconds())
            remaining_minutes = max(1, math.ceil(remaining_seconds / 60))
            # KỂ CẢ KHI NHẬP ĐÚNG MẬT KHẨU: Vẫn phải từ chối đăng nhập (S-04, T-10)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Tài khoản đang bị khóa tạm thời do nhập sai mật khẩu quá nhiều lần. Vui lòng thử lại sau {remaining_minutes} phút.",
                headers={
                    "X-Locked-Until": locked_until.isoformat(),
                    "X-Remaining-Minutes": str(remaining_minutes),
                    "X-Failed-Attempts": str(user.failed_attempts or 0),
                },
            )

        # 2. Nếu đã hết thời gian khóa tạm: reset trạng thái khóa để cho phép thử
        if locked_until and locked_until <= now:
            user.locked_until = None
            user.failed_attempts = 0
            db.commit()

        # 3. Xác thực mật khẩu bằng argon2id
        is_password_valid = verify_password(login_data.password, user.hashed_password)

        if not is_password_valid:
            user.failed_attempts = (user.failed_attempts or 0) + 1
            if user.failed_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
                user.locked_until = now + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail=f"Tài khoản đã bị tạm khóa {settings.ACCOUNT_LOCKOUT_MINUTES} phút do nhập sai mật khẩu {settings.MAX_FAILED_LOGIN_ATTEMPTS} lần liên tiếp. Vui lòng thử lại sau {settings.ACCOUNT_LOCKOUT_MINUTES} phút.",
                    headers={
                        "X-Failed-Attempts": str(user.failed_attempts),
                        "X-Remaining-Minutes": str(settings.ACCOUNT_LOCKOUT_MINUTES),
                    },
                )
            else:
                db.commit()
                # CÙNG MỘT câu thông báo lỗi duy nhất ("Email hoặc mật khẩu không chính xác")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email hoặc mật khẩu không chính xác.",
                    headers={"X-Failed-Attempts": str(user.failed_attempts)},
                )

        # 4. Mật khẩu đúng: Kiểm tra tài khoản có bị admin vô hiệu hóa không
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản hiện đang bị vô hiệu hóa.",
            )

        # 5. Đăng nhập thành công -> Reset failed_attempts và locked_until
        user.failed_attempts = 0
        user.locked_until = None
        db.commit()

        access_token = create_access_token(
            subject=user.email,
            role=user.role,
            organization_id=user.organization_id,
        )

        # Đặt cookie phiên có cờ HttpOnly và Secure khi chạy HTTPS/Production/Staging
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite="lax",
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
        )


        return Token(
            access_token=access_token,
            token_type="bearer",
            role=user.role,
            organization_id=user.organization_id,
            user_email=user.email,
            full_name=user.full_name,
        )

    # 6. Email không tồn tại: Trả về cùng một câu lỗi duy nhất, không tiết lộ sự tồn tại của email
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email hoặc mật khẩu không chính xác.",
    )


@router.post("/simulate-lockout")
def simulate_lockout(
    payload: SimulateLockoutRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Giả lập tài khoản nhập sai 5 lần liên tiếp để test tiêu chuẩn S-04 / T-10.
    Khóa tài khoản 15 phút.
    """
    ensure_supply_chain_demo_users(db)
    user = UserRepository.get_by_email(db, payload.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng với email này.",
        )

    now = datetime.now(UTC)
    user.failed_attempts = settings.MAX_FAILED_LOGIN_ATTEMPTS
    user.locked_until = now + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
    db.commit()

    return {
        "status": "success",
        "message": f"Đã giả lập khóa tài khoản {user.email} trong {settings.ACCOUNT_LOCKOUT_MINUTES} phút (5 lần sai).",
        "failed_attempts": user.failed_attempts,
        "locked_until": user.locked_until.isoformat(),
        "remaining_minutes": settings.ACCOUNT_LOCKOUT_MINUTES,
    }


@router.post("/reset-lockout")
def reset_lockout(
    payload: SimulateLockoutRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Mở khóa nhanh và reset số lần sai về 0 để tiếp tục test.
    """
    ensure_supply_chain_demo_users(db)
    user = UserRepository.get_by_email(db, payload.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng với email này.",
        )

    user.failed_attempts = 0
    user.locked_until = None
    db.commit()

    return {
        "status": "success",
        "message": f"Đã mở khóa và đặt lại số lần sai cho {user.email}.",
        "failed_attempts": 0,
        "is_locked": False,
    }


@router.get("/lockout-status", response_model=LockoutStatusResponse)
def get_lockout_status(
    email: str = Query(..., description="Email cần kiểm tra trạng thái khóa"),
    db: Annotated[Session, Depends(get_db)] = None,
):
    """Kiểm tra số lần nhập sai và thời gian khóa còn lại của email."""
    ensure_supply_chain_demo_users(db)
    user = UserRepository.get_by_email(db, email)
    if not user:
        return LockoutStatusResponse(
            email=email,
            failed_attempts=0,
            is_locked=False,
            remaining_minutes=None,
            locked_until=None,
        )

    now = datetime.now(UTC)
    locked_until = _normalize_dt(user.locked_until)
    is_locked = bool(locked_until and locked_until > now)
    remaining_minutes = None
    if is_locked and locked_until:
        rem_sec = int((locked_until - now).total_seconds())
        remaining_minutes = max(1, math.ceil(rem_sec / 60))

    return LockoutStatusResponse(
        email=user.email,
        failed_attempts=user.failed_attempts or 0,
        is_locked=is_locked,
        remaining_minutes=remaining_minutes,
        locked_until=user.locked_until,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    """Xem thông tin tài khoản hiện tại (kiểm tra trạng thái phiên làm việc)."""
    return current_user


@router.post("/logout")
def logout(response: Response):
    """
    Đăng xuất an toàn: Hủy cookie phiên access_token.
    """
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="lax",
        path="/",
    )
    return {"status": "success", "message": "Đăng xuất thành công và đã hủy cookie phiên."}


@router.post("/quick-role-token", response_model=Token)
def get_quick_role_token(
    role: str = Query(..., description="Vai trò cần chuyển đổi trong 7 vai trò"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    """
    Tiện ích chuyển đổi nhanh phiên làm việc giữa các vai trò demo cho môi trường học tập/phát triển:
    Yêu cầu bảo mật:
    1. Chỉ bật khi APP_ENV=development VÀ ENABLE_DEMO_ROLE_SWITCH=true. Mặc định luôn tắt.
    2. Tuyệt đối không hỗ trợ ở môi trường staging và production (403 Forbidden).
    3. Không cho phép người chưa đăng nhập tự cấp token cho bất kỳ tài khoản nào (401 Unauthorized).
    4. Không cho phép endpoint demo cấp quyền quản trị (system_admin) mà chưa qua xác thực chuẩn (403 Forbidden).
    """
    if settings.APP_ENV != "development" or not settings.ENABLE_DEMO_ROLE_SWITCH:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tính năng chuyển vai trò demo đã bị vô hiệu hóa vì lý do an toàn bảo mật. Vui lòng đăng nhập qua /api/v1/auth/login.",
        )

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Yêu cầu xác thực danh tính trước khi sử dụng tính năng chuyển đổi vai trò.",
        )

    ensure_supply_chain_demo_users(db)
    role_normalized = role.lower().strip()
    ROLE_ALIASES = {
        "farm": UserRole.FARM.value,
        "farmer": UserRole.FARM.value,
        "farm_owner": UserRole.FARM.value,
        "vung_trong": UserRole.FARM.value,
        "coop": UserRole.COOP.value,
        "processing": UserRole.COOP.value,
        "processing_coop": UserRole.COOP.value,
        "htx": UserRole.COOP.value,
        "so_che": UserRole.COOP.value,
        "logistics": UserRole.LOGISTICS.value,
        "van_tai": UserRole.LOGISTICS.value,
        "distributor": UserRole.DISTRIBUTOR.value,
        "retailer": UserRole.DISTRIBUTOR.value,
        "ban_le": UserRole.DISTRIBUTOR.value,
        "phan_phoi": UserRole.DISTRIBUTOR.value,
        "inspector": UserRole.INSPECTOR.value,
        "kiem_tra": UserRole.INSPECTOR.value,
        "thanh_tra": UserRole.INSPECTOR.value,
        "system_admin": UserRole.SYSTEM_ADMIN.value,
        "admin": UserRole.SYSTEM_ADMIN.value,
        "quan_tri": UserRole.SYSTEM_ADMIN.value,
    }
    target_role = ROLE_ALIASES.get(role_normalized, role_normalized)

    # Tuyệt đối cấm cấp token vai trò quản trị qua demo endpoint
    if target_role in (UserRole.SYSTEM_ADMIN.value, "system_admin", "admin", "quan_tri"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không được phép cấp quyền quản trị hệ thống (system_admin) qua endpoint demo. Quản trị viên bắt buộc phải đăng nhập qua quy trình xác thực chuẩn.",
        )

    target_config = None
    for cfg in DEMO_USERS_CONFIG:
        if cfg["role"] == target_role:
            target_config = cfg
            break

    if not target_config:
        target_config = DEMO_USERS_CONFIG[0]

    user = UserRepository.get_by_email(db, target_config["email"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy tài khoản demo cho vai trò {role}.",
        )

    access_token = create_access_token(
        subject=user.email,
        role=user.role,
        organization_id=user.organization_id,
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        organization_id=user.organization_id,
        user_email=user.email,
        full_name=user.full_name,
    )


