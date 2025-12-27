"""
Unit tests for normalized college schema.

Tests the split architecture with:
- CollegeRepository: Institutional data
- CollegeMajorStatsRepository: Major-specific RAG data
- JOIN queries between tables
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.infrastructure.db.models.college import (
    College, 
    CollegeCreate,
    CollegeMajorStats,
    CollegeMajorStatsCreate,
    CollegeWithMajorStats,
)
from app.infrastructure.db.repositories.college_repository import (
    CollegeRepository,
    CollegeMajorStatsRepository,
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
def college_repo(mock_session):
    """College repository with mocked session."""
    return CollegeRepository(mock_session)


@pytest.fixture
def stats_repo(mock_session):
    """Major stats repository with mocked session."""
    return CollegeMajorStatsRepository(mock_session)


@pytest.fixture
def sample_college_id():
    """Sample college UUID."""
    return uuid4()


@pytest.fixture
def mit_college_data():
    """MIT institutional data."""
    return CollegeCreate(
        name="Massachusetts Institute of Technology",
        campus_setting="URBAN",
        need_blind_international=True,
        meets_full_need=True,
    )


@pytest.fixture
def mit_cs_stats(sample_college_id):
    """MIT Computer Science major stats."""
    return CollegeMajorStatsCreate(
        college_id=sample_college_id,
        major_name="Computer Science",
        acceptance_rate=0.04,
        median_gpa=3.97,
        sat_25th=1520,
        sat_75th=1580,
        major_strength=10,
        data_source="gemini",
    )


@pytest.fixture
def mit_physics_stats(sample_college_id):
    """MIT Physics major stats."""
    return CollegeMajorStatsCreate(
        college_id=sample_college_id,
        major_name="Physics",
        acceptance_rate=0.04,
        median_gpa=3.95,
        sat_25th=1510,
        sat_75th=1570,
        major_strength=10,
        data_source="gemini",
    )


# ============== College Repository Tests ==============

class TestCollegeRepository:
    """Tests for CollegeRepository (institutional data)."""
    
    @pytest.mark.asyncio
    async def test_get_by_name(self, college_repo, mock_session):
        """get_by_name should query by unique name."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await college_repo.get_by_name("MIT")
        
        mock_session.execute.assert_called_once()
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_or_create_creates_new(self, college_repo, mock_session, mit_college_data):
        """get_or_create should create new college if not exists."""
        # Mock get_by_name returns None (not found)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        with patch.object(college_repo, 'create', new_callable=AsyncMock) as mock_create:
            new_college = College(**mit_college_data.model_dump(), id=uuid4())
            mock_create.return_value = new_college
            
            college, created = await college_repo.get_or_create(mit_college_data)
            
            assert created is True
            mock_create.assert_called_once_with(mit_college_data)


# ============== Major Stats Repository Tests ==============

class TestCollegeMajorStatsRepository:
    """Tests for CollegeMajorStatsRepository (major-specific data)."""
    
    @pytest.mark.asyncio
    async def test_get_by_college_and_major(self, stats_repo, mock_session, sample_college_id):
        """get_by_college_and_major should query by composite key."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await stats_repo.get_by_college_and_major(
            sample_college_id, 
            "Computer Science"
        )
        
        mock_session.execute.assert_called_once()
        assert result is None
    
    @pytest.mark.asyncio
    async def test_upsert_creates_new(self, stats_repo, mock_session, sample_college_id, mit_cs_stats):
        """upsert should create new stats if not exists."""
        # Mock get_by_college_and_major returns None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        with patch.object(stats_repo, 'create', new_callable=AsyncMock) as mock_create:
            new_stats = CollegeMajorStats(**mit_cs_stats.model_dump(), id=uuid4())
            mock_create.return_value = new_stats
            
            result = await stats_repo.upsert(sample_college_id, mit_cs_stats)
            
            mock_create.assert_called_once()


# ============== Normalized Schema Tests ==============

class TestNormalizedSchema:
    """Tests for normalized schema behavior."""
    
    def test_college_create_no_major_fields(self, mit_college_data):
        """CollegeCreate should NOT have major-specific fields."""
        assert not hasattr(mit_college_data, 'acceptance_rate')
        assert not hasattr(mit_college_data, 'median_gpa')
        assert not hasattr(mit_college_data, 'target_major')
    
    def test_stats_create_has_college_id(self, mit_cs_stats):
        """CollegeMajorStatsCreate should have college_id FK."""
        assert hasattr(mit_cs_stats, 'college_id')
        assert mit_cs_stats.college_id is not None
    
    def test_different_majors_same_college(self, mit_cs_stats, mit_physics_stats):
        """Same college_id can have different major stats."""
        assert mit_cs_stats.college_id == mit_physics_stats.college_id
        assert mit_cs_stats.major_name != mit_physics_stats.major_name
        # Both can have different stats
        assert mit_cs_stats.median_gpa != mit_physics_stats.median_gpa


class TestCollegeWithMajorStats:
    """Tests for JOINed response model."""
    
    def test_combined_view_has_all_fields(self):
        """CollegeWithMajorStats should have both institution and stats fields."""
        combined = CollegeWithMajorStats(
            id=uuid4(),
            name="MIT",
            campus_setting="URBAN",
            need_blind_international=True,
            meets_full_need=True,
            major_name="Computer Science",
            acceptance_rate=0.04,
            median_gpa=3.97,
            sat_25th=1520,
            sat_75th=1580,
            major_strength=10,
            data_source="gemini",
            updated_at=datetime.utcnow(),
        )
        
        # Institution fields
        assert combined.name == "MIT"
        assert combined.need_blind_international is True
        
        # Major-specific fields
        assert combined.major_name == "Computer Science"
        assert combined.acceptance_rate == 0.04
        assert combined.major_strength == 10
