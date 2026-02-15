"""
Integration Tests for Webhooks (Stripe)

Verifies:
- Signature verification failure (400)
- Successful event processing
- Idempotency (prevent double processing)
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.infrastructure.payments.stripe_service import StripeServiceError


class TestStripeWebhooks:
    
    @pytest.fixture
    def mock_stripe_service(self):
        """Mock the Stripe service factory."""
        with patch("app.api.routes.webhooks.get_stripe_service") as mock_get:
            mock_service = MagicMock()
            mock_get.return_value = mock_service
            yield mock_service

    @pytest.fixture
    def mock_sub_repo(self):
        """Mock the Subscription repository factory."""
        with patch("app.api.routes.webhooks.get_subscription_repository") as mock_get:
            mock_repo = AsyncMock()
            mock_get.return_value = mock_repo
            yield mock_repo

    @pytest.mark.asyncio
    async def test_webhook_missing_signature(self, client):
        """Webhook without signature header should fail 400."""
        response = client.post("/api/webhooks/stripe", json={"id": "evt_123"})
        assert response.status_code == 400
        assert "Missing Stripe signature" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature(self, client, mock_stripe_service):
        """Webhook with invalid signature should fail 400."""
        mock_stripe_service.verify_webhook_signature.side_effect = StripeServiceError("Bad sig")
        
        response = client.post(
            "/api/webhooks/stripe", 
            json={"id": "evt_123"},
            headers={"stripe-signature": "invalid_sig"}
        )
        assert response.status_code == 400
        assert "Invalid signature" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webhook_success_checkout(self, client, mock_stripe_service, mock_sub_repo):
        """Valid checkout.session.completed event should trigger handler."""
        # 1. Mock signature verification to return a valid event
        event_payload = {
            "id": "evt_checkout_ok",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_123",
                    "customer": "cus_test",
                    "subscription": "sub_test",
                    "metadata": {
                        "user_id": "00000000-0000-0000-0000-000000000001",
                        "tier": "student"
                    }
                }
            }
        }
        mock_stripe_service.verify_webhook_signature.return_value = event_payload

        # 2. Mock Idempotency functions (module level)
        # We patch where they are IMPORTED in the router
        with patch("app.api.routes.webhooks.is_event_processed", new_callable=AsyncMock) as mock_is_proc, \
             patch("app.api.routes.webhooks.mark_event_processed", new_callable=AsyncMock) as mock_mark_proc:
            
            mock_is_proc.return_value = False  # Not processed yet
            
            response = client.post(
                "/api/webhooks/stripe", 
                json=event_payload,
                headers={"stripe-signature": "valid_sig"}
            )
            
            assert response.status_code == 200
            assert response.json() == {"status": "success"}
            
            # Verify repo upsert was called
            assert mock_sub_repo.upsert.called
            
            # Verify marked as processed
            mock_mark_proc.assert_called_with("evt_checkout_ok", "checkout.session.completed")

    @pytest.mark.asyncio
    async def test_webhook_idempotency(self, client, mock_stripe_service, mock_sub_repo):
        """Duplicate event should return 'already_processed' and skip logic."""
        event_payload = {
            "id": "evt_duplicate",
            "type": "checkout.session.completed",
            "data": {"object": {}}
        }
        mock_stripe_service.verify_webhook_signature.return_value = event_payload

        with patch("app.api.routes.webhooks.is_event_processed", new_callable=AsyncMock) as mock_is_proc, \
             patch("app.api.routes.webhooks.mark_event_processed", new_callable=AsyncMock) as mock_mark_proc:
            
            mock_is_proc.return_value = True  # Already processed!
            
            response = client.post(
                "/api/webhooks/stripe", 
                json=event_payload,
                headers={"stripe-signature": "valid_sig"}
            )
            
            assert response.status_code == 200
            assert response.json() == {"status": "already_processed"}
            
            # Verify repo was NOT called
            assert not mock_sub_repo.upsert.called
            # Verify we didn't try to mark it again (optional, depending on implementation)
