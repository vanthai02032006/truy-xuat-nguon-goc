import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.v1 import api_v1_router
from app.api.v1.batches import get_public_batch_trace
from app.core.config import settings
from app.schemas.batch import PublicBatchTraceResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Tự động kiểm tra và nạp dữ liệu mẫu ban đầu nếu DB đang trống khi khởi động."""
    import os

    if not os.getenv("PYTEST_CURRENT_TEST") and os.getenv("TESTING") != "1":
        try:
            from app.services.database_seeder import seed_database_if_empty

            seed_database_if_empty()
        except Exception as e:  # noqa: BLE001
            logger.warning("Khởi động: Bỏ qua tự động seed DB: %s", e)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# 1. Cấu hình Trusted Host Middleware (DuckDNS, VPS IP, localhost, wildcard)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)

# 2. Cấu hình CORS Middleware (DuckDNS HTTP & HTTPS, CSRF Trusted Origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Cấu hình Tenant Isolation Middleware (Epic E-02: Cô lập dữ liệu theo Organization ID & Inspector Read-only)
from app.middlewares.tenant_isolation import TenantIsolationMiddleware

app.add_middleware(TenantIsolationMiddleware)

# 4. Gắn router API v1
app.include_router(api_v1_router)

# Đường dẫn tới file SPA giao diện tĩnh
STATIC_SPA_PATH = Path(__file__).resolve().parent.parent / "static" / "index.html"


@app.get("/", include_in_schema=False)
def home(request: Request, format: str | None = None):
    """
    Tự động chuyển hướng (HTTP 302) từ route gốc / sang giao diện ứng dụng /app/.
    Hỗ trợ trả về JSON nếu client yêu cầu rõ ràng qua ?format=json.
    """
    if format == "json" or request.headers.get("x-format") == "json":
        return {
            "project": "Truy xuất nguồn gốc và giám sát chuỗi lạnh nông sản",
            "team": "Khối 18 N4",
            "status": "ok",
        }
    return RedirectResponse(
        url=settings.DEFAULT_APP_REDIRECT,
        status_code=status.HTTP_302_FOUND,
    )


@app.get("/health")
def health():
    """Endpoint kiểm tra sức khỏe hệ thống (Health Check) phục vụ Docker và CI/CD."""
    return {"status": "ok"}


@app.get("/app", response_class=HTMLResponse, include_in_schema=False)
@app.get("/app/", response_class=HTMLResponse)
@app.get("/spa", response_class=HTMLResponse, include_in_schema=False)
@app.get("/spa/", response_class=HTMLResponse, include_in_schema=False)
def get_spa_interface():
    """Phục vụ trực tiếp giao diện Nông Sản Lành (Single-File SPA)."""
    if STATIC_SPA_PATH.exists():
        return FileResponse(STATIC_SPA_PATH)
    return HTMLResponse("<h3>Giao diện đang được cập nhật. Vui lòng thử lại sau.</h3>")


@app.get(
    "/public/batches/{batch_code}",
    response_model=PublicBatchTraceResponse,
    tags=["Public"],
)
@app.get(
    "/api/v1/public/batches/{batch_code}",
    response_model=PublicBatchTraceResponse,
    tags=["Public"],
)
def get_public_batch_trace_global(
    batch_code: str,
    db: Annotated[Session, Depends(get_db)],
):
    """API Tra cứu công khai nguồn gốc lô hàng theo mã định danh (S-48 / S-50)."""
    return get_public_batch_trace(batch_code=batch_code, db=db)

