from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.chain_event import ChainEvent
from app.models.cold_chain import TransportTrip, TripBatch
from app.models.farmer import FarmerIdentity
from app.models.recall import RecallAffectedBatch
from app.models.user import User, UserRole
from app.schemas.inspection_dossier import (
    DossierBatchInfo,
    DossierColdChainInfo,
    DossierExportMetadata,
    DossierFarmerInfo,
    DossierIntegrityInfo,
    DossierLineageInfo,
    DossierRecallInfo,
    DossierTimelineEvent,
    InspectionDossierResponse,
)
from app.services.hash_chain_service import GENESIS_HASH, verify_chain_integrity
from app.services.lineage_dag_service import LineageDagService


class InspectionDossierService:
    @classmethod
    def generate_dossier(
        cls,
        db: Session,
        batch_id: int,
        inspector_user: User,
    ) -> InspectionDossierResponse:
        """
        User Story S-52, S-53: Tổng hợp Hồ sơ Kiểm tra Truy xuất nguồn gốc chính thức.
        Bao gồm:
        1. Thông tin lô hàng & cơ sở quản lý.
        2. Kết quả kiểm tra toàn vẹn chuỗi Hash SHA-256 tại thời điểm xuất + Terminal Hash.
        3. Dòng thời gian sự kiện hoàn chỉnh (Chain Events).
        4. Phả hệ tổ tiên & hậu duệ (Lineage DAG).
        5. Lịch sử giám sát chuỗi lạnh & vi phạm (Cold Chain Monitoring).
        6. Tình trạng lệnh thu hồi khẩn cấp (Recall Orders).
        7. Nguồn gốc nông hộ (tuân thủ Nghị định 13/2023/NĐ-CP).
        """
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy lô hàng với ID {batch_id}.",
            )

        # 1. Thông tin lô hàng
        org_name = batch.organization.name if batch.organization else f"Tổ chức #{batch.organization_id}"
        land_plot_name = batch.land_plot.name if batch.land_plot else None

        batch_info = DossierBatchInfo(
            id=batch.id,
            batch_code=batch.batch_code,
            product_name=batch.product_name,
            initial_quantity=batch.initial_quantity,
            remaining_quantity=batch.remaining_quantity,
            unit=batch.unit,
            status=batch.status,
            organization_id=batch.organization_id,
            organization_name=org_name,
            land_plot_name=land_plot_name,
            created_at=batch.created_at,
        )

        # 2. Kiểm tra tính toàn vẹn chuỗi Hash (S-12)
        integrity_res = verify_chain_integrity(db, batch_id=batch.id)
        events = (
            db.query(ChainEvent)
            .filter(ChainEvent.batch_id == batch.id)
            .order_by(ChainEvent.id.asc())
            .all()
        )

        terminal_hash = events[-1].current_hash if events else GENESIS_HASH
        first_hash = events[0].previous_hash if events else GENESIS_HASH

        status_label = (
            "TOÀN VẸN 100% (HỢP LỆ)"
            if integrity_res["valid"]
            else f"CẢNH BÁO: PHÁT HIỆN CAN THIỆP TẠI SỰ KIỆN #{integrity_res.get('broken_event_id')}"
        )

        integrity_info = DossierIntegrityInfo(
            valid=integrity_res["valid"],
            status_label=status_label,
            total_events=len(events),
            genesis_hash=first_hash,
            terminal_current_hash=terminal_hash,
            checked_at=datetime.now(UTC),
            message=integrity_res["message"],
        )

        # 3. Dòng thời gian sự kiện hoàn chỉnh
        timeline_events = []
        for idx, e in enumerate(events):
            e_org_name = e.organization.name if e.organization else f"Tổ chức #{e.organization_id}"
            timeline_events.append(
                DossierTimelineEvent(
                    id=e.id,
                    index=idx + 1,
                    event_type=e.event_type,
                    event_data=e.event_data,
                    organization_name=e_org_name,
                    previous_hash=e.previous_hash,
                    current_hash=e.current_hash,
                    created_at=e.created_at,
                )
            )

        # 4. Phả hệ tổ tiên & hậu duệ (S-21, S-26)
        ancestors_data = []
        descendants_data = []
        try:
            upstream = LineageDagService.trace_upstream_roots(db, batch.id)
            ancestors_data = upstream.get("roots", [])
        except Exception:
            ancestors_data = []

        try:
            downstream = LineageDagService.trace_downstream_descendants(db, batch.id)
            descendants_data = downstream.get("descendants", [])
        except Exception:
            descendants_data = []

        lineage_info = DossierLineageInfo(
            ancestor_count=len(ancestors_data),
            ancestors=ancestors_data,
            descendant_count=len(descendants_data),
            descendants=descendants_data,
        )

        # 5. Lịch sử giám sát chuỗi lạnh & vi phạm (S-40 -> S-45)
        trip_batches = db.query(TripBatch).filter(TripBatch.batch_id == batch.id).all()
        trips_list = []
        all_violations = []

        for tb in trip_batches:
            t = tb.trip
            if not t:
                continue
            carrier_name = t.carrier_organization.name if t.carrier_organization else f"Org #{t.carrier_org_id}"
            trips_list.append(
                {
                    "trip_code": t.trip_code,
                    "vehicle_code": t.vehicle_code,
                    "carrier_name": carrier_name,
                    "driver_name": t.driver_name,
                    "temp_range": f"{t.min_temperature}°C - {t.max_temperature}°C",
                    "status": t.status,
                    "start_time": t.start_time.isoformat() if t.start_time else None,
                }
            )
            for v in t.violations:
                all_violations.append(
                    {
                        "trip_code": t.trip_code,
                        "vehicle_code": t.vehicle_code,
                        "duration_minutes": v.duration_minutes,
                        "peak_temperature": v.peak_temperature,
                        "threshold": v.threshold,
                        "violation_type": v.violation_type,
                        "started_at": v.started_at.isoformat() if v.started_at else None,
                        "ended_at": v.ended_at.isoformat() if v.ended_at else None,
                    }
                )

        cold_chain_info = DossierColdChainInfo(
            trips_count=len(trips_list),
            violations_count=len(all_violations),
            has_violations=len(all_violations) > 0,
            violations=all_violations,
            trips=trips_list,
        )

        # 6. Tình trạng lệnh thu hồi khẩn cấp (S-33 -> S-38)
        recall_entries = (
            db.query(RecallAffectedBatch)
            .filter(RecallAffectedBatch.batch_id == batch.id)
            .all()
        )
        recalls_list = []
        for re in recall_entries:
            r = re.recall
            if r:
                recalls_list.append(
                    {
                        "recall_code": r.recall_code,
                        "title": r.title,
                        "severity": r.severity,
                        "status": r.status,
                        "scope_mode": r.scope_mode,
                        "reason": r.reason,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                    }
                )

        recall_info = DossierRecallInfo(
            is_recalled=len(recalls_list) > 0,
            recalls=recalls_list,
        )

        # 7. Thông tin nông hộ / vùng trồng (S-56 - Nghị định 13/2023/NĐ-CP)
        farmer_ref = batch.farmer_ref_id
        if not farmer_ref and batch.land_plot:
            farmer_ref = batch.land_plot.farmer_ref_id

        farmer_obj = None
        if farmer_ref:
            farmer_obj = (
                db.query(FarmerIdentity)
                .filter(FarmerIdentity.farmer_ref_id == farmer_ref)
                .first()
            )

        if farmer_obj:
            if farmer_obj.is_anonymized:
                farmer_info = DossierFarmerInfo(
                    farmer_ref_id=farmer_obj.farmer_ref_id,
                    display_name=f"Nông hộ ẩn danh ({farmer_obj.farmer_ref_id})",
                    province=farmer_obj.province,
                    is_anonymized=True,
                    phone="[ĐÃ XÓA THEO NĐ 13/2023/NĐ-CP]",
                    detail_address="[ĐÃ XÓA THEO NĐ 13/2023/NĐ-CP]",
                )
            else:
                farmer_info = DossierFarmerInfo(
                    farmer_ref_id=farmer_obj.farmer_ref_id,
                    display_name=farmer_obj.full_name or f"Nông hộ {farmer_obj.farmer_ref_id}",
                    province=farmer_obj.province,
                    is_anonymized=False,
                    phone=farmer_obj.phone,
                    detail_address=farmer_obj.detail_address,
                )
        else:
            farmer_info = DossierFarmerInfo(
                farmer_ref_id=farmer_ref,
                display_name=land_plot_name or "Vùng trồng HTX",
                province="Lâm Đồng",
                is_anonymized=False,
                phone=None,
                detail_address=batch.land_plot.address if batch.land_plot else None,
            )

        # 8. Metadata xuất hồ sơ
        now_utc = datetime.now(UTC)
        date_str = now_utc.strftime("%Y%m%d")
        rand_code = secrets.token_hex(2).upper()
        doc_code = f"HSKT-{date_str}-{batch.id:04d}-{rand_code}"

        export_metadata = DossierExportMetadata(
            official_dossier_code=doc_code,
            exported_at=now_utc,
            inspector_name=inspector_user.full_name or inspector_user.email,
            inspector_role=inspector_user.role,
        )

        return InspectionDossierResponse(
            batch_info=batch_info,
            integrity_verification=integrity_info,
            event_timeline=timeline_events,
            lineage=lineage_info,
            cold_chain=cold_chain_info,
            recalls=recall_info,
            farmer_origin=farmer_info,
            export_metadata=export_metadata,
        )
