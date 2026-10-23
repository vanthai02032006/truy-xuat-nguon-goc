"""
User Story S-50: giới hạn tần suất tra cứu công khai để chống dò quét mã lô.

Một địa chỉ IP tra cứu quá 30 mã lô KHÁC NHAU trong 60 giây thì bị chặn tạm.
Mã không tồn tại cũng được đếm (kiểm tra trước khi truy vấn cơ sở dữ liệu).
Tra lại một mã đã tra trong cửa sổ thời gian thì không bị tính thêm.
"""

from __future__ import annotations

import threading
import time


class PublicLookupRateLimiter:
    def __init__(self, max_distinct_codes: int = 30, window_seconds: float = 60.0):
        self.max_distinct_codes = max_distinct_codes
        self.window_seconds = window_seconds
        self._hits: dict[str, dict[str, float]] = {}
        self._lock = threading.Lock()

    def allow(self, client_key: str, batch_code: str) -> bool:
        now = time.monotonic()
        code = (batch_code or "").strip().upper()
        with self._lock:
            # Dọn các IP đã hết hạn để bộ nhớ không phình theo thời gian
            for key in [k for k, codes in self._hits.items() if not codes or max(codes.values()) < now - self.window_seconds]:
                del self._hits[key]

            codes = self._hits.setdefault(client_key, {})
            for old_code in [c for c, t in codes.items() if t < now - self.window_seconds]:
                del codes[old_code]

            if code in codes:
                codes[code] = now
                return True
            if len(codes) >= self.max_distinct_codes:
                return False
            codes[code] = now
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


public_lookup_limiter = PublicLookupRateLimiter()
