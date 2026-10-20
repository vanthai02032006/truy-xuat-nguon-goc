import sqlalchemy as sa
from alembic import op

revision = "0006_handovers_and_chain_events"
down_revision = "0005_batch_material_logs_phi"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Bổ sung trường status cho bảng batches (mặc định 'active')
    op.add_column(
        "batches",
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="active",
        ),
    )

    # 2. Tạo bảng handovers (User Story S-15, S-16: Bàn giao lô hàng giữa các tổ chức)
    op.create_table(
        "handovers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "batch_id",
            sa.Integer(),
            sa.ForeignKey("batches.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "from_org_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "to_org_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="PENDING",
            index=True,
        ),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # 3. Tạo bảng chain_events (Chuỗi hash SHA-256 bảo đảm tính toàn vẹn sự kiện)
    op.create_table(
        "chain_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "batch_id",
            sa.Integer(),
            sa.ForeignKey("batches.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("event_type", sa.String(50), nullable=False, index=True),
        sa.Column("previous_hash", sa.String(64), nullable=False),
        sa.Column("current_hash", sa.String(64), nullable=False, index=True),
        sa.Column("event_data", sa.JSON(), nullable=False),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_table("chain_events")
    op.drop_table("handovers")
    op.drop_column("batches", "status")
