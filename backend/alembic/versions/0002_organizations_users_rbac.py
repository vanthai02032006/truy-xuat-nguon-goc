import sqlalchemy as sa

from alembic import op

revision = "0002_organizations_users_rbac"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Bảng organizations (Tổ chức: HTX, Nhà phân phối, v.v.)
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 2. Bảng users (Tài khoản người dùng, phân quyền RBAC và tổ chức)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="member"),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 3. Thêm cột organization_id vào bảng batches
    op.add_column(
        "batches",
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )

    # 4. Bảng security_logs (Nhật ký cảnh báo an ninh & thử truy cập chéo tổ chức)
    op.create_table(
        "security_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("user_org_id", sa.Integer(), nullable=True),
        sa.Column("attempt_type", sa.String(100), nullable=False),
        sa.Column("target_resource", sa.String(100), nullable=False),
        sa.Column("target_id", sa.String(100), nullable=True),
        sa.Column("target_org_id", sa.Integer(), nullable=True),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("ip_address", sa.String(100), nullable=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_table("security_logs")
    op.drop_column("batches", "organization_id")
    op.drop_table("users")
    op.drop_table("organizations")
