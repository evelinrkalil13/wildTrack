"""add zone color column

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "zones",
        sa.Column(
            "color",
            sa.String(7),
            nullable=False,
            server_default="#52b788",
        ),
    )


def downgrade() -> None:
    op.drop_column("zones", "color")
