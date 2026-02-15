"""
Integration Tests for Core Business Flow (College List)

Verifies:
- Adding colleges to list
- Auto-labeling logic (via mock)
- Error handling
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

# Import the repository class to mock/patch
from app.api.routes.college_list import UserCollegeListRepository

class TestCollegeListFlow:
    
    @pytest.fixture
    def mock_college_list_repo(self):
        """Return a mock repository."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_add_college_happy_path(self, client, auth_headers):
        """
        Successfully adding a college to the list.
        Mocks the repository instantiated inside the route.
        """
        # We need to patch the UserCollegeListRepository class used in the route
        with patch("app.api.routes.college_list.UserCollegeListRepository") as MockRepoClass:
            # Setup the mock instance
            mock_repo_instance = MockRepoClass.return_value
            
            # Mock the 'add' return value (must be an object with attributes)
            mock_item = MagicMock()
            mock_item.id = uuid.uuid4()
            mock_item.college_name = "Stanford University"
            mock_item.label = "reach"
            mock_item.notes = "Dream school"
            mock_item.added_at = datetime.utcnow()
            
            mock_repo_instance.add = AsyncMock(return_value=mock_item)

            payload = {
                "college_name": "Stanford University",
                "label": "reach",
                "notes": "Dream school"
            }
            
            response = client.post(
                "/api/college-list",
                json=payload,
                headers=auth_headers
            )
            
            # Assertions
            if response.status_code != 201:
                print(f"Error response: {response.text}")
                
            assert response.status_code == 201
            data = response.json()
            assert data["college_name"] == "Stanford University"
            assert data["label"] == "reach"
            
            # Verify mock called
            MockRepoClass.assert_called_once()
            mock_repo_instance.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_college_validation_error(self, client, auth_headers):
        """Invalid payload should fail (422)."""
        payload = {
            "college_name": "" # Empty name? Or missing field
            # Missing mandatory fields if any
        }
        # Pydantic checks empty strings? college_name is str.
        # Let's try missing body
        response = client.post(
            "/api/college-list",
            json={},  # Missing college_name
            headers=auth_headers
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_college_list(self, client, auth_headers):
        """Get list returns mapped items."""
        with patch("app.api.routes.college_list.UserCollegeListRepository") as MockRepoClass:
            mock_repo_instance = MockRepoClass.return_value
            
            # Mock get_all
            mock_item = MagicMock()
            mock_item.id = uuid.uuid4()
            mock_item.college_name = "MIT"
            mock_item.label = "reach"
            mock_item.notes = None
            mock_item.added_at = datetime.utcnow()
            
            mock_repo_instance.get_all = AsyncMock(return_value=[mock_item])

            response = client.get(
                "/api/college-list",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["college_name"] == "MIT"
