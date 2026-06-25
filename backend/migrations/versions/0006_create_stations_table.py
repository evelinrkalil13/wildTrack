"""create stations table

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import ENUM as PGEnum

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

station_status_enum = PGEnum(
    "active", "inactive", "maintenance", "offline",
    name="station_status",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        "CREATE TYPE station_status AS ENUM ('active', 'inactive', 'maintenance', 'offline')"
    )

    op.create_table(
        "stations",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "zone_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("zones.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=False),
        sa.Column("geom", Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("status", station_status_enum, nullable=False, server_default="active"),
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

    op.create_index("idx_stations_zone_id", "stations", ["zone_id"])
    op.create_index("idx_stations_geom", "stations", ["geom"], postgresql_using="gist")
    op.create_index(
        "idx_stations_status_active",
        "stations",
        ["status"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "idx_stations_zone_status",
        "stations",
        ["zone_id", "status"],
    )
    op.create_index(
        "uq_stations_code_active",
        "stations",
        [sa.text("lower(code)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.execute(
        """
        CREATE TRIGGER set_stations_updated_at
        BEFORE UPDATE ON stations
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS set_stations_updated_at ON stations")
    op.drop_index("uq_stations_code_active", table_name="stations")
    op.drop_index("idx_stations_zone_status", table_name="stations")
    op.drop_index("idx_stations_status_active", table_name="stations")
    op.drop_index("idx_stations_geom", table_name="stations")
    op.drop_index("idx_stations_zone_id", table_name="stations")
    op.drop_table("stations")
    op.execute("DROP TYPE IF EXISTS station_status")
