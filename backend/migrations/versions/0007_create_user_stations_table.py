"""create user_stations table

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-18

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PGEnum

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

station_user_role_enum = PGEnum(
    "owner", "researcher", "field_operator",
    name="station_user_role",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        "CREATE TYPE station_user_role AS ENUM ('owner', 'researcher', 'field_operator')"
    )

    op.create_table(
        "user_stations",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "station_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("stations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", station_user_role_enum, nullable=False),
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

    op.create_index(
        "uq_user_stations_active",
        "user_stations",
        ["user_id", "station_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.execute(
        """
        CREATE TRIGGER set_user_stations_updated_at
        BEFORE UPDATE ON user_stations
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS set_user_stations_updated_at ON user_stations")
    op.drop_index("uq_user_stations_active", table_name="user_stations")
    op.drop_table("user_stations")
    op.execute("DROP TYPE IF EXISTS station_user_role")
