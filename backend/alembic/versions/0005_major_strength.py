"""add_major_strength_column

Revision ID: 0005_major_strength
Revises: 0004_college_stats
Create Date: 2025-12-24

Adds major_strength column to colleges_cache for storing program ranking data.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005_major_strength'
down_revision: Union[str, Sequence[str], None] = '0004_college_stats'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add major_strength column to colleges_cache."""
    op.add_column('colleges_cache', sa.Column('major_strength', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Remove major_strength column from colleges_cache."""
    op.drop_column('colleges_cache', 'major_strength')
