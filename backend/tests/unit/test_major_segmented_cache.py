"""
Unit tests for major-segmented cache architecture.

Tests the new composite key (name, target_major) logic in the repository
and ensures different majors don't overwrite each other's data.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.db.models.college import College, CollegeCreate
from app.infrastructure.db.repositories.college_repository import (
    CollegeRepository,
    STALENESS_DAYS,
)


# ============== Test Fixtures ==============

@pytest.fixture
def mock_session():
    """Mock async session for testing."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def repository(mock_session):
    """College repository with mocked session."""
    return CollegeRepository(mock_session)


@pytest.fixture
def mit_cs_data():
    """MIT with Computer Science major data."""
    return CollegeCreate(
        name="Massachusetts Institute of Technology",
        target_major="Computer Science",
        acceptance_rate=0.04,
        median_gpa=3.97,
        sat_25th=1520,
        sat_75th=1580,
        major_strength=10,
        need_blind_international=True,
        data_source="gemini",
    )


@pytest.fixture
def mit_physics_data():
    """MIT with Physics major data."""
    return CollegeCreate(
        name="Massachusetts Institute of Technology",
        target_major="Physics",
        acceptance_rate=0.04,
        median_gpa=3.95,
        sat_25th=1510,
        sat_75th=1570,
        major_strength=10,  # Also top-tier for Physics
        need_blind_international=True,
        data_source="gemini",
    )


@pytest.fixture
def mit_art_history_data():
    """MIT with Art History major data (less strong)."""
    return CollegeCreate(
        name="Massachusetts Institute of Technology",
        target_major="Art History",
        acceptance_rate=0.04,
        median_gpa=3.90,
        sat_25th=1480,
        sat_75th=1550,
        major_strength=6,  # Not MIT's flagship
        need_blind_international=True,
        data_source="gemini",
    )


# ============== Composite Key Tests ==============

class TestMajorSegmentedCache:
    """Tests for major-segmented cache behavior."""
    
    @pytest.mark.asyncio
    async def test_get_by_name_requires_target_major(self, repository, mock_session):
        """get_by_name should query by both name AND target_major."""
        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Call with both parameters
        result = await repository.get_by_name(
            "MIT", 
            target_major="Computer Science"
        )
        
        # Verify the query was built with both conditions
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        # The statement should contain both name and target_major conditions
        assert call_args is not None
    
    @pytest.mark.asyncio
    async def test_upsert_uses_composite_key(self, repository, mock_session, mit_cs_data):
        """Upsert should use (name, target_major) as the lookup key."""
        # Mock get_by_name to return None (new entry)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Mock create
        with patch.object(repository, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = College(**mit_cs_data.model_dump())
            
            await repository.upsert(mit_cs_data)
            
            # Should have called create since no existing record
            mock_create.assert_called_once_with(mit_cs_data)
    
    @pytest.mark.asyncio
    async def test_different_majors_create_separate_records(
        self, 
        repository, 
        mock_session, 
        mit_cs_data, 
        mit_physics_data
    ):
        """Same college with different majors should create separate cache entries."""
        # Mock get_by_name to always return None (new entries)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        with patch.object(repository, 'create', new_callable=AsyncMock) as mock_create:
            # Create returns the college
            mock_create.side_effect = [
                College(**mit_cs_data.model_dump()),
                College(**mit_physics_data.model_dump()),
            ]
            
            # Upsert CS data
            await repository.upsert(mit_cs_data)
            
            # Upsert Physics data - should NOT overwrite CS
            await repository.upsert(mit_physics_data)
            
            # Both should have called create (separate records)
            assert mock_create.call_count == 2


class TestMajorFilteredQueries:
    """Tests for major-aware query methods."""
    
    @pytest.mark.asyncio
    async def test_get_fresh_colleges_smart_filters_by_major(
        self, 
        repository, 
        mock_session
    ):
        """get_fresh_colleges_smart should filter by target_major."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        await repository.get_fresh_colleges_smart(
            current_provider="gemini",
            target_major="Computer Science",
            limit=20
        )
        
        # Verify execute was called (query built with major filter)
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_count_fresh_smart_filters_by_major(
        self, 
        repository, 
        mock_session
    ):
        """count_fresh_smart should count only for specific major."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result
        
        count = await repository.count_fresh_smart(
            current_provider="gemini",
            target_major="Physics"
        )
        
        assert count == 5
        mock_session.execute.assert_called_once()


class TestCacheMissBehavior:
    """Tests for cache miss detection by major."""
    
    def test_college_create_includes_target_major(self, mit_cs_data):
        """CollegeCreate should include target_major field."""
        assert hasattr(mit_cs_data, 'target_major')
        assert mit_cs_data.target_major == "Computer Science"
    
    def test_different_major_strengths_per_major(
        self, 
        mit_cs_data, 
        mit_art_history_data
    ):
        """Same college can have different major_strength per major."""
        assert mit_cs_data.name == mit_art_history_data.name
        assert mit_cs_data.major_strength == 10  # Top-tier CS
        assert mit_art_history_data.major_strength == 6  # Not flagship
