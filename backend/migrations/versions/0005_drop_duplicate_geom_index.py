"""drop duplicate geom index on zones

GeoAlchemy2 Geometry column auto-creates idx_zones_geom via create_table.
Migration 0004 also created ix_zones_geom explicitly. This migration drops
the auto-created duplicate so only the explicitly managed index remains.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-17

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("idx_zones_geom", table_name="zones", postgresql_using="gist")


def downgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_zones_geom ON zones USING gist (geom)"
    )
