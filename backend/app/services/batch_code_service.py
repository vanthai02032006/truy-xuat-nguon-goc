from __future__ import annotations

import secrets
from typing import Final

from sqlalchemy.orm import Session

from app.models.batch import Batch

# Bảng chữ cái an toàn gồm 31 ký tự:
# - Chữ số: '2'..'9' (đã loại bỏ '0' và '1')
# - Chữ cái in hoa: A-Z (đã loại bỏ 'O', 'I', 'L')
SAFE_ALPHABET: Final[str] = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"

# Tập hợp các ký tự cấm dễ gây nhầm lẫn khi đọc hoặc gõ tay
FORBIDDEN_CHARS: Final[frozenset[str]] = frozenset("0O1IL0o1il")

DEFAULT_CODE_LENGTH: Final[int] = 8


def generate_secure_batch_code(length: int = DEFAULT_CODE_LENGTH) -> str:
    """
    Sinh mã lô ngẫu nhiên an toàn (cryptographically secure random).
    - Độ dài: mặc định đúng 8 ký tự.
    - Ký tự: chỉ lấy từ SAFE_ALPHABET (31 ký tự), loại trừ hoàn toàn '0', 'O', '1', 'I', 'L'.
    - Không gian mẫu: 31^8 ≈ 852.891.456.281 (852 tỷ) tổ hợp khả dĩ.
    """
    return "".join(secrets.choice(SAFE_ALPHABET) for _ in range(length))


def is_valid_batch_code(code: str, length: int = DEFAULT_CODE_LENGTH) -> bool:
    """
    Kiểm tra tính hợp lệ của mã lô:
    - Đúng độ dài quy định (8 ký tự).
    - Không chứa bất kỳ ký tự cấm nào ('0', 'O', '1', 'I', 'L').
    - Toàn bộ ký tự phải thuộc SAFE_ALPHABET.
    """
    if not isinstance(code, str) or len(code) != length:
        return False
    if any(char in FORBIDDEN_CHARS for char in code):
        return False
    return all(char in SAFE_ALPHABET for char in code)


def generate_unique_batch_code(db: Session, max_retries: int = 20) -> str:
    """
    Sinh mã lô hàng ngẫu nhiên an toàn và đảm bảo UNIQUE ở tầng cơ sở dữ liệu.
    Nếu mã sinh ra vô tình trùng với mã đã tồn tại trong DB, hàm sẽ tự động thử sinh lại.
    """
    for _ in range(max_retries):
        code = generate_secure_batch_code(DEFAULT_CODE_LENGTH)
        # Kiểm tra sự tồn tại trong database
        exists = (
            db.query(Batch.id).filter(Batch.batch_code == code).first() is not None
        )
        if not exists:
            return code

    raise RuntimeError(
        f"Không thể sinh mã lô duy nhất sau {max_retries} lần thử liên tiếp."
    )
