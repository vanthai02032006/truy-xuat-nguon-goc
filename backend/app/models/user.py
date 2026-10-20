import enum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class UserRole(str, enum.Enum):
    # 7 Vai trò thuộc các tổ chức độc lập trong chuỗi cung ứng theo Epic E-02:
    FARM = "farm"  # Vùng trồng (Farm)
    PROCESSING = "processing"  # Hợp tác xã sơ chế (Processing Co-op)
    LOGISTICS = "logistics"  # Đơn vị vận chuyển lạnh (Logistics / Cold Chain Transporter)
    RETAILER = "retailer"  # Nhà phân phối / Bán lẻ (Distributor / Retailer)
    INSPECTOR = "inspector"  # Cán bộ kiểm tra (Inspector - Read-only toàn hệ thống)
    SYSTEM_ADMIN = "system_admin"  # Quản trị hệ thống (System Admin)
    CONSUMER = "consumer"  # Người tiêu dùng (Consumer - không cần đăng nhập)

    # Vai trò kế thừa / tương thích ngược
    ADMIN = "admin"
    FARM_OWNER = "farm_owner"
    SUPERVISOR = "supervisor"
    OWNER = "owner"
    FIELD_MANAGER = "field_manager"
    MEMBER = "member"
    FARMER = "farmer"
    VUNG_TRONG = "vung_trong"


# Danh mục 7 vai trò chuỗi cung ứng độc lập chuẩn Epic E-02
SUPPLY_CHAIN_ROLES = {
    UserRole.FARM.value,
    UserRole.PROCESSING.value,
    UserRole.LOGISTICS.value,
    UserRole.RETAILER.value,
    UserRole.INSPECTOR.value,
    UserRole.SYSTEM_ADMIN.value,
    UserRole.CONSUMER.value,
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
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    organization = relationship("Organization")
