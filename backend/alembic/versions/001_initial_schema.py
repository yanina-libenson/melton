"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2025-12-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create agents table
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True), nullable=False, index=True
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("model_config", postgresql.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Create integrations table
    op.create_table(
        "integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("platform_id", sa.String(100), nullable=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config", postgresql.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Create tools table
    op.create_table(
        "tools",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "integration_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("integrations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tool_schema", postgresql.JSON(), nullable=False),
        sa.Column("config", postgresql.JSON(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Create encrypted_credentials table
    op.create_table(
        "encrypted_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "integration_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("integrations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("credential_type", sa.String(50), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("token_expiry", sa.DateTime(), nullable=True),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column("oauth_token_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Create conversations table
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("channel_type", sa.String(50), nullable=False),
        sa.Column("external_user_id", sa.String(255), nullable=True, index=True),
        sa.Column("conversation_metadata", postgresql.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Create messages table
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_calls", postgresql.JSON(), nullable=False),
        sa.Column("message_metadata", postgresql.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
    )

    # Create deployments table
    op.create_table(
        "deployments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("channel_type", sa.String(50), nullable=False),
        sa.Column("config", postgresql.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Create execution_traces table
    op.create_table(
        "execution_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("step_type", sa.String(50), nullable=False),
        sa.Column("step_data", postgresql.JSON(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("execution_traces")
    op.drop_table("deployments")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("encrypted_credentials")
    op.drop_table("tools")
    op.drop_table("integrations")
    op.drop_table("agents")
