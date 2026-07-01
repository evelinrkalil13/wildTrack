"""create animals table

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PGEnum

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

animal_sex_enum = PGEnum(
    "male", "female", "unknown",
    name="animal_sex",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE TYPE animal_sex AS ENUM ('male', 'female', 'unknown')")

    op.create_table(
        "animals",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("rfid_tag", sa.String(100), nullable=True),
        sa.Column("species", sa.String(255), nullable=False),
        sa.Column("sex", animal_sex_enum, nullable=False, server_default="unknown"),
        sa.Column("estimated_age", sa.String(100), nullable=True),
        sa.Column("is_identified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("notes", sa.Text, nullable=True),
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

    # Partial unique: one RFID tag per active animal
    op.create_index(
        "animals_rfid_key",
        "animals",
        ["rfid_tag"],
        unique=True,
        postgresql_where=sa.text("rfid_tag IS NOT NULL AND deleted_at IS NULL"),
    )

    # Support indexes
    op.create_index(
        "idx_animals_rfid_active",
        "animals",
        ["rfid_tag"],
        postgresql_where=sa.text("rfid_tag IS NOT NULL AND deleted_at IS NULL"),
    )
    op.create_index(
        "idx_animals_species_active",
        "animals",
        ["species"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # CHECK: is_identified must be consistent with rfid_tag
    op.execute(
        "ALTER TABLE animals ADD CONSTRAINT animals_identified_chk "
        "CHECK ("
        "  (is_identified = TRUE AND rfid_tag IS NOT NULL) OR "
        "  (is_identified = FALSE)"
        ")"
    )

    # CHECK: species must be non-blank
    op.execute(
        "ALTER TABLE animals ADD CONSTRAINT animals_species_len_chk "
        "CHECK (LENGTH(TRIM(species)) > 0)"
    )

    op.execute(
        """
        CREATE TRIGGER set_animals_updated_at
        BEFORE UPDATE ON animals
        FOR EACH ROW EXECUTE FUNCTION set_updated_at()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS set_animals_updated_at ON animals")
    op.execute("ALTER TABLE animals DROP CONSTRAINT IF EXISTS animals_species_len_chk")
    op.execute("ALTER TABLE animals DROP CONSTRAINT IF EXISTS animals_identified_chk")
    op.drop_index("idx_animals_species_active", table_name="animals")
    op.drop_index("idx_animals_rfid_active", table_name="animals")
    op.drop_index("animals_rfid_key", table_name="animals")
    op.drop_table("animals")
    op.execute("DROP TYPE IF EXISTS animal_sex")
