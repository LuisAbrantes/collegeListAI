"""add_admission_fields_to_colleges

Revision ID: ea06f5b72373
Revises: 951b4fd3ef49
Create Date: 2026-01-04 22:35:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'ea06f5b72373'
down_revision: Union[str, Sequence[str], None] = '951b4fd3ef49'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add admission statistics and metadata fields to colleges table."""
    # City
    op.add_column('colleges', sa.Column('city', sa.String(length=100), nullable=True))
    
    # Admission statistics
    op.add_column('colleges', sa.Column('acceptance_rate', sa.Float(), nullable=True))
    op.add_column('colleges', sa.Column('sat_25th', sa.Integer(), nullable=True))
    op.add_column('colleges', sa.Column('sat_75th', sa.Integer(), nullable=True))
    op.add_column('colleges', sa.Column('act_25th', sa.Integer(), nullable=True))
    op.add_column('colleges', sa.Column('act_75th', sa.Integer(), nullable=True))
    op.add_column('colleges', sa.Column('student_size', sa.Integer(), nullable=True))
    
    # Freshness tracking
    op.add_column('colleges', sa.Column('updated_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove admission fields from colleges table."""
    op.drop_column('colleges', 'updated_at')
    op.drop_column('colleges', 'student_size')
    op.drop_column('colleges', 'act_75th')
    op.drop_column('colleges', 'act_25th')
    op.drop_column('colleges', 'sat_75th')
    op.drop_column('colleges', 'sat_25th')
    op.drop_column('colleges', 'acceptance_rate')
    op.drop_column('colleges', 'city')
