"""create foods table

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "foods",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
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

    # Partial unique: one name per active food
    op.create_index(
        "foods_name_key",
        "foods",
        ["name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # Support index
    op.create_index(
        "idx_foods_name_active",
        "foods",
        ["name"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.execute(
        "ALTER TABLE foods ADD CONSTRAINT foods_name_len_chk "
        "CHECK (LENGTH(TRIM(name)) > 0)"
    )
    op.execute(
        "ALTER TABLE foods ADD CONSTRAINT foods_type_len_chk "
        "CHECK (LENGTH(TRIM(type)) > 0)"
    )

    op.execute(
        """
        CREATE TRIGGER set_foods_updated_at
        BEFORE UPDATE ON foods
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS set_foods_updated_at ON foods")
    op.execute("ALTER TABLE foods DROP CONSTRAINT IF EXISTS foods_type_len_chk")
    op.execute("ALTER TABLE foods DROP CONSTRAINT IF EXISTS foods_name_len_chk")
    op.drop_index("idx_foods_name_active", table_name="foods")
    op.drop_index("foods_name_key", table_name="foods")
    op.drop_table("foods")
