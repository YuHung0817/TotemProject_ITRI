"""fix image dimension backfill path

Revision ID: ba7e42c19d31
Revises: 64ad9af7d820
Create Date: 2026-07-22
"""
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from PIL import Image


revision: str = "ba7e42c19d31"
down_revision: Union[str, None] = "64ad9af7d820"
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
    image_root = Path(__file__).resolve().parents[2] / "data" / "images"
    rows = connection.execute(
        sa.select(assets.c.id, assets.c.storage_key).where(
            sa.or_(assets.c.width.is_(None), assets.c.height.is_(None))
        )
    ).all()
    for asset_id, storage_key in rows:
        image_file = image_root / Path(storage_key).name
        try:
            with Image.open(image_file) as image:
                width, height = image.size
        except (OSError, ValueError):
            continue
        connection.execute(
            assets.update().where(assets.c.id == asset_id).values(width=width, height=height)
        )


def downgrade() -> None:
    pass
