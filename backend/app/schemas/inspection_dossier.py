from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DossierBatchInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_code: str
    product_name: str
    initial_quantity: float
    remaining_quantity: float
    unit: str
    status: str
    organization_id: int
    organization_name: str | None = None
    land_plot_name: str | None = None
    created_at: datetime


class DossierIntegrityInfo(BaseModel):
    valid: bool
    status_label: str  # "TOÀN VẸN 100% (HỢP LỆ)" hoặc "CẢNH BÁO: PHÁT HIỆN CAN THIỆP"
    total_events: int
    genesis_hash: str
    terminal_current_hash: str
    checked_at: datetime
    message: str


class DossierTimelineEvent(BaseModel):
    id: int
    index: int
    event_type: str
    event_data: str
    organization_name: str
    previous_hash: str
    current_hash: str
    created_at: datetime


class DossierLineageInfo(BaseModel):
    ancestor_count: int
    ancestors: list[dict[str, Any]] = []
    descendant_count: int
    descendants: list[dict[str, Any]] = []


class DossierColdChainInfo(BaseModel):
    trips_count: int
    violations_count: int
    has_violations: bool
    violations: list[dict[str, Any]] = []
    trips: list[dict[str, Any]] = []


class DossierRecallInfo(BaseModel):
    is_recalled: bool
    recalls: list[dict[str, Any]] = []


class DossierFarmerInfo(BaseModel):
    farmer_ref_id: str | None = None
    display_name: str
    province: str
    is_anonymized: bool
    phone: str | None = None
    detail_address: str | None = None


class DossierExportMetadata(BaseModel):
    official_dossier_code: str  # HSKT-YYYYMMDD-XXXX
    exported_at: datetime
    inspector_name: str
    inspector_role: str
    issuer_authority: str = "Chi cục Trồng trọt & Bảo vệ Thực vật - Hệ thống Quốc gia Nông Sản Lành"


class InspectionDossierResponse(BaseModel):
    """User Stories S-52, S-53: Hồ sơ kiểm tra truy xuất nguồn gốc chính thức."""

    model_config = ConfigDict(from_attributes=True)

    batch_info: DossierBatchInfo
    integrity_verification: DossierIntegrityInfo
    event_timeline: list[DossierTimelineEvent]
    lineage: DossierLineageInfo
    cold_chain: DossierColdChainInfo
    recalls: DossierRecallInfo
    farmer_origin: DossierFarmerInfo
    export_metadata: DossierExportMetadata
