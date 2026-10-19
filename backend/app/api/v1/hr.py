from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    OWNER_ROLES,
    get_db,
    require_farm_owner_or_admin,
    require_field_supervisor_or_above,
)
from app.models.hr import DailyTask, Timesheet, Worker
from app.models.user import User
from app.schemas.hr import (
    DailyTaskCreate,
    DailyTaskResponse,
    PayrollSummary,
    TimesheetCreate,
    TimesheetResponse,
    WorkerCreate,
    WorkerResponse,
)

router = APIRouter(prefix="/hr", tags=["HR & Workforce"])


@router.get("/workers", response_model=list[WorkerResponse])
def list_workers(
    current_user: Annotated[User, Depends(require_field_supervisor_or_above)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
):
    """
    Danh sách nhân sự / công nhân nông trại.
    RÀNG BUỘC RBAC CỐT LÕI:
    - Chủ nông trại (Farm Owner) & Admin: Xem đầy đủ mức thù lao/ngày (daily_rate).
    - Giám sát nông trại (Supervisor): Mức thù lao (daily_rate) bị ẩn (trả về None).
    """
    query = db.query(Worker)
    if current_user.organization_id is not None:
        query = query.filter(Worker.organization_id == current_user.organization_id)
    workers = query.offset(skip).limit(limit).all()

    is_owner_or_admin = current_user.role in OWNER_ROLES

    results = []
    for w in workers:
        results.append(
            WorkerResponse(
                id=w.id,
                full_name=w.full_name,
                worker_type=w.worker_type,
                phone=w.phone,
                daily_rate=w.daily_rate if is_owner_or_admin else None,
                organization_id=w.organization_id,
                created_at=w.created_at,
            )
        )
    return results


@router.post(
    "/workers", response_model=WorkerResponse, status_code=status.HTTP_201_CREATED
)
def create_worker(
    worker_in: WorkerCreate,
    current_user: Annotated[User, Depends(require_farm_owner_or_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    """Thêm mới công nhân nông trại kèm định mức thù lao (Chỉ Chủ nông trại hoặc Admin)."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Người dùng chưa được gán vào tổ chức/nông trại.",
        )
    worker = Worker(
        full_name=worker_in.full_name,
        worker_type=worker_in.worker_type,
        phone=worker_in.phone,
        daily_rate=worker_in.daily_rate,
        organization_id=current_user.organization_id,
    )
    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


@router.get("/tasks", response_model=list[DailyTaskResponse])
def list_tasks(
    current_user: Annotated[User, Depends(require_field_supervisor_or_above)],
    db: Annotated[Session, Depends(get_db)],
    date_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
):
    """Danh sách giao việc / phân công nhiệm vụ hiện trường."""
    query = db.query(DailyTask)
    if current_user.organization_id is not None:
        query = query.filter(DailyTask.organization_id == current_user.organization_id)
    if date_filter:
        query = query.filter(DailyTask.task_date == date_filter)
    return query.order_by(DailyTask.id.desc()).offset(skip).limit(limit).all()


@router.post(
    "/tasks", response_model=DailyTaskResponse, status_code=status.HTTP_201_CREATED
)
def create_task(
    task_in: DailyTaskCreate,
    current_user: Annotated[User, Depends(require_field_supervisor_or_above)],
    db: Annotated[Session, Depends(get_db)],
):
    """Giám sát nông trại phân công việc cho công nhân tại thửa đất."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Người dùng chưa được gán vào tổ chức/nông trại.",
        )
    task = DailyTask(
        title=task_in.title,
        description=task_in.description,
        plot_id=task_in.plot_id,
        worker_id=task_in.worker_id,
        supervisor_id=current_user.id,
        status="assigned",
        task_date=task_in.task_date,
        organization_id=current_user.organization_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/timesheets", response_model=list[TimesheetResponse])
def list_timesheets(
    current_user: Annotated[User, Depends(require_field_supervisor_or_above)],
    db: Annotated[Session, Depends(get_db)],
    date_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
):
    """Danh sách bảng chấm công và sản lượng thu hoạch."""
    query = db.query(Timesheet)
    if current_user.organization_id is not None:
        query = query.filter(Timesheet.organization_id == current_user.organization_id)
    if date_filter:
        query = query.filter(Timesheet.date == date_filter)
    return query.order_by(Timesheet.id.desc()).offset(skip).limit(limit).all()


@router.post(
    "/timesheets", response_model=TimesheetResponse, status_code=status.HTTP_201_CREATED
)
def create_timesheet(
    sheet_in: TimesheetCreate,
    current_user: Annotated[User, Depends(require_field_supervisor_or_above)],
    db: Annotated[Session, Depends(get_db)],
):
    """Giám sát nông trại ghi nhận chấm công hằng ngày của công nhân."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Người dùng chưa được gán vào tổ chức/nông trại.",
        )
    # Kiểm tra worker tồn tại trong tổ chức
    worker = db.query(Worker).filter(Worker.id == sheet_in.worker_id).first()
    if not worker or (
        current_user.organization_id
        and worker.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy công nhân trong nông trại.",
        )

    timesheet = Timesheet(
        worker_id=sheet_in.worker_id,
        date=sheet_in.date,
        hours_worked=sheet_in.hours_worked,
        output_quantity=sheet_in.output_quantity,
        output_unit=sheet_in.output_unit,
        status="submitted",
        supervisor_id=current_user.id,
        organization_id=current_user.organization_id,
    )
    db.add(timesheet)
    db.commit()
    db.refresh(timesheet)
    return timesheet


@router.post("/timesheets/{timesheet_id}/approve", response_model=TimesheetResponse)
def approve_timesheet(
    timesheet_id: int,
    current_user: Annotated[User, Depends(require_farm_owner_or_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    """Chủ nông trại duyệt bảng chấm công để xác nhận tính lương."""
    timesheet = db.query(Timesheet).filter(Timesheet.id == timesheet_id).first()
    if not timesheet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy bảng chấm công với ID {timesheet_id}",
        )
    if (
        current_user.organization_id
        and timesheet.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền duyệt bảng chấm công của nông trại khác.",
        )
    timesheet.status = "approved"
    timesheet.approver_id = current_user.id
    db.commit()
    db.refresh(timesheet)
    return timesheet


@router.get("/payroll", response_model=PayrollSummary)
def get_payroll_summary(
    current_user: Annotated[User, Depends(require_farm_owner_or_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Báo cáo tổng kết chi phí nhân công / tiền lương nông trại.
    RÀNG BUỘC RBAC CỐT LÕI:
    - Chỉ Chủ nông trại (Farm Owner) và Admin mới có quyền truy cập.
    - Giám sát nông trại (Supervisor) bị chặn hoàn toàn (403 Forbidden).
    """
    org_id = current_user.organization_id or 1
    workers = db.query(Worker).filter(Worker.organization_id == org_id).all()
    worker_rates = {w.id: w.daily_rate for w in workers}

    timesheets = db.query(Timesheet).filter(Timesheet.organization_id == org_id).all()

    total_hours = sum(ts.hours_worked for ts in timesheets)
    total_wage = 0.0
    for ts in timesheets:
        rate = worker_rates.get(ts.worker_id, 0.0)
        # Giả sử 1 ngày công chuẩn = 8 giờ
        total_wage += (rate / 8.0) * ts.hours_worked

    return PayrollSummary(
        organization_id=org_id,
        total_workers=len(workers),
        total_hours_worked=round(total_hours, 2),
        total_estimated_wage=round(total_wage, 2),
    )
