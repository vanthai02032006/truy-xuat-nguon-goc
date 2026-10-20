from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.batch import Batch
from app.models.chain_event import ChainEvent

# Chuỗi khởi đầu cố định (GENESIS) cho sự kiện đầu tiên của lô hàng (Task T-24)
GENESIS_HASH = "GENESIS"
VALID_GENESIS_HASHES = {GENESIS_HASH, "GENESIS_HASH", "0" * 64}


def canonicalize_event_data(event_data: Any) -> str:
    """
    Chuẩn hóa nội dung sự kiện theo chuẩn Canonical JSON (Task T-24):
    1. Sắp xếp thứ tự các khóa theo bảng chữ cái (alphabetical key sorting).
    2. Định dạng ngày, giờ và số cố định.
    3. Bỏ khoảng trắng thừa (separators=(',', ':'), strip text).
    4. Đảm bảo tính tất định: Hai đối tượng JSON có cùng nội dung nhưng thứ tự khóa
       khác nhau sẽ luôn ra cùng một chuỗi chuẩn hóa và cùng một mã băm SHA-256.
    """
    if event_data is None:
        return ""

    parsed = None
    if isinstance(event_data, str):
        trimmed = event_data.strip()
        if (trimmed.startswith("{") and trimmed.endswith("}")) or (
            trimmed.startswith("[") and trimmed.endswith("]")
        ):
            try:
                parsed = json.loads(trimmed)
            except (json.JSONDecodeError, ValueError):
                parsed = None
        if parsed is None:
            # Không phải định dạng JSON -> chuỗi văn bản thông thường
            return trimmed
    else:
        parsed = event_data

    def _normalize(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                str(k).strip(): _normalize(v)
                for k, v in sorted(obj.items(), key=lambda item: str(item[0]))
            }
        elif isinstance(obj, list):
            return [_normalize(x) for x in obj]
        elif isinstance(obj, float):
            if obj.is_integer():
                return int(obj)
            return round(obj, 6)
        elif isinstance(obj, (datetime, date)):
            if isinstance(obj, datetime):
                if obj.tzinfo is not None:
                    return obj.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                return obj.strftime("%Y-%m-%dT%H:%M:%SZ")
            return obj.isoformat()
        elif isinstance(obj, str):
            return obj.strip()
        return obj

    normalized = _normalize(parsed)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def format_event_timestamp(dt: datetime | str | None) -> str:
    """Định dạng mốc thời gian cố định phục vụ hàm băm."""
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt.strip()
    if isinstance(dt, datetime):
        if dt.tzinfo is not None:
            dt = dt.astimezone(UTC).replace(tzinfo=None)
        return dt.isoformat()
    return str(dt)


def calculate_event_hash(
    batch_id: int,
    event_type: str,
    event_data: Any,
    org_id: int | None,
    prev_hash: str,
    timestamp_str: str | datetime | None = "",
) -> str:
    """
    Tính giá trị băm SHA-256 chuẩn hóa cho một sự kiện chuỗi cung ứng (S-10, T-24).
    Nội dung sự kiện được chuẩn hóa Canonical JSON trước khi tính băm.
    """
    canonical_data = canonicalize_event_data(event_data)
    ts_str = format_event_timestamp(timestamp_str)
    raw = f"{batch_id}|{event_type}|{canonical_data}|{org_id or ''}|{prev_hash}|{ts_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def record_chain_event(
    db: Session,
    batch_id: int,
    event_type: str,
    event_data: Any,
    organization_id: int | None,
    timestamp: datetime | None = None,
) -> ChainEvent:
    """
    Ghi một sự kiện mới vào chuỗi Hash SHA-256 (User Story S-10, S-11, T-24, T-26).
    - Sự kiện đầu tiên của lô dùng prev_hash là chuỗi khởi đầu cố định (GENESIS).
    - Các sự kiện tiếp theo nối tiếp prev_hash = current_hash của sự kiện trước đó của lô.
    - Bảng là append-only, được bảo chứng bằng SHA-256.
    """
    now_dt = (
        (timestamp.astimezone(UTC).replace(tzinfo=None) if timestamp.tzinfo else timestamp)
        if timestamp
        else datetime.now(UTC).replace(tzinfo=None)
    )
    ts_str = format_event_timestamp(now_dt)

    # Lấy sự kiện gần nhất CỦA LÔ HÀNG NÀY
    last_event = (
        db.query(ChainEvent)
        .filter(ChainEvent.batch_id == batch_id)
        .order_by(ChainEvent.id.desc())
        .first()
    )
    prev_hash = last_event.current_hash if last_event else GENESIS_HASH

    curr_hash = calculate_event_hash(
        batch_id=batch_id,
        event_type=event_type,
        event_data=event_data,
        org_id=organization_id,
        prev_hash=prev_hash,
        timestamp_str=ts_str,
    )

    canonical_data = canonicalize_event_data(event_data)

    event = ChainEvent(
        batch_id=batch_id,
        event_type=event_type,
        event_data=canonical_data,
        organization_id=organization_id,
        previous_hash=prev_hash,
        current_hash=curr_hash,
        created_at=now_dt,
    )
    db.add(event)
    db.flush()
    return event


