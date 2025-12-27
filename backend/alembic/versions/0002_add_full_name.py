"""Add name column to profiles

Revision ID: 0002_add_full_name
Revises: 0001_baseline
Create Date: 2025-12-23

Adds name column for UI personalization.
NOTE: This field is for UI/UX only - NOT sent to AI.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0002_add_full_name'
down_revision: Union[str, Sequence[str], None] = '0001_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add name column to profiles table."""
    op.add_column(
        'profiles',
        sa.Column('name', sa.String(100), nullable=True)
    )


def downgrade() -> None:
    """Remove name column."""
    op.drop_column('profiles', 'name')
