"""Update agents table for user relationships and public access

Revision ID: 20260117_0001
Revises: 20260117_0000
Create Date: 2026-01-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Delete existing test agents that reference non-existent users
    # This is safe because these are only test/development data
    op.execute("DELETE FROM agents WHERE user_id NOT IN (SELECT id FROM users)")

    # Add FK constraint to users
    op.create_foreign_key(
        "fk_agents_user_id",
        "agents",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE"
    )

    # Add public agent fields
    op.add_column("agents", sa.Column("slug", sa.String(100), nullable=True))
    op.add_column("agents", sa.Column("access_mode", sa.String(20), nullable=False, server_default="private"))
    op.add_column("agents", sa.Column("public_name", sa.String(255), nullable=True))
    op.add_column("agents", sa.Column("public_description", sa.Text(), nullable=True))
    op.add_column("agents", sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"))

    # Create unique index for slug per user
    op.create_index(
        "idx_agents_user_slug",
        "agents",
        ["user_id", "slug"],
        unique=True,
        postgresql_where=sa.text("slug IS NOT NULL")
    )


def downgrade() -> None:
    op.drop_index("idx_agents_user_slug", table_name="agents")
    op.drop_column("agents", "is_published")
    op.drop_column("agents", "public_description")
    op.drop_column("agents", "public_name")
    op.drop_column("agents", "access_mode")
    op.drop_column("agents", "slug")
    op.drop_constraint("fk_agents_user_id", "agents", type_="foreignkey")
