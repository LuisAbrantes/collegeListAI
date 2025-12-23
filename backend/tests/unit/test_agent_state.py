"""
Unit tests for agent state definitions.

Tests the state creation and helper functions.
"""

import pytest

from app.agents.state import (
    create_initial_state,
    is_domestic_student,
    StudentProfile,
)


class TestIsDomesticStudent:
    """Tests for is_domestic_student function."""
    
    def test_us_citizen_is_domestic(self):
        """US citizens should be classified as domestic."""
        profile: StudentProfile = {"citizenship_status": "US_CITIZEN"}
        assert is_domestic_student(profile) is True
    
    def test_permanent_resident_is_domestic(self):
        """Permanent residents should be classified as domestic."""
        profile: StudentProfile = {"citizenship_status": "PERMANENT_RESIDENT"}
        assert is_domestic_student(profile) is True
    
    def test_daca_is_domestic(self):
        """DACA students should be classified as domestic."""
        profile: StudentProfile = {"citizenship_status": "DACA"}
        assert is_domestic_student(profile) is True
    
    def test_international_is_not_domestic(self):
        """International students should not be classified as domestic."""
        profile: StudentProfile = {"citizenship_status": "INTERNATIONAL"}
        assert is_domestic_student(profile) is False
    
    def test_empty_profile_is_not_domestic(self):
        """Empty profile should default to not domestic."""
        profile: StudentProfile = {}
        assert is_domestic_student(profile) is False


class TestCreateInitialState:
    """Tests for create_initial_state function."""
    
    def test_creates_valid_state(self, sample_domestic_profile):
        """Should create a valid initial state."""
        state = create_initial_state(
            user_query="Best CS schools",
            profile=sample_domestic_profile,
            excluded_colleges=["MIT"]
        )
        
        assert state["user_query"] == "Best CS schools"
        assert state["profile"] == sample_domestic_profile
        assert state["excluded_colleges"] == ["MIT"]
        assert state["research_results"] == []
        assert state["recommendations"] == []
        assert state["error"] is None
    
    def test_defaults_excluded_colleges_to_empty_list(self, sample_domestic_profile):
        """Should default excluded_colleges to empty list."""
        state = create_initial_state(
            user_query="Best CS schools",
            profile=sample_domestic_profile,
        )
        
        assert state["excluded_colleges"] == []
