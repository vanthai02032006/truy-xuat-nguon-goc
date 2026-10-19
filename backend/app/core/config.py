from __future__ import annotations

import os
from dataclasses import dataclass, field


def _parse_comma_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


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
    APP_PORT: int = int(os.getenv("APP_PORT", "80"))

    # Security & JWT
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY", "truyxuatnguongoc-super-secret-key-s05-2026"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Tên miền DuckDNS & Mạng
    ALLOWED_HOSTS: list[str] = field(
        default_factory=lambda: _parse_comma_list(
            os.getenv(
                "ALLOWED_HOSTS",
                "nong-san-lanh-k18-n4.duckdns.org,160.191.245.209,localhost,127.0.0.1,*",
            )
        )
    )

    CSRF_TRUSTED_ORIGINS: list[str] = field(
        default_factory=lambda: _parse_comma_list(
            os.getenv(
                "CSRF_TRUSTED_ORIGINS",
                "http://nong-san-lanh-k18-n4.duckdns.org,https://nong-san-lanh-k18-n4.duckdns.org,http://160.191.245.209",
            )
        )
    )

    CORS_ORIGINS: list[str] = field(
        default_factory=lambda: _parse_comma_list(
            os.getenv(
                "CORS_ORIGINS",
                "http://nong-san-lanh-k18-n4.duckdns.org,https://nong-san-lanh-k18-n4.duckdns.org,http://160.191.245.209,http://localhost,http://localhost:80,http://localhost:8000,http://localhost:3000,*",
            )
        )
    )

    DEFAULT_APP_REDIRECT: str = "/app/"


settings = Settings()
