from __future__ import annotations

import os

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-32chars")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models
from app.api.deps import get_db
from app.core.database import Base
from app.core.security import get_password_hash
from app.main import app
from app.models.batch import Batch
from app.models.organization import Organization
from app.models.user import User, UserRole

# In-memory SQLite cho test tích hợp độc lập và siêu nhanh trong CI
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Tạo schema bảng trước khi chạy test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Cung cấp session DB riêng biệt được rollback/clean cho mỗi test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    """Cung cấp TestClient với get_db override trỏ vào test session."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seed_data(db_session):
    """Khởi tạo dữ liệu mẫu 2 tổ chức, 3 người dùng, 3 lô hàng phục vụ kiểm thử."""
    # 1. Hai tổ chức khác nhau
    org1 = Organization(id=1, name="Hợp tác xã Nông Sản Thắng Lợi", code="HTX-TL")
    org2 = Organization(id=2, name="Hợp tác xã Rau Sạch Đà Lạt", code="HTX-DL")
    db_session.add_all([org1, org2])
    db_session.flush()

    # 2. Ba người dùng với các vai trò khác nhau
    user_org1 = User(
        id=1,
        email="member1@thangloi.vn",
        hashed_password=get_password_hash("password123"),
        full_name="Nguyễn Văn A (HTX Thắng Lợi)",
        role=UserRole.MEMBER.value,
        organization_id=1,
        is_active=True,
    )
    user_org2 = User(
        id=2,
        email="member2@dalat.vn",
        hashed_password=get_password_hash("password123"),
        full_name="Trần Thị B (HTX Đà Lạt)",
        role=UserRole.MEMBER.value,
        organization_id=2,
        is_active=True,
    )
    inspector = User(
        id=3,
        email="inspector@kiemdinh.gov.vn",
        hashed_password=get_password_hash("password123"),
        full_name="Lê Văn C (Cán bộ kiểm tra)",
        role=UserRole.INSPECTOR.value,
        organization_id=None,
        is_active=True,
    )
    db_session.add_all([user_org1, user_org2, inspector])
    db_session.flush()

    # 3. Ba lô hàng thuộc về 2 tổ chức
    batch1_org1 = Batch(
        id=1,
        batch_code="BATCH-TL-001",
        product_name="Cà chua Beef Thắng Lợi",
        organization_id=1,
    )
    batch2_org1 = Batch(
        id=2,
        batch_code="BATCH-TL-002",
        product_name="Dưa leo Baby Thắng Lợi",
        organization_id=1,
    )
    batch3_org2 = Batch(
        id=3,
        batch_code="BATCH-DL-001",
        product_name="Xà lách Thủy canh Đà Lạt",
        organization_id=2,
    )
    db_session.add_all([batch1_org1, batch2_org1, batch3_org2])
    db_session.commit()

    return {
        "org1": org1,
        "org2": org2,
        "user_org1": user_org1,
        "user_org2": user_org2,
        "inspector": inspector,
        "batch1_org1": batch1_org1,
        "batch2_org1": batch2_org1,
        "batch3_org2": batch3_org2,
    }
