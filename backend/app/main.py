from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.api.v1 import api_v1_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
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

# 3. Gắn router API v1
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
