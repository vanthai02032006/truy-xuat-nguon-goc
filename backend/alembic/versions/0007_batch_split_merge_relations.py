import sqlalchemy as sa

from alembic import op

revision = "0007_batch_split_merge_relations"
down_revision = "0006_handovers_and_chain_events"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Bổ sung các trường khối lượng và đơn vị tính cho bảng batches
    op.add_column(
        "batches",
        sa.Column(
            "initial_quantity",
            sa.Float(),
            nullable=False,
            server_default="100.0",
        ),
    )
    op.add_column(
        "batches",
        sa.Column(
            "remaining_quantity",
            sa.Float(),
            nullable=False,
            server_default="100.0",
        ),
    )
    op.add_column(
        "batches",
        sa.Column(
            "unit",
            sa.String(20),
            nullable=False,
            server_default="kg",
        ),
    )

    # 2. Tạo bảng quan hệ batch_relations (User Story S-17, S-18, S-19: Tách lô & Gộp lô)
    op.create_table(
        "batch_relations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "parent_batch_id",
            sa.Integer(),
            sa.ForeignKey("batches.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "child_batch_id",
            sa.Integer(),
            sa.ForeignKey("batches.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "relation_type",
            sa.String(20),
            nullable=False,
            index=True,
        ),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_table("batch_relations")
    op.drop_column("batches", "unit")
    op.drop_column("batches", "remaining_quantity")
    op.drop_column("batches", "initial_quantity")
