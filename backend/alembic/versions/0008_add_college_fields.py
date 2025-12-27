"""add_missing_college_fields

Revision ID: 0008_add_college_fields
Revises: 0007_normalize_colleges
Create Date: 2025-12-26

Adds missing fields to colleges table:
- tuition_in_state
- tuition_out_of_state
- tuition_international
- need_blind_domestic
- state
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0008_add_college_fields'
down_revision: Union[str, Sequence[str], None] = '0007_normalize_colleges'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing fields to colleges table."""
    # Tuition fields
    op.add_column('colleges', sa.Column('tuition_in_state', sa.Float(), nullable=True))
    op.add_column('colleges', sa.Column('tuition_out_of_state', sa.Float(), nullable=True))
    op.add_column('colleges', sa.Column('tuition_international', sa.Float(), nullable=True))
    
    # Need-blind for domestic students (default True)
    op.add_column('colleges', sa.Column('need_blind_domestic', sa.Boolean(), 
                                         server_default=sa.text('true'), nullable=False))
    
    # State location
    op.add_column('colleges', sa.Column('state', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Remove added fields from colleges table."""
    op.drop_column('colleges', 'state')
    op.drop_column('colleges', 'need_blind_domestic')
    op.drop_column('colleges', 'tuition_international')
    op.drop_column('colleges', 'tuition_out_of_state')
    op.drop_column('colleges', 'tuition_in_state')
