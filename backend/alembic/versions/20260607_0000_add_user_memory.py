"""Add user_memory table

Revision ID: a1b2c3d4e5f6
Revises: f5a6b7c8d9e0
Create Date: 2026-06-07 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_memory",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("collection", sa.String(100), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_foreign_key(
        "fk_user_memory_user_id",
        "user_memory",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_user_memory_agent_id",
        "user_memory",
        "agents",
        ["agent_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # One record per (operator, agent, collection, label): re-saving updates it.
    op.create_unique_constraint(
        "uq_user_memory_scope_label",
        "user_memory",
        ["user_id", "agent_id", "collection", "label"],
    )

    op.create_index("idx_user_memory_user", "user_memory", ["user_id"])
    op.create_index("idx_user_memory_agent", "user_memory", ["agent_id"])
    op.create_index("idx_user_memory_collection", "user_memory", ["collection"])


def downgrade() -> None:
    op.drop_index("idx_user_memory_collection", table_name="user_memory")
    op.drop_index("idx_user_memory_agent", table_name="user_memory")
    op.drop_index("idx_user_memory_user", table_name="user_memory")
    op.drop_constraint("uq_user_memory_scope_label", "user_memory", type_="unique")
    op.drop_constraint("fk_user_memory_agent_id", "user_memory", type_="foreignkey")
    op.drop_constraint("fk_user_memory_user_id", "user_memory", type_="foreignkey")
    op.drop_table("user_memory")
