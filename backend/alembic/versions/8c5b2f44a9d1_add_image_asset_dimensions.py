"""add image asset dimensions

Revision ID: 8c5b2f44a9d1
Revises: cc7a2afe48bd
Create Date: 2026-07-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8c5b2f44a9d1"
down_revision: Union[str, None] = "cc7a2afe48bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("image_assets", sa.Column("width", sa.Integer(), nullable=True))
    op.add_column("image_assets", sa.Column("height", sa.Integer(), nullable=True))

def downgrade() -> None:
    op.drop_column("image_assets", "height")
    op.drop_column("image_assets", "width")
