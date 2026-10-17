from fastapi import FastAPI

app = FastAPI(
    title="Truy xuất nguồn gốc và giám sát chuỗi lạnh nông sản",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "project": "Truy xuất nguồn gốc và giám sát chuỗi lạnh nông sản",
        "team": "Khối 18 N4",
        "status": "ok"
    }


@app.get("/health")
def health():
    return {"status": "ok"}

