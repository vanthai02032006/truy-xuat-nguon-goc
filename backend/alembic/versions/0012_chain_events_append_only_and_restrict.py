"""0012_chain_events_append_only_and_restrict

Revision ID: 0012_chain_events_append_only_and_restrict
Revises: 0011_products_catalog
Create Date: 2026-10-21

User Story S-10, S-11, S-12:
1. Thiết lập cơ chế trigger chống sửa (UPDATE) và chống xóa (DELETE) trên bảng chain_events trong PostgreSQL.
2. Thay đổi ràng buộc khóa ngoại batch_id từ ON DELETE CASCADE sang ON DELETE RESTRICT để ngăn chặn
   việc xóa một lô hàng kéo theo cascade xóa sạch toàn bộ lịch sử chuỗi băm sự kiện.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0012_chain_events_append_only_and_restrict"
down_revision = "0011_products_catalog"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # 1. Trong PostgreSQL: Thay đổi khóa ngoại batch_id từ CASCADE sang RESTRICT
    if bind.dialect.name == "postgresql":
        op.drop_constraint("chain_events_batch_id_fkey", "chain_events", type_="foreignkey")
        op.create_foreign_key(
            "chain_events_batch_id_fkey",
            "chain_events",
            "batches",
            ["batch_id"],
            ["id"],
            ondelete="RESTRICT",
        )

        # 2. Tạo hàm trigger chặn mọi thao tác UPDATE và DELETE
        op.execute("""
        CREATE OR REPLACE FUNCTION prevent_chain_events_tamper()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'Bảng chain_events là chỉ-thêm (append-only - S-11). Nghiêm cấm mọi thao tác UPDATE hoặc DELETE.';
        END;
        $$ LANGUAGE plpgsql;
        """)

        # 3. Tạo trigger BEFORE UPDATE
        op.execute("""
        DROP TRIGGER IF EXISTS trg_prevent_chain_events_update ON chain_events;
        CREATE TRIGGER trg_prevent_chain_events_update
        BEFORE UPDATE ON chain_events
        FOR EACH ROW
        EXECUTE FUNCTION prevent_chain_events_tamper();
        """)

        # 4. Tạo trigger BEFORE DELETE
        op.execute("""
        DROP TRIGGER IF EXISTS trg_prevent_chain_events_delete ON chain_events;
        CREATE TRIGGER trg_prevent_chain_events_delete
        BEFORE DELETE ON chain_events
        FOR EACH ROW
        EXECUTE FUNCTION prevent_chain_events_tamper();
        """)


def downgrade():
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        # Gỡ bỏ trigger và hàm trigger
        op.execute("DROP TRIGGER IF EXISTS trg_prevent_chain_events_update ON chain_events;")
        op.execute("DROP TRIGGER IF EXISTS trg_prevent_chain_events_delete ON chain_events;")
        op.execute("DROP FUNCTION IF EXISTS prevent_chain_events_tamper();")

        # Khôi phục khóa ngoại CASCADE
        op.drop_constraint("chain_events_batch_id_fkey", "chain_events", type_="foreignkey")
        op.create_foreign_key(
            "chain_events_batch_id_fkey",
            "chain_events",
            "batches",
            ["batch_id"],
            ["id"],
            ondelete="CASCADE",
        )
