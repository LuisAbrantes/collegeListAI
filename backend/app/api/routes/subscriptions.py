"""
Subscription API Routes

REST API endpoints for subscription management.
Follows FastAPI best practices with dependency injection.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.config.settings import get_settings
from app.domain.subscription import (
    Subscription,
    SubscriptionTier,
    SubscriptionStatus,
    Currency,
    BillingPeriod,
    CreateCheckoutRequest,
    PortalSessionRequest,
    SubscriptionStatusResponse,
    PricingResponse,
    PricingTier,
    CheckoutResponse,
    PortalResponse,
    TIER_LIMITS,
    can_use_chat,
    get_conversations_limit,
)
from app.infrastructure.payments.stripe_service import (
    StripeService,
    StripeServiceError,
    get_stripe_service,
)
from app.infrastructure.db.repositories.subscription_repository import (
    SubscriptionRepository,
    get_subscription_repository,
)
from app.api.dependencies import get_current_user_id


logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Dependencies
# =============================================================================

async def get_user_email(user_id: str) -> str:
    """
    Get user email from Supabase.
    
    TODO: Implement actual email lookup from user profile.
    """
    # For now, return placeholder - will be fetched from profile
    return f"{user_id}@placeholder.com"


# =============================================================================
# Subscription Status Endpoints
# =============================================================================

@router.get("/subscriptions/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    user_id: str = Depends(get_current_user_id),
    repo: SubscriptionRepository = Depends(get_subscription_repository),
):
    """
    Get the current user's subscription status.
    
    Creates a free tier subscription if none exists.
    """
    try:
        subscription = await repo.get_or_create_free(user_id)
        
        return SubscriptionStatusResponse(
            tier=subscription.tier,
            status=subscription.status,
            is_active=subscription.tier != SubscriptionTier.FREE and subscription.status == SubscriptionStatus.ACTIVE,
            billing_period=subscription.billing_period,
            conversations_used=subscription.conversations_used,
            conversations_limit=subscription.conversations_limit,
            can_chat=can_use_chat(subscription),
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            currency=subscription.currency,
        )
        
    except Exception as e:
        logger.error(f"Error getting subscription status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subscription status"
        )


# =============================================================================
# Checkout Endpoints
# =============================================================================

@router.post("/subscriptions/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CreateCheckoutRequest,
    user_id: str = Depends(get_current_user_id),
    stripe_service: StripeService = Depends(get_stripe_service),
    repo: SubscriptionRepository = Depends(get_subscription_repository),
):
    """
    Create a Stripe Checkout session for subscription purchase.
    
    Args:
        request: Checkout request with tier, currency, billing period, and URLs
        
    Returns:
        CheckoutResponse with checkout URL and session ID
    """
    settings = get_settings()
    
    # Validate tier is purchasable
    if request.tier == SubscriptionTier.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot purchase free tier"
        )
    
    try:
        # Get or create subscription record
        subscription = await repo.get_or_create_free(user_id)
        
        # Get or create Stripe customer
        email = await get_user_email(user_id)
        customer = await stripe_service.get_or_create_customer(
            user_id=user_id,
            email=email,
            existing_customer_id=subscription.stripe_customer_id,
        )
        
        # Save customer ID if new
        if not subscription.stripe_customer_id:
            subscription.stripe_customer_id = customer.id
            await repo.update(subscription)
        
        # Create checkout session
        session = await stripe_service.create_checkout_session(
            customer_id=customer.id,
            tier=request.tier,
            currency=request.currency,
            billing_period=request.billing_period,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            user_id=user_id,
        )
        
        logger.info(f"Created checkout session {session.id} for user {user_id}")
        
        return CheckoutResponse(
            checkout_url=session.url,
            session_id=session.id,
        )
        
    except StripeServiceError as e:
        logger.error(f"Stripe error creating checkout: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session"
        )


# =============================================================================
# Portal Endpoints
# =============================================================================

@router.post("/subscriptions/portal", response_model=PortalResponse)
async def create_portal_session(
    request: PortalSessionRequest,
    user_id: str = Depends(get_current_user_id),
    stripe_service: StripeService = Depends(get_stripe_service),
    repo: SubscriptionRepository = Depends(get_subscription_repository),
):
    """
    Create a Stripe Customer Portal session.
    
    Allows customers to manage their subscription:
    - Update payment method
    - Cancel subscription
    - View invoices
    """
    try:
        subscription = await repo.get_by_user_id(user_id)
        
        if not subscription or not subscription.stripe_customer_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No subscription found. Please subscribe first."
            )
        
        session = await stripe_service.create_portal_session(
            customer_id=subscription.stripe_customer_id,
            return_url=request.return_url,
        )
        
        return PortalResponse(portal_url=session.url)
        
    except StripeServiceError as e:
        logger.error(f"Stripe error creating portal: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating portal session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create portal session"
        )


# =============================================================================
# Pricing Endpoints
# =============================================================================

@router.get("/subscriptions/pricing", response_model=PricingResponse)
async def get_pricing_info(
    currency: Currency = Currency.USD,
):
    """
    Get current pricing information for available tiers.
    
    Launch strategy: only Free + Student are visible.
    Senior tier is reserved for future rollout.
    
    Args:
        currency: Currency for price display (USD or BRL)
        
    Returns:
        PricingResponse with available tier pricing
    """
    settings = get_settings()
    
    # Pricing in cents — only launch-visible tiers
    pricing = {
        Currency.USD: {
            SubscriptionTier.STUDENT: {
                "monthly": 1000 if settings.launch_promo_active else 1500,
                "annual": 9900,
            },
        },
        Currency.BRL: {
            SubscriptionTier.STUDENT: {
                "monthly": 5000 if settings.launch_promo_active else 7900,
                "annual": 49900,
            },
        },
    }
    
    tier_pricing = pricing.get(currency, pricing[Currency.USD])
    
    tiers = [
        PricingTier(
            tier=SubscriptionTier.FREE,
            name="Free",
            monthly_price=0,
            annual_price=0,
            features=TIER_LIMITS[SubscriptionTier.FREE]["features"],
            popular=False,
        ),
        PricingTier(
            tier=SubscriptionTier.STUDENT,
            name="Student",
            monthly_price=tier_pricing[SubscriptionTier.STUDENT]["monthly"],
            annual_price=tier_pricing[SubscriptionTier.STUDENT]["annual"],
            features=TIER_LIMITS[SubscriptionTier.STUDENT]["features"],
            popular=True,
        ),
    ]
    
    return PricingResponse(
        currency=currency,
        tiers=tiers,
        launch_promo_active=settings.launch_promo_active,
    )
