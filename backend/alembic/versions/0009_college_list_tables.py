"""add_college_list_tables

Revision ID: 0009_college_list_tables
Revises: 0008_add_college_fields
Create Date: 2025-12-27

Adds tables for user college list management:
- user_college_list: Saved colleges in user's list
- user_exclusions: Schools to never suggest again
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0009_college_list_tables'
down_revision: Union[str, Sequence[str], None] = '0008_add_college_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create college list and exclusion tables."""
    
    # User's saved college list
    op.create_table(
        'user_college_list',
        sa.Column('id', sa.UUID(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('college_name', sa.String(255), nullable=False),
        sa.Column('label', sa.String(50), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('added_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('user_id', 'college_name', name='uq_user_college_list_user_college')
    )
    op.create_index('ix_user_college_list_user_id', 'user_college_list', ['user_id'])
    
    # User's exclusions
    op.create_table(
        'user_exclusions',
        sa.Column('id', sa.UUID(), nullable=False, primary_key=True),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('profiles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('college_name', sa.String(255), nullable=False),
        sa.Column('reason', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('user_id', 'college_name', name='uq_user_exclusions_user_college')
    )
    op.create_index('ix_user_exclusions_user_id', 'user_exclusions', ['user_id'])


def downgrade() -> None:
    """Remove college list and exclusion tables."""
    op.drop_index('ix_user_exclusions_user_id', table_name='user_exclusions')
    op.drop_table('user_exclusions')
    op.drop_index('ix_user_college_list_user_id', table_name='user_college_list')
    op.drop_table('user_college_list')
