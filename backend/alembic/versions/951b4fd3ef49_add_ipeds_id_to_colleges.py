"""add_ipeds_id_to_colleges

Revision ID: 951b4fd3ef49
Revises: 0009_college_list_tables
Create Date: 2026-01-04 22:02:32.428482

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '951b4fd3ef49'
down_revision: Union[str, Sequence[str], None] = '0009_college_list_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ipeds_id column to colleges table."""
    # Add IPEDS Unit ID column for College Scorecard integration
    op.add_column('colleges', sa.Column('ipeds_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_colleges_ipeds_id'), 'colleges', ['ipeds_id'], unique=False)


def downgrade() -> None:
    """Remove ipeds_id column from colleges table."""
    op.drop_index(op.f('ix_colleges_ipeds_id'), table_name='colleges')
    op.drop_column('colleges', 'ipeds_id')
