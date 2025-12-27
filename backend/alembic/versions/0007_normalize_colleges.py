"""normalize_colleges_schema

Revision ID: 0007_normalize_colleges
Revises: 0006_major_segmented_cache
Create Date: 2025-12-26

Normalizes colleges_cache into two tables:
- colleges: Fixed institutional data (one row per university)
- college_major_stats: Major-specific RAG data

Migrates all existing data to preserve the cache populated by Ollama/Gemini.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0007_normalize_colleges'
down_revision: Union[str, Sequence[str], None] = '0006_major_segmented_cache'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Normalize colleges_cache into proper relational tables.
    
    Steps:
    1. Create new 'colleges' table for institutional data
    2. Create new 'college_major_stats' table for major-specific data
    3. Migrate data from colleges_cache to normalized tables
    4. Rename colleges_cache to colleges_cache_backup
    """
    
    # Step 1: Create colleges table
    op.create_table(
        'colleges',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('campus_setting', sa.String(length=50), nullable=True),
        sa.Column('need_blind_international', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('meets_full_need', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', name='colleges_name_unique')
    )
    
    # Add index on name for fast lookups
    op.create_index('ix_colleges_name', 'colleges', ['name'])
    
    # Step 2: Create college_major_stats table
    op.create_table(
        'college_major_stats',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('college_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('major_name', sa.String(length=100), nullable=False),
        sa.Column('acceptance_rate', sa.Float(), nullable=True),
        sa.Column('median_gpa', sa.Float(), nullable=True),
        sa.Column('sat_25th', sa.Integer(), nullable=True),
        sa.Column('sat_75th', sa.Integer(), nullable=True),
        sa.Column('major_strength', sa.Integer(), nullable=True),
        sa.Column('data_source', sa.String(length=100), nullable=True, server_default='gemini'),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['college_id'], ['colleges.id'], name='fk_college_major_stats_college_id', ondelete='CASCADE'),
        sa.UniqueConstraint('college_id', 'major_name', name='college_major_stats_unique')
    )
    
    # Add indexes for efficient queries
    op.create_index('ix_college_major_stats_college_id', 'college_major_stats', ['college_id'])
    op.create_index('ix_college_major_stats_major_name', 'college_major_stats', ['major_name'])
    op.create_index('ix_college_major_stats_major_updated', 'college_major_stats', ['major_name', 'updated_at'])
    
    # Step 3: Migrate data from colleges_cache
    # 3a: Insert unique colleges (take first occurrence for institutional data)
    op.execute("""
        INSERT INTO colleges (id, name, campus_setting, need_blind_international, meets_full_need, created_at)
        SELECT DISTINCT ON (name)
            gen_random_uuid(),
            name,
            campus_setting,
            COALESCE(need_blind_international, false),
            COALESCE(meets_full_need, false),
            COALESCE(updated_at, now())
        FROM colleges_cache
        ORDER BY name, updated_at DESC;
    """)
    
    # 3b: Insert major stats with FK references
    op.execute("""
        INSERT INTO college_major_stats (id, college_id, major_name, acceptance_rate, median_gpa, sat_25th, sat_75th, major_strength, data_source, updated_at)
        SELECT 
            gen_random_uuid(),
            c.id,
            COALESCE(cc.target_major, 'general'),
            cc.acceptance_rate,
            cc.median_gpa,
            cc.sat_25th,
            cc.sat_75th,
            cc.major_strength,
            cc.data_source,
            cc.updated_at
        FROM colleges_cache cc
        JOIN colleges c ON c.name = cc.name;
    """)
    
    # Step 4: Rename old table as backup (preserving data for rollback)
    op.rename_table('colleges_cache', 'colleges_cache_backup')


def downgrade() -> None:
    """
    Revert to denormalized colleges_cache table.
    """
    # Rename backup back to original
    op.rename_table('colleges_cache_backup', 'colleges_cache')
    
    # Drop new tables
    op.drop_index('ix_college_major_stats_major_updated', table_name='college_major_stats')
    op.drop_index('ix_college_major_stats_major_name', table_name='college_major_stats')
    op.drop_index('ix_college_major_stats_college_id', table_name='college_major_stats')
    op.drop_table('college_major_stats')
    
    op.drop_index('ix_colleges_name', table_name='colleges')
    op.drop_table('colleges')
