from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse

from app.api.v1 import api_v1_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

# Gắn router API v1
app.include_router(api_v1_router)

# Đường dẫn tới file SPA giao diện tĩnh
STATIC_SPA_PATH = Path(__file__).resolve().parent.parent / "static" / "index.html"


@app.get("/")
def home():
    return {
        "project": "Truy xuất nguồn gốc và giám sát chuỗi lạnh nông sản",
        "team": "Khối 18 N4",
        "status": "ok",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/app", response_class=HTMLResponse)
@app.get("/spa", response_class=HTMLResponse)
def get_spa_interface():
    """Phục vụ trực tiếp giao diện Nông Sản Lành (Single-File SPA) ngay trên cổng 8000."""
    if STATIC_SPA_PATH.exists():
        return FileResponse(STATIC_SPA_PATH)
    return HTMLResponse("<h3>Giao diện đang được cập nhật. Vui lòng thử lại sau.</h3>")
