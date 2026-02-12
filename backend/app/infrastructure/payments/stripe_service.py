"""
Stripe Payment Service

Clean Architecture infrastructure service for Stripe payment processing.
Handles checkout sessions, customer management, and billing portal.

Following stripe-integration skill patterns:
- Hosted Checkout for minimal PCI burden
- Customer Portal for subscription management
- Idempotent webhook handling
"""

import logging
from typing import Optional
import stripe
from stripe import StripeError

from app.config.settings import get_settings
from app.domain.subscription import (
    SubscriptionTier,
    Currency,
    BillingPeriod,
)


logger = logging.getLogger(__name__)


class StripeServiceError(Exception):
    """Base exception for Stripe service errors."""
    pass


class StripeService:
    """
    Stripe payment processing service.
    
    Implements Repository pattern for payment operations.
    All methods are stateless and idempotent where possible.
    """
    
    def __init__(self):
        """Initialize Stripe with API key from settings."""
        settings = get_settings()
        self._api_key = settings.stripe_secret_key
        self._webhook_secret = settings.stripe_webhook_secret
        
        if self._api_key:
            stripe.api_key = self._api_key
        
        # Price ID mapping: (tier, currency, period) -> stripe_price_id
        # Using settings that match .env naming convention
        # Launch prices are used when launch_promo_active is True
        self._price_map = {
            # Student Monthly (launch prices)
            (SubscriptionTier.STUDENT, Currency.USD, BillingPeriod.MONTHLY): (
                settings.stripe_price_id_launch_usd if settings.launch_promo_active 
                else settings.stripe_price_id_regular_usd
            ),
            (SubscriptionTier.STUDENT, Currency.BRL, BillingPeriod.MONTHLY): (
                settings.stripe_price_id_launch_brl if settings.launch_promo_active 
                else settings.stripe_price_id_regular_brl
            ),
            # Student Annual
            (SubscriptionTier.STUDENT, Currency.USD, BillingPeriod.ANNUAL): settings.stripe_price_id_annual_usd,
            (SubscriptionTier.STUDENT, Currency.BRL, BillingPeriod.ANNUAL): settings.stripe_price_id_annual_brl,
            
            # Senior Monthly (uses same price structure as Student for now - USD only)
            (SubscriptionTier.SENIOR, Currency.USD, BillingPeriod.MONTHLY): (
                settings.stripe_price_id_launch_usd if settings.launch_promo_active 
                else settings.stripe_price_id_regular_usd
            ),
            (SubscriptionTier.SENIOR, Currency.BRL, BillingPeriod.MONTHLY): (
                settings.stripe_price_id_launch_brl if settings.launch_promo_active 
                else settings.stripe_price_id_regular_brl
            ),
            # Senior Annual
            (SubscriptionTier.SENIOR, Currency.USD, BillingPeriod.ANNUAL): settings.stripe_price_id_annual_usd,
            (SubscriptionTier.SENIOR, Currency.BRL, BillingPeriod.ANNUAL): settings.stripe_price_id_annual_brl,
        }
    
    def _get_price_id(
        self,
        tier: SubscriptionTier,
        currency: Currency,
        billing_period: BillingPeriod,
    ) -> str:
        """Get Stripe Price ID for given tier/currency/period combination."""
        price_id = self._price_map.get((tier, currency, billing_period))
        
        if not price_id:
            raise StripeServiceError(
                f"No price configured for {tier.value}/{currency.value}/{billing_period.value}"
            )
        
        return price_id
    
    # =========================================================================
    # Customer Management
    # =========================================================================
    
    async def create_customer(
        self,
        user_id: str,
        email: str,
        name: Optional[str] = None,
    ) -> stripe.Customer:
        """
        Create a new Stripe customer.
        
        Args:
            user_id: Internal user ID (stored in metadata)
            email: Customer email for receipts
            name: Optional customer name
            
        Returns:
            stripe.Customer object
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata={
                    "user_id": user_id,
                    "source": "college_list_ai",
                },
            )
            logger.info(f"Created Stripe customer {customer.id} for user {user_id}")
            return customer
            
        except StripeError as e:
            logger.error(f"Failed to create Stripe customer: {e}")
            raise StripeServiceError(f"Failed to create customer: {e.user_message}")
    
    async def get_or_create_customer(
        self,
        user_id: str,
        email: str,
        existing_customer_id: Optional[str] = None,
    ) -> stripe.Customer:
        """
        Get existing customer or create new one.
        
        Args:
            user_id: Internal user ID
            email: Customer email
            existing_customer_id: Optional existing Stripe customer ID
            
        Returns:
            stripe.Customer object
        """
        if existing_customer_id:
            try:
                customer = stripe.Customer.retrieve(existing_customer_id)
                if not customer.get("deleted"):
                    return customer
            except StripeError:
                logger.warning(f"Customer {existing_customer_id} not found, creating new")
        
        return await self.create_customer(user_id, email)
    
    # =========================================================================
    # Checkout Session (MRR Subscription Flow)
    # =========================================================================
    
    async def create_checkout_session(
        self,
        customer_id: str,
        tier: SubscriptionTier,
        currency: Currency,
        billing_period: BillingPeriod,
        success_url: str,
        cancel_url: str,
        user_id: str,
    ) -> stripe.checkout.Session:
        """
        Create a Stripe Checkout Session for subscription.
        
        Uses Hosted Checkout for minimal PCI compliance burden.
        
        Args:
            customer_id: Stripe customer ID
            tier: Subscription tier to purchase
            currency: Payment currency
            billing_period: Monthly or annual billing
            success_url: Redirect after successful payment
            cancel_url: Redirect after cancelled payment
            user_id: Internal user ID for metadata
            
        Returns:
            stripe.checkout.Session with checkout URL
        """
        price_id = self._get_price_id(tier, currency, billing_period)
        
        try:
            session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=["card"],
                line_items=[
                    {
                        "price": price_id,
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url,
                allow_promotion_codes=True,
                billing_address_collection="auto",
                metadata={
                    "user_id": user_id,
                    "tier": tier.value,
                    "currency": currency.value,
                    "billing_period": billing_period.value,
                },
                subscription_data={
                    "metadata": {
                        "user_id": user_id,
                        "tier": tier.value,
                    },
                },
            )
            
            logger.info(
                f"Created checkout session {session.id} for user {user_id}, "
                f"tier={tier.value}, currency={currency.value}"
            )
            return session
            
        except StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            raise StripeServiceError(f"Failed to create checkout: {e.user_message}")
    
    # =========================================================================
    # Customer Portal (Subscription Management)
    # =========================================================================
    
    async def create_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> stripe.billing_portal.Session:
        """
        Create a Billing Portal session for self-service management.
        
        Allows customers to:
        - Update payment method
        - Cancel subscription
        - View invoices
        
        Args:
            customer_id: Stripe customer ID
            return_url: URL to return to after portal session
            
        Returns:
            stripe.billing_portal.Session with portal URL
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            
            logger.info(f"Created portal session for customer {customer_id}")
            return session
            
        except StripeError as e:
            logger.error(f"Failed to create portal session: {e}")
            raise StripeServiceError(f"Failed to create portal: {e.user_message}")
    
    # =========================================================================
    # Subscription Queries
    # =========================================================================
    
    async def get_subscription(
        self,
        subscription_id: str,
    ) -> Optional[stripe.Subscription]:
        """
        Retrieve a subscription by ID.
        
        Args:
            subscription_id: Stripe subscription ID
            
        Returns:
            stripe.Subscription or None if not found
        """
        try:
            return stripe.Subscription.retrieve(subscription_id)
        except StripeError as e:
            logger.warning(f"Failed to retrieve subscription {subscription_id}: {e}")
            return None
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        cancel_at_period_end: bool = True,
    ) -> stripe.Subscription:
        """
        Cancel a subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            cancel_at_period_end: If True, cancel at end of billing period
            
        Returns:
            Updated stripe.Subscription
        """
        try:
            if cancel_at_period_end:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True,
                )
            else:
                subscription = stripe.Subscription.cancel(subscription_id)
            
            logger.info(
                f"Cancelled subscription {subscription_id}, "
                f"at_period_end={cancel_at_period_end}"
            )
            return subscription
            
        except StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            raise StripeServiceError(f"Failed to cancel: {e.user_message}")
    
    # =========================================================================
    # Webhook Verification
    # =========================================================================
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> stripe.Event:
        """
        Verify webhook signature and construct event.
        
        Per stripe-integration skill:
        "Always verify webhook signatures"
        
        Args:
            payload: Raw request body
            signature: Stripe-Signature header
            
        Returns:
            stripe.Event if valid
            
        Raises:
            StripeServiceError if signature invalid
        """
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self._webhook_secret,
            )
            return event
            
        except ValueError as e:
            raise StripeServiceError(f"Invalid payload: {e}")
        except stripe.error.SignatureVerificationError as e:
            raise StripeServiceError(f"Invalid signature: {e}")


# =============================================================================
# Singleton Instance (Dependency Injection Ready)
# =============================================================================

_stripe_service_instance: Optional[StripeService] = None


def get_stripe_service() -> StripeService:
    """Get or create Stripe service singleton."""
    global _stripe_service_instance
    
    if _stripe_service_instance is None:
        _stripe_service_instance = StripeService()
    
    return _stripe_service_instance
