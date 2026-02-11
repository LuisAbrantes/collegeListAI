"""
Subscription Repository

Data access layer for subscription persistence.
Follows Repository pattern for Clean Architecture.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import uuid4, UUID

from sqlmodel import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.infrastructure.db.database import get_session_context
from app.infrastructure.db.models.subscription import SubscriptionModel
from app.domain.subscription import (
    Subscription,
    SubscriptionTier,
    SubscriptionStatus,
    Currency,
    BillingPeriod,
    get_conversations_limit,
)


logger = logging.getLogger(__name__)


class SubscriptionRepository:
    """
    Repository for subscription data access.
    
    Implements CRUD operations with domain model mapping.
    Uses async SQLModel for database operations.
    """
    
    # =========================================================================
    # Query Methods
    # =========================================================================
    
    async def get_by_user_id(self, user_id: str) -> Optional[Subscription]:
        """
        Get subscription by user ID.
        
        Args:
            user_id: Internal user ID
            
        Returns:
            Subscription domain model or None
        """
        async with get_session_context() as session:
            # Convert string user_id to UUID for PostgreSQL compatibility
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
            statement = select(SubscriptionModel).where(
                SubscriptionModel.user_id == user_uuid
            )
            result = await session.execute(statement)
            model = result.scalar_one_or_none()
            
            if model:
                return self._to_domain(model)
            
            return None
    
    async def get_by_stripe_customer_id(
        self, 
        stripe_customer_id: str,
    ) -> Optional[Subscription]:
        """
        Get subscription by Stripe customer ID.
        
        Args:
            stripe_customer_id: Stripe customer ID
            
        Returns:
            Subscription domain model or None
        """
        async with get_session_context() as session:
            statement = select(SubscriptionModel).where(
                SubscriptionModel.stripe_customer_id == stripe_customer_id
            )
            result = await session.execute(statement)
            model = result.scalar_one_or_none()
            
            if model:
                return self._to_domain(model)
            
            return None
    
    async def get_by_stripe_subscription_id(
        self,
        stripe_subscription_id: str,
    ) -> Optional[Subscription]:
        """
        Get subscription by Stripe subscription ID.
        
        Args:
            stripe_subscription_id: Stripe subscription ID
            
        Returns:
            Subscription domain model or None
        """
        async with get_session_context() as session:
            statement = select(SubscriptionModel).where(
                SubscriptionModel.stripe_subscription_id == stripe_subscription_id
            )
            result = await session.execute(statement)
            model = result.scalar_one_or_none()
            
            if model:
                return self._to_domain(model)
            
            return None
    
    # =========================================================================
    # Command Methods
    # =========================================================================
    
    async def create(self, subscription: Subscription) -> Subscription:
        """
        Create a new subscription.
        
        Args:
            subscription: Subscription domain model
            
        Returns:
            Created subscription with ID
        """
        async with get_session_context() as session:
            model = self._to_model(subscription)
            model.id = uuid4()
            model.created_at = datetime.utcnow()
            model.updated_at = datetime.utcnow()
            
            session.add(model)
            await session.commit()
            await session.refresh(model)
            
            logger.info(f"Created subscription {model.id} for user {model.user_id}")
            return self._to_domain(model)
    
    async def upsert(self, subscription: Subscription) -> Subscription:
        """
        Create or update subscription by user_id.
        
        Uses PostgreSQL upsert for atomicity.
        
        Args:
            subscription: Subscription domain model
            
        Returns:
            Created/updated subscription
        """
        async with get_session_context() as session:
            now = datetime.utcnow()
            
            # Convert string user_id to UUID
            user_uuid = UUID(subscription.user_id) if isinstance(subscription.user_id, str) else subscription.user_id
            
            values = {
                "user_id": user_uuid,
                "stripe_customer_id": subscription.stripe_customer_id,
                "stripe_subscription_id": subscription.stripe_subscription_id,
                "tier": subscription.tier.value,
                "status": subscription.status.value,
                "currency": subscription.currency.value,
                "billing_period": subscription.billing_period.value,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "conversations_used": subscription.conversations_used,
                "conversations_limit": subscription.conversations_limit,
                "updated_at": now,
            }
            
            if not subscription.id:
                values["id"] = uuid4()
                values["created_at"] = now
            
            stmt = pg_insert(SubscriptionModel).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["user_id"],
                set_={
                    "stripe_customer_id": stmt.excluded.stripe_customer_id,
                    "stripe_subscription_id": stmt.excluded.stripe_subscription_id,
                    "tier": stmt.excluded.tier,
                    "status": stmt.excluded.status,
                    "currency": stmt.excluded.currency,
                    "billing_period": stmt.excluded.billing_period,
                    "current_period_start": stmt.excluded.current_period_start,
                    "current_period_end": stmt.excluded.current_period_end,
                    "cancel_at_period_end": stmt.excluded.cancel_at_period_end,
                    "conversations_used": stmt.excluded.conversations_used,
                    "conversations_limit": stmt.excluded.conversations_limit,
                    "updated_at": now,
                },
            )
            
            await session.execute(stmt)
            await session.commit()
            
            # Fetch the result
            return await self.get_by_user_id(subscription.user_id)
    
    async def update(self, subscription: Subscription) -> Subscription:
        """
        Update an existing subscription.
        
        Args:
            subscription: Subscription with updated values
            
        Returns:
            Updated subscription
        """
        async with get_session_context() as session:
            statement = select(SubscriptionModel).where(
                SubscriptionModel.user_id == subscription.user_id
            )
            result = await session.execute(statement)
            model = result.scalar_one_or_none()
            
            if not model:
                raise ValueError(f"Subscription not found for user {subscription.user_id}")
            
            # Update fields
            model.stripe_customer_id = subscription.stripe_customer_id
            model.stripe_subscription_id = subscription.stripe_subscription_id
            model.tier = subscription.tier.value
            model.status = subscription.status.value
            model.currency = subscription.currency.value
            model.billing_period = subscription.billing_period.value
            model.current_period_start = subscription.current_period_start
            model.current_period_end = subscription.current_period_end
            model.cancel_at_period_end = subscription.cancel_at_period_end
            model.conversations_used = subscription.conversations_used
            model.conversations_limit = subscription.conversations_limit
            model.updated_at = datetime.utcnow()
            
            await session.commit()
            await session.refresh(model)
            
            logger.info(f"Updated subscription for user {subscription.user_id}")
            return self._to_domain(model)
    
    async def increment_conversations(self, user_id: str) -> Optional[Subscription]:
        """
        Increment conversation count for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Updated subscription or None
        """
        async with get_session_context() as session:
            statement = select(SubscriptionModel).where(
                SubscriptionModel.user_id == user_id
            )
            result = await session.execute(statement)
            model = result.scalar_one_or_none()
            
            if model:
                model.conversations_used += 1
                model.updated_at = datetime.utcnow()
                await session.commit()
                await session.refresh(model)
                return self._to_domain(model)
            
            return None
    
    async def reset_monthly_conversations(self) -> int:
        """
        Reset conversation counts for all free tier users.
        
        Called by monthly cron job.
        
        Returns:
            Number of subscriptions reset
        """
        async with get_session_context() as session:
            statement = select(SubscriptionModel).where(
                SubscriptionModel.tier == SubscriptionTier.FREE.value
            )
            result = await session.execute(statement)
            models = result.scalars().all()
            
            count = 0
            for model in models:
                model.conversations_used = 0
                model.updated_at = datetime.utcnow()
                count += 1
            
            await session.commit()
            logger.info(f"Reset conversations for {count} free tier users")
            return count
    
    async def get_or_create_free(self, user_id: str) -> Subscription:
        """
        Get existing subscription or create a free tier subscription.
        
        Args:
            user_id: User ID
            
        Returns:
            Subscription (existing or new free tier)
        """
        existing = await self.get_by_user_id(user_id)
        if existing:
            return existing
        
        free_sub = Subscription(
            user_id=user_id,
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            conversations_limit=get_conversations_limit(SubscriptionTier.FREE),
        )
        
        return await self.create(free_sub)
    
    # =========================================================================
    # Mapping Methods
    # =========================================================================
    
    def _to_domain(self, model: SubscriptionModel) -> Subscription:
        """Convert database model to domain entity."""
        return Subscription(
            id=str(model.id),
            user_id=str(model.user_id),
            stripe_customer_id=model.stripe_customer_id,
            stripe_subscription_id=model.stripe_subscription_id,
            tier=SubscriptionTier(model.tier),
            status=SubscriptionStatus(model.status),
            currency=Currency(model.currency) if model.currency else Currency.USD,
            billing_period=BillingPeriod(model.billing_period) if model.billing_period else BillingPeriod.MONTHLY,
            current_period_start=model.current_period_start,
            current_period_end=model.current_period_end,
            cancel_at_period_end=model.cancel_at_period_end or False,
            conversations_used=model.conversations_used or 0,
            conversations_limit=model.conversations_limit or 3,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    def _to_model(self, domain: Subscription) -> SubscriptionModel:
        """Convert domain entity to database model."""
        # Convert string IDs to UUID for PostgreSQL compatibility
        model_id = UUID(domain.id) if domain.id and isinstance(domain.id, str) else None
        user_uuid = UUID(domain.user_id) if isinstance(domain.user_id, str) else domain.user_id
        
        return SubscriptionModel(
            id=model_id,
            user_id=user_uuid,
            stripe_customer_id=domain.stripe_customer_id,
            stripe_subscription_id=domain.stripe_subscription_id,
            tier=domain.tier.value,
            status=domain.status.value,
            currency=domain.currency.value,
            billing_period=domain.billing_period.value,
            current_period_start=domain.current_period_start,
            current_period_end=domain.current_period_end,
            cancel_at_period_end=domain.cancel_at_period_end,
            conversations_used=domain.conversations_used,
            conversations_limit=domain.conversations_limit,
        )


# =============================================================================
# Singleton Instance
# =============================================================================

_subscription_repo_instance: Optional[SubscriptionRepository] = None


def get_subscription_repository() -> SubscriptionRepository:
    """Get or create subscription repository singleton."""
    global _subscription_repo_instance
    
    if _subscription_repo_instance is None:
        _subscription_repo_instance = SubscriptionRepository()
    
    return _subscription_repo_instance
