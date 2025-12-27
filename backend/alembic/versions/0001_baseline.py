"""Baseline migration - existing schema

Revision ID: 0001_baseline
Revises: 
Create Date: 2025-12-23

This is a baseline migration that marks the existing database schema
as the starting point for Alembic. No changes are made.

The existing tables (profiles, colleges_cache) were created via Supabase
and this migration exists only to establish the Alembic version history.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001_baseline'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Baseline migration - no changes needed.
    
    Existing tables:
    - profiles: User profiles with academic and preference data
    - colleges_cache: Cached university data with vector embeddings
    - user_exclusions: User's blacklisted colleges
    """
    pass


def downgrade() -> None:
    """Cannot downgrade from baseline."""
    pass
