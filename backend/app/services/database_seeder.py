from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.api.v1.auth import ensure_supply_chain_demo_users
from app.core.database import SessionLocal
from app.models.batch import Batch
from app.models.batch_relation import BatchRelation, BatchRelationType
from app.models.chain_event import ChainEvent
from app.models.cold_chain import (
    ColdChainViolation,
    TemperatureTelemetry,
    TransportTrip,
    TripBatch,
    TripStatus,
    ViolationType,
)
from app.models.farmer import FarmerIdentity
from app.models.handover import Handover, HandoverStatus
from app.models.land_plot import LandPlot
from app.models.material import BatchMaterialLog
from app.models.organization import Organization
from app.models.product import Product
from app.models.recall import (
    Recall,
    RecallAffectedBatch,
    RecallOrganizationAction,
    RecallSeverity,
    RecallStatus,
)
from app.services.batch_code_service import generate_unique_batch_code
from app.services.hash_chain_service import record_chain_event

logger = logging.getLogger(__name__)


def seed_database_if_empty(db: Session | None = None) -> dict[str, Any]:
    """
    Tự động kiểm tra và nạp dữ liệu mẫu ban đầu nếu cơ sở dữ liệu đang trống (0 lô hàng).
    Nạp đầy đủ 6 tài khoản/tổ chức, danh mục sản phẩm, thửa đất, 13 lô hàng qua 4 tầng tách/gộp,
    chuỗi hash SHA-256 thật, bàn giao, giám sát chuỗi lạnh và thu hồi khẩn cấp.
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        batch_count = db.query(Batch).count()
        if batch_count > 0:
            logger.info("Cơ sở dữ liệu đã có %d lô hàng, bỏ qua tự động seed.", batch_count)
            return {
                "status": "skipped",
                "message": f"Cơ sở dữ liệu đã có sẵn {batch_count} lô hàng.",
                "total_batches": batch_count,
            }

        logger.info("Cơ sở dữ liệu trống. Bắt đầu nạp dữ liệu mẫu toàn diện cho hệ thống...")
        return run_full_database_seed(db)
    finally:
        if should_close:
            db.close()


def run_full_database_seed(db: Session, force_reset: bool = False) -> dict[str, Any]:
    """
    Nạp dữ liệu mẫu toàn diện cho cả 6 vai trò chuỗi cung ứng:
    1. 6 Tổ chức & 6 Tài khoản người dùng (DEMO_USERS_CONFIG)
    2. Danh mục sản phẩm dùng chung toàn hệ thống (Product)
    3. Thửa đất vùng trồng (LandPlot) & Thông tin nông hộ NĐ 13 (FarmerIdentity)
    4. 13 Lô hàng qua 4 tầng phả hệ (Split/Merge DAG) với mã an toàn 8 ký tự chuẩn S-08
    5. Chuỗi sự kiện Hash SHA-256 nối chuỗi chuẩn S-10, S-12
    6. Bản ghi Bàn giao luân chuyển chuỗi cung ứng (Handover S-15, S-16)
    7. Chuyến vận chuyển lạnh & Cảm biến IoT nhiệt độ (ColdChain S-40 -> S-45)
    8. Lệnh thu hồi khẩn cấp và phong tỏa (Recall S-33 -> S-38)
    """
    if force_reset:
        logger.warning("Đang xóa sạch dữ liệu cũ để reset toàn bộ hệ thống...")
        db.query(RecallOrganizationAction).delete(synchronize_session=False)
        db.query(RecallAffectedBatch).delete(synchronize_session=False)
        db.query(Recall).delete(synchronize_session=False)
        db.query(TripBatch).delete(synchronize_session=False)
        db.query(ColdChainViolation).delete(synchronize_session=False)
        db.query(TemperatureTelemetry).delete(synchronize_session=False)
        db.query(TransportTrip).delete(synchronize_session=False)
        db.query(Handover).delete(synchronize_session=False)
        db.query(BatchMaterialLog).delete(synchronize_session=False)
        db.query(BatchRelation).delete(synchronize_session=False)
        db.query(ChainEvent).delete(synchronize_session=False)
        db.query(Batch).delete(synchronize_session=False)
        db.commit()

    # 1. Đảm bảo 6 tổ chức và 6 tài khoản người dùng
    ensure_supply_chain_demo_users(db)
    db.commit()

    org_farm = db.query(Organization).filter(Organization.id == 10).first()
    org_coop = db.query(Organization).filter(Organization.id == 20).first()
    org_log = db.query(Organization).filter(Organization.id == 30).first()
    org_ret = db.query(Organization).filter(Organization.id == 40).first()

    # 2. Danh mục sản phẩm dùng chung toàn hệ thống (S-07)
    sample_products = [
        ("Cà Chua Beef Hữu Cơ", "kg", "Cà chua giống Beef Đà Lạt đạt chuẩn hữu cơ GlobalGAP"),
        ("Dâu Tây New Zealand", "kg", "Dâu giống New Zealand trồng giá thể nhà màng VietGAP"),
        ("Dưa Lưới Huỳnh Long", "kg", "Dưa lưới ruột vàng vị ngọt thanh tiêu chuẩn Organic EU"),
        ("Bơ Sáp 034 Chuỗi Lạnh", "kg", "Bơ sáp 034 Đạ Sar kiểm soát bảo quản lạnh 3-5°C"),
        ("Nho Hạ Đen Quầy Kệ", "kg", "Nho hạ đen không hạt tiêu chuẩn phân phối hệ thống siêu thị"),
    ]
    for name, unit, desc in sample_products:
        p = db.query(Product).filter(Product.name == name).first()
        if not p:
            p = Product(name=name, unit=unit, description=desc)
            db.add(p)
    db.commit()

    # 3. Nông hộ định danh riêng biệt (S-56 - Nghị định 13/2023/NĐ-CP)
    farmer_ref = "FMR-DL-001"
    farmer = db.query(FarmerIdentity).filter(FarmerIdentity.farmer_ref_id == farmer_ref).first()
    if not farmer:
        farmer = FarmerIdentity(
            farmer_ref_id=farmer_ref,
            organization_id=org_farm.id,
            full_name="Nguyễn Văn Nông Nghiệp",
            phone="0912345678",
            id_card="049089012345",
            detail_address="Thôn 1, Xã Đạ Sar, Huyện Lạc Dương, Tỉnh Lâm Đồng",
            province="Lâm Đồng",
            is_anonymized=False,
        )
        db.add(farmer)
        db.commit()

    # 4. Thửa đất vùng trồng cho HTX Nông Nghiệp Thắng Lợi (org_id = 10)
    plot_a1 = db.query(LandPlot).filter(LandPlot.name == "Thửa A1 - Nhà Màng Cà Chua Beef").first()
    if not plot_a1:
        plot_a1 = LandPlot(
            name="Thửa A1 - Nhà Màng Cà Chua Beef",
            area=2500,
            unit="m2",
            address="Xã Đạ Sar, Huyện Lạc Dương, Tỉnh Lâm Đồng",
            latitude="11.9404",
            longitude="108.4583",
            organization_id=org_farm.id,
            farmer_ref_id=farmer_ref,
        )
        db.add(plot_a1)

    plot_b2 = db.query(LandPlot).filter(LandPlot.name == "Thửa B2 - Vườn Dâu Tây Hữu Cơ").first()
    if not plot_b2:
        plot_b2 = LandPlot(
            name="Thửa B2 - Vườn Dâu Tây Hữu Cơ",
            area=1800,
            unit="m2",
            address="Xã Đạ Sar, Huyện Lạc Dương, Tỉnh Lâm Đồng",
            latitude="11.9421",
            longitude="108.4595",
            organization_id=org_farm.id,
            farmer_ref_id=farmer_ref,
        )
        db.add(plot_b2)

    plot_c1 = db.query(LandPlot).filter(LandPlot.name == "Thửa C1 - Khu Dưa Lưới Huỳnh Long").first()
    if not plot_c1:
        plot_c1 = LandPlot(
            name="Thửa C1 - Khu Dưa Lưới Huỳnh Long",
            area=3200,
            unit="m2",
            address="Thôn Lạc Nghiệp, Huyện Đơn Dương, Tỉnh Lâm Đồng",
            latitude="11.7821",
            longitude="108.5714",
            organization_id=org_farm.id,
            farmer_ref_id=farmer_ref,
        )
        db.add(plot_c1)

    db.commit()
    db.refresh(plot_a1)
    db.refresh(plot_b2)
    db.refresh(plot_c1)

    # 5. Khởi tạo 13 Lô hàng qua 4 tầng phả hệ (S-08, S-17, S-18, S-19, S-22)
    # TẦNG 1: 3 Lô thu hoạch gốc (Roots) tại Vùng Trồng (Org 10)
    def make_batch(
        product_name: str,
        initial_qty: float,
        remaining_qty: float,
        unit: str,
        org_id: int,
        plot_id: int | None = None,
        farmer_id: str | None = None,
    ) -> Batch:
        code = generate_unique_batch_code(db)
        b = Batch(
            batch_code=code,
            product_name=product_name,
            initial_quantity=initial_qty,
            remaining_quantity=remaining_qty,
            unit=unit,
            organization_id=org_id,
            land_plot_id=plot_id,
            farmer_ref_id=farmer_id,
        )
        db.add(b)
        db.flush()
        return b

    # Level 1: Roots
    b_root1 = make_batch("Cà Chua Beef Hữu Cơ", 1000.0, 0.0, "kg", org_farm.id, plot_a1.id, farmer_ref)
    b_root2 = make_batch("Dâu Tây New Zealand", 450.0, 450.0, "kg", org_farm.id, plot_b2.id, farmer_ref)
    b_root3 = make_batch("Cà Chua Beef Hữu Cơ", 800.0, 0.0, "kg", org_farm.id, plot_a1.id, farmer_ref)

    # Ghi sự kiện HARVEST vào chuỗi băm của các lô gốc
    for root_b in [b_root1, b_root2, b_root3]:
        record_chain_event(
            db=db,
            batch_id=root_b.id,
            event_type="HARVEST",
            event_data={
                "batch_code": root_b.batch_code,
                "product_name": root_b.product_name,
                "quantity": root_b.initial_quantity,
                "unit": root_b.unit,
                "farmer_ref_id": root_b.farmer_ref_id,
                "land_plot_id": root_b.land_plot_id,
                "harvest_date": datetime.now(UTC).strftime("%Y-%m-%d"),
            },
            organization_id=org_farm.id,
        )

    # Level 2: Tách lô (Split) từ Root 1 và Root 3 tại Vùng Trồng
    b_split1a = make_batch("Cà Chua Beef Hữu Cơ", 600.0, 0.0, "kg", org_farm.id, plot_a1.id, farmer_ref)
    b_split1b = make_batch("Cà Chua Beef Hữu Cơ", 400.0, 0.0, "kg", org_farm.id, plot_a1.id, farmer_ref)

    b_split3a = make_batch("Cà Chua Beef Hữu Cơ", 500.0, 0.0, "kg", org_farm.id, plot_a1.id, farmer_ref)
    b_split3b = make_batch("Cà Chua Beef Hữu Cơ", 300.0, 0.0, "kg", org_farm.id, plot_a1.id, farmer_ref)

    # Lưu quan hệ Split
    db.add(BatchRelation(parent_batch_id=b_root1.id, child_batch_id=b_split1a.id, relation_type=BatchRelationType.SPLIT, quantity=600.0))
    db.add(BatchRelation(parent_batch_id=b_root1.id, child_batch_id=b_split1b.id, relation_type=BatchRelationType.SPLIT, quantity=400.0))
    db.add(BatchRelation(parent_batch_id=b_root3.id, child_batch_id=b_split3a.id, relation_type=BatchRelationType.SPLIT, quantity=500.0))
    db.add(BatchRelation(parent_batch_id=b_root3.id, child_batch_id=b_split3b.id, relation_type=BatchRelationType.SPLIT, quantity=300.0))
    db.flush()

    for child_b, parent_b, qty in [
        (b_split1a, b_root1, 600.0),
        (b_split1b, b_root1, 400.0),
        (b_split3a, b_root3, 500.0),
        (b_split3b, b_root3, 300.0),
    ]:
        record_chain_event(
            db=db,
            batch_id=child_b.id,
            event_type="BATCH_SPLIT_CREATED",
            event_data={
                "batch_code": child_b.batch_code,
                "parent_batch_code": parent_b.batch_code,
                "split_quantity": qty,
                "unit": child_b.unit,
            },
            organization_id=org_farm.id,
        )

    # Level 3: Gộp lô (Merge) tại HTX Sơ Chế Bảo Lộc (Org 20)
    # Lô M1 gộp từ 1A (600kg) + 3A (500kg) = 1100kg
    b_merge_m1 = make_batch("Cà Chua Beef Hữu Cơ", 1100.0, 0.0, "kg", org_coop.id)
    db.add(BatchRelation(parent_batch_id=b_split1a.id, child_batch_id=b_merge_m1.id, relation_type=BatchRelationType.MERGE, quantity=600.0))
    db.add(BatchRelation(parent_batch_id=b_split3a.id, child_batch_id=b_merge_m1.id, relation_type=BatchRelationType.MERGE, quantity=500.0))

    # Lô M2 gộp từ 1B (400kg) + 3B (300kg) = 700kg
    b_merge_m2 = make_batch("Cà Chua Beef Hữu Cơ", 700.0, 700.0, "kg", org_coop.id)
    db.add(BatchRelation(parent_batch_id=b_split1b.id, child_batch_id=b_merge_m2.id, relation_type=BatchRelationType.MERGE, quantity=400.0))
    db.add(BatchRelation(parent_batch_id=b_split3b.id, child_batch_id=b_merge_m2.id, relation_type=BatchRelationType.MERGE, quantity=300.0))
    db.flush()

    record_chain_event(
        db=db,
        batch_id=b_merge_m1.id,
        event_type="BATCH_MERGE_CREATED",
        event_data={
            "batch_code": b_merge_m1.batch_code,
            "parent_codes": [b_split1a.batch_code, b_split3a.batch_code],
            "total_quantity": 1100.0,
            "unit": "kg",
        },
        organization_id=org_coop.id,
    )
    record_chain_event(
        db=db,
        batch_id=b_merge_m2.id,
        event_type="BATCH_MERGE_CREATED",
        event_data={
            "batch_code": b_merge_m2.batch_code,
            "parent_codes": [b_split1b.batch_code, b_split3b.batch_code],
            "total_quantity": 700.0,
            "unit": "kg",
        },
        organization_id=org_coop.id,
    )

    # Level 4: Tách và Phân Phối Bán Lẻ tại Siêu Thị BioMart (Org 40)
    # Tách từ M1 (1100kg) thành Retail 1 (500kg) và Retail 2 (600kg)
    b_retail1 = make_batch("Cà Chua Beef Hữu Cơ", 500.0, 500.0, "kg", org_ret.id)
    b_retail2 = make_batch("Cà Chua Beef Hữu Cơ", 600.0, 600.0, "kg", org_ret.id)
    db.add(BatchRelation(parent_batch_id=b_merge_m1.id, child_batch_id=b_retail1.id, relation_type=BatchRelationType.SPLIT, quantity=500.0))
    db.add(BatchRelation(parent_batch_id=b_merge_m1.id, child_batch_id=b_retail2.id, relation_type=BatchRelationType.SPLIT, quantity=600.0))

    # Lô độc lập bổ sung: Dưa lưới và Bơ sáp
    b_melon = make_batch("Dưa Lưới Huỳnh Long", 1500.0, 1500.0, "kg", org_coop.id, plot_c1.id, farmer_ref)
    b_avo = make_batch("Bơ Sáp 034 Chuỗi Lạnh", 800.0, 800.0, "kg", org_log.id)

    db.flush()

    for ret_b, parent_b, q in [
        (b_retail1, b_merge_m1, 500.0),
        (b_retail2, b_merge_m1, 600.0),
        (b_melon, b_melon, 1500.0),
        (b_avo, b_avo, 800.0),
    ]:
        record_chain_event(
            db=db,
            batch_id=ret_b.id,
            event_type="BATCH_DISTRIBUTED",
            event_data={
                "batch_code": ret_b.batch_code,
                "quantity": q,
                "unit": ret_b.unit,
                "destination": "BioMart Supermarket",
            },
            organization_id=ret_b.organization_id,
        )

    # 6. Nhật ký vật tư & Thời gian cách ly PHI (S-62)
    applied_dt_str = (datetime.now(UTC) - timedelta(days=12)).strftime("%Y-%m-%d")
    safe_dt_str = (datetime.now(UTC) - timedelta(days=5)).strftime("%Y-%m-%d")
    mat_log = BatchMaterialLog(
        batch_id=b_root1.id,
        organization_id=org_farm.id,
        material_name="Chế phẩm sinh học Neem Oil",
        category="pesticide",
        dosage="50ml / 20L nước",
        applied_date=applied_dt_str,
        isolation_days=7,
        safe_harvest_date=safe_dt_str,
        applied_by="Kỹ sư Trần Nam",
        notes="Phun phòng bọ trĩ lứa quả non, đã cách ly đủ 7 ngày",
    )
    db.add(mat_log)
    record_chain_event(
        db=db,
        batch_id=b_root1.id,
        event_type="MATERIAL_APPLIED_PHI",
        event_data={
            "material_name": mat_log.material_name,
            "isolation_days": mat_log.isolation_days,
            "safe_harvest_date": safe_dt_str,
            "status": "COMPLIANT",
        },
        organization_id=org_farm.id,
    )

    # 7. Bàn giao luân chuyển chuỗi cung ứng (S-15, S-16)
    ho1 = Handover(
        batch_id=b_split1a.id,
        from_org_id=org_farm.id,
        to_org_id=org_coop.id,
        status=HandoverStatus.ACCEPTED.value,
        temperature="4.2°C",
    )
    db.add(ho1)
    record_chain_event(
        db=db,
        batch_id=b_split1a.id,
        event_type="HANDOVER_ACCEPTED",
        event_data={
            "handover_id": 1,
            "from_org": org_farm.name,
            "to_org": org_coop.name,
            "temperature": "4.2°C",
        },
        organization_id=org_coop.id,
    )

    ho2 = Handover(
        batch_id=b_retail1.id,
        from_org_id=org_coop.id,
        to_org_id=org_ret.id,
        status=HandoverStatus.PENDING.value,
        temperature="3.8°C",
    )
    db.add(ho2)

    # 8. Chuyến xe lạnh & Giám sát nhiệt độ (S-40 -> S-45)
    trip = TransportTrip(
        trip_code="TRIP-2026-COLD-01",
        vehicle_code="29C-8819 (Thùng Lạnh Thermo King)",
        carrier_org_id=org_log.id,
        driver_name="Lê Vận Tải",
        min_temperature=2.0,
        max_temperature=8.0,
        status=TripStatus.IN_TRANSIT.value,
        start_time=datetime.now(UTC) - timedelta(hours=3),
    )
    db.add(trip)
    db.flush()

    # Gắn lô retail1 và avo vào chuyến xe
    db.add(TripBatch(trip_id=trip.id, batch_id=b_retail1.id))
    db.add(TripBatch(trip_id=trip.id, batch_id=b_avo.id))
    db.flush()

    # Ghi nhận cảm biến IoT 3 điểm
    now = datetime.now(UTC)
    db.add(TemperatureTelemetry(trip_id=trip.id, timestamp=now - timedelta(hours=2), temperature=4.1))
    db.add(TemperatureTelemetry(trip_id=trip.id, timestamp=now - timedelta(hours=1), temperature=4.5))
    db.add(TemperatureTelemetry(trip_id=trip.id, timestamp=now - timedelta(minutes=10), temperature=4.2))

    # Ghi nhận 1 sự kiện vi phạm mẫu kèm nối hash chain (S-45)
    violation = ColdChainViolation(
        trip_id=trip.id,
        started_at=now - timedelta(hours=2),
        ended_at=now - timedelta(hours=1, minutes=15),
        duration_minutes=45.0,
        peak_temperature=15.5,
        threshold=8.0,
        violation_type=ViolationType.HIGH_TEMPERATURE.value,
        status="DETECTED",
        hash_recorded=True,
    )
    db.add(violation)
    db.flush()

    for carried_batch in [b_retail1, b_avo]:
        record_chain_event(
            db=db,
            batch_id=carried_batch.id,
            event_type="COLD_CHAIN_VIOLATION",
            event_data={
                "trip_code": trip.trip_code,
                "vehicle_code": trip.vehicle_code,
                "duration_minutes": 45.0,
                "peak_temperature": 15.5,
                "threshold": 8.0,
                "violation_type": "HIGH_TEMPERATURE",
            },
            organization_id=org_log.id,
        )

    # 9. Lệnh thu hồi khẩn cấp mẫu (S-33 -> S-38)
    recall = Recall(
        recall_code="REC-2026-DALAT-01",
        source_batch_id=b_split3b.id,
        initiator_organization_id=org_farm.id,
        reason="Cảnh báo phát hiện dư lượng hoạt chất bảo vệ thực vật vượt ngưỡng cho phép 0.02ppm",
        severity=RecallSeverity.CRITICAL.value,
        status=RecallStatus.ACTIVE.value,
        total_affected_batches=2,
        total_affected_kg=1000.0,
    )
    db.add(recall)
    db.flush()

    db.add(RecallAffectedBatch(recall_id=recall.id, batch_id=b_split3b.id, organization_id=org_farm.id, initial_quantity=300.0, remaining_quantity=300.0))
    db.add(RecallAffectedBatch(recall_id=recall.id, batch_id=b_merge_m2.id, organization_id=org_coop.id, initial_quantity=700.0, remaining_quantity=700.0))

    db.add(RecallOrganizationAction(recall_id=recall.id, organization_id=org_coop.id, status="PENDING", action_notes="Cần niêm phong lô M2"))
    db.add(RecallOrganizationAction(recall_id=recall.id, organization_id=org_farm.id, status="CONFIRMED_ISOLATED", action_notes="Đã cách ly tại kho"))

    record_chain_event(
        db=db,
        batch_id=b_split3b.id,
        event_type="RECALL_DECLARED",
        event_data={
            "recall_code": recall.recall_code,
            "reason": recall.reason,
            "severity": recall.severity,
        },
        organization_id=org_farm.id,
    )

    db.commit()

    all_seeded_batches = (
        db.query(Batch)
        .order_by(Batch.id.asc())
        .all()
    )
    codes_list = [b.batch_code for b in all_seeded_batches]

    logger.info("Nạp dữ liệu mẫu thành công với %d lô hàng: %s", len(codes_list), codes_list)

    return {
        "status": "success",
        "message": f"Đã nạp thành công bộ dữ liệu mẫu thật ({len(codes_list)} lô hàng, 6 vai trò, phả hệ 4 tầng, chuỗi băm SHA-256).",
        "total_batches": len(codes_list),
        "batch_codes": codes_list,
        "sample_batch_to_trace": codes_list[0],
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    session = SessionLocal()
    try:
        res = run_full_database_seed(session, force_reset=True)
        print(f"Seed hoan tat: {res}")
    finally:
        session.close()
