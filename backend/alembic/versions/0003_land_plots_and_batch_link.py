import sqlalchemy as sa

from alembic import op

revision = "0003_land_plots_and_batch_link"
down_revision = "0002_organizations_users_rbac"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Bảng land_plots (Thửa đất của vùng trồng - Story S-06)
    op.create_table(
        "land_plots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("area", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False, server_default="m2"),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
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

    # 2. Thêm cột land_plot_id vào bảng batches để liên kết lô thu hoạch với thửa đất
    op.add_column(
        "batches",
        sa.Column(
            "land_plot_id",
            sa.Integer(),
            sa.ForeignKey("land_plots.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("batches", "land_plot_id")
    op.drop_table("land_plots")
