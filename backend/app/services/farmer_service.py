from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.farmer import FarmerIdentity
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.farmer import (
    FarmerAnonymizeResponse,
    FarmerCreateRequest,
    FarmerResponse,
)
from app.services.hash_chain_service import verify_chain_integrity


class FarmerService:
    @staticmethod
    def generate_farmer_ref_id(province_prefix: str = "DL") -> str:
        """Sinh mã tham chiếu bí danh cho nông hộ: FMR-{PROVINCE}-{RANDOM}."""
        rand = secrets.token_hex(3).upper()
        return f"FMR-{province_prefix}-{rand}"

    @classmethod
    def to_farmer_response(cls, f: FarmerIdentity) -> FarmerResponse:
        org_name = f.organization.name if f.organization else None
        if f.is_anonymized:
            display_name = f"Nông hộ ẩn danh ({f.farmer_ref_id})"
            full_name = None
            phone = None
            id_card = None
            detail_address = "[ĐÃ XÓA THEO NĐ 13/2023/NĐ-CP]"
        else:
            display_name = f.full_name or f"Nông hộ {f.farmer_ref_id}"
            full_name = f.full_name
            phone = f.phone
            id_card = f.id_card
            detail_address = f.detail_address

        return FarmerResponse(
            id=f.id,
            farmer_ref_id=f.farmer_ref_id,
            full_name=full_name,
            phone=phone,
            id_card=id_card,
            detail_address=detail_address,
            province=f.province,
            organization_id=f.organization_id,
            organization_name=org_name,
            is_anonymized=f.is_anonymized,
            anonymized_at=f.anonymized_at,
            anonymize_reason=f.anonymize_reason,
            display_name=display_name,
            created_at=f.created_at,
        )

    @classmethod
    def create_farmer(
        cls,
        db: Session,
        user: User,
        payload: FarmerCreateRequest,
    ) -> FarmerResponse:
        """
        Tạo hồ sơ nông hộ có định danh cá nhân (S-56).
        Dữ liệu cá nhân (PII) được cô lập tại bảng farmer_identities.
        """
        org_id = payload.organization_id or user.organization_id
        if not org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vui lòng xác định Tổ chức/HTX quản lý nông hộ.",
            )

        org = db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tổ chức #{org_id} không tồn tại.",
            )

        ref_id = payload.farmer_ref_id.strip() if payload.farmer_ref_id else cls.generate_farmer_ref_id()

        existing = db.query(FarmerIdentity).filter(FarmerIdentity.farmer_ref_id == ref_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã tham chiếu nông hộ {ref_id} đã tồn tại.",
            )

        farmer = FarmerIdentity(
            farmer_ref_id=ref_id,
            full_name=payload.full_name.strip(),
            phone=payload.phone.strip(),
            id_card=payload.id_card.strip() if payload.id_card else None,
            detail_address=payload.detail_address.strip(),
            province=payload.province.strip() if payload.province else "Lâm Đồng",
            organization_id=org_id,
            is_anonymized=False,
        )
        db.add(farmer)
        db.commit()
        db.refresh(farmer)
        return cls.to_farmer_response(farmer)

    @classmethod
    def list_farmers(
        cls,
        db: Session,
        user: User,
        skip: int = 0,
        limit: int = 100,
    ) -> list[FarmerResponse]:
        """Lấy danh sách hồ sơ nông hộ."""
        query = db.query(FarmerIdentity)
        is_admin_or_inspector = user.role in [
            UserRole.INSPECTOR.value,
            UserRole.SYSTEM_ADMIN.value,
            UserRole.ADMIN.value,
        ]
        if not is_admin_or_inspector and user.organization_id:
            query = query.filter(FarmerIdentity.organization_id == user.organization_id)

        farmers = query.order_by(FarmerIdentity.id.desc()).offset(skip).limit(limit).all()
        return [cls.to_farmer_response(f) for f in farmers]

    @classmethod
    def get_farmer_by_ref(cls, db: Session, farmer_ref_id: str) -> FarmerResponse:
        farmer = (
            db.query(FarmerIdentity)
            .filter(FarmerIdentity.farmer_ref_id == farmer_ref_id.strip())
            .first()
        )
        if not farmer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy nông hộ với mã tham chiếu {farmer_ref_id}.",
            )
        return cls.to_farmer_response(farmer)

    @classmethod
    def anonymize_farmer(
        cls,
        db: Session,
        user: User,
        farmer_ref_id: str,
        reason: str,
    ) -> FarmerAnonymizeResponse:
        """
        User Story S-56: Xóa / Ẩn danh dữ liệu cá nhân của nông hộ theo Nghị định 13/2023/NĐ-CP.
        
        Quy trình xử lý:
        1. Xóa toàn bộ PII (Họ tên, SĐT, CCCD, Địa chỉ chi tiết) trong bảng farmer_identities.
        2. Đánh dấu is_anonymized = True, ghi nhận anonymized_at và reason.
        3. TUYỆT ĐỐI KHÔNG SỬA BẢNG chain_events (vì chuỗi hash chỉ lưu farmer_ref_id).
        4. Kiểm tra lại tính toàn vẹn SHA-256 (S-12) của mọi lô hàng liên quan -> Khớp 100% hợp lệ!
        """
        farmer = (
            db.query(FarmerIdentity)
            .filter(FarmerIdentity.farmer_ref_id == farmer_ref_id.strip())
            .first()
        )
        if not farmer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy nông hộ với mã tham chiếu {farmer_ref_id}.",
            )

        is_admin = user.role in [UserRole.SYSTEM_ADMIN.value, UserRole.ADMIN.value]
        if not is_admin and farmer.organization_id != user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện xóa dữ liệu cá nhân của nông hộ thuộc tổ chức khác.",
            )

        if farmer.is_anonymized:
            # Đã ẩn danh từ trước
            now_dt = farmer.anonymized_at or datetime.now(UTC)
        else:
            now_dt = datetime.now(UTC)
            # Xóa sạch PII
            farmer.full_name = None
            farmer.phone = None
            farmer.id_card = None
            farmer.detail_address = None
            farmer.is_anonymized = True
            farmer.anonymized_at = now_dt
            farmer.anonymize_reason = reason.strip()
            db.commit()
            db.refresh(farmer)

        # Tìm các lô hàng liên quan đến nông hộ này
        batches = (
            db.query(Batch)
            .filter(Batch.farmer_ref_id == farmer.farmer_ref_id)
            .all()
        )

        all_valid = True
        integrity_messages = []

        if batches:
            for b in batches:
                check = verify_chain_integrity(db=db, batch_id=b.id)
                if not check["valid"]:
                    all_valid = False
                    integrity_messages.append(f"Lô {b.batch_code}: {check['message']}")
                else:
                    integrity_messages.append(f"Lô {b.batch_code}: Toàn vẹn 100%")
            summary_msg = "; ".join(integrity_messages)
        else:
            summary_msg = "Không có lô hàng nào cần xác thực hoặc chuỗi sự kiện rỗng."

        return FarmerAnonymizeResponse(
            success=True,
            farmer_ref_id=farmer.farmer_ref_id,
            message=(
                f"Đã xóa toàn bộ thông tin định danh cá nhân của nông hộ {farmer.farmer_ref_id} "
                f"theo Nghị định 13/2023/NĐ-CP thành công. Dữ liệu PII đã được loại bỏ hoàn toàn."
            ),
            is_anonymized=True,
            anonymized_at=now_dt,
            batches_checked_count=len(batches),
            chain_integrity_valid=all_valid,
            integrity_message=f"Xác thực toàn vẹn SHA-256 (S-12): {summary_msg}",
        )
