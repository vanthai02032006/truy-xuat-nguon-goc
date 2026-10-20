from __future__ import annotations

import re
from collections.abc import Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import SessionLocal
from app.core.security import decode_access_token
from app.models.user import UserRole
from app.repositories.batch_repository import BatchRepository
from app.repositories.land_plot_repository import LandPlotRepository
from app.repositories.security_log_repository import SecurityLogRepository
from app.repositories.user_repository import UserRepository

# Regex patterns nhận diện các API thao tác tài nguyên đơn lẻ
BATCH_DETAIL_REGEX = re.compile(r"^/api/v1/batches/(\d+)(?:/.*)?$")
LAND_PLOT_DETAIL_REGEX = re.compile(r"^/api/v1/land-plots/(\d+)(?:/.*)?$")


def _get_db_session():
    """Lấy DB session, tương thích với FastAPI dependency override trong kiểm thử."""
    from app.api.deps import get_db
    from app.main import app

    override = app.dependency_overrides.get(get_db)
    if override is not None:
        result = override()
        if hasattr(result, "__next__"):
            return next(result), False
        return result, False
    return SessionLocal(), True


class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """
    Middleware cô lập dữ liệu theo Organization ID (Backlog Epic E-02 / S-05):
    1. Mỗi tổ chức độc lập trong chuỗi cung ứng chỉ được xem và thao tác trên
       các lô hàng/thửa đất thuộc quyền quản lý của tổ chức mình.
    2. Cố tình gọi API lấy dữ liệu của tổ chức khác -> Trả về HTTP 403 Forbidden
       và ghi nhận ngay vào bảng SecurityLog (nhật ký an ninh).
    3. Riêng vai trò "Cán bộ kiểm tra" (Inspector) có quyền tra cứu (GET) lô của
       mọi tổ chức nhưng CHỈ Ở CHẾ ĐỘ READ-ONLY. Cố tình tạo/sửa/xóa (POST, PUT, DELETE)
       sẽ bị trả về HTTP 403 Forbidden và ghi log an ninh vi phạm quyền kiểm tra.
    4. Người tiêu dùng (Consumer) tra cứu công khai tại /api/v1/batches/public/{batch_code}
       không bị chặn và không yêu cầu đăng nhập.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path
        method = request.method

        # 1. Bỏ qua các đường dẫn công khai (Public routes bypass)
        if (
            path in ["/", "/health", "/spa", "/spa/", "/app", "/app/"]
            or path.startswith(
                (
                    "/static/",
                    "/docs",
                    "/redoc",
                    "/openapi.json",
                    "/api/v1/auth/login",
                    "/api/v1/batches/public/",
                )
            )
            or method == "OPTIONS"
        ):
            return await call_next(request)

        # 2. Trích xuất Authorization Bearer token hoặc HttpOnly Cookie
        token: str | None = None
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
        elif "access_token" in request.cookies:
            token = request.cookies.get("access_token")

        # Nếu không có token, cho request đi tiếp để Dependency get_current_user xử lý HTTP 401
        if not token:
            return await call_next(request)

        # 3. Giải mã token để lấy ngữ cảnh người dùng & tổ chức
        payload = decode_access_token(token)
        if not payload or "sub" not in payload:
            return await call_next(request)

        user_email = payload.get("sub")
        user_role = str(payload.get("role", "")).lower()
        user_org_id = payload.get("organization_id")
        if user_org_id is None:
            user_org_id = payload.get("org_id")

        # Lưu thông tin tenant context vào request.state phục vụ các hàm xử lý bên dưới
        request.state.user_email = user_email
        request.state.user_role = user_role
        request.state.tenant_org_id = user_org_id

        client_ip = request.client.host if request.client else "unknown"

        # 4. Kiểm tra Cán bộ kiểm tra (Inspector) cố tình tạo mới lô hàng
        if path == "/api/v1/batches" and method == "POST" and user_role == UserRole.INSPECTOR.value:
            db, should_close = _get_db_session()
            try:
                user_obj = UserRepository.get_by_email(db, user_email)
                current_uid = user_obj.id if user_obj else None
                SecurityLogRepository.log_attempt(
                    db=db,
                    user_id=current_uid,
                    user_email=user_email,
                    user_org_id=user_org_id,
                    attempt_type="inspector_write_violation",
                    target_resource="batch",
                    target_id="new_batch",
                    target_org_id=None,
                    endpoint=path,
                    method=method,
                    ip_address=client_ip,
                    description="Cán bộ kiểm tra cố gắng tạo mới lô hàng (chỉ được phép đọc).",
                )
            finally:
                if should_close:
                    db.close()

            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Cán bộ kiểm tra chỉ có quyền xem dữ liệu (chế độ chỉ đọc)."},
            )

        # 5. Kiểm tra tài nguyên Lô hàng cụ thể: /api/v1/batches/{batch_id}...
        batch_match = BATCH_DETAIL_REGEX.match(path)
        if batch_match:
            try:
                target_batch_id = int(batch_match.group(1))
            except ValueError:
                target_batch_id = None

            if target_batch_id:
                db, should_close = _get_db_session()
                try:
                    user_obj = UserRepository.get_by_email(db, user_email)
                    current_uid = user_obj.id if user_obj else None
                    if user_obj and user_org_id is None:
                        user_org_id = user_obj.organization_id

                    batch = BatchRepository.get_by_id(db, target_batch_id)
                    if batch:
                        # 5.1 Trường hợp là Cán bộ kiểm tra (Inspector)
                        if user_role == UserRole.INSPECTOR.value:
                            if method not in ["GET", "HEAD", "OPTIONS"]:
                                SecurityLogRepository.log_attempt(
                                    db=db,
                                    user_id=current_uid,
                                    user_email=user_email,
                                    user_org_id=user_org_id,
                                    attempt_type="inspector_write_violation",
                                    target_resource="batch",
                                    target_id=str(batch.id),
                                    target_org_id=batch.organization_id,
                                    endpoint=path,
                                    method=method,
                                    ip_address=client_ip,
                                    description="Cán bộ kiểm tra cố gắng thực hiện thao tác ghi/sửa/xóa trên lô hàng (chỉ được phép đọc).",
                                )
                                return JSONResponse(
                                    status_code=status.HTTP_403_FORBIDDEN,
                                    content={
                                        "detail": "Cán bộ kiểm tra chỉ có quyền xem dữ liệu (chế độ chỉ đọc)."
                                    },
                                )
                            # Cho phép Inspector đọc dữ liệu của mọi tổ chức
                            return await call_next(request)

                        # 5.2 Trường hợp là Quản trị hệ thống (System Admin)
                        if user_role in [UserRole.SYSTEM_ADMIN.value, UserRole.ADMIN.value, "system_admin", "admin"]:
                            return await call_next(request)

                        # 5.3 Trường hợp là thành viên chuỗi cung ứng (Farm, Processing, Logistics, Retailer,...)
                        if batch.organization_id != user_org_id:
                            SecurityLogRepository.log_attempt(
                                db=db,
                                user_id=current_uid,
                                user_email=user_email,
                                user_org_id=user_org_id,
                                attempt_type="cross_tenant_access_denied",
                                target_resource="batch",
                                target_id=str(batch.id),
                                target_org_id=batch.organization_id,
                                endpoint=path,
                                method=method,
                                ip_address=client_ip,
                                description=(
                                    f"Người dùng {user_email} (Tổ chức {user_org_id}) "
                                    f"cố tình gọi API truy cập lô #{batch.id} của Tổ chức {batch.organization_id}."
                                ),
                            )
                            return JSONResponse(
                                status_code=status.HTTP_403_FORBIDDEN,
                                content={"detail": "Không có quyền truy cập dữ liệu của tổ chức khác."},
                            )
                finally:
                    if should_close:
                        db.close()

        # 6. Kiểm tra tài nguyên Thửa đất cụ thể: /api/v1/land-plots/{plot_id}...
        plot_match = LAND_PLOT_DETAIL_REGEX.match(path)
        if plot_match:
            try:
                target_plot_id = int(plot_match.group(1))
            except ValueError:
                target_plot_id = None

            if target_plot_id:
                db, should_close = _get_db_session()
                try:
                    user_obj = UserRepository.get_by_email(db, user_email)
                    current_uid = user_obj.id if user_obj else None
                    if user_obj and user_org_id is None:
                        user_org_id = user_obj.organization_id

                    plot = LandPlotRepository.get_by_id(db, target_plot_id)
                    if plot:
                        # 6.1 Trường hợp là Cán bộ kiểm tra
                        if user_role == UserRole.INSPECTOR.value:
                            if method not in ["GET", "HEAD", "OPTIONS"]:
                                SecurityLogRepository.log_attempt(
                                    db=db,
                                    user_id=current_uid,
                                    user_email=user_email,
                                    user_org_id=user_org_id,
                                    attempt_type="inspector_write_violation",
                                    target_resource="land_plot",
                                    target_id=str(plot.id),
                                    target_org_id=plot.organization_id,
                                    endpoint=path,
                                    method=method,
                                    ip_address=client_ip,
                                    description="Cán bộ kiểm tra cố gắng thực hiện thao tác ghi/sửa/xóa trên thửa đất (chỉ được phép đọc).",
                                )
                                return JSONResponse(
                                    status_code=status.HTTP_403_FORBIDDEN,
                                    content={
                                        "detail": "Cán bộ kiểm tra chỉ có quyền xem dữ liệu (chế độ chỉ đọc)."
                                    },
                                )
                            return await call_next(request)

                        # 6.2 Quản trị hệ thống
                        if user_role in [UserRole.SYSTEM_ADMIN.value, UserRole.ADMIN.value, "system_admin", "admin"]:
                            return await call_next(request)

                        # 6.3 Người dùng tổ chức khác
                        if plot.organization_id != user_org_id:
                            SecurityLogRepository.log_attempt(
                                db=db,
                                user_id=current_uid,
                                user_email=user_email,
                                user_org_id=user_org_id,
                                attempt_type="cross_tenant_access_denied",
                                target_resource="land_plot",
                                target_id=str(plot.id),
                                target_org_id=plot.organization_id,
                                endpoint=path,
                                method=method,
                                ip_address=client_ip,
                                description=(
                                    f"Người dùng {user_email} (Tổ chức {user_org_id}) "
                                    f"cố tình gọi API truy cập thửa đất #{plot.id} của Tổ chức {plot.organization_id}."
                                ),
                            )
                            return JSONResponse(
                                status_code=status.HTTP_403_FORBIDDEN,
                                content={"detail": "Không có quyền truy cập dữ liệu thửa đất của tổ chức khác."},
                            )
                finally:
                    if should_close:
                        db.close()

        # Thực thi tiếp chuỗi middleware và gán header xác nhận cô lập tenant
        response = await call_next(request)
        response.headers["X-Tenant-Isolation"] = "enforced"
        return response
