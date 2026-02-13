"""
Stripe Webhook Handler

Handles Stripe webhook events for subscription lifecycle management.
Implements idempotent event processing backed by the database (survives restarts).

Critical Events:
- checkout.session.completed: Activate subscription after payment
- invoice.payment_succeeded: Extend subscription period
- invoice.payment_failed: Handle failed payment
- customer.subscription.updated: Sync subscription changes
- customer.subscription.deleted: Downgrade to free tier
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, status
from sqlalchemy import text

from app.domain.subscription import (
    Subscription,
    SubscriptionTier,
    SubscriptionStatus,
    Currency,
    BillingPeriod,
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
from app.infrastructure.db.database import get_session_context


logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Idempotency: DB-backed processed event tracking
# =============================================================================

async def is_event_processed(event_id: str) -> bool:
    """Check if a webhook event has already been processed (DB query)."""
    async with get_session_context() as session:
        result = await session.execute(
            text("SELECT 1 FROM processed_webhook_events WHERE event_id = :eid"),
            {"eid": event_id},
        )
        return result.scalar_one_or_none() is not None


async def mark_event_processed(event_id: str, event_type: str) -> None:
    """Record a processed webhook event in the database."""
    async with get_session_context() as session:
        await session.execute(
            text(
                "INSERT INTO processed_webhook_events (event_id, event_type) "
                "VALUES (:eid, :etype) ON CONFLICT (event_id) DO NOTHING"
            ),
            {"eid": event_id, "etype": event_type},
        )


# =============================================================================
# Webhook Endpoint
# =============================================================================

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.
    
    Verifies signature and processes subscription lifecycle events.
    Returns 200 OK to acknowledge receipt (Stripe will retry on failure).
    """
    stripe_service = get_stripe_service()
    repo = get_subscription_repository()
    
    # Get raw payload and signature
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature"
        )
    
    # Verify signature
    try:
        event = stripe_service.verify_webhook_signature(payload, signature)
    except StripeServiceError as e:
        logger.error(f"Webhook signature verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature"
        )
    
    event_id = event.get("id")
    event_type = event.get("type")
    
    # Idempotency check
    if is_event_processed(event_id):
        logger.info(f"Event {event_id} already processed, skipping")
        return {"status": "already_processed"}
    
    logger.info(f"Processing webhook event: {event_type} ({event_id})")
    
    try:
        # Route to appropriate handler
        if event_type == "checkout.session.completed":
            await handle_checkout_completed(event["data"]["object"], repo)
            
        elif event_type == "invoice.payment_succeeded":
            await handle_invoice_payment_succeeded(event["data"]["object"], repo)
            
        elif event_type == "invoice.payment_failed":
            await handle_invoice_payment_failed(event["data"]["object"], repo)
            
        elif event_type == "customer.subscription.updated":
            await handle_subscription_updated(event["data"]["object"], repo)
            
        elif event_type == "customer.subscription.deleted":
            await handle_subscription_deleted(event["data"]["object"], repo)
            
        else:
            logger.debug(f"Unhandled event type: {event_type}")
        
        # Mark as processed (DB-backed)
        await mark_event_processed(event_id, event_type)
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error processing webhook {event_type}: {e}")
        # Return 200 to prevent Stripe retries for non-recoverable errors
        # In production, you might want to return 500 for transient errors
        return {"status": "error", "message": str(e)}


# =============================================================================
# Event Handlers
# =============================================================================

