"""Add RLS policies for all remaining tables

Revision ID: 0012
Revises: 0011_analytics_rls_policies
Create Date: 2026-01-12

Fixes Security Advisor warnings for:
- colleges (public read)
- college_major_stats (public read)
- user_college_list (user-owned)
- user_exclusions (user-owned)
- chat_threads (user-owned)
- chat_messages (user-owned via thread)
- alembic_version (internal only)
"""

from alembic import op


revision = '0012_complete_rls_policies'
down_revision = '0011_analytics_rls_policies'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # =========================================================================
    # 1. COLLEGES (Public Read)
    # =========================================================================
    op.execute("ALTER TABLE public.colleges ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY colleges_select_policy ON public.colleges
        FOR SELECT USING (true)
    """)

    # =========================================================================
    # 2. COLLEGE_MAJOR_STATS (Public Read)
    # =========================================================================
    op.execute("ALTER TABLE public.college_major_stats ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY college_major_stats_select_policy ON public.college_major_stats
        FOR SELECT USING (true)
    """)

    # =========================================================================
    # 3. USER_COLLEGE_LIST (User-owned)
    # =========================================================================
    op.execute("ALTER TABLE public.user_college_list ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY user_college_list_select_policy ON public.user_college_list
        FOR SELECT USING (user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY user_college_list_insert_policy ON public.user_college_list
        FOR INSERT WITH CHECK (user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY user_college_list_update_policy ON public.user_college_list
        FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY user_college_list_delete_policy ON public.user_college_list
        FOR DELETE USING (user_id = auth.uid())
    """)

    # =========================================================================
    # 4. USER_EXCLUSIONS (User-owned)
    # =========================================================================
    op.execute("ALTER TABLE public.user_exclusions ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY user_exclusions_select_policy ON public.user_exclusions
        FOR SELECT USING (user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY user_exclusions_insert_policy ON public.user_exclusions
        FOR INSERT WITH CHECK (user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY user_exclusions_delete_policy ON public.user_exclusions
        FOR DELETE USING (user_id = auth.uid())
    """)

    # =========================================================================
    # 5. CHAT_THREADS (User-owned)
    # =========================================================================
    op.execute("ALTER TABLE public.chat_threads ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY chat_threads_select_policy ON public.chat_threads
        FOR SELECT USING (user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY chat_threads_insert_policy ON public.chat_threads
        FOR INSERT WITH CHECK (user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY chat_threads_update_policy ON public.chat_threads
        FOR UPDATE USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid())
    """)
    op.execute("""
        CREATE POLICY chat_threads_delete_policy ON public.chat_threads
        FOR DELETE USING (user_id = auth.uid())
    """)

    # =========================================================================
    # 6. CHAT_MESSAGES (User-owned via thread relationship)
    # =========================================================================
    op.execute("ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY chat_messages_select_policy ON public.chat_messages
        FOR SELECT USING (
            EXISTS (
                SELECT 1 FROM public.chat_threads
                WHERE chat_threads.id = chat_messages.thread_id
                AND chat_threads.user_id = auth.uid()
            )
        )
    """)
    op.execute("""
        CREATE POLICY chat_messages_insert_policy ON public.chat_messages
        FOR INSERT WITH CHECK (
            EXISTS (
                SELECT 1 FROM public.chat_threads
                WHERE chat_threads.id = thread_id
                AND chat_threads.user_id = auth.uid()
            )
        )
    """)
    op.execute("""
        CREATE POLICY chat_messages_delete_policy ON public.chat_messages
        FOR DELETE USING (
            EXISTS (
                SELECT 1 FROM public.chat_threads
                WHERE chat_threads.id = chat_messages.thread_id
                AND chat_threads.user_id = auth.uid()
            )
        )
    """)

    # =========================================================================
    # 7. ALEMBIC_VERSION (Internal only - no public access)
    # =========================================================================
    op.execute("ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY")
    # No policies = no access via PostgREST, only service_role can access


def downgrade() -> None:
    # Drop all policies and disable RLS
    tables = [
        'colleges', 'college_major_stats', 'user_college_list',
        'user_exclusions', 'chat_threads', 'chat_messages', 'alembic_version'
    ]
    
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_select_policy ON public.{table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_policy ON public.{table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_update_policy ON public.{table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_delete_policy ON public.{table}")
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY")
