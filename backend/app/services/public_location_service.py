"""
User Story S-60: vị trí hiển thị trên bản đồ công khai.

Bản đồ công khai chỉ được ghim ở mức xã/huyện hoặc tỉnh, không lộ toạ độ chính xác của thửa đất:
- Toạ độ thửa đất (S-06) được làm tròn 2 chữ số thập phân (~1 km).
- Điểm phân phối chỉ có địa chỉ chữ, nên được ghim tại trung tâm tỉnh/thành nhận ra từ địa chỉ.
"""

from __future__ import annotations

import re
import unicodedata

PUBLIC_COORD_DECIMALS = 2

# Trung tâm hành chính (tỉnh lỵ) của các tỉnh/thành, kèm tên gọi thường gặp trong địa chỉ.
_PROVINCE_CENTERS: list[tuple[str, tuple[str, ...], float, float]] = [
    ("TP. Hồ Chí Minh", ("ho chi minh", "tp.hcm", "tphcm", "hcm", "sai gon"), 10.78, 106.70),
    ("Hà Nội", ("ha noi",), 21.03, 105.85),
    ("Hải Phòng", ("hai phong",), 20.86, 106.68),
    ("Đà Nẵng", ("da nang",), 16.05, 108.21),
    ("Cần Thơ", ("can tho",), 10.03, 105.78),
    ("Lâm Đồng", ("lam dong", "da lat", "bao loc", "duc trong", "lac duong"), 11.94, 108.44),
    ("Khánh Hòa", ("khanh hoa", "nha trang"), 12.24, 109.19),
    ("Đắk Lắk", ("dak lak", "dac lac", "buon ma thuot"), 12.67, 108.04),
    ("Đắk Nông", ("dak nong", "gia nghia"), 12.00, 107.69),
    ("Gia Lai", ("gia lai", "pleiku"), 13.98, 108.00),
    ("Kon Tum", ("kon tum",), 14.35, 108.00),
    ("Bình Thuận", ("binh thuan", "phan thiet"), 10.93, 108.10),
    ("Ninh Thuận", ("ninh thuan", "phan rang"), 11.57, 108.99),
    ("Phú Yên", ("phu yen", "tuy hoa"), 13.10, 109.30),
    ("Bình Định", ("binh dinh", "quy nhon"), 13.78, 109.22),
    ("Quảng Ngãi", ("quang ngai",), 15.12, 108.80),
    ("Quảng Nam", ("quang nam", "tam ky", "hoi an"), 15.57, 108.47),
    ("Huế", ("thua thien hue", "hue"), 16.46, 107.59),
    ("Quảng Trị", ("quang tri", "dong ha"), 16.82, 107.10),
    ("Quảng Bình", ("quang binh", "dong hoi"), 17.47, 106.62),
    ("Hà Tĩnh", ("ha tinh",), 18.34, 105.90),
    ("Nghệ An", ("nghe an", "tp vinh", "thanh pho vinh"), 18.68, 105.68),
    ("Thanh Hóa", ("thanh hoa",), 19.81, 105.78),
    ("Ninh Bình", ("ninh binh",), 20.25, 105.97),
    ("Nam Định", ("nam dinh",), 20.43, 106.16),
    ("Thái Bình", ("thai binh",), 20.45, 106.34),
    ("Hà Nam", ("ha nam", "phu ly"), 20.54, 105.91),
    ("Hưng Yên", ("hung yen",), 20.65, 106.05),
    ("Hải Dương", ("hai duong",), 20.94, 106.33),
    ("Bắc Ninh", ("bac ninh",), 21.18, 106.06),
    ("Bắc Giang", ("bac giang",), 21.27, 106.19),
    ("Quảng Ninh", ("quang ninh", "ha long"), 20.95, 107.08),
    ("Lạng Sơn", ("lang son",), 21.85, 106.76),
    ("Cao Bằng", ("cao bang",), 22.67, 106.26),
    ("Bắc Kạn", ("bac kan", "bac can"), 22.15, 105.83),
    ("Thái Nguyên", ("thai nguyen",), 21.59, 105.85),
    ("Tuyên Quang", ("tuyen quang",), 21.82, 105.21),
    ("Hà Giang", ("ha giang",), 22.82, 104.98),
    ("Lào Cai", ("lao cai", "sa pa"), 22.48, 103.97),
    ("Yên Bái", ("yen bai",), 21.72, 104.91),
    ("Phú Thọ", ("phu tho", "viet tri"), 21.32, 105.40),
    ("Vĩnh Phúc", ("vinh phuc", "vinh yen"), 21.31, 105.60),
    ("Hòa Bình", ("hoa binh",), 20.82, 105.34),
    ("Sơn La", ("son la", "moc chau"), 21.33, 103.91),
    ("Điện Biên", ("dien bien",), 21.39, 103.02),
    ("Lai Châu", ("lai chau",), 22.40, 103.47),
    ("Đồng Nai", ("dong nai", "bien hoa"), 10.95, 106.82),
    ("Bình Dương", ("binh duong", "thu dau mot"), 10.98, 106.65),
    ("Bình Phước", ("binh phuoc", "dong xoai"), 11.53, 106.89),
    ("Tây Ninh", ("tay ninh",), 11.31, 106.10),
    ("Bà Rịa - Vũng Tàu", ("ba ria", "vung tau"), 10.50, 107.17),
    ("Long An", ("long an", "tan an"), 10.54, 106.41),
    ("Tiền Giang", ("tien giang", "my tho"), 10.36, 106.36),
    ("Bến Tre", ("ben tre",), 10.24, 106.38),
    ("Trà Vinh", ("tra vinh",), 9.93, 106.35),
    ("Vĩnh Long", ("vinh long",), 10.25, 105.97),
    ("Đồng Tháp", ("dong thap", "cao lanh"), 10.46, 105.63),
    ("An Giang", ("an giang", "long xuyen"), 10.39, 105.44),
    ("Kiên Giang", ("kien giang", "rach gia", "phu quoc"), 10.01, 105.08),
    ("Hậu Giang", ("hau giang", "vi thanh"), 9.78, 105.47),
    ("Sóc Trăng", ("soc trang",), 9.60, 105.97),
    ("Bạc Liêu", ("bac lieu",), 9.29, 105.72),
    ("Cà Mau", ("ca mau",), 9.18, 105.15),
]


def _normalize(text: str) -> str:
    """Bỏ dấu tiếng Việt, chữ thường, gom khoảng trắng để so khớp tên địa danh."""
    text = (text or "").replace("Đ", "D").replace("đ", "d")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.lower()).strip()


def resolve_province_center(address: str | None) -> tuple[str, float, float] | None:
    """
    Nhận ra tỉnh/thành trong địa chỉ chữ và trả về (tên tỉnh, vĩ độ, kinh độ) của trung tâm tỉnh.
    Địa chỉ Việt Nam ghi tỉnh ở cuối, nên ưu tiên tên xuất hiện sau cùng.
    """
    norm = _normalize(address or "")
    if not norm:
        return None
    best: tuple[int, str, float, float] | None = None
    for display, aliases, lat, lng in _PROVINCE_CENTERS:
        for alias in aliases:
            for m in re.finditer(r"(?<![a-z])" + re.escape(alias) + r"(?![a-z])", norm):
                if best is None or m.start() > best[0]:
                    best = (m.start(), display, lat, lng)
    if best is None:
        return None
    return best[1], best[2], best[3]


def round_public_coordinate(value: float) -> float:
    """Làm tròn toạ độ thửa đất tới mức xã/huyện cho bản đồ công khai."""
    return round(float(value), PUBLIC_COORD_DECIMALS)
