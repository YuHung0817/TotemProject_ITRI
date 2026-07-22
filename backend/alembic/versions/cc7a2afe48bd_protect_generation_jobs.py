"""protect generation jobs

Revision ID: cc7a2afe48bd
Revises: f0f40d90734c
Create Date: 2026-07-21 13:59:52.517990
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "cc7a2afe48bd"
down_revision: Union[str, None] = "f0f40d90734c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "generation_jobs",
        sa.Column(
            "result_record_ids",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column(
        "generation_jobs",
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_generation_jobs_one_active_user",
        "generation_jobs",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('pending', 'running')"),
        postgresql_where=sa.text("status IN ('pending', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_generation_jobs_one_active_user", table_name="generation_jobs")
    op.drop_column("generation_jobs", "finished_at")
    op.drop_column("generation_jobs", "result_record_ids")
