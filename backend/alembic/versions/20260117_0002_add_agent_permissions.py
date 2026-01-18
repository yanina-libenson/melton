"""Add agent permissions table

Revision ID: 20260117_0002
Revises: 20260117_0001
Create Date: 2026-01-17 19:15:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd3e4f5a6b7c8'
down_revision: Union[str, None] = 'c2d3e4f5a6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create agent_permissions table
    op.create_table(
        "agent_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("granted_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_type", sa.String(20), nullable=False),
        sa.Column("granted_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )

    # Add foreign key constraints
    op.create_foreign_key(
        "fk_agent_permissions_agent_id",
        "agent_permissions",
        "agents",
        ["agent_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_agent_permissions_user_id",
        "agent_permissions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_agent_permissions_granted_by",
        "agent_permissions",
        "users",
        ["granted_by"],
        ["id"],
        ondelete="CASCADE",
    )

    # Add unique constraint (one permission per user per agent)
    op.create_unique_constraint(
        "uq_agent_permissions_agent_user",
        "agent_permissions",
        ["agent_id", "user_id"],
    )

    # Add indexes for efficient querying
    op.create_index("idx_agent_permissions_agent", "agent_permissions", ["agent_id"])
    op.create_index("idx_agent_permissions_user", "agent_permissions", ["user_id"])

    # Add shareable fields to agents table
    op.add_column("agents", sa.Column("is_shareable", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("agents", sa.Column("share_code", sa.String(100), nullable=True, unique=True))

    # Grant admin permissions to existing agent owners
    # This ensures backward compatibility - all existing agents get admin permissions for their creators
    op.execute("""
        INSERT INTO agent_permissions (agent_id, user_id, granted_by, permission_type, granted_at)
        SELECT id, user_id, user_id, 'admin', NOW()
        FROM agents
        WHERE user_id IS NOT NULL
    """)


def downgrade() -> None:
    # Remove columns from agents
    op.drop_column("agents", "share_code")
    op.drop_column("agents", "is_shareable")

    # Drop indexes
    op.drop_index("idx_agent_permissions_user", "agent_permissions")
    op.drop_index("idx_agent_permissions_agent", "agent_permissions")

    # Drop table (foreign keys will be dropped automatically due to CASCADE)
    op.drop_table("agent_permissions")
