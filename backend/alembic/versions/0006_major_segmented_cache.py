"""add_target_major_segmented_cache

Revision ID: 0006_major_segmented_cache
Revises: 0005_major_strength
Create Date: 2025-12-24

Adds target_major column and composite unique constraint for major-segmented cache.
Allows the same university to have different statistics for different majors.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006_major_segmented_cache'
down_revision: Union[str, Sequence[str], None] = '0005_major_strength'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add target_major column and composite unique constraint."""
    # Step 1: Add target_major column with default value for existing records
    op.add_column(
        'colleges_cache',
        sa.Column('target_major', sa.String(length=100), nullable=False, server_default='general')
    )
    
    # Step 2: Drop existing unique constraint on name
    # Note: Supabase/PostgreSQL auto-creates this as 'colleges_cache_name_key'
    op.drop_constraint('colleges_cache_name_key', 'colleges_cache', type_='unique')
    
    # Step 3: Create composite unique constraint on (name, target_major)
    op.create_unique_constraint(
        'colleges_cache_name_major_unique',
        'colleges_cache',
        ['name', 'target_major']
    )
    
    # Step 4: Add index on target_major for efficient filtering
    op.create_index(
        'ix_colleges_cache_target_major',
        'colleges_cache',
        ['target_major']
    )
    
    # Step 5: Add COMPOSITE index on (target_major, updated_at) for staleness queries
    # This optimizes get_fresh_colleges_smart which filters by BOTH major AND date
    op.create_index(
        'ix_colleges_cache_major_updated',
        'colleges_cache',
        ['target_major', 'updated_at']
    )


def downgrade() -> None:
    """Revert to single name constraint."""
    # Drop the composite performance index
    op.drop_index('ix_colleges_cache_major_updated', table_name='colleges_cache')
    
    # Drop the target_major index
    op.drop_index('ix_colleges_cache_target_major', table_name='colleges_cache')
    
    # Drop the composite unique constraint
    op.drop_constraint('colleges_cache_name_major_unique', 'colleges_cache', type_='unique')
    
    # Restore the original unique constraint on name only
    op.create_unique_constraint('colleges_cache_name_key', 'colleges_cache', ['name'])
    
    # Drop the target_major column
    op.drop_column('colleges_cache', 'target_major')
