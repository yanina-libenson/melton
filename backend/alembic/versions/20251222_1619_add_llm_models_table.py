"""add_llm_models_table

Revision ID: 85023cae20fe
Revises: a6364ba4b378
Create Date: 2025-12-22 16:19:13.515327

"""
from typing import Sequence, Union
import uuid
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '85023cae20fe'
down_revision: Union[str, None] = 'a6364ba4b378'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create llm_models table
    op.create_table(
        'llm_models',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('model_id', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_llm_models_model_id'), 'llm_models', ['model_id'], unique=True)
    op.create_index(op.f('ix_llm_models_provider'), 'llm_models', ['provider'], unique=False)

    # Seed with current models
    llm_models_table = sa.table(
        'llm_models',
        sa.column('id', sa.UUID()),
        sa.column('model_id', sa.String()),
        sa.column('provider', sa.String()),
        sa.column('display_name', sa.String()),
        sa.column('is_active', sa.Boolean()),
        sa.column('created_at', sa.DateTime()),
        sa.column('updated_at', sa.DateTime()),
    )

    now = datetime.utcnow()
    seed_data = [
        # Anthropic models
        {
            'id': uuid.uuid4(),
            'model_id': 'claude-sonnet-4-5-20250929',
            'provider': 'anthropic',
            'display_name': 'Claude Sonnet 4.5',
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': uuid.uuid4(),
            'model_id': 'claude-opus-4-5-20251101',
            'provider': 'anthropic',
            'display_name': 'Claude Opus 4.5',
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': uuid.uuid4(),
            'model_id': 'claude-3-5-sonnet-20241022',
            'provider': 'anthropic',
            'display_name': 'Claude 3.5 Sonnet',
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        # OpenAI models
        {
            'id': uuid.uuid4(),
            'model_id': 'gpt-4o',
            'provider': 'openai',
            'display_name': 'GPT-4o',
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': uuid.uuid4(),
            'model_id': 'gpt-4o-mini',
            'provider': 'openai',
            'display_name': 'GPT-4o Mini',
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': uuid.uuid4(),
            'model_id': 'o1',
            'provider': 'openai',
            'display_name': 'OpenAI o1',
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': uuid.uuid4(),
            'model_id': 'o1-mini',
            'provider': 'openai',
            'display_name': 'OpenAI o1-mini',
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        # Google models
        {
            'id': uuid.uuid4(),
            'model_id': 'gemini-2.0-flash-exp',
            'provider': 'google',
            'display_name': 'Gemini 2.0 Flash',
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
        {
            'id': uuid.uuid4(),
            'model_id': 'gemini-1.5-pro',
            'provider': 'google',
            'display_name': 'Gemini 1.5 Pro',
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        },
    ]

    op.bulk_insert(llm_models_table, seed_data)


def downgrade() -> None:
    op.drop_index(op.f('ix_llm_models_provider'), table_name='llm_models')
    op.drop_index(op.f('ix_llm_models_model_id'), table_name='llm_models')
    op.drop_table('llm_models')
