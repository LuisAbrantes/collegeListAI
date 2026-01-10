"""Add user_events and application_outcomes tables

Revision ID: 0010
Revises: 0009_college_list_tables
Create Date: 2026-01-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers
revision = '0010_user_events_and_outcomes'
down_revision = 'ea06f5b72373'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create user_events table
    op.create_table(
        'user_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('college_name', sa.String(255), nullable=True),
        sa.Column('metadata', JSONB, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    # Indexes for user_events
    op.create_index('idx_user_events_user_id', 'user_events', ['user_id'])
    op.create_index('idx_user_events_type', 'user_events', ['event_type'])
    op.create_index('idx_user_events_created_at', 'user_events', ['created_at'])
    
    # Create application_outcomes table
    op.create_table(
        'application_outcomes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('college_name', sa.String(255), nullable=False),
        sa.Column('predicted_label', sa.String(50), nullable=True),
        sa.Column('outcome_status', sa.String(50), nullable=False),
        sa.Column('cycle_year', sa.Integer, nullable=False),
        sa.Column('submitted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
    )
    
    # Indexes for application_outcomes
    op.create_index('idx_outcomes_user_id', 'application_outcomes', ['user_id'])
    op.create_index('idx_outcomes_college', 'application_outcomes', ['college_name'])
    op.create_index('idx_outcomes_cycle', 'application_outcomes', ['cycle_year'])
    
    # Unique constraint: one outcome per user + college
    op.create_unique_constraint(
        'uq_user_college_outcome',
        'application_outcomes',
        ['user_id', 'college_name']
    )


def downgrade() -> None:
    op.drop_table('application_outcomes')
    op.drop_table('user_events')
