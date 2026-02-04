"""Add RLS policies for analytics tables

Revision ID: 0011
Revises: 0010_user_events_and_outcomes
Create Date: 2026-01-10
"""

from alembic import op


# revision identifiers
revision = '0011_analytics_rls_policies'
down_revision = '0010_user_events_and_outcomes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable RLS on user_events
    op.execute("ALTER TABLE user_events ENABLE ROW LEVEL SECURITY")
    
    # Policy: Users can only insert their own events
    op.execute("""
        CREATE POLICY user_events_insert_policy ON user_events
        FOR INSERT
        WITH CHECK (user_id = auth.uid())
    """)
    
    # Policy: Users can only select their own events
    op.execute("""
        CREATE POLICY user_events_select_policy ON user_events
        FOR SELECT
        USING (user_id = auth.uid())
    """)
    
    # Enable RLS on application_outcomes
    op.execute("ALTER TABLE application_outcomes ENABLE ROW LEVEL SECURITY")
    
    # Policy: Users can only insert their own outcomes
    op.execute("""
        CREATE POLICY outcomes_insert_policy ON application_outcomes
        FOR INSERT
        WITH CHECK (user_id = auth.uid())
    """)
    
    # Policy: Users can only select their own outcomes
    op.execute("""
        CREATE POLICY outcomes_select_policy ON application_outcomes
        FOR SELECT
        USING (user_id = auth.uid())
    """)
    
    # Policy: Users can only update their own outcomes
    op.execute("""
        CREATE POLICY outcomes_update_policy ON application_outcomes
        FOR UPDATE
        USING (user_id = auth.uid())
        WITH CHECK (user_id = auth.uid())
    """)


def downgrade() -> None:
    # Drop policies
    op.execute("DROP POLICY IF EXISTS user_events_insert_policy ON user_events")
    op.execute("DROP POLICY IF EXISTS user_events_select_policy ON user_events")
    op.execute("DROP POLICY IF EXISTS outcomes_insert_policy ON application_outcomes")
    op.execute("DROP POLICY IF EXISTS outcomes_select_policy ON application_outcomes")
    op.execute("DROP POLICY IF EXISTS outcomes_update_policy ON application_outcomes")
    
    # Disable RLS
    op.execute("ALTER TABLE user_events DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE application_outcomes DISABLE ROW LEVEL SECURITY")
