"""Add users table for creator authentication

Revision ID: 20260117_0000
Revises: 20251222_1619_add_llm_models_table
Create Date: 2026-01-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, None] = "85023cae20fe"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("subdomain", sa.String(100), unique=True, nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Create indexes
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_subdomain", "users", ["subdomain"])


def downgrade() -> None:
    op.drop_index("idx_users_subdomain", table_name="users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")