def verify_chain_integrity(
    db: Session,
    batch_id: int | None = None,
    batch_code: str | None = None,
) -> dict[str, Any]:
    """
    Thuật toán kiểm tra tính toàn vẹn chuỗi hash (User Story S-12, Task T-26, T-29).
    - Xác định chính xác vị trí sự kiện đầu tiên bị sửa lén hoặc bị xóa làm đứt mạch.
    - Đánh dấu nghi vấn (compromised) mọi sự kiện nằm phía sau vị trí đứt mạch/bị sửa.
    """
    batch_obj = None
    if batch_code and not batch_id:
        batch_obj = db.query(Batch).filter(Batch.batch_code == batch_code.strip()).first()
        if batch_obj:
            batch_id = batch_obj.id

    query = db.query(ChainEvent).order_by(ChainEvent.id.asc())
    if batch_id:
        query = query.filter(ChainEvent.batch_id == batch_id)
        if not batch_obj:
            batch_obj = db.query(Batch).filter(Batch.id == batch_id).first()

    events = query.all()
    if not events:
        return {
            "valid": True,
            "batch_id": batch_id,
            "batch_code": batch_obj.batch_code if batch_obj else None,
            "total_events": 0,
            "broken_event_id": None,
            "broken_event_index": None,
            "message": "Chuỗi sự kiện trống",
            "events": [],
        }

    first_broken_index: int | None = None
    first_broken_id: int | None = None
    first_failure_reason: str | None = None
    event_details: list[dict[str, Any]] = []

    for idx, e in enumerate(events):
        seq = idx + 1
        item_status = "valid"
        item_message = "Toàn vẹn (Khớp mã băm và liên kết chuỗi)"

        if first_broken_index is not None:
            # Nếu sự kiện trước đã bị sửa/đứt gãy -> Mọi sự kiện phía sau bị đánh dấu nghi vấn
            item_status = "compromised"
            item_message = (
                f"Nghi vấn: Kế thừa từ sự kiện #{first_broken_id} (thứ tự {first_broken_index}) "
                "đã bị sửa lén hoặc đứt mạch chuỗi khối."
            )
        else:
            # 1. Kiểm tra tính liên tục của previous_hash
            if idx == 0:
                if e.previous_hash not in VALID_GENESIS_HASHES and batch_id is not None:
                    item_status = "tampered"
                    item_message = (
                        f"Mã khởi đầu (Genesis hash) không hợp lệ tại sự kiện #{e.id}: '{e.previous_hash}'."
                    )
                    first_broken_index = seq
                    first_broken_id = e.id
                    first_failure_reason = item_message
            else:
                prev_event = events[idx - 1]
                if e.previous_hash != prev_event.current_hash:
                    item_status = "broken_link"
                    item_message = (
                        f"Đứt gãy liên kết chuỗi tại sự kiện #{e.id} (thứ tự {seq}): "
                        f"previous_hash '{e.previous_hash[:16]}...' không khớp với current_hash "
                        f"của sự kiện trước #{prev_event.id} '{prev_event.current_hash[:16]}...'."
                    )
                    first_broken_index = seq
                    first_broken_id = e.id
                    first_failure_reason = item_message

            # 2. Kiểm tra tính toàn vẹn băm của chính sự kiện (nếu liên kết chưa bị đứt)
            if first_broken_index is None:
                recomputed = calculate_event_hash(
                    batch_id=e.batch_id,
                    event_type=e.event_type,
                    event_data=e.event_data,
                    org_id=e.organization_id,
                    prev_hash=e.previous_hash,
                    timestamp_str=format_event_timestamp(e.created_at),
                )
                if not e.current_hash or e.current_hash != recomputed:
                    item_status = "tampered"
                    item_message = (
                        f"Nội dung sự kiện #{e.id} ({e.event_type}) đã bị sửa lén trong CSDL! "
                        f"Mã băm lưu trữ '{e.current_hash[:16]}...' không khớp với mã băm tính lại "
                        f"từ nội dung chuẩn hóa '{recomputed[:16]}...'."
                    )
                    first_broken_index = seq
                    first_broken_id = e.id
                    first_failure_reason = item_message

        event_details.append(
            {
                "id": e.id,
                "index": seq,
                "batch_id": e.batch_id,
                "event_type": e.event_type,
                "event_data": e.event_data,
                "organization_id": e.organization_id,
                "previous_hash": e.previous_hash,
                "current_hash": e.current_hash,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "status": item_status,
                "message": item_message,
            }
        )

    is_valid = first_broken_index is None
    return {
        "valid": is_valid,
        "batch_id": batch_id,
        "batch_code": batch_obj.batch_code if batch_obj else None,
        "total_events": len(events),
        "broken_event_id": first_broken_id,
        "broken_event_index": first_broken_index,
        "first_failure_reason": first_failure_reason,
        "message": (
            "Chuỗi hash toàn vẹn 100%"
            if is_valid
            else f"Phát hiện xâm phạm tính toàn vẹn tại sự kiện #{first_broken_id} (vị trí {first_broken_index})"
        ),
        "events": event_details,
    }


