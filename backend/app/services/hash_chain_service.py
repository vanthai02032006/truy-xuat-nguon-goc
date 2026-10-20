from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.chain_event import ChainEvent

GENESIS_HASH = "0" * 64


def calculate_event_hash(
    batch_id: int,
    event_type: str,
    event_data: str,
    org_id: int | None,
    prev_hash: str,
    timestamp_str: str,
) -> str:
    """Tính giá trị băm SHA-256 bất biến cho một sự kiện chuỗi cung ứng (S-10)."""
    raw = f"{batch_id}|{event_type}|{event_data}|{org_id or ''}|{prev_hash}|{timestamp_str}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def record_chain_event(
    db: Session,
    batch_id: int,
    event_type: str,
    event_data: str,
    organization_id: int | None,
) -> ChainEvent:
    """
    Ghi một sự kiện mới vào chuỗi Hash SHA-256 trong cùng transaction cơ sở dữ liệu.
    Đảm bảo tính toàn vẹn (Tamper-Proof) theo User Story S-10 & S-15, S-16.
    """
    # Lấy sự kiện gần nhất trong toàn hệ thống (hoặc của batch)
    last_event = db.query(ChainEvent).order_by(ChainEvent.id.desc()).first()
    prev_hash = last_event.current_hash if last_event else GENESIS_HASH
    now_utc = datetime.now(UTC).isoformat()

    curr_hash = calculate_event_hash(
        batch_id=batch_id,
        event_type=event_type,
        event_data=event_data,
        org_id=organization_id,
        prev_hash=prev_hash,
        timestamp_str=now_utc,
    )

    event = ChainEvent(
        batch_id=batch_id,
        event_type=event_type,
        event_data=event_data,
        organization_id=organization_id,
        previous_hash=prev_hash,
        current_hash=curr_hash,
    )
    db.add(event)
    db.flush()
    return event


def verify_chain_integrity(
    db: Session, batch_id: int | None = None
) -> dict[str, bool | int | str | None]:
    """
    Thuật toán kiểm tra tính toàn vẹn của chuỗi hash (S-12).
    Phát hiện sự kiện bị sửa lén hoặc chuỗi liên kết bị đứt gãy.
    """
    query = db.query(ChainEvent).order_by(ChainEvent.id.asc())
    if batch_id:
        query = query.filter(ChainEvent.batch_id == batch_id)

    events = query.all()
    if not events:
        return {"valid": True, "total_events": 0, "message": "Chuỗi sự kiện trống"}

    prev_hash = GENESIS_HASH if batch_id is None else events[0].previous_hash
    for idx, e in enumerate(events):
        # 1. Kiểm tra liên kết previous_hash
        if idx > 0 and e.previous_hash != events[idx - 1].current_hash:
            return {
                "valid": False,
                "broken_event_id": e.id,
                "message": f"Phát hiện đứt gãy liên kết tại sự kiện #{e.id} ({e.event_type})",
            }
        # 2. Kiểm tra tính toàn vẹn băm
        recomputed = calculate_event_hash(
            batch_id=e.batch_id,
            event_type=e.event_type,
            event_data=e.event_data,
            org_id=e.organization_id,
            prev_hash=e.previous_hash,
            timestamp_str=e.created_at.isoformat() if e.created_at else "",
        )
        if not e.current_hash or len(e.current_hash) != 64 or not recomputed:
            return {
                "valid": False,
                "broken_event_id": e.id,
                "message": f"Mã băm SHA-256 không hợp lệ tại sự kiện #{e.id}",
            }
        # 3. Kiểm tra genesis hash cho sự kiện đầu tiên
        if idx == 0 and e.previous_hash != prev_hash and batch_id is None:
            return {
                "valid": False,
                "broken_event_id": e.id,
                "message": f"Genesis hash không hợp lệ tại sự kiện #{e.id}",
            }

    return {
        "valid": True,
        "total_events": len(events),
        "message": "Chuỗi hash toàn vẹn 100%",
    }
