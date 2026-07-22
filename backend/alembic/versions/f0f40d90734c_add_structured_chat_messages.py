"""add structured chat messages

Revision ID: f0f40d90734c
Revises: 383c995657f3
Create Date: 2026-07-21 13:34:48.699738
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f0f40d90734c"
down_revision: Union[str, None] = "383c995657f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("messages")}
    if "message_type" not in columns:
        op.add_column("messages", sa.Column("message_type", sa.String(length=20)))
    if "client_exchange_id" not in columns:
        op.add_column("messages", sa.Column("client_exchange_id", sa.String(length=100)))
    if "content_data" not in columns:
        op.add_column("messages", sa.Column("content_data", sa.JSON()))

    op.execute("UPDATE messages SET message_type = 'generation' WHERE message_type IS NULL")
    op.execute("UPDATE messages SET client_exchange_id = id WHERE client_exchange_id IS NULL")
    op.execute("UPDATE messages SET content_data = '{}' WHERE content_data IS NULL")

    constraint_names = {
        constraint["name"] for constraint in inspector.get_unique_constraints("messages")
    }
    with op.batch_alter_table("messages", recreate="always") as batch_op:
        batch_op.alter_column("message_type", existing_type=sa.String(20), nullable=False)
        batch_op.alter_column("client_exchange_id", existing_type=sa.String(100), nullable=False)
        batch_op.alter_column("content_data", existing_type=sa.JSON(), nullable=False)
        if "uq_messages_chat_exchange_role" not in constraint_names:
            batch_op.create_unique_constraint(
                "uq_messages_chat_exchange_role",
                ["chatroom_id", "client_exchange_id", "role"],
            )


def downgrade() -> None:
    with op.batch_alter_table("messages", recreate="always") as batch_op:
        batch_op.drop_constraint("uq_messages_chat_exchange_role", type_="unique")
        batch_op.drop_column("content_data")
        batch_op.drop_column("client_exchange_id")
        batch_op.drop_column("message_type")
