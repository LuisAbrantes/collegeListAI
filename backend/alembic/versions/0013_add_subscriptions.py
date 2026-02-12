"""Add subscriptions table

Revision ID: 0013
Revises: 0012_complete_rls_policies
Create Date: 2026-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0013_add_subscriptions'
down_revision: Union[str, None] = '0012_complete_rls_policies'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create subscriptions table for Stripe subscription management."""
    
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False, unique=True, index=True),
        
        # Stripe IDs
        sa.Column('stripe_customer_id', sa.String(255), unique=True, index=True),
        sa.Column('stripe_subscription_id', sa.String(255), unique=True, index=True),
        
        # Subscription details
        sa.Column('tier', sa.String(20), server_default='free', nullable=False),
        sa.Column('status', sa.String(20), server_default='active', nullable=False),
        sa.Column('currency', sa.String(3), server_default='USD'),
        sa.Column('billing_period', sa.String(20), server_default='monthly'),
        
        # Billing period dates
        sa.Column('current_period_start', sa.DateTime(timezone=True)),
        sa.Column('current_period_end', sa.DateTime(timezone=True)),
        sa.Column('cancel_at_period_end', sa.Boolean, server_default='false'),
        
        # Usage tracking
        sa.Column('conversations_used', sa.Integer, server_default='0'),
        sa.Column('conversations_limit', sa.Integer, server_default='3'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Create index for status queries
    op.create_index(
        'ix_subscriptions_tier_status',
        'subscriptions',
        ['tier', 'status']
    )
    
    # Enable RLS
    op.execute('ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY')
    
    # RLS Policy: Users can only see their own subscription
    op.execute("""
        CREATE POLICY "Users can view own subscription"
        ON subscriptions FOR SELECT
        TO authenticated
        USING (user_id = auth.uid()::text)
    """)
    
    # RLS Policy: Service role can manage all subscriptions (for webhooks)
    op.execute("""
        CREATE POLICY "Service role manages subscriptions"
        ON subscriptions FOR ALL
        TO service_role
        USING (true)
        WITH CHECK (true)
    """)


def downgrade() -> None:
    """Drop subscriptions table."""
    
    # Drop policies
    op.execute('DROP POLICY IF EXISTS "Users can view own subscription" ON subscriptions')
    op.execute('DROP POLICY IF EXISTS "Service role manages subscriptions" ON subscriptions')
    
    # Drop table
    op.drop_table('subscriptions')