async def handle_checkout_completed(session: dict, repo: SubscriptionRepository):
    """
    Handle successful checkout session completion.
    
    Activates the subscription for the user.
    """
    # Extract metadata
    metadata = session.get("metadata", {})
    user_id = metadata.get("user_id")
    tier_value = metadata.get("tier", "student")
    currency_value = metadata.get("currency", "USD")
    billing_period_value = metadata.get("billing_period", "monthly")
    
    if not user_id:
        logger.error("Checkout completed without user_id in metadata")
        return
    
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    
    # Map tier
    try:
        tier = SubscriptionTier(tier_value)
    except ValueError:
        tier = SubscriptionTier.STUDENT
    
    try:
        currency = Currency(currency_value)
    except ValueError:
        currency = Currency.USD
    
    try:
        billing_period = BillingPeriod(billing_period_value)
    except ValueError:
        billing_period = BillingPeriod.MONTHLY
    
    # Create/update subscription
    subscription = Subscription(
        user_id=user_id,
        stripe_customer_id=customer_id,
        stripe_subscription_id=subscription_id,
        tier=tier,
        status=SubscriptionStatus.ACTIVE,
        currency=currency,
        billing_period=billing_period,
        conversations_limit=get_conversations_limit(tier),
        conversations_used=0,  # Reset on new subscription
    )
    
    await repo.upsert(subscription)
    logger.info(f"Activated {tier.value} subscription for user {user_id}")


async def handle_invoice_payment_succeeded(invoice: dict, repo: SubscriptionRepository):
    """
    Handle successful invoice payment.
    
    Extends subscription period and resets usage counters.
    """
    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")
    
    if not customer_id or not subscription_id:
        return
    
    subscription = await repo.get_by_stripe_customer_id(customer_id)
    
    if subscription:
        # Update period dates from subscription object
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.conversations_used = 0  # Reset monthly usage
        subscription.updated_at = datetime.utcnow()
        
        await repo.update(subscription)
        logger.info(f"Renewed subscription for customer {customer_id}")


async def handle_invoice_payment_failed(invoice: dict, repo: SubscriptionRepository):
    """
    Handle failed invoice payment.
    
    Sets subscription to past_due status.
    """
    customer_id = invoice.get("customer")
    
    if not customer_id:
        return
    
    subscription = await repo.get_by_stripe_customer_id(customer_id)
    
    if subscription:
        subscription.status = SubscriptionStatus.PAST_DUE
        subscription.updated_at = datetime.utcnow()
        
        await repo.update(subscription)
        logger.warning(f"Payment failed for customer {customer_id}, set to past_due")


async def handle_subscription_updated(subscription_data: dict, repo: SubscriptionRepository):
    """
    Handle subscription updates from Stripe.
    
    Syncs cancel_at_period_end and status changes.
    """
    customer_id = subscription_data.get("customer")
    
    if not customer_id:
        return
    
    subscription = await repo.get_by_stripe_customer_id(customer_id)
    
    if subscription:
        # Sync status
        stripe_status = subscription_data.get("status")
        if stripe_status == "active":
            subscription.status = SubscriptionStatus.ACTIVE
        elif stripe_status == "past_due":
            subscription.status = SubscriptionStatus.PAST_DUE
        elif stripe_status == "canceled":
            subscription.status = SubscriptionStatus.CANCELED
        elif stripe_status == "trialing":
            subscription.status = SubscriptionStatus.TRIALING
        
        # Sync cancel status
        subscription.cancel_at_period_end = subscription_data.get("cancel_at_period_end", False)
        
        # Sync period end
        period_end = subscription_data.get("current_period_end")
        if period_end:
            subscription.current_period_end = datetime.fromtimestamp(period_end)
        
        subscription.updated_at = datetime.utcnow()
        
        await repo.update(subscription)
        logger.info(f"Synced subscription updates for customer {customer_id}")


async def handle_subscription_deleted(subscription_data: dict, repo: SubscriptionRepository):
    """
    Handle subscription cancellation/deletion.
    
    Downgrades user to free tier.
    """
    customer_id = subscription_data.get("customer")
    
    if not customer_id:
        return
    
    subscription = await repo.get_by_stripe_customer_id(customer_id)
    
    if subscription:
        # Downgrade to free tier
        subscription.tier = SubscriptionTier.FREE
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.stripe_subscription_id = None
        subscription.conversations_limit = get_conversations_limit(SubscriptionTier.FREE)
        subscription.current_period_end = None
        subscription.cancel_at_period_end = False
        subscription.updated_at = datetime.utcnow()
        
        await repo.update(subscription)
        logger.info(f"Downgraded customer {customer_id} to free tier")
