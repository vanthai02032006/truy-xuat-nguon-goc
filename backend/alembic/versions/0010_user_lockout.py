import sqlalchemy as sa

from alembic import op

revision = "0010_user_lockout"
down_revision = "0009_cold_chain_monitoring"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "failed_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "locked_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_attempts")
