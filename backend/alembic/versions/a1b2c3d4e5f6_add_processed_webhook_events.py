"""add processed_webhook_events table

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2026-02-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '0013_add_subscriptions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'processed_webhook_events',
        sa.Column('event_id', sa.String(255), primary_key=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column(
            'processed_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )
    # Index for cleanup queries (delete events older than X days)
    op.create_index(
        'ix_processed_webhook_events_processed_at',
        'processed_webhook_events',
        ['processed_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_processed_webhook_events_processed_at')
    op.drop_table('processed_webhook_events')
