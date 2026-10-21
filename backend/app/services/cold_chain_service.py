from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.chain_event import ChainEvent
from app.models.cold_chain import (
    ColdChainViolation,
    TemperatureTelemetry,
    TransportTrip,
    TripBatch,
    TripStatus,
    ViolationType,
)
from app.models.handover import Handover
from app.models.organization import Organization
from app.models.user import User
from app.services.batch_access_service import can_view_batch
from app.schemas.cold_chain import (
    ColdChainViolationItem,
    ScenarioSimulationResponse,
    TelemetryReadingInput,
    TelemetryReadingItem,
    TransportTripDetailResponse,
    TransportTripResponse,
    TripBatchItem,
    TripCreateRequest,
)
from app.services.hash_chain_service import record_chain_event


def _normalize_dt(dt: datetime | None) -> datetime | None:
    """Đảm bảo datetime luôn có tzinfo UTC để so sánh chính xác trên mọi database (SQLite/Postgres)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class ColdChainService:
    @staticmethod
    def generate_trip_code() -> str:
        """Sinh mã chuyến xe lạnh duy nhất: TRIP-YYYYMMDD-XXXXXX."""
        date_str = datetime.now(UTC).strftime("%Y%m%d")
        rand_str = secrets.token_hex(3).upper()
        return f"TRIP-{date_str}-{rand_str}"

    @classmethod
    def create_trip(
        cls,
        db: Session,
        user: User,
        payload: TripCreateRequest,
    ) -> TransportTripResponse:
        """
        User Story S-40: Tạo Chuyến vận chuyển gồm: Mã chuyến, Mã thùng lạnh/xe lạnh, Danh sách các lô hàng đang chở.
        """
        role_lower = str(user.role).lower()
        allowed_roles = ["transporter", "logistics", "carrier", "admin", "system_admin"]
        if role_lower not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ Đơn vị vận chuyển lạnh (Transporter/Carrier/Logistics) hoặc Quản trị hệ thống mới có quyền tạo Chuyến vận chuyển.",
            )

        carrier_org_id = payload.carrier_org_id or user.organization_id
        if not carrier_org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vui lòng xác định Đơn vị vận chuyển lạnh (carrier_org_id).",
            )

        carrier_org = db.query(Organization).filter(Organization.id == carrier_org_id).first()
        if not carrier_org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy tổ chức vận chuyển với ID {carrier_org_id}.",
            )

        # Kiểm tra danh sách các lô hàng có tồn tại không
        batch_ids = list(set(payload.batch_ids))
        batches = db.query(Batch).filter(Batch.id.in_(batch_ids)).all()
        found_ids = {b.id for b in batches}
        missing_ids = set(batch_ids) - found_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy các lô hàng với ID: {list(missing_ids)}",
            )

        trip_code = payload.trip_code.strip() if payload.trip_code else cls.generate_trip_code()

        # Kiểm tra mã chuyến có bị trùng lặp không
        existing_trip = db.query(TransportTrip).filter(TransportTrip.trip_code == trip_code).first()
        if existing_trip:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã chuyến {trip_code} đã tồn tại trong hệ thống.",
            )

        trip = TransportTrip(
            trip_code=trip_code,
            vehicle_code=payload.vehicle_code.strip(),
            carrier_org_id=carrier_org_id,
            driver_name=payload.driver_name.strip() if payload.driver_name else None,
            min_temperature=payload.min_temperature,
            max_temperature=payload.max_temperature,
            status=TripStatus.IN_TRANSIT.value,
            start_time=datetime.now(UTC),
        )
        db.add(trip)
        db.flush()

        batch_items = []
        for b in batches:
            tb = TripBatch(trip_id=trip.id, batch_id=b.id)
            db.add(tb)
            batch_items.append(
                TripBatchItem(batch_id=b.id, batch_code=b.batch_code, product_name=b.product_name)
            )

            # Ghi nhận sự kiện xuất phát vận chuyển vào Hash Chain của từng lô
            record_chain_event(
                db=db,
                batch_id=b.id,
                event_type="COLD_CHAIN_DISPATCH",
                event_data=(
                    f"Khởi hành chuyến xe lạnh {trip.trip_code} ({trip.vehicle_code}) "
                    f"bởi {carrier_org.name}. Ngưỡng bảo quản: {trip.min_temperature}°C - {trip.max_temperature}°C."
                ),
                organization_id=carrier_org_id,
            )

        db.commit()
        db.refresh(trip)

        return TransportTripResponse(
            id=trip.id,
            trip_code=trip.trip_code,
            vehicle_code=trip.vehicle_code,
            carrier_org_id=trip.carrier_org_id,
            carrier_org_name=carrier_org.name,
            driver_name=trip.driver_name,
            min_temperature=trip.min_temperature,
            max_temperature=trip.max_temperature,
            status=trip.status,
            start_time=trip.start_time,
            end_time=trip.end_time,
            created_at=trip.created_at,
            batches=batch_items,
            violations_count=0,
            readings_count=0,
        )

    @classmethod
    def list_trips(
        cls,
        db: Session,
        user: User,
        status_filter: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[TransportTripResponse]:
        """Lấy danh sách các chuyến vận chuyển chuỗi lạnh (S-40)."""
        query = db.query(TransportTrip)
        role_lower = str(user.role).lower()
        is_admin_or_inspector = role_lower in ("system_admin", "admin", "inspector")

        # 1. Quản trị hệ thống & Cán bộ kiểm tra: Xem toàn bộ chuyến xe trong chuỗi cung ứng
        if is_admin_or_inspector:
            pass
        elif role_lower in ("carrier", "transporter", "logistics"):
            # 2. Đơn vị vận chuyển lạnh: CHỈ xem các chuyến do chính tổ chức mình phụ trách
            if user.organization_id:
                query = query.filter(TransportTrip.carrier_org_id == user.organization_id)
            else:
                query = query.filter(TransportTrip.id == -1)
        else:
            # 3. Nông hộ, HTX, Nhà phân phối:
            # Không trực tiếp phụ trách chuyến xe nên thấy chuyến xe nếu có lô hàng liên quan đến tổ chức của mình
            if user.organization_id:
                org_batch_ids = {
                    b_id
                    for (b_id,) in db.query(Batch.id)
                    .filter(Batch.organization_id == user.organization_id)
                    .all()
                }
                # Lấy thêm các lô hàng qua Handover (from_org_id hoặc to_org_id)
                handover_batch_ids = {
                    h_b_id
                    for (h_b_id,) in db.query(Handover.batch_id)
                    .filter(
                        (Handover.from_org_id == user.organization_id)
                        | (Handover.to_org_id == user.organization_id)
                    )
                    .all()
                }
                org_batch_ids.update(handover_batch_ids)
                # Lấy thêm các lô hàng có ChainEvent của tổ chức này
                event_batch_ids = {
                    e_b_id
                    for (e_b_id,) in db.query(ChainEvent.batch_id)
                    .filter(ChainEvent.organization_id == user.organization_id)
                    .all()
                }
                org_batch_ids.update(event_batch_ids)

                if org_batch_ids:
                    query = (
                        query.join(TripBatch, TripBatch.trip_id == TransportTrip.id)
                        .filter(TripBatch.batch_id.in_(org_batch_ids))
                        .distinct()
                    )
                else:
                    query = query.filter(TransportTrip.id == -1)
            else:
                query = query.filter(TransportTrip.id == -1)

        if status_filter:
            query = query.filter(TransportTrip.status == status_filter)

        trips = query.order_by(TransportTrip.created_at.desc()).offset(skip).limit(limit).all()

        results = []
        for t in trips:
            carrier_name = t.carrier_organization.name if t.carrier_organization else None
            batch_items = [
                TripBatchItem(
                    batch_id=tb.batch.id,
                    batch_code=tb.batch.batch_code,
                    product_name=tb.batch.product_name,
                )
                for tb in t.trip_batches
                if tb.batch
            ]
            v_count = len(t.violations)
            r_count = len(t.telemetry_readings)
            results.append(
                TransportTripResponse(
                    id=t.id,
                    trip_code=t.trip_code,
                    vehicle_code=t.vehicle_code,
                    license_plate=t.vehicle_code,
                    carrier_org_id=t.carrier_org_id,
                    carrier_org_name=carrier_name,
                    carrier_name=carrier_name,
                    driver_name=t.driver_name,
                    min_temperature=t.min_temperature,
                    max_temperature=t.max_temperature,
                    status=t.status,
                    start_time=t.start_time,
                    end_time=t.end_time,
                    created_at=t.created_at,
                    batches=batch_items,
                    violations_count=v_count,
                    violation_count=v_count,
                    readings_count=r_count,
                )
            )
        return results

    @classmethod
    def get_trip_detail(
        cls, db: Session, trip_id: int, user: User | None = None
    ) -> TransportTripDetailResponse:
        """Xem chi tiết chuyến xe, gồm các lô hàng, danh sách vi phạm và telemetry gần nhất."""
        trip = db.query(TransportTrip).filter(TransportTrip.id == trip_id).first()
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy chuyến xe với ID {trip_id}.",
            )

        if user:
            role_lower = str(user.role).lower()
            if role_lower not in ("system_admin", "admin", "inspector"):
                if role_lower in ("carrier", "transporter", "logistics"):
                    if trip.carrier_org_id != user.organization_id:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Bạn không có quyền xem chi tiết chuyến xe của đơn vị vận chuyển khác.",
                        )
                else:
                    trip_batch_org_ids = {
                        tb.batch.organization_id for tb in trip.trip_batches if tb.batch
                    }
                    related_org_ids = set(trip_batch_org_ids)
                    for tb in trip.trip_batches:
                        if tb.batch:
                            for h in tb.batch.handovers:
                                if h.from_org_id:
                                    related_org_ids.add(h.from_org_id)
                                if h.to_org_id:
                                    related_org_ids.add(h.to_org_id)
                    if user.organization_id and user.organization_id not in related_org_ids:
                        has_access = False
                        for tb in trip.trip_batches:
                            if tb.batch and can_view_batch(user.organization_id, tb.batch, db, user.role)[0]:
                                has_access = True
                                break
                        if not has_access:
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail="Bạn không có quyền xem thông tin chuyến xe này.",
                            )

        carrier_name = trip.carrier_organization.name if trip.carrier_organization else None
        batch_items = [
            TripBatchItem(
                batch_id=tb.batch.id,
                batch_code=tb.batch.batch_code,
                product_name=tb.batch.product_name,
            )
            for tb in trip.trip_batches
            if tb.batch
        ]

        violation_items = [
            ColdChainViolationItem(
                id=v.id,
                trip_id=v.trip_id,
                started_at=v.started_at,
                ended_at=v.ended_at,
                start_time=v.started_at,
                end_time=v.ended_at,
                duration_minutes=v.duration_minutes,
                peak_temperature=v.peak_temperature,
                threshold=v.threshold,
                violation_type=v.violation_type,
                status=v.status,
                hash_recorded=v.hash_recorded,
                created_at=v.created_at,
            )
            for v in trip.violations
        ]

        recent_readings = [
            TelemetryReadingItem(timestamp=r.timestamp, temperature=r.temperature)
            for r in trip.telemetry_readings[-100:]  # 100 điểm gần nhất
        ]

        return TransportTripDetailResponse(
            id=trip.id,
            trip_code=trip.trip_code,
            vehicle_code=trip.vehicle_code,
            license_plate=trip.vehicle_code,
            carrier_org_id=trip.carrier_org_id,
            carrier_org_name=carrier_name,
            carrier_name=carrier_name,
            driver_name=trip.driver_name,
            min_temperature=trip.min_temperature,
            max_temperature=trip.max_temperature,
            status=trip.status,
            start_time=trip.start_time,
            end_time=trip.end_time,
            created_at=trip.created_at,
            batches=batch_items,
            violations_count=len(violation_items),
            violation_count=len(violation_items),
            readings_count=len(trip.telemetry_readings),
            violations=violation_items,
            recent_telemetry=recent_readings,
            telemetry=recent_readings,
        )

    @classmethod
    def ingest_telemetry(
        cls,
        db: Session,
        readings: list[TelemetryReadingInput],
        user: User | None = None,
    ) -> dict[str, Any]:
        """
        User Story S-41: Endpoint nhận mảng dữ liệu cảm biến: { trip_id, timestamp, temperature }.
        - Bỏ qua các bản ghi có timestamp cũ hơn bản ghi mới nhất đã lưu.
        - Gọi thuật toán phát hiện vi phạm có độ trễ 30 phút (S-43).
        - Tự động ghi vi phạm vào Hash Chain của toàn bộ lô hàng trên chuyến xe (S-45).
        """
        if not readings:
            return {
                "accepted_count": 0,
                "ignored_count": 0,
                "message": "Không có dữ liệu telemetry nào được gửi.",
                "violations_detected": [],
            }

        # Nhóm dữ liệu theo trip_id
        trips_readings: dict[int, list[TelemetryReadingInput]] = {}
        for r in readings:
            trips_readings.setdefault(r.trip_id, []).append(r)

        total_accepted = 0
        total_ignored = 0
        all_new_violations: list[ColdChainViolationItem] = []

        for trip_id, t_readings in trips_readings.items():
            trip = db.query(TransportTrip).filter(TransportTrip.id == trip_id).first()
            if not trip:
                # Bỏ qua nếu trip_id không tồn tại
                total_ignored += len(t_readings)
                continue

            # Lấy timestamp mới nhất đã lưu trong DB cho chuyến này
            latest_db_ts = (
                db.query(func.max(TemperatureTelemetry.timestamp))
                .filter(TemperatureTelemetry.trip_id == trip_id)
                .scalar()
            )
            latest_norm_ts = _normalize_dt(latest_db_ts)

            # Sắp xếp các bản ghi mới gửi theo timestamp tăng dần
            t_readings.sort(
                key=lambda x: _normalize_dt(x.timestamp) or datetime.min.replace(tzinfo=UTC)
            )

            accepted_for_trip = []
            for r in t_readings:
                r_norm_ts = _normalize_dt(r.timestamp)
                # Quy tắc S-41: Bỏ qua các bản ghi có timestamp cũ hơn bản ghi mới nhất đã lưu
                if latest_norm_ts is not None and r_norm_ts is not None and r_norm_ts <= latest_norm_ts:
                    total_ignored += 1
                    continue
                # Bỏ qua nếu trùng timestamp ngay trong batch gửi
                if accepted_for_trip:
                    last_acc_norm = _normalize_dt(accepted_for_trip[-1].timestamp)
                    if last_acc_norm is not None and r_norm_ts is not None and r_norm_ts <= last_acc_norm:
                        total_ignored += 1
                        continue

                accepted_for_trip.append(r)

            if accepted_for_trip:
                # Lưu các bản ghi hợp lệ vào DB
                for valid_r in accepted_for_trip:
                    telemetry_obj = TemperatureTelemetry(
                        trip_id=trip_id,
                        timestamp=valid_r.timestamp,
                        temperature=valid_r.temperature,
                    )
                    db.add(telemetry_obj)
                db.flush()
                total_accepted += len(accepted_for_trip)

                # Chạy thuật toán phát hiện vi phạm chuỗi lạnh S-43 và ghi Hash Chain S-45
                new_violations = cls.detect_and_record_violations(db, trip, actor_id=user.id if user else None)
                all_new_violations.extend(new_violations)

        db.commit()

        return {
            "accepted_count": total_accepted,
            "ignored_count": total_ignored,
            "message": f"Đã tiếp nhận thành công {total_accepted} điểm đo nhiệt độ (bỏ qua {total_ignored} điểm cũ).",
            "violations_detected": all_new_violations,
        }

    @classmethod
    def detect_and_record_violations(
        cls,
        db: Session,
        trip: TransportTrip,
        actor_id: int | None = None,
    ) -> list[ColdChainViolationItem]:
        """
        User Story S-43: Thuật toán phát hiện vi phạm có độ trễ 30 phút:
        - Nhiệt độ vượt quá ngưỡng cho phép nhất thời (ví dụ: mở cửa xe vài phút) KHÔNG bị coi là vi phạm.
        - Chỉ khi nhiệt độ vượt ngưỡng LIÊN TỤC TRÊN 30 PHÚT thì hệ thống mới kích hoạt 1 sự kiện "Vi phạm chuỗi lạnh".
        - Hai lần vượt ngưỡng cách nhau dưới 5 phút thì gộp thành 1 lần vi phạm duy nhất.
        User Story S-45:
        - Tự động ghi sự kiện vi phạm vào chuỗi hash của toàn bộ các lô hàng có mặt trên chuyến xe đó.
        """
        # Lấy toàn bộ telemetry của chuyến xe theo thứ tự thời gian
        readings = (
            db.query(TemperatureTelemetry)
            .filter(TemperatureTelemetry.trip_id == trip.id)
            .order_by(TemperatureTelemetry.timestamp.asc())
            .all()
        )
        if len(readings) < 2:
            return []

        max_threshold = trip.max_temperature
        min_threshold = trip.min_temperature

        # 1. Gom nhóm các điểm vượt ngưỡng thành các đợt (raw episodes)
        raw_episodes: list[dict[str, Any]] = []
        current_ep: dict[str, Any] | None = None

        for r in readings:
            is_over = r.temperature > max_threshold
            is_under = r.temperature < min_threshold

            if is_over or is_under:
                v_type = ViolationType.HIGH_TEMPERATURE.value if is_over else ViolationType.FREEZING.value
                thresh = max_threshold if is_over else min_threshold

                if current_ep is None:
                    current_ep = {
                        "started_at": r.timestamp,
                        "ended_at": r.timestamp,
                        "peak_temp": r.temperature,
                        "v_type": v_type,
                        "threshold": thresh,
                    }
                else:
                    current_ep["ended_at"] = r.timestamp
                    if is_over:
                        current_ep["peak_temp"] = max(current_ep["peak_temp"], r.temperature)
                    else:
                        current_ep["peak_temp"] = min(current_ep["peak_temp"], r.temperature)
            else:
                if current_ep is not None:
                    raw_episodes.append(current_ep)
                    current_ep = None

        if current_ep is not None:
            raw_episodes.append(current_ep)

        if not raw_episodes:
            return []

        # 2. Quy tắc S-43: Hai lần vượt ngưỡng cách nhau DƯỚI 5 PHÚT (300 giây) thì GỘP THÀNH 1 LẦN VI PHẠM DUY NHẤT
        merged_episodes: list[dict[str, Any]] = []
        for ep in raw_episodes:
            if not merged_episodes:
                merged_episodes.append(ep)
            else:
                prev = merged_episodes[-1]
                ep_start = _normalize_dt(ep["started_at"])
                prev_end = _normalize_dt(prev["ended_at"])
                gap_seconds = (
                    (ep_start - prev_end).total_seconds()
                    if (ep_start is not None and prev_end is not None)
                    else 999999.0
                )
                # Nếu cách nhau < 300 giây (5 phút) và cùng loại vi phạm: gộp lại
                if gap_seconds < 300 and prev["v_type"] == ep["v_type"]:
                    ep_end = _normalize_dt(ep["ended_at"])
                    if ep_end is not None and prev_end is not None and ep_end > prev_end:
                        prev["ended_at"] = ep["ended_at"]
                    if prev["v_type"] == ViolationType.HIGH_TEMPERATURE.value:
                        prev["peak_temp"] = max(prev["peak_temp"], ep["peak_temp"])
                    else:
                        prev["peak_temp"] = min(prev["peak_temp"], ep["peak_temp"])
                else:
                    merged_episodes.append(ep)

        # 3. Quy tắc S-43: Chỉ khi nhiệt độ vượt ngưỡng LIÊN TỤC TRÊN 30 PHÚT mới kích hoạt vi phạm
        new_violations: list[ColdChainViolationItem] = []
        batches_on_trip = [tb.batch for tb in trip.trip_batches if tb.batch]

        for ep in merged_episodes:
            ep_start = _normalize_dt(ep["started_at"])
            ep_end = _normalize_dt(ep["ended_at"])
            duration_minutes = (
                (ep_end - ep_start).total_seconds() / 60.0
                if (ep_start is not None and ep_end is not None)
                else 0.0
            )

            # Tiêu chí S-43: Phải liên tục từ 30 phút trở lên (>= 30.0 phút)
            if duration_minutes < 30.0:
                continue

            # Kiểm tra xem đợt vi phạm này đã được lưu vào database chưa
            existing = (
                db.query(ColdChainViolation)
                .filter(
                    ColdChainViolation.trip_id == trip.id,
                    ColdChainViolation.started_at == ep["started_at"],
                )
                .first()
            )

            if existing:
                # Nếu đợt vi phạm cũ tiếp tục kéo dài: cập nhật lại ended_at và peak_temp
                if existing.ended_at < ep["ended_at"]:
                    existing.ended_at = ep["ended_at"]
                    existing.duration_minutes = round(duration_minutes, 1)
                    existing.peak_temperature = ep["peak_temp"]
                continue

            # Tạo bản ghi vi phạm mới
            violation = ColdChainViolation(
                trip_id=trip.id,
                started_at=ep["started_at"],
                ended_at=ep["ended_at"],
                duration_minutes=round(duration_minutes, 1),
                peak_temperature=ep["peak_temp"],
                threshold=ep["threshold"],
                violation_type=ep["v_type"],
                status="DETECTED",
                hash_recorded=False,
            )
            db.add(violation)
            db.flush()

            # 4. User Story S-45: Tự động ghi sự kiện vi phạm vào Hash Chain của toàn bộ các lô hàng trên chuyến xe
            for b in batches_on_trip:
                record_chain_event(
                    db=db,
                    batch_id=b.id,
                    event_type="COLD_CHAIN_VIOLATION",
                    event_data=(
                        f"CẢNH BÁO VI PHẠM CHUỖI LẠNH trên chuyến xe {trip.vehicle_code} (#{trip.trip_code}): "
                        f"Nhiệt độ đỉnh {ep['peak_temp']}°C vượt ngưỡng {ep['threshold']}°C "
                        f"liên tục {round(duration_minutes, 1)} phút. "
                        f"Bắt đầu: {ep['started_at'].isoformat()} - Kết thúc: {ep['ended_at'].isoformat()}."
                    ),
                    organization_id=trip.carrier_org_id,
                )

            violation.hash_recorded = True
            db.flush()

            new_violations.append(
                ColdChainViolationItem(
                    id=violation.id,
                    trip_id=violation.trip_id,
                    started_at=violation.started_at,
                    ended_at=violation.ended_at,
                    duration_minutes=violation.duration_minutes,
                    peak_temperature=violation.peak_temperature,
                    threshold=violation.threshold,
                    violation_type=violation.violation_type,
                    status=violation.status,
                    hash_recorded=violation.hash_recorded,
                    created_at=violation.created_at,
                )
            )

        return new_violations

    @classmethod
    def simulate_scenario(
        cls,
        db: Session,
        trip_id: int,
        scenario_id: int,
        reset_previous_telemetry: bool = True,
        user: User | None = None,
    ) -> ScenarioSimulationResponse:
        """
        User Story S-42: Script Giả lập Cảm biến theo 5 kịch bản mẫu:
        - Kịch bản 1: Không vượt ngưỡng (ổn định an toàn 2°C - 8°C).
        - Kịch bản 2: Vượt ngưỡng 10 phút (mở cửa xe tạm thời) -> KHÔNG tính là vi phạm.
        - Kịch bản 3: Vượt ngưỡng liên tục 45 phút (> 30 phút) -> Tính 1 vi phạm.
        - Kịch bản 4: Hai lần vượt cách nhau dưới 5 phút -> Gộp thành 1 vi phạm.
        - Kịch bản 5: Vượt qua nửa đêm (cross-midnight).
        """
        trip = db.query(TransportTrip).filter(TransportTrip.id == trip_id).first()
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy chuyến xe với ID {trip_id}.",
            )

        if user:
            role_lower = str(user.role).lower()
            if role_lower not in ("carrier", "transporter", "logistics", "admin", "system_admin"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Chỉ Đơn vị vận chuyển hoặc Quản trị hệ thống mới có quyền chạy mô phỏng cảm biến IoT.",
                )
            if role_lower in ("carrier", "transporter", "logistics") and trip.carrier_org_id != user.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bạn không có quyền can thiệp vào chuyến xe của đơn vị vận chuyển khác.",
                )

        if reset_previous_telemetry:
            # Xóa các bản ghi telemetry và vi phạm cũ của chuyến để quan sát kịch bản độc lập
            db.query(ColdChainViolation).filter(ColdChainViolation.trip_id == trip_id).delete(
                synchronize_session=False
            )
            db.query(TemperatureTelemetry).filter(TemperatureTelemetry.trip_id == trip_id).delete(
                synchronize_session=False
            )
            db.commit()

        now = datetime.now(UTC)
        readings_to_inject: list[dict[str, Any]] = []

        if scenario_id == 1:
            scenario_name = "Kịch bản 1: Không vượt ngưỡng"
            description = (
                "Nhiệt độ bảo quản lạnh được duy trì ổn định trong dải an toàn (3.5°C - 5.0°C) "
                "suốt hành trình 60 phút."
            )
            rule_explanation = (
                "Nhiệt độ hoàn toàn nằm trong dải cho phép (2.0°C - 8.0°C). "
                "Hệ thống xác nhận hành trình đạt chuẩn, không có vi phạm nào."
            )
            base_time = now - timedelta(minutes=60)
            offsets_and_temps = [
                (0, 4.0),
                (5, 4.2),
                (10, 3.8),
                (15, 4.5),
                (20, 4.1),
                (25, 4.8),
                (30, 5.0),
                (35, 4.3),
                (40, 3.9),
                (45, 4.1),
                (50, 4.4),
                (55, 4.0),
            ]
            for m, temp in offsets_and_temps:
                readings_to_inject.append({"timestamp": base_time + timedelta(minutes=m), "temp": temp})

        elif scenario_id == 2:
            scenario_name = "Kịch bản 2: Vượt ngưỡng 10 phút (mở cửa xe tạm thời) -> KHÔNG tính vi phạm"
            description = (
                "Xe mở cửa bốc dỡ hàng tại điểm dừng làm nhiệt độ tăng lên 13.5°C trong vòng 10 phút, "
                "sau đó đóng kín thùng làm lạnh về 4.0°C."
            )
            rule_explanation = (
                "Độ trễ vi phạm 30 phút (S-43): Dao động nhiệt nhất thời dưới 30 phút (10 phút) "
                "được công nhận là hoạt động vận hành bình thường, KHÔNG bị coi là vi phạm."
            )
            base_time = now - timedelta(minutes=40)
            offsets_and_temps = [
                (0, 4.0),
                (5, 4.2),
                (10, 12.0),  # Bắt đầu mở cửa xe
                (15, 13.5),  # Đỉnh nhiệt độ
                (20, 10.5),  # Đóng cửa xe (vượt 10 phút)
                (25, 4.5),   # Trở về an toàn
                (30, 4.0),
            ]
            for m, temp in offsets_and_temps:
                readings_to_inject.append({"timestamp": base_time + timedelta(minutes=m), "temp": temp})

        elif scenario_id == 3:
            scenario_name = "Kịch bản 3: Vượt ngưỡng liên tục 45 phút (> 30 phút) -> Tính 1 vi phạm"
            description = (
                "Hệ thống làm lạnh gặp sự cố làm nhiệt độ vượt 8°C liên tục suốt 45 phút, "
                "nhiệt độ đỉnh đạt 16.5°C trước khi kỹ thuật viên khắc phục."
            )
            rule_explanation = (
                "Quy tắc S-43 & S-45: Nhiệt độ vượt ngưỡng liên tục trên 30 phút (45 phút) "
                "kích hoạt 1 sự kiện Vi phạm chuỗi lạnh và tự động ghi vào chuỗi Hash SHA-256."
            )
            base_time = now - timedelta(minutes=65)
            offsets_and_temps = [
                (0, 4.0),
                (5, 4.5),
                (10, 9.5),   # Bắt đầu vượt ngưỡng
                (20, 13.0),
                (30, 16.5),  # Đỉnh nhiệt độ 16.5°C
                (40, 15.0),
                (50, 12.0),
                (55, 9.2),   # Kết thúc đợt (45 phút)
                (60, 4.5),   # Làm lạnh sâu trở lại
            ]
            for m, temp in offsets_and_temps:
                readings_to_inject.append({"timestamp": base_time + timedelta(minutes=m), "temp": temp})

        elif scenario_id == 4:
            scenario_name = "Kịch bản 4: Hai lần vượt cách nhau dưới 5 phút -> Gộp thành 1 vi phạm"
            description = (
                "Lần 1 vượt 18 phút (đỉnh 12°C), hạ nhiệt 3 phút (< 5 phút), sau đó vượt tiếp 20 phút (đỉnh 15.5°C)."
            )
            rule_explanation = (
                "Quy tắc Gộp vi phạm (S-43): Hai lần vượt ngưỡng cách nhau dưới 5 phút (300s) "
                "tự động gộp thành 1 sự kiện vi phạm duy nhất (tổng 41 phút > 30 phút)."
            )
            base_time = now - timedelta(minutes=55)
            offsets_and_temps = [
                (0, 9.0),    # Bắt đầu đợt 1
                (10, 12.0),
                (18, 9.5),   # Kết thúc đợt 1 (18 phút)
                (20, 6.0),   # Hạ nhiệt ngắn 2-3 phút (< 5 phút)
                (21, 9.8),   # Bắt đầu đợt 2
                (30, 15.5),  # Đỉnh đợt 2
                (41, 9.0),   # Kết thúc đợt 2 (kéo dài 20 phút)
                (45, 4.0),   # Trở lại an toàn
            ]
            for m, temp in offsets_and_temps:
                readings_to_inject.append({"timestamp": base_time + timedelta(minutes=m), "temp": temp})

        elif scenario_id == 5:
            scenario_name = "Kịch bản 5: Vượt qua nửa đêm (Cross-midnight)"
            description = (
                "Sự cố nhiệt độ bắt đầu lúc 23:40 đêm hôm trước, kéo dài xuyên qua 00:00 "
                "đến 00:25 sáng hôm sau (tổng 45 phút, đỉnh 15.8°C)."
            )
            rule_explanation = (
                "Xử lý chuẩn hóa thời gian UTC liên tục: Vi phạm xuyên qua mốc nửa đêm (00:00) "
                "vẫn được ghi nhận chính xác là 1 vi phạm duy nhất, không bị chia tách hay lỗi ngày."
            )
            # Tạo mốc đêm hôm trước lúc 23:35
            base_date = (now - timedelta(days=1)).replace(hour=23, minute=35, second=0, microsecond=0)
            offsets_and_temps = [
                (0, 4.0),    # 23:35
                (5, 10.0),   # 23:40: bắt đầu vượt
                (15, 13.5),  # 23:50
                (24, 15.8),  # 23:59: Đỉnh nhiệt độ lúc nửa đêm
                (35, 14.0),  # 00:10 (hôm sau)
                (45, 11.5),  # 00:20 (hôm sau)
                (50, 9.0),   # 00:25 (hôm sau, kết thúc 45 phút)
                (55, 4.5),   # 00:30 (hôm sau, hạ về an toàn)
            ]
            for m, temp in offsets_and_temps:
                readings_to_inject.append({"timestamp": base_date + timedelta(minutes=m), "temp": temp})

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Kịch bản #{scenario_id} không hợp lệ. Vui lòng chọn từ 1 đến 5.",
            )

        # Lưu các điểm đo vào bảng TemperatureTelemetry
        for item in readings_to_inject:
            db.add(
                TemperatureTelemetry(
                    trip_id=trip.id,
                    timestamp=item["timestamp"],
                    temperature=item["temp"],
                )
            )
        db.flush()

        # Gọi thuật toán phát hiện vi phạm và ghi Hash Chain
        detected_violations = cls.detect_and_record_violations(
            db=db,
            trip=trip,
            actor_id=user.id if user else None,
        )
        db.commit()

        violations_count = len(detected_violations)
        is_violated = violations_count > 0

        return ScenarioSimulationResponse(
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            trip_id=trip.id,
            trip_code=trip.trip_code,
            vehicle_code=trip.vehicle_code,
            readings_injected=len(readings_to_inject),
            violations_count=violations_count,
            violations=detected_violations,
            is_violated=is_violated,
            description=description,
            rule_explanation=rule_explanation,
            hash_chain_updated=is_violated,
        )

