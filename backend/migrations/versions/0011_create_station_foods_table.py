"""create station_foods table

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "station_foods",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "station_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("stations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "food_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("foods.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean, nullable=False, server_default="true"),
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

    # Regular unique: a food can only be associated with a station once
    op.create_index(
        "station_foods_pair_key",
        "station_foods",
        ["station_id", "food_id"],
        unique=True,
    )

    # Partial unique: at most one active food per station
    op.create_index(
        "station_foods_one_active_idx",
        "station_foods",
        ["station_id"],
        unique=True,
        postgresql_where=sa.text("active = TRUE"),
    )

    # Support indexes
    op.create_index("idx_station_foods_station_id", "station_foods", ["station_id"])
    op.create_index("idx_station_foods_food_id", "station_foods", ["food_id"])

    op.execute(
        """
        CREATE TRIGGER set_station_foods_updated_at
        BEFORE UPDATE ON station_foods
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS set_station_foods_updated_at ON station_foods")
    op.drop_index("idx_station_foods_food_id", table_name="station_foods")
    op.drop_index("idx_station_foods_station_id", table_name="station_foods")
    op.drop_index("station_foods_one_active_idx", table_name="station_foods")
    op.drop_index("station_foods_pair_key", table_name="station_foods")
    op.drop_table("station_foods")
