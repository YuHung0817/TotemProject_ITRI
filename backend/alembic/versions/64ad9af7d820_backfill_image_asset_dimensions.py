"""backfill image asset dimensions

Revision ID: 64ad9af7d820
Revises: 8c5b2f44a9d1
Create Date: 2026-07-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.services.storage_service import image_metadata, image_path


revision: str = "64ad9af7d820"
down_revision: Union[str, None] = "8c5b2f44a9d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    assets = sa.table(
        "image_assets",
        sa.column("id", sa.String()),
        sa.column("storage_key", sa.String()),
        sa.column("width", sa.Integer()),
        sa.column("height", sa.Integer()),
    )
    rows = connection.execute(
        sa.select(assets.c.id, assets.c.storage_key).where(
            sa.or_(assets.c.width.is_(None), assets.c.height.is_(None))
        )
    ).all()
    for asset_id, storage_key in rows:
        try:
            if not image_path(storage_key).is_file():
                continue
            _, _, width, height = image_metadata(storage_key)
        except (OSError, ValueError):
            continue
        connection.execute(
            assets.update().where(assets.c.id == asset_id).values(width=width, height=height)
        )


def downgrade() -> None:
    pass
