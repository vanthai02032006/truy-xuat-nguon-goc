from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import (
    OWNER_ROLES,
    get_current_user,
    get_db,
)
from app.models.finance import FinancialTransaction
from app.models.user import User
from app.repositories.security_log_repository import SecurityLogRepository
from app.schemas.finance import (
    FinancialSummaryResponse,
    TransactionCreate,
    TransactionResponse,
)

router = APIRouter(prefix="/finance", tags=["Finance & Business"])


def verify_finance_access(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    RÀNG BUỘC RBAC CỐT LÕI:
    - Chỉ Chủ nông trại (Farm Owner) và Admin mới có quyền truy cập module Tài chính.
    - Giám sát nông trại (Supervisor) bị CHẶN HOÀN TOÀN (403 Forbidden).
    - Mọi hành vi cố gắng truy cập trái phép đều được ghi nhật ký an ninh (Security Log).
    """
    if current_user.role not in OWNER_ROLES:
        client_ip = request.client.host if request.client else "unknown"
        SecurityLogRepository.log_attempt(
            db=db,
            user_id=current_user.id,
            user_email=current_user.email,
            user_org_id=current_user.organization_id,
            attempt_type="financial_data_access_violation",
            target_resource="finance",
            target_id=None,
            target_org_id=current_user.organization_id,
            endpoint=request.url.path,
            method=request.method,
            ip_address=client_ip,
            description=(
                f"Người dùng {current_user.email} với vai trò '{current_user.role}' "
                f"cố tình truy cập trái phép phân hệ tài chính/doanh thu/lợi nhuận."
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Quyền truy cập bị từ chối. Chỉ Chủ nông trại hoặc Quản trị viên mới được phép xem và quản lý dữ liệu tài chính.",
        )
    return current_user


@router.get("/summary", response_model=FinancialSummaryResponse)
def get_financial_summary(
    current_user: Annotated[User, Depends(verify_finance_access)],
    db: Annotated[Session, Depends(get_db)],
):
    """Báo cáo phân tích tài chính nông trại (Doanh thu, Chi phí, Lợi nhuận ròng)."""
    org_id = current_user.organization_id or 1
    transactions = (
        db.query(FinancialTransaction)
        .filter(FinancialTransaction.organization_id == org_id)
        .all()
    )

    total_revenue = sum(
        t.amount for t in transactions if t.transaction_type == "revenue"
    )
    total_expense = sum(
        t.amount for t in transactions if t.transaction_type == "expense"
    )
    net_profit = total_revenue - total_expense

    return FinancialSummaryResponse(
        organization_id=org_id,
        total_revenue=round(total_revenue, 2),
        total_expense=round(total_expense, 2),
        net_profit=round(net_profit, 2),
        transaction_count=len(transactions),
    )


@router.get("/transactions", response_model=list[TransactionResponse])
def list_transactions(
    current_user: Annotated[User, Depends(verify_finance_access)],
    db: Annotated[Session, Depends(get_db)],
    type_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
):
    """Danh sách giao dịch thu chi tài chính."""
    query = db.query(FinancialTransaction)
    if current_user.organization_id is not None:
        query = query.filter(
            FinancialTransaction.organization_id == current_user.organization_id
        )
    if type_filter:
        query = query.filter(FinancialTransaction.transaction_type == type_filter)
    return (
        query.order_by(FinancialTransaction.id.desc()).offset(skip).limit(limit).all()
    )


@router.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(
    tx_in: TransactionCreate,
    current_user: Annotated[User, Depends(verify_finance_access)],
    db: Annotated[Session, Depends(get_db)],
):
    """Ghi nhận giao dịch tài chính (bán nông sản, chi phí nguyên vật liệu, vận chuyển, v.v.)."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Người dùng chưa được gán vào tổ chức/nông trại.",
        )
    tx = FinancialTransaction(
        transaction_type=tx_in.transaction_type,
        category=tx_in.category,
        amount=tx_in.amount,
        description=tx_in.description,
        transaction_date=tx_in.transaction_date,
        organization_id=current_user.organization_id,
        created_by_id=current_user.id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx
