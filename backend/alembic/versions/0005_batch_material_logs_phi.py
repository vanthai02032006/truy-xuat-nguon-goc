import sqlalchemy as sa

from alembic import op

revision = "0005_batch_material_logs_phi"
down_revision = "0004_rbac_matrix_and_workflows"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "batch_material_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "batch_id",
            sa.Integer(),
            sa.ForeignKey("batches.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "material_id",
            sa.Integer(),
            sa.ForeignKey("materials.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("material_name", sa.String(200), nullable=False),
        sa.Column(
            "category", sa.String(50), nullable=False, server_default="pesticide"
        ),
        sa.Column("dosage", sa.String(100), nullable=False),
        sa.Column("applied_date", sa.String(20), nullable=False),
        sa.Column("isolation_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("safe_harvest_date", sa.String(20), nullable=False),
        sa.Column("applied_by", sa.String(100), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
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
    op.drop_table("batch_material_logs")
