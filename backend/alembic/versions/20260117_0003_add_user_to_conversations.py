"""Add user_id to conversations for Phase 2

Revision ID: 20260117_0003
Revises: d3e4f5a6b7c8
Create Date: 2026-01-17 20:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, None] = 'd3e4f5a6b7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_id column to conversations (nullable for now)
    op.add_column(
        "conversations",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_conversations_user_id",
        "conversations",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add index for efficient querying
    op.create_index("idx_conversations_user", "conversations", ["user_id"])

    # Add conversation metadata fields
    op.add_column(
        "conversations",
        sa.Column("title", sa.String(255), nullable=True)
    )
    op.add_column(
        "conversations",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column(
        "conversations",
        sa.Column("last_message_preview", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    # Remove columns
    op.drop_column("conversations", "last_message_preview")
    op.drop_column("conversations", "is_archived")
    op.drop_column("conversations", "title")

    # Remove index
    op.drop_index("idx_conversations_user", "conversations")

    # Remove column (foreign key will be dropped automatically)
    op.drop_column("conversations", "user_id")
