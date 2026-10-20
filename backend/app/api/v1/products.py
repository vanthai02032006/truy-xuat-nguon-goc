from __future__ import annotations

import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_admin
from app.models.product import Product
from app.models.user import User
from app.repositories.product_repository import ProductRepository
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductResponse])
def list_products(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    q: str | None = Query(default=None, description="Tìm kiếm theo tên sản phẩm"),
):
    """
    User Story S-07, Task T-16:
    Danh mục sản phẩm dùng chung cho toàn hệ thống (không lọc theo organization_id).
    Mọi vai trò đăng nhập (Vùng trồng, HTX sơ chế, Logistics, Inspector, Admin...) đều xem được.
    """
    return ProductRepository.list(db, skip=skip, limit=limit, query=q)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Lấy thông tin chi tiết một sản phẩm trong danh mục dùng chung."""
    product = ProductRepository.get(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm có ID {product_id}.",
        )
    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[User, Depends(require_admin)],
):
    """
    User Story S-07, Task T-16, T-17:
    Tạo sản phẩm mới trong danh mục toàn hệ thống.
    - CHỈ vai trò "Quản trị hệ thống (Admin)" mới có quyền gọi API ghi (các vai trò khác trả về 403).
    - Đơn vị tính bắt buộc chọn từ danh sách đóng (enum: 'kg', 'tấn', 'thùng').
    - Chặn thêm sản phẩm trùng tên (trả về 400 Bad Request).
    """
    clean_name = product_in.name.strip()
    existing = ProductRepository.get_by_name(db, clean_name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Sản phẩm với tên '{clean_name}' đã tồn tại trong hệ thống.",
        )

    new_product = Product(
        name=clean_name,
        unit=product_in.unit.value,
        description=product_in.description.strip() if product_in.description else None,
    )
    return ProductRepository.create(db, new_product)


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[User, Depends(require_admin)],
):
    """
    User Story S-07, Task T-17:
    Cập nhật thông tin sản phẩm (Chỉ Admin).
    Chặn trùng tên với sản phẩm khác đã có trong hệ thống.
    """
    product = ProductRepository.get(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm có ID {product_id}.",
        )

    if product_in.name is not None:
        clean_name = product_in.name.strip()
        existing = ProductRepository.get_by_name(db, clean_name)
        if existing and existing.id != product_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sản phẩm với tên '{clean_name}' đã tồn tại trong hệ thống.",
            )
        product.name = clean_name

    if product_in.unit is not None:
        product.unit = product_in.unit.value

    if product_in.description is not None:
        product.description = (
            product_in.description.strip() if product_in.description else None
        )

    return ProductRepository.update(db, product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[User, Depends(require_admin)],
):
    """
    User Story S-07:
    Xóa sản phẩm khỏi danh mục (Chỉ Admin).
    """
    product = ProductRepository.get(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sản phẩm có ID {product_id}.",
        )
    ProductRepository.delete(db, product)


class ProductCsvImportRequest(BaseModel):
    csv_content: str = Field(..., description="Nội dung tệp CSV chứa danh mục sản phẩm")


class ProductCsvImportResponse(BaseModel):
    imported_count: int
    skipped_count: int
    total_rows: int
    errors: list[str] = []


@router.post("/import-csv", response_model=ProductCsvImportResponse)
def import_products_csv(
    payload: ProductCsvImportRequest,
    db: Annotated[Session, Depends(get_db)],
    admin_user: Annotated[User, Depends(require_admin)],
):
    """
    User Story S-32: Nhập danh mục sản phẩm từ tệp CSV (Chỉ Admin).
    - Cột: name (tên sản phẩm), unit (đơn vị: kg/tấn/thùng), description (mô tả), standard (tiêu chuẩn).
    - Kiểm tra đơn vị tính bắt buộc là enum: 'kg', 'tấn', 'thùng'.
    - Bỏ qua các sản phẩm trùng tên.
    """
    lines = payload.csv_content.strip()
    if not lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nội dung CSV không được để trống.",
        )

    f = io.StringIO(lines)
    reader = csv.DictReader(f)
    imported = 0
    skipped = 0
    total = 0
    errors = []

    valid_units = {"kg", "tấn", "thùng"}

    for idx, row in enumerate(reader, start=2):
        total += 1
        clean_row = {str(k).strip().lower(): str(v).strip() for k, v in row.items() if k}
        name = clean_row.get("name") or clean_row.get("tên sản phẩm") or clean_row.get("tên")
        unit = clean_row.get("unit") or clean_row.get("đơn vị tính") or clean_row.get("đơn vị")
        desc = clean_row.get("description") or clean_row.get("mô tả") or ""

        if not name:
            errors.append(f"Dòng {idx}: Thiếu tên sản phẩm.")
            skipped += 1
            continue

        if not unit or unit.lower() not in valid_units:
            errors.append(f"Dòng {idx} ({name}): Đơn vị tính '{unit}' không hợp lệ. Chỉ chấp nhận 'kg', 'tấn', 'thùng'.")
            skipped += 1
            continue

        unit = unit.lower()

        existing = ProductRepository.get_by_name(db, name)
        if existing:
            skipped += 1
            continue

        new_prod = Product(
            name=name,
            unit=unit,
            description=desc if desc else None,
        )
        db.add(new_prod)
        imported += 1

    db.commit()
    return ProductCsvImportResponse(
        imported_count=imported,
        skipped_count=skipped,
        total_rows=total,
        errors=errors,
    )

