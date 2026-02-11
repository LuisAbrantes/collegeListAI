"""
Subscription Database Model

SQLModel table for subscription data persistence.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID as PGUUID


class SubscriptionModel(SQLModel, table=True):
    """
    Subscription table for storing user subscription data.
    
    Maps to the 'subscriptions' table in PostgreSQL.
    """
    
    __tablename__ = "subscriptions"
    
    id: UUID = Field(default_factory=uuid4, sa_column=Column(PGUUID(as_uuid=True), primary_key=True))
    user_id: UUID = Field(sa_column=Column(PGUUID(as_uuid=True), unique=True, index=True, nullable=False))
    
    # Stripe IDs
    stripe_customer_id: Optional[str] = Field(default=None, unique=True, index=True)
    stripe_subscription_id: Optional[str] = Field(default=None, unique=True, index=True)
    
    # Subscription details
    tier: str = Field(default="free")
    status: str = Field(default="active")
    currency: str = Field(default="USD")
    billing_period: str = Field(default="monthly")
    
    # Billing period dates
    current_period_start: Optional[datetime] = Field(default=None)
    current_period_end: Optional[datetime] = Field(default=None)
    cancel_at_period_end: bool = Field(default=False)
    
    # Usage tracking
    conversations_used: int = Field(default=0)
    conversations_limit: int = Field(default=3)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
