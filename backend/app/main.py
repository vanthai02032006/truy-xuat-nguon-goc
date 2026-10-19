from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)


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
