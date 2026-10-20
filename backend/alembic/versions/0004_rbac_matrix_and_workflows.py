import sqlalchemy as sa
from alembic import op

revision = "0004_rbac_matrix_and_workflows"
down_revision = "0003_land_plots_and_batch_link"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Bảng materials (Kho vật tư nông nghiệp)
    op.create_table(
        "materials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(50), nullable=False, index=True),
        sa.Column(
            "category", sa.String(50), nullable=False, server_default="fertilizer"
        ),
        sa.Column(
            "quantity_in_stock", sa.Float(), nullable=False, server_default="0.0"
        ),
        sa.Column("unit", sa.String(50), nullable=False, server_default="kg"),
        sa.Column("min_threshold", sa.Float(), nullable=False, server_default="10.0"),
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

    # 2. Bảng material_requests (Đề xuất cấp phát vật tư từ Giám sát đến Chủ nông trại)
    op.create_table(
        "material_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("material_name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False, server_default="kg"),
        sa.Column("purpose", sa.String(255), nullable=True),
        sa.Column("urgency", sa.String(50), nullable=False, server_default="normal"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column(
            "requester_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "approver_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("rejection_reason", sa.String(255), nullable=True),
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
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 3. Bảng workers (Hồ sơ nhân sự / công nhân nông trại)
    op.create_table(
        "workers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column(
            "worker_type", sa.String(50), nullable=False, server_default="seasonal"
        ),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("daily_rate", sa.Float(), nullable=False, server_default="250000.0"),
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

    # 4. Bảng daily_tasks (Phân công nhiệm vụ tại hiện trường)
    op.create_table(
        "daily_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "plot_id",
            sa.Integer(),
            sa.ForeignKey("land_plots.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "worker_id",
            sa.Integer(),
            sa.ForeignKey("workers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "supervisor_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="assigned"),
        sa.Column("task_date", sa.String(20), nullable=False),
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

    # 5. Bảng timesheets (Chấm công và thu hoạch)
    op.create_table(
        "timesheets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "worker_id",
            sa.Integer(),
            sa.ForeignKey("workers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.String(20), nullable=False),
        sa.Column("hours_worked", sa.Float(), nullable=False, server_default="8.0"),
        sa.Column("output_quantity", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("output_unit", sa.String(50), nullable=False, server_default="kg"),
        sa.Column("status", sa.String(50), nullable=False, server_default="submitted"),
        sa.Column(
            "supervisor_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "approver_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
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

    # 6. Bảng financial_transactions (Thu chi & tài chính nông trại)
    op.create_table(
        "financial_transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("transaction_type", sa.String(50), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("transaction_date", sa.String(20), nullable=False),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 7. Bảng farming_logs (Nhật ký canh tác nông nghiệp)
    op.create_table(
        "farming_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plot_id",
            sa.Integer(),
            sa.ForeignKey("land_plots.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("activity_type", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("materials_used", sa.String(255), nullable=True),
        sa.Column("activity_date", sa.String(20), nullable=False),
        sa.Column(
            "supervisor_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
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

    # 8. Bảng field_incidents (Sự cố sâu bệnh hại và đồng ruộng)
    op.create_table(
        "field_incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plot_id",
            sa.Integer(),
            sa.ForeignKey("land_plots.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("incident_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False, server_default="medium"),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("action_taken", sa.String(500), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="reported"),
        sa.Column(
            "reported_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
    op.drop_table("field_incidents")
    op.drop_table("farming_logs")
    op.drop_table("financial_transactions")
    op.drop_table("timesheets")
    op.drop_table("daily_tasks")
    op.drop_table("workers")
    op.drop_table("material_requests")
    op.drop_table("materials")
