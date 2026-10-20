from __future__ import annotations

import time
from typing import Any

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.batch import Batch
from app.models.organization import Organization
from app.services.batch_code_service import (
    DEFAULT_CODE_LENGTH,
    FORBIDDEN_CHARS,
    generate_secure_batch_code,
    generate_unique_batch_code,
    is_valid_batch_code,
)


def get_auth_headers(
    user_email: str, role: str, org_id: int | None
) -> dict[str, str]:
    token = create_access_token(
        subject=user_email, role=role, organization_id=org_id
    )
    return {"Authorization": f"Bearer {token}"}


def test_batch_code_10000_consecutive_generations_no_duplicates_no_forbidden_chars():
    """
    User Story S-08 - Tiêu chí chấp nhận 4:
    Sinh thử 10.000 mã liên tiếp để khẳng định:
    1. Không bị trùng lặp (10.000 mã hoàn toàn khác biệt).
    2. Mỗi mã có đúng 8 ký tự.
    3. Không chứa các ký tự cấm dễ nhầm lẫn: '0', 'O', '1', 'I', 'L'.
    4. Toàn bộ ký tự trong mã đều thuộc SAFE_ALPHABET (31 ký tự an toàn).
    """
    total = 10_000
    generated_codes = set()

    start_time = time.perf_counter()
    for _ in range(total):
        code = generate_secure_batch_code(DEFAULT_CODE_LENGTH)

        # 1. Độ dài chuẩn 8 ký tự
        assert len(code) == 8, f"Mã '{code}' không có đúng 8 ký tự!"

        # 2. Không chứa ký tự cấm dễ gây nhầm lẫn
        for forbidden in FORBIDDEN_CHARS:
            assert forbidden not in code, (
                f"LỖI: Mã '{code}' chứa ký tự cấm '{forbidden}'!"
            )

        # 3. Ký tự phải thuộc bảng SAFE_ALPHABET
        assert is_valid_batch_code(code), f"Mã '{code}' không hợp lệ!"

        generated_codes.add(code)

    elapsed = time.perf_counter() - start_time

    # 4. Đảm bảo 10.000 mã là duy nhất tuyệt đối (không bị trùng lặp)
    assert len(generated_codes) == total, (
        f"LỖI TRÙNG LẶP: Sinh {total} mã nhưng chỉ có {len(generated_codes)} mã duy nhất!"
    )
    # Tốc độ sinh 10.000 mã bằng CSPRNG phải nhanh (< 3 giây)
    assert elapsed < 3.0, (
        f"Thời gian sinh 10.000 mã quá chậm: {elapsed:.2f} giây"
    )


def test_generate_unique_batch_code_with_db_retry(db_session: Session):
    """
    User Story S-08 - Tiêu chí 3:
    Đảm bảo ràng buộc UNIQUE ở tầng DB. Nếu sinh trùng thì tự động thử sinh lại.
    """
    org = Organization(name="HTX An Toàn", code="HTX-AT-01")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    # Tạo trước 1 lô hàng
    first_code = generate_unique_batch_code(db_session)
    batch = Batch(
        batch_code=first_code,
        product_name="Dưa Leo Baby",
        organization_id=org.id,
    )
    db_session.add(batch)
    db_session.commit()

    # Sinh mã tiếp theo đảm bảo không trùng với first_code
    second_code = generate_unique_batch_code(db_session)
    assert second_code != first_code
    assert is_valid_batch_code(second_code)


def test_api_generate_code_endpoint(
    client: TestClient, seed_data: dict[str, Any]
):
    """
    Kiểm tra endpoint GET /api/v1/batches/generate-code:
    Trả về mã 8 ký tự hợp lệ, không chứa ký tự cấm.
    """
    user = seed_data["user_org1"]
    headers = get_auth_headers(user.email, user.role, user.organization_id)
    response = client.get("/api/v1/batches/generate-code", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    code = data["batch_code"]
    assert len(code) == 8
    assert is_valid_batch_code(code)
    for forbidden in FORBIDDEN_CHARS:
        assert forbidden not in code


def test_api_create_batch_with_auto_generated_code(
    client: TestClient, seed_data: dict[str, Any]
):
    """
    Kiểm tra tạo lô hàng POST /api/v1/batches không truyền batch_code:
    Hệ thống tự động sinh mã an toàn 8 ký tự và lưu thành công vào database.
    """
    user = seed_data["user_org1"]
    headers = get_auth_headers(user.email, user.role, user.organization_id)
    payload = {
        "product_name": "Cải Xoăn Kale Hữu Cơ",
        "batch_code": None,  # Không truyền mã lô
    }
    response = client.post("/api/v1/batches", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    created_code = data["batch_code"]
    assert len(created_code) == 8
    assert is_valid_batch_code(created_code)
