"""create devices table

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PGEnum

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

device_status_enum = PGEnum(
    "online", "offline", "unassigned",
    name="device_status",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        "CREATE TYPE device_status AS ENUM ('online', 'offline', 'unassigned')"
    )

    op.create_table(
        "devices",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("serial_number", sa.String(100), nullable=False),
        sa.Column("mac_address", sa.String(17), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column(
            "station_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("stations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", device_status_enum, nullable=False, server_default="unassigned"),
        sa.Column("firmware_version", sa.String(50), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Partial unique: one serial per active device
    op.create_index(
        "uq_devices_serial_active",
        "devices",
        ["serial_number"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Partial unique: at most one non-unassigned device per station
    op.create_index(
        "uq_devices_station_one_active",
        "devices",
        ["station_id"],
        unique=True,
        postgresql_where=sa.text("status != 'unassigned' AND deleted_at IS NULL"),
    )

    # Support indexes
    op.create_index("idx_devices_station_id", "devices", ["station_id"])
    op.create_index(
        "idx_devices_last_seen_active",
        "devices",
        ["last_seen"],
        postgresql_where=sa.text("deleted_at IS NULL AND status != 'unassigned'"),
    )
    op.create_index("idx_devices_station_status", "devices", ["station_id", "status"])

    # Integrity constraint: unassigned ↔ station_id IS NULL
    op.execute(
        "ALTER TABLE devices ADD CONSTRAINT chk_devices_status_station "
        "CHECK ("
        "  (status = 'unassigned' AND station_id IS NULL) OR "
        "  (status != 'unassigned' AND station_id IS NOT NULL)"
        ")"
    )

    op.execute(
        """
        CREATE TRIGGER set_devices_updated_at
        BEFORE UPDATE ON devices
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS set_devices_updated_at ON devices")
    op.execute("ALTER TABLE devices DROP CONSTRAINT IF EXISTS chk_devices_status_station")
    op.drop_index("idx_devices_station_status", table_name="devices")
    op.drop_index("idx_devices_last_seen_active", table_name="devices")
    op.drop_index("idx_devices_station_id", table_name="devices")
    op.drop_index("uq_devices_station_one_active", table_name="devices")
    op.drop_index("uq_devices_serial_active", table_name="devices")
    op.drop_table("devices")
    op.execute("DROP TYPE IF EXISTS device_status")
