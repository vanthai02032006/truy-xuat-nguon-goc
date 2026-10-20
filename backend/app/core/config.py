from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field


def _parse_comma_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass
class Settings:
    PROJECT_NAME: str = "Truy xuất nguồn gốc và giám sát chuỗi lạnh nông sản"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Môi trường chạy (development, staging, production, testing)
    APP_ENV: str = field(
        default_factory=lambda: os.getenv("APP_ENV", "development").lower()
    )

    # Cờ bật tắt tính năng chuyển đổi vai trò demo:
    # Mặc định luôn là FALSE. Chỉ được phép bật ở development khi ENABLE_DEMO_ROLE_SWITCH=true.
    # Ở staging và production, cờ này LUÔN LUÔN bị ép thành False.
    ENABLE_DEMO_ROLE_SWITCH: bool = field(
        default_factory=lambda: (
            os.getenv("APP_ENV", "development").lower() == "development"
            and os.getenv("ENABLE_DEMO_ROLE_SWITCH", "false").lower() in ("true", "1")
        )
    )

    # Database
    POSTGRES_DB: str = field(default_factory=lambda: os.getenv("POSTGRES_DB", "farm_db"))
    POSTGRES_USER: str = field(default_factory=lambda: os.getenv("POSTGRES_USER", "farm_user"))
    POSTGRES_PASSWORD: str = field(default_factory=lambda: os.getenv("POSTGRES_PASSWORD", ""))

    DATABASE_URL: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            (
                "sqlite:///:memory:"
                if (
                    "pytest" in sys.modules
                    or os.getenv("PYTEST_CURRENT_TEST")
                    or os.getenv("TESTING") == "1"
                    or os.getenv("APP_ENV", "").lower() == "testing"
                )
                else (
                    f"postgresql+psycopg://{os.getenv('POSTGRES_USER', 'farm_user')}:{os.getenv('POSTGRES_PASSWORD', '')}@localhost:5432/{os.getenv('POSTGRES_DB', 'farm_db')}"
                    if os.getenv("POSTGRES_PASSWORD")
                    else ""
                )
            ),
        )
    )
    APP_PORT: int = field(default_factory=lambda: int(os.getenv("APP_PORT", "80")))

    # Security & JWT: Bắt buộc cung cấp trong production/staging. Trong test mode dùng mock key an toàn.
    SECRET_KEY: str = field(
        default_factory=lambda: os.getenv("SECRET_KEY")
        or (
            "test-secret-key-for-testing-only-32chars"
            if (
                "pytest" in sys.modules
                or os.getenv("PYTEST_CURRENT_TEST")
                or os.getenv("TESTING") == "1"
                or os.getenv("APP_ENV", "").lower() == "testing"
            )
            else ""
        )
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Cookie bảo mật
    COOKIE_SECURE: bool = field(
        default_factory=lambda: (
            os.getenv("APP_ENV", "development").lower() in ("production", "staging")
            or os.getenv("COOKIE_SECURE", "true").lower() in ("true", "1")
        )
    )

    # Chính sách khóa tài khoản khi đăng nhập sai nhiều lần (User Story S-04 / T-10)
    MAX_FAILED_LOGIN_ATTEMPTS: int = field(
        default_factory=lambda: int(os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5"))
    )
    ACCOUNT_LOCKOUT_MINUTES: int = field(
        default_factory=lambda: int(os.getenv("ACCOUNT_LOCKOUT_MINUTES", "15"))
    )

    # Tên miền DuckDNS & Mạng
    ALLOWED_HOSTS: list[str] = field(
        default_factory=lambda: _parse_comma_list(
            os.getenv(
                "ALLOWED_HOSTS",
                "nong-san-lanh-k18-n4.duckdns.org,160.191.245.209,localhost,127.0.0.1,testserver",
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
                "http://nong-san-lanh-k18-n4.duckdns.org,https://nong-san-lanh-k18-n4.duckdns.org,http://160.191.245.209,http://localhost,http://localhost:80,http://localhost:8000,http://localhost:3000",
            )
        )
    )

    DEFAULT_APP_REDIRECT: str = "/app/"

    @property
    def IS_TEST(self) -> bool:
        return bool(
            os.getenv("PYTEST_CURRENT_TEST")
            or os.getenv("TESTING") == "1"
            or self.APP_ENV == "testing"
        )

    @property
    def masked_database_url(self) -> str:
        """Che giấu mật khẩu trong chuỗi kết nối database khi ghi log."""
        if not self.DATABASE_URL:
            return ""
        return re.sub(r":([^:@]+)@", r":***@", self.DATABASE_URL)

    def validate_required_env(self) -> None:
        """
        Kiểm tra tính hợp lệ và sự hiện diện của các biến môi trường bắt buộc:
        - Báo rõ biến môi trường bắt buộc nào bị thiếu và dừng khởi động an toàn.
        - Không cho phép giá trị mặc định không an toàn trong production/staging.
        - Không cho phép wildcard '*' trong production.
        """
        if self.IS_TEST:
            return

        missing = []

        # 1. Kiểm tra SECRET_KEY
        if not self.SECRET_KEY:
            missing.append("SECRET_KEY (Bắt buộc thiết lập chuỗi bí mật an toàn tối thiểu 32 ký tự)")
        elif self.APP_ENV in ("production", "staging"):
            insecure_keys = (
                "truyxuatnguongoc-super-secret-key-s05-2026",
                "replace_with_a_local_secret",
                "changeme",
                "secret",
                "GENERATE_A_RANDOM_SECRET_KEY_AT_LEAST_32_CHARS",
            )
            if self.SECRET_KEY in insecure_keys or len(self.SECRET_KEY) < 32:
                missing.append(
                    "SECRET_KEY (Không được sử dụng giá trị mẫu hoặc ngắn hơn 32 ký tự trong môi trường production/staging)"
                )

        # 2. Kiểm tra Database Password
        if not self.DATABASE_URL:
            if not self.POSTGRES_PASSWORD:
                missing.append("POSTGRES_PASSWORD (hoặc DATABASE_URL với mật khẩu hợp lệ)")
        else:
            if self.APP_ENV in ("production", "staging"):
                insecure_passwords = (
                    "replace_with_a_local_secret",
                    "YOUR_SECURE_POSTGRES_PASSWORD_HERE",
                )
                if any(p in self.DATABASE_URL for p in insecure_passwords):
                    missing.append(
                        "DATABASE_URL (Chứa mật khẩu mặc định không an toàn trong môi trường production/staging)"
                    )

        # 3. Kiểm tra Wildcard trong Allowed Hosts và CORS cho Production
        if self.APP_ENV == "production":
            if "*" in self.ALLOWED_HOSTS:
                missing.append("ALLOWED_HOSTS (Tuyệt đối không sử dụng wildcard '*' trong production)")
            if "*" in self.CORS_ORIGINS:
                missing.append("CORS_ORIGINS (Tuyệt đối không sử dụng wildcard '*' trong production)")

        if missing:
            err_msg = (
                "LỖI BẢO MẬT KHỞI ĐỘNG (P0): Các biến môi trường bắt buộc sau đây bị thiếu hoặc không an toàn:\n"
                + "\n".join(f"  - {m}" for m in missing)
            )
            raise RuntimeError(err_msg)


settings = Settings()

