"""Add chat_threads and chat_messages tables

Revision ID: 0003_add_chat_tables
Revises: 0002_add_full_name
Create Date: 2025-12-23

Creates tables for chat persistence:
- chat_threads: Stores conversation threads per user
- chat_messages: Stores individual messages within threads
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0003_add_chat_tables'
down_revision = '0002_add_full_name'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create chat_threads table
    op.create_table(
        'chat_threads',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('langgraph_thread_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chat_threads_user_id', 'chat_threads', ['user_id'], unique=False)
    
    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('thread_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sources', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['thread_id'], ['chat_threads.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chat_messages_thread_id', 'chat_messages', ['thread_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_chat_messages_thread_id', table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index('idx_chat_threads_user_id', table_name='chat_threads')
    op.drop_table('chat_threads')
