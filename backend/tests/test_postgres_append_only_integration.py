from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.batch import Batch
from app.models.organization import Organization
from app.services.hash_chain_service import (
    GENESIS_HASH,
    record_chain_event,
    verify_chain_integrity,
)

# Biến môi trường trỏ đến cơ sở dữ liệu PostgreSQL thật
TEST_POSTGRESQL_URL = os.getenv("TEST_POSTGRESQL_URL") or os.getenv("POSTGRES_TEST_DATABASE_URL")
TEST_POSTGRESQL_RUNTIME_URL = os.getenv("TEST_POSTGRESQL_RUNTIME_URL")

TRIGGER_SETUP_SQL = """
CREATE OR REPLACE FUNCTION prevent_chain_events_tamper()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Bảng chain_events là chỉ-thêm (append-only - S-11). Nghiêm cấm mọi thao tác UPDATE hoặc DELETE.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_chain_events_update ON chain_events;
CREATE TRIGGER trg_prevent_chain_events_update
BEFORE UPDATE ON chain_events
FOR EACH ROW
EXECUTE FUNCTION prevent_chain_events_tamper();

DROP TRIGGER IF EXISTS trg_prevent_chain_events_delete ON chain_events;
CREATE TRIGGER trg_prevent_chain_events_delete
BEFORE DELETE ON chain_events
FOR EACH ROW
EXECUTE FUNCTION prevent_chain_events_tamper();
"""


