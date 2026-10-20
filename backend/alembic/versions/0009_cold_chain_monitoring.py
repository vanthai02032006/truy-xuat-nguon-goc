import sqlalchemy as sa

from alembic import op

revision = "0009_cold_chain_monitoring"
down_revision = "0008_batch_recalls"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Bảng transport_trips (S-40: Quản lý chuyến vận chuyển lạnh)
    op.create_table(
        "transport_trips",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trip_code", sa.String(50), unique=True, nullable=False),
        sa.Column("vehicle_code", sa.String(100), nullable=False, index=True),
        sa.Column(
            "carrier_org_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("driver_name", sa.String(100), nullable=True),
        sa.Column("min_temperature", sa.Float(), nullable=False, server_default=sa.text("2.0")),
        sa.Column("max_temperature", sa.Float(), nullable=False, server_default=sa.text("8.0")),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'IN_TRANSIT'"), index=True),
        sa.Column("start_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 2. Bảng trip_batches (Danh sách các lô hàng đang chở trên chuyến xe)
    op.create_table(
        "trip_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "trip_id",
            sa.Integer(),
            sa.ForeignKey("transport_trips.id", ondelete="CASCADE"),
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
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 3. Bảng temperature_telemetry (S-41: Dữ liệu chuỗi thời gian cảm biến nhiệt độ)
    op.create_table(
        "temperature_telemetry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "trip_id",
            sa.Integer(),
            sa.ForeignKey("transport_trips.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 4. Bảng cold_chain_violations (S-43, S-45: Sự kiện vi phạm chuỗi lạnh được phát hiện)
    op.create_table(
        "cold_chain_violations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "trip_id",
            sa.Integer(),
            sa.ForeignKey("transport_trips.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Float(), nullable=False),
        sa.Column("peak_temperature", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("violation_type", sa.String(50), nullable=False, server_default=sa.text("'HIGH_TEMPERATURE'")),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'DETECTED'"), index=True),
        sa.Column("hash_recorded", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table("cold_chain_violations")
    op.drop_table("temperature_telemetry")
    op.drop_table("trip_batches")
    op.drop_table("transport_trips")
