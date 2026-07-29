"""sync image bundle expiry

Revision ID: d6f1a8c42e7b
Revises: ba7e42c19d31
Create Date: 2026-07-27 16:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d6f1a8c42e7b"
down_revision: Union[str, None] = "ba7e42c19d31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    image_records = sa.table(
        "image_records",
        sa.column("id", sa.String()),
        sa.column("expires_at", sa.DateTime(timezone=True)),
    )
    image_assets = sa.table(
        "image_assets",
        sa.column("image_record_id", sa.String()),
        sa.column("expires_at", sa.DateTime(timezone=True)),
        sa.column("deleted_at", sa.DateTime(timezone=True)),
        sa.column("deletion_status", sa.String()),
    )
    record_expiry = (
        sa.select(image_records.c.expires_at)
        .where(image_records.c.id == image_assets.c.image_record_id)
        .scalar_subquery()
    )
    op.execute(
        image_assets.update()
        .where(
            image_assets.c.deleted_at.is_(None),
            image_assets.c.deletion_status == "active",
        )
        .values(expires_at=record_expiry)
    )


def downgrade() -> None:
    # Previous per-asset deadlines cannot be reconstructed after synchronization.
    pass
