"""Add confirmation_requests table

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-06-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "confirmation_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tool_use_id", sa.String(255), nullable=False),
        sa.Column("tool_name", sa.String(255), nullable=False),
        sa.Column("tool_args", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("reference_id", sa.String(64), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_foreign_key(
        "fk_confirmation_requests_conversation_id",
        "confirmation_requests",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_confirmation_requests_message_id",
        "confirmation_requests",
        "messages",
        ["message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # reference_id is the idempotency key: at most one request per reference_id.
    op.create_unique_constraint(
        "uq_confirmation_requests_reference_id",
        "confirmation_requests",
        ["reference_id"],
    )

    op.create_index(
        "idx_confirmation_requests_conversation",
        "confirmation_requests",
        ["conversation_id"],
    )
    op.create_index(
        "idx_confirmation_requests_status", "confirmation_requests", ["status"]
    )
    op.create_index(
        "idx_confirmation_requests_expires_at", "confirmation_requests", ["expires_at"]
    )


def downgrade() -> None:
    op.drop_index("idx_confirmation_requests_expires_at", table_name="confirmation_requests")
    op.drop_index("idx_confirmation_requests_status", table_name="confirmation_requests")
    op.drop_index("idx_confirmation_requests_conversation", table_name="confirmation_requests")
    op.drop_constraint(
        "uq_confirmation_requests_reference_id",
        "confirmation_requests",
        type_="unique",
    )
    op.drop_constraint(
        "fk_confirmation_requests_message_id", "confirmation_requests", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_confirmation_requests_conversation_id",
        "confirmation_requests",
        type_="foreignkey",
    )
    op.drop_table("confirmation_requests")
