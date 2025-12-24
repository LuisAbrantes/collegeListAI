"""add_college_stats_fields

Revision ID: 0004_college_stats
Revises: 0003_add_chat_tables
Create Date: 2025-12-23

Adds structured fields to colleges_cache for Smart Sourcing RAG Pipeline.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004_college_stats'
down_revision: Union[str, Sequence[str], None] = '0003_add_chat_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add structured stats fields to colleges_cache."""
    # Add new columns to colleges_cache
    op.add_column('colleges_cache', sa.Column('acceptance_rate', sa.Float(), nullable=True))
    op.add_column('colleges_cache', sa.Column('median_gpa', sa.Float(), nullable=True))
    op.add_column('colleges_cache', sa.Column('sat_25th', sa.Integer(), nullable=True))
    op.add_column('colleges_cache', sa.Column('sat_75th', sa.Integer(), nullable=True))
    op.add_column('colleges_cache', sa.Column('need_blind_international', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('colleges_cache', sa.Column('meets_full_need', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('colleges_cache', sa.Column('campus_setting', sa.String(length=50), nullable=True))
    op.add_column('colleges_cache', sa.Column('data_source', sa.String(length=100), nullable=True))
    op.add_column('colleges_cache', sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True))


def downgrade() -> None:
    """Remove stats fields from colleges_cache."""
    op.drop_column('colleges_cache', 'updated_at')
    op.drop_column('colleges_cache', 'data_source')
    op.drop_column('colleges_cache', 'campus_setting')
    op.drop_column('colleges_cache', 'meets_full_need')
    op.drop_column('colleges_cache', 'need_blind_international')
    op.drop_column('colleges_cache', 'sat_75th')
    op.drop_column('colleges_cache', 'sat_25th')
    op.drop_column('colleges_cache', 'median_gpa')
    op.drop_column('colleges_cache', 'acceptance_rate')
