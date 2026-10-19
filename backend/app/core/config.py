import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    PROJECT_NAME: str = "Truy xuất nguồn gốc và giám sát chuỗi lạnh nông sản"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "farm_db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "farm_user")
    POSTGRES_PASSWORD: str = os.getenv(
        "POSTGRES_PASSWORD", "replace_with_a_local_secret"
    )
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@localhost:5432/{POSTGRES_DB}",
    )
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))

    # Security & JWT
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "truyxuatnguongoc-super-secret-key-s05-2026"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day


settings = Settings()
