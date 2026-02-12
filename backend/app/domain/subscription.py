"""
Subscription Domain Models

Domain models for subscription management following Clean Architecture.
Enums, DTOs, and domain entities for the subscription bounded context.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class SubscriptionTier(str, Enum):
    """Subscription tier levels."""
    FREE = "free"
    STUDENT = "student"
    SENIOR = "senior"


class SubscriptionStatus(str, Enum):
    """Subscription lifecycle status."""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"


class Currency(str, Enum):
    """Supported payment currencies."""
    USD = "USD"
    BRL = "BRL"


class BillingPeriod(str, Enum):
    """Billing period for subscriptions."""
    MONTHLY = "monthly"
    ANNUAL = "annual"


# =============================================================================
# Domain Entities
# =============================================================================

class Subscription(BaseModel):
    """Core subscription domain entity."""
    id: Optional[str] = None
    user_id: str
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    tier: SubscriptionTier = SubscriptionTier.FREE
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    currency: Currency = Currency.USD
    billing_period: BillingPeriod = BillingPeriod.MONTHLY
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    conversations_used: int = 0
    conversations_limit: int = 3
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =============================================================================
# Request/Response DTOs
# =============================================================================

class CreateCheckoutRequest(BaseModel):
    """Request DTO for creating a checkout session."""
    tier: SubscriptionTier = Field(
        default=SubscriptionTier.STUDENT,
        description="Subscription tier to purchase"
    )
    billing_period: BillingPeriod = Field(
        default=BillingPeriod.MONTHLY,
        description="Billing period (monthly or annual)"
    )
    currency: Currency = Field(
        default=Currency.USD,
        description="Payment currency"
    )
    success_url: str = Field(..., description="Redirect URL after successful payment")
    cancel_url: str = Field(..., description="Redirect URL after cancelled payment")


class PortalSessionRequest(BaseModel):
    """Request DTO for creating a billing portal session."""
    return_url: str = Field(..., description="URL to return to after portal session")


class SubscriptionStatusResponse(BaseModel):
    """Response DTO for subscription status."""
    tier: SubscriptionTier
    status: SubscriptionStatus
    is_active: bool = Field(description="Whether user has active paid subscription")
    billing_period: Optional[BillingPeriod] = None
    conversations_used: int = Field(description="Conversations used this billing cycle")
    conversations_limit: int = Field(description="Maximum conversations allowed")
    can_chat: bool = Field(description="Whether user can start new conversations")
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    currency: Optional[Currency] = None


class PricingTier(BaseModel):
    """Pricing information for a single tier."""
    tier: SubscriptionTier
    name: str
    monthly_price: int  # In cents
    annual_price: int  # In cents
    features: list[str]
    popular: bool = False


class PricingResponse(BaseModel):
    """Response DTO for pricing information."""
    currency: Currency
    tiers: list[PricingTier]
    launch_promo_active: bool = False


class CheckoutResponse(BaseModel):
    """Response DTO for checkout session creation."""
    checkout_url: str
    session_id: str


class PortalResponse(BaseModel):
    """Response DTO for portal session creation."""
    portal_url: str


# =============================================================================
# Tier Configuration (Business Logic)
# =============================================================================

TIER_LIMITS = {
    SubscriptionTier.FREE: {
        "conversations_limit": 3,
        "schools_limit": 10,
        "features": [
            "3 AI conversations per month",
            "Save up to 10 schools",
            "Basic recommendations",
        ],
    },
    SubscriptionTier.STUDENT: {
        "conversations_limit": -1,  # Unlimited
        "schools_limit": -1,  # Unlimited
        "features": [
            "Unlimited AI conversations",
            "Unlimited school saves",
            "Full financial aid analysis",
            "Deep profile analysis",
            "Scholarship matcher",
            "Community access",
            "Early access to new features",
        ],
    },
    # Senior tier kept for future rollout — hidden from pricing at launch
    SubscriptionTier.SENIOR: {
        "conversations_limit": -1,
        "schools_limit": -1,
        "features": [
            "Everything in Student",
            "Dedicated advisor sessions",
            "Custom application timeline",
            "Essay review assistance",
            "Priority support (24h)",
        ],
    },
}


def get_conversations_limit(tier: SubscriptionTier) -> int:
    """Get the conversation limit for a tier. -1 means unlimited."""
    return TIER_LIMITS.get(tier, {}).get("conversations_limit", 3)


def can_use_chat(subscription: Subscription) -> bool:
    """Check if user can start a new conversation."""
    if subscription.tier == SubscriptionTier.FREE:
        limit = get_conversations_limit(subscription.tier)
        return subscription.conversations_used < limit
    return subscription.status == SubscriptionStatus.ACTIVE
