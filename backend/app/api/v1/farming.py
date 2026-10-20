from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db,
    require_field_supervisor_or_above,
)
from app.models.farming import FarmingLog, FieldIncident
from app.models.land_plot import LandPlot
from app.models.user import User, UserRole
from app.schemas.farming import (
    FarmingLogCreate,
    FarmingLogResponse,
    FieldIncidentCreate,
    FieldIncidentResolve,
    FieldIncidentResponse,
)

router = APIRouter(prefix="/farming", tags=["Farming Operations"])


@router.get("/logs", response_model=list[FarmingLogResponse])
def list_farming_logs(
    current_user: Annotated[User, Depends(require_field_supervisor_or_above)],
    db: Annotated[Session, Depends(get_db)],
    plot_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
):
    """Nhật ký hoạt động canh tác nông nghiệp hằng ngày."""
    query = db.query(FarmingLog)
    if (
        current_user.role not in [UserRole.INSPECTOR.value, UserRole.SYSTEM_ADMIN.value, "inspector", "system_admin", "admin"]
        and current_user.organization_id is not None
    ):
        query = query.filter(FarmingLog.organization_id == current_user.organization_id)
    if plot_id is not None:
        query = query.filter(FarmingLog.plot_id == plot_id)
    return query.order_by(FarmingLog.id.desc()).offset(skip).limit(limit).all()


@router.post(
    "/logs", response_model=FarmingLogResponse, status_code=status.HTTP_201_CREATED
)
def create_farming_log(
    log_in: FarmingLogCreate,
    current_user: Annotated[User, Depends(require_field_supervisor_or_above)],
    db: Annotated[Session, Depends(get_db)],
):
    """Ghi nhận hoạt động canh tác (tưới tiêu, bón phân, phun thuốc, thu hoạch)."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Người dùng chưa được gán vào tổ chức/nông trại.",
        )
    # Kiểm tra thửa đất tồn tại trong nông trại
    plot = db.query(LandPlot).filter(LandPlot.id == log_in.plot_id).first()
    if not plot or (
        current_user.organization_id
        and plot.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy thửa đất #{log_in.plot_id} trong nông trại.",
        )

    log_entry = FarmingLog(
        plot_id=log_in.plot_id,
        activity_type=log_in.activity_type,
        description=log_in.description,
        materials_used=log_in.materials_used,
        activity_date=log_in.activity_date,
        supervisor_id=current_user.id,
        organization_id=current_user.organization_id,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


@router.get("/incidents", response_model=list[FieldIncidentResponse])
def list_field_incidents(
    current_user: Annotated[User, Depends(require_field_supervisor_or_above)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = None,
    plot_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
):
    """Danh sách sự cố đồng ruộng (sâu bệnh hại, thời tiết bất thường, hỏng máy móc)."""
    query = db.query(FieldIncident)
    if (
        current_user.role not in [UserRole.INSPECTOR.value, UserRole.SYSTEM_ADMIN.value, "inspector", "system_admin", "admin"]
        and current_user.organization_id is not None
    ):
        query = query.filter(
            FieldIncident.organization_id == current_user.organization_id
        )
    if status_filter:
        query = query.filter(FieldIncident.status == status_filter)
    if plot_id is not None:
        query = query.filter(FieldIncident.plot_id == plot_id)
    return query.order_by(FieldIncident.id.desc()).offset(skip).limit(limit).all()


@router.post(
    "/incidents",
    response_model=FieldIncidentResponse,
    status_code=status.HTTP_201_CREATED,
)
def report_field_incident(
    incident_in: FieldIncidentCreate,
    current_user: Annotated[User, Depends(require_field_supervisor_or_above)],
    db: Annotated[Session, Depends(get_db)],
):
    """Giám sát hiện trường báo cáo sự cố phát sinh tại thửa đất."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Người dùng chưa được gán vào tổ chức/nông trại.",
        )
    plot = db.query(LandPlot).filter(LandPlot.id == incident_in.plot_id).first()
    if not plot or (
        current_user.organization_id
        and plot.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy thửa đất #{incident_in.plot_id} trong nông trại.",
        )

    incident = FieldIncident(
        plot_id=incident_in.plot_id,
        incident_type=incident_in.incident_type,
        severity=incident_in.severity,
        description=incident_in.description,
        status="reported",
        reported_by_id=current_user.id,
        organization_id=current_user.organization_id,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


@router.put("/incidents/{incident_id}/resolve", response_model=FieldIncidentResponse)
def resolve_field_incident(
    incident_id: int,
    resolve_in: FieldIncidentResolve,
    current_user: Annotated[User, Depends(require_field_supervisor_or_above)],
    db: Annotated[Session, Depends(get_db)],
):
    """Xử lý và đóng sự cố đồng ruộng."""
    incident = db.query(FieldIncident).filter(FieldIncident.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sự cố với ID {incident_id}",
        )
    if (
        current_user.organization_id
        and incident.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền xử lý sự cố của nông trại khác.",
        )

    incident.status = "resolved"
    incident.action_taken = resolve_in.action_taken
    db.commit()
    db.refresh(incident)
    return incident
