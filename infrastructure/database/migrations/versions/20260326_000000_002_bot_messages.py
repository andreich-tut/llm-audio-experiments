"""Add bot_messages table for message tracking

Revision ID: 002_bot_messages
Revises: 001_initial
Create Date: 2026-03-26 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import reflection

# revision identifiers, used by Alembic.
revision: str = "002_bot_messages"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    conn = op.get_bind()
    inspector = reflection.Inspector.from_engine(conn.engine)  # type: ignore[attr-defined]
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    conn = op.get_bind()
    inspector = reflection.Inspector.from_engine(conn.engine)  # type: ignore[attr-defined]
    indexes = inspector.get_indexes(table_name)
    return any(idx["name"] == index_name for idx in indexes)


def upgrade() -> None:
    # Bot messages table
    if not _table_exists("bot_messages"):
        op.create_table(
            "bot_messages",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("chat_id", sa.BigInteger(), nullable=False),
            sa.Column("message_id", sa.BigInteger(), nullable=False),
            sa.Column("direction", sa.String(length=4), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not _index_exists("bot_messages", "idx_bot_messages_user_created"):
        op.create_index("idx_bot_messages_user_created", "bot_messages", ["user_id", "created_at"], unique=False)
    if not _index_exists("bot_messages", "idx_bot_messages_user_id"):
        op.create_index("idx_bot_messages_user_id", "bot_messages", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("bot_messages")