@pytest.mark.skipif(
    not TEST_POSTGRESQL_URL,
    reason=(
        "Yêu cầu PostgreSQL thật (cấu hình qua biến môi trường TEST_POSTGRESQL_URL) để kiểm chứng "
        "trigger PL/pgSQL và quyền phân tách role. Không dùng SQLite để giả lập kiểm chứng quyền PostgreSQL."
    ),
)
class TestPostgreSQLAppendOnlyIntegration:
    """
    Bộ kiểm thử tích hợp thực tế trên cơ sở dữ liệu PostgreSQL (User Stories S-10, S-11, S-12).
    Kiểm chứng:
    1. INSERT sự kiện hợp lệ hoạt động bình thường.
    2. UPDATE trực tiếp bằng câu lệnh SQL bị PostgreSQL trigger từ chối.
    3. DELETE trực tiếp bằng câu lệnh SQL bị PostgreSQL trigger từ chối.
    4. Chuỗi 1 sự kiện duy nhất được kiểm tra là hợp lệ.
    5. Phát hiện sự kiện bị sửa lén hoặc chuỗi bị đứt mạch tại đúng vị trí index.
    """

    @pytest.fixture(scope="class")
    def pg_engine(self):
        engine = create_engine(TEST_POSTGRESQL_URL)
        Base.metadata.create_all(bind=engine)
        # Thiết lập Trigger chống sửa/xóa trên PostgreSQL
        with engine.begin() as conn:
            conn.execute(text(TRIGGER_SETUP_SQL))
        yield engine
        engine.dispose()

    @pytest.fixture
    def pg_session(self, pg_engine):
        session_factory = sessionmaker(bind=pg_engine)
        session = session_factory()
        yield session
        session.rollback()
        session.close()

    @pytest.fixture
    def sample_batch(self, pg_session):
        org = Organization(name="Hợp tác xã Nông sản Thật", code="HTX_REAL_PG")
        pg_session.add(org)
        pg_session.flush()

        batch = Batch(
            batch_code=f"PG-TEST-{int(datetime.now(UTC).timestamp())}",
            product_name="Hồ tiêu đen Phú Quốc",
            organization_id=org.id,
            initial_quantity=100.0,
            remaining_quantity=100.0,
            unit="kg",
        )
        pg_session.add(batch)
        pg_session.commit()
        return batch

    def test_pg_insert_valid_chain_event_works(self, pg_session, sample_batch):
        """1. INSERT sự kiện hợp lệ qua hash_chain_service hoạt động bình thường trên PostgreSQL."""
        event = record_chain_event(
            db=pg_session,
            batch_id=sample_batch.id,
            event_type="BATCH_INITIALIZED",
            event_data={"plot": "Khu Đông", "note": "Ghi nhận sự kiện trên PostgreSQL thật"},
            organization_id=sample_batch.organization_id,
        )
        pg_session.commit()

        assert event.id is not None
        assert event.previous_hash == GENESIS_HASH
        assert len(event.current_hash) == 64

        # Truy vấn trực tiếp từ PostgreSQL
        row = pg_session.execute(
            text("SELECT id, event_type, previous_hash FROM chain_events WHERE id = :id"),
            {"id": event.id},
        ).fetchone()
        assert row is not None
        assert row[0] == event.id
        assert row[1] == "BATCH_INITIALIZED"

    def test_pg_sql_update_rejected_by_trigger(self, pg_session, sample_batch):
        """2. UPDATE trực tiếp bằng câu lệnh SQL bị PostgreSQL trigger từ chối triệt để."""
        event = record_chain_event(
            db=pg_session,
            batch_id=sample_batch.id,
            event_type="STAGE_DATA",
            event_data={"status": "Nguyên bản"},
            organization_id=sample_batch.organization_id,
        )
        pg_session.commit()

        with pytest.raises(DBAPIError) as exc_info:
            pg_session.execute(
                text("UPDATE chain_events SET event_data = '{\"status\": \"Hacker Sửa\"}' WHERE id = :id"),
                {"id": event.id},
            )
            pg_session.commit()

        # Xác minh lỗi do chính trigger prevent_chain_events_tamper bắn ra
        err_msg = str(exc_info.value).lower()
        assert "chỉ-thêm" in err_msg or "append-only" in err_msg or "nghiêm cấm" in err_msg

    def test_pg_sql_delete_rejected_by_trigger(self, pg_session, sample_batch):
        """3. DELETE trực tiếp bằng câu lệnh SQL bị PostgreSQL trigger từ chối triệt để."""
        event = record_chain_event(
            db=pg_session,
            batch_id=sample_batch.id,
            event_type="STAGE_DELETE_TEST",
            event_data={"status": "Không thể xóa"},
            organization_id=sample_batch.organization_id,
        )
        pg_session.commit()

        with pytest.raises(DBAPIError) as exc_info:
            pg_session.execute(
                text("DELETE FROM chain_events WHERE id = :id"),
                {"id": event.id},
            )
            pg_session.commit()

        err_msg = str(exc_info.value).lower()
        assert "chỉ-thêm" in err_msg or "append-only" in err_msg or "nghiêm cấm" in err_msg

    def test_pg_single_event_chain_is_valid(self, pg_session, sample_batch):
        """4. Chuỗi 1 sự kiện trên PostgreSQL được xác thực là toàn vẹn và hợp lệ."""
        record_chain_event(
            db=pg_session,
            batch_id=sample_batch.id,
            event_type="SINGLE_EVENT",
            event_data={"status": "Chuỗi đơn lẻ"},
            organization_id=sample_batch.organization_id,
        )
        pg_session.commit()

        report = verify_chain_integrity(db=pg_session, batch_id=sample_batch.id)
        assert report["valid"] is True
        assert report["total_events"] >= 1
        assert report["broken_event_id"] is None

    def test_pg_tampered_event_detected_by_integrity_check(self, pg_session, pg_engine, sample_batch):
        """5. Phát hiện sự kiện bị sửa lén dữ liệu trên PostgreSQL tại đúng vị trí index."""
        record_chain_event(
            db=pg_session,
            batch_id=sample_batch.id,
            event_type="E1",
            event_data={"v": 1},
            organization_id=sample_batch.organization_id,
        )
        e2 = record_chain_event(
            db=pg_session,
            batch_id=sample_batch.id,
            event_type="E2",
            event_data={"v": 2},
            organization_id=sample_batch.organization_id,
        )
        pg_session.commit()

        # Tạm thời vô hiệu hóa trigger để mô phỏng một kẻ xâm nhập có quyền admin sửa lén database
        with pg_engine.begin() as conn:
            conn.execute(text("ALTER TABLE chain_events DISABLE TRIGGER trg_prevent_chain_events_update;"))
            conn.execute(
                text("UPDATE chain_events SET event_data = '{\"v\": 999}' WHERE id = :id"),
                {"id": e2.id},
            )
            conn.execute(text("ALTER TABLE chain_events ENABLE TRIGGER trg_prevent_chain_events_update;"))

        # Thuật toán verify_chain_integrity phải phát hiện ra sự kiện e2 bị sửa lén
        report = verify_chain_integrity(db=pg_session, batch_id=sample_batch.id)
        assert report["valid"] is False
        assert report["broken_event_id"] == e2.id
        assert "đã bị sửa lén" in report["first_failure_reason"]

    def test_pg_multi_event_broken_link_detected_at_exact_position(self, pg_session, pg_engine, sample_batch):
        """6. Phát hiện sự kiện bị mất/xóa làm đứt mạch liên kết trên PostgreSQL tại đúng index."""
        record_chain_event(
            db=pg_session,
            batch_id=sample_batch.id,
            event_type="NODE_1",
            event_data={"node": 1},
            organization_id=sample_batch.organization_id,
        )
        e2 = record_chain_event(
            db=pg_session,
            batch_id=sample_batch.id,
            event_type="NODE_2",
            event_data={"node": 2},
            organization_id=sample_batch.organization_id,
        )
        e3 = record_chain_event(
            db=pg_session,
            batch_id=sample_batch.id,
            event_type="NODE_3",
            event_data={"node": 3},
            organization_id=sample_batch.organization_id,
        )
        pg_session.commit()

        # Vô hiệu hóa trigger tạm thời để mô phỏng sự kiện e2 bị xóa
        with pg_engine.begin() as conn:
            conn.execute(text("ALTER TABLE chain_events DISABLE TRIGGER trg_prevent_chain_events_delete;"))
            conn.execute(text("DELETE FROM chain_events WHERE id = :id"), {"id": e2.id})
            conn.execute(text("ALTER TABLE chain_events ENABLE TRIGGER trg_prevent_chain_events_delete;"))

        report = verify_chain_integrity(db=pg_session, batch_id=sample_batch.id)
        assert report["valid"] is False
        assert report["broken_event_id"] == e3.id
        assert "Đứt gãy liên kết chuỗi" in report["first_failure_reason"]

    @pytest.mark.skipif(
        not TEST_POSTGRESQL_RUNTIME_URL,
        reason="Chưa cung cấp TEST_POSTGRESQL_RUNTIME_URL (kết nối dưới tài khoản farm_app_user)."
    )
    def test_pg_runtime_role_denied_update_and_delete_privilege(self):
        """
        7. Kiểm tra quyền của tài khoản Runtime (farm_app_user):
        PostgreSQL trực tiếp từ chối quyền UPDATE và DELETE bằng lỗi 'permission denied for table chain_events'
        ngay cả khi trigger không được gọi.
        """
        runtime_engine = create_engine(TEST_POSTGRESQL_RUNTIME_URL)
        with runtime_engine.connect() as conn:
            # 1. Thao tác SELECT vẫn thành công
            conn.execute(text("SELECT count(*) FROM chain_events"))

            # 2. Thao tác UPDATE bị từ chối ở tầng quyền bảng (GRANT/REVOKE)
            with pytest.raises(ProgrammingError) as exc_update:
                conn.execute(text("UPDATE chain_events SET event_data = 'test' WHERE id = 1"))
            assert "permission denied" in str(exc_update.value).lower()

            # 3. Thao tác DELETE bị từ chối ở tầng quyền bảng (GRANT/REVOKE)
            with pytest.raises(ProgrammingError) as exc_delete:
                conn.execute(text("DELETE FROM chain_events WHERE id = 1"))
            assert "permission denied" in str(exc_delete.value).lower()
        runtime_engine.dispose()
