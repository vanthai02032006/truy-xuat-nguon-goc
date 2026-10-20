import sqlalchemy as sa
from alembic import op

revision = "0008_batch_recalls"
down_revision = "0007_batch_split_merge_relations"
branch_labels = None
depends_on = None


def upgrade():
    # 0. Mo rong cot version_num cua alembic_version len VARCHAR(128) neu tren PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "alembic_version",
            "version_num",
            type_=sa.String(128),
            existing_type=sa.String(32),
        )

    # 1. Bảng recalls (Epic E-06, S-33: Mở lệnh thu hồi khẩn cấp)
    op.create_table(
        "recalls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recall_code", sa.String(50), unique=True, nullable=False),
        sa.Column(
            "source_batch_id",
            sa.Integer(),
            sa.ForeignKey("batches.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "initiator_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "initiator_organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False, server_default=sa.text("'CRITICAL'")),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'ACTIVE'"), index=True),
        sa.Column("total_affected_batches", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_affected_kg", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("total_stock_kg", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("total_sold_kg", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )

    # 2. Bảng recall_affected_batches (S-34, S-35: Các lô con/cháu bị khoanh vùng)
    op.create_table(
        "recall_affected_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "recall_id",
            sa.Integer(),
            sa.ForeignKey("recalls.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "batch_id",
            sa.Integer(),
            sa.ForeignKey("batches.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("generation", sa.String(20), nullable=False, server_default=sa.text("'ROOT'")),
        sa.Column("initial_quantity", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("remaining_quantity", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("sold_quantity", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("current_location", sa.String(255), nullable=True),
        sa.Column("batch_status_before", sa.String(50), nullable=True),
        sa.Column("is_isolated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("isolated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 3. Bảng recall_organization_actions (S-36, S-37: Tiến độ xử lý của từng tổ chức)
    op.create_table(
        "recall_organization_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "recall_id",
            sa.Integer(),
            sa.ForeignKey("recalls.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'PENDING'"), index=True),
        sa.Column("action_notes", sa.String(500), nullable=True),
        sa.Column(
            "confirmed_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("affected_batch_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("stock_kg", sa.Float(), nullable=False, server_default=sa.text("0.0")),
    )


def downgrade():
    op.drop_table("recall_organization_actions")
    op.drop_table("recall_affected_batches")
    op.drop_table("recalls")
