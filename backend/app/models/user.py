import enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UserRole(str, enum.Enum):
    # 6 Vai trò chuẩn hóa trong toàn hệ thống (Epic E-02):
    FARM = "farm"                  # Vùng trồng (Farm)
    COOP = "coop"                  # Hợp tác xã sơ chế (Co-op / Processing)
    LOGISTICS = "logistics"        # Đơn vị vận chuyển lạnh (Logistics / Cold Chain Transporter)
    DISTRIBUTOR = "distributor"    # Nhà phân phối / Bán lẻ (Distributor / Retailer)
    INSPECTOR = "inspector"        # Cán bộ kiểm tra (Inspector - Read-only toàn hệ thống)
    SYSTEM_ADMIN = "system_admin"  # Quản trị hệ thống (System Admin)
    CONSUMER = "consumer"          # Người tiêu dùng (Consumer - không cần đăng nhập)

    # Vai trò kế thừa / tương thích ngược
    PROCESSING = "processing"
    RETAILER = "retailer"
    ADMIN = "admin"
    FARM_OWNER = "farm_owner"
    SUPERVISOR = "supervisor"
    OWNER = "owner"
    FIELD_MANAGER = "field_manager"
    MEMBER = "member"
    FARMER = "farmer"
    VUNG_TRONG = "vung_trong"


# 6 Vai trò chuẩn hóa chuỗi cung ứng chính thức
STANDARDIZED_ROLES = {
    UserRole.FARM.value,
    UserRole.COOP.value,
    UserRole.LOGISTICS.value,
    UserRole.DISTRIBUTOR.value,
    UserRole.INSPECTOR.value,
    UserRole.SYSTEM_ADMIN.value,
}

# Danh mục các vai trò được chấp nhận trong chuỗi cung ứng (bao gồm alias)
SUPPLY_CHAIN_ROLES = STANDARDIZED_ROLES | {
    UserRole.CONSUMER.value,
    "processing",
    "retailer",
    "admin",
    "farm_owner",
    "supervisor",
    "owner",
}


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=False)
    role = Column(String(50), default=UserRole.MEMBER.value, nullable=False)
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    failed_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    organization = relationship("Organization")