def simulate_tamper_attack(
    db: Session,
    batch_id: int,
    action: str,
    event_id: int | None = None,
    tamper_value: str | None = None,
) -> dict[str, Any]:
    """
    Mô phỏng sửa lén SQL / Xóa sự kiện giữa chuỗi (Test T-30, User Story S-12).
    Chỉ dành cho Cán bộ kiểm tra & Quản trị hệ thống kiểm thử thuật toán chống gian lận.
    """
    events = (
        db.query(ChainEvent)
        .filter(ChainEvent.batch_id == batch_id)
        .order_by(ChainEvent.id.asc())
        .all()
    )
    if not events:
        return {"success": False, "message": "Lô hàng chưa có sự kiện nào trong chuỗi."}

    action_lower = action.strip().lower()

    if action_lower == "tamper_data":
        # Sửa lén nội dung event_data bằng SQL trực tiếp
        target_event = None
        if event_id:
            target_event = next((e for e in events if e.id == event_id), None)
        if not target_event:
            # Chọn sự kiện ở giữa chuỗi (hoặc sự kiện đầu tiên nếu chỉ có 1)
            target_idx = len(events) // 2
            target_event = events[target_idx]

        modified_text = (
            tamper_value
            if tamper_value
            else f"{target_event.event_data} [ĐÃ BỊ SỬA LÉN TRỰC TIẾP TRONG DATABASE - TEST T-30]"
        )

        db.execute(
            text("UPDATE chain_events SET event_data = :d WHERE id = :id"),
            {"d": modified_text, "id": target_event.id},
        )
        db.commit()

        return {
            "success": True,
            "action": "tamper_data",
            "tampered_event_id": target_event.id,
            "tampered_event_type": target_event.event_type,
            "message": (
                f"Đã mô phỏng sửa lén nội dung sự kiện #{target_event.id} ({target_event.event_type}) "
                "bằng câu lệnh SQL trực tiếp mà không tính lại hash."
            ),
        }

    elif action_lower == "delete_event":
        # Xóa một sự kiện ở giữa chuỗi để làm đứt gãy liên kết previous_hash
        if len(events) < 2:
            return {
                "success": False,
                "message": "Cần ít nhất 2 sự kiện để mô phỏng xóa sự kiện làm đứt mạch liên kết.",
            }

        target_event = None
        if event_id:
            target_event = next((e for e in events if e.id == event_id), None)
        if not target_event:
            # Chọn sự kiện thứ 2 (hoặc giữa) để sự kiện sau bị đứt liên kết
            target_idx = 1 if len(events) >= 2 else 0
            target_event = events[target_idx]

        deleted_id = target_event.id
        deleted_type = target_event.event_type
        db.execute(text("DELETE FROM chain_events WHERE id = :id"), {"id": deleted_id})
        db.commit()

        return {
            "success": True,
            "action": "delete_event",
            "deleted_event_id": deleted_id,
            "deleted_event_type": deleted_type,
            "message": (
                f"Đã mô phỏng xóa trực tiếp sự kiện #{deleted_id} ({deleted_type}) khỏi database. "
                "Sự kiện kế tiếp sẽ bị đứt mạch previous_hash."
            ),
        }

    elif action_lower == "reset":
        # Khôi phục tính toàn vẹn bằng cách tính lại toàn bộ hash cho chuỗi hiện có
        prev_hash = GENESIS_HASH
        for e in events:
            curr_hash = calculate_event_hash(
                batch_id=e.batch_id,
                event_type=e.event_type,
                event_data=e.event_data,
                org_id=e.organization_id,
                prev_hash=prev_hash,
                timestamp_str=format_event_timestamp(e.created_at),
            )
            db.execute(
                text(
                    "UPDATE chain_events SET previous_hash = :p, current_hash = :c WHERE id = :id"
                ),
                {"p": prev_hash, "c": curr_hash, "id": e.id},
            )
            prev_hash = curr_hash
        db.commit()

        return {
            "success": True,
            "action": "reset",
            "message": "Đã khôi phục tính toàn vẹn chuỗi hash thành công.",
        }

    return {"success": False, "message": f"Hành động không hợp lệ: '{action}'."}
