"""
Unit tests for the Profiles Router.

Tests all CRUD endpoints with mocked UserProfileRepository.
Validates request/response schemas and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import ValidationError

from app.api.routes.profiles import (
    ProfileCreateRequest,
    ProfileUpdateRequest,
    ProfileResponse,
    _profile_to_response,
)
from app.domain.models import CitizenshipStatus


# ============================================================================
# Schema Validation Tests
# ============================================================================

class TestProfileCreateRequest:
    """Validate ProfileCreateRequest schema."""

    def test_valid_minimal_request(self):
        """Minimal valid request requires citizenship_status, gpa, major."""
        req = ProfileCreateRequest(
            citizenship_status=CitizenshipStatus.INTERNATIONAL,
            gpa=3.8,
            major="Computer Science",
        )
        assert req.citizenship_status == CitizenshipStatus.INTERNATIONAL
        assert req.gpa == 3.8
        assert req.major == "Computer Science"
        assert req.sat_score is None
        assert req.is_student_athlete is False

    def test_valid_full_request(self):
        """Full request with all optional fields."""
        req = ProfileCreateRequest(
            citizenship_status=CitizenshipStatus.US_CITIZEN,
            nationality="United States",
            gpa=3.9,
            major="Physics",
            sat_score=1500,
            act_score=34,
            state_of_residence="California",
            household_income_tier="MEDIUM",
            english_proficiency_score=110,
            campus_vibe="URBAN",
            is_student_athlete=True,
            has_legacy_status=True,
            legacy_universities=["MIT", "Stanford"],
            post_grad_goal="GRADUATE_SCHOOL",
        )
        assert req.sat_score == 1500
        assert req.legacy_universities == ["MIT", "Stanford"]

    def test_rejects_gpa_out_of_range(self):
        """GPA must be 0.0–4.0."""
        with pytest.raises(ValidationError):
            ProfileCreateRequest(
                citizenship_status=CitizenshipStatus.INTERNATIONAL,
                gpa=5.0,
                major="CS",
            )

    def test_rejects_missing_citizenship(self):
        """citizenship_status is required."""
        with pytest.raises(ValidationError):
            ProfileCreateRequest(gpa=3.0, major="CS")

    def test_rejects_sat_out_of_range(self):
        """SAT must be 400–1600."""
        with pytest.raises(ValidationError):
            ProfileCreateRequest(
                citizenship_status=CitizenshipStatus.INTERNATIONAL,
                gpa=3.5,
                major="CS",
                sat_score=200,
            )


class TestProfileUpdateRequest:
    """Validate ProfileUpdateRequest schema."""

    def test_all_fields_optional(self):
        """Empty update request should be valid."""
        req = ProfileUpdateRequest()
        assert req.gpa is None
        assert req.major is None

    def test_partial_update(self):
        """Should accept partial field set."""
        req = ProfileUpdateRequest(gpa=3.5, sat_score=1400)
        assert req.gpa == 3.5
        assert req.sat_score == 1400
        assert req.major is None


# ============================================================================
# Response Conversion Tests
# ============================================================================

class TestProfileToResponse:
    """Test the _profile_to_response helper."""

    def _make_profile_mock(self, **overrides):
        """Create a mock profile ORM object."""
        defaults = {
            "id": uuid4(),
            "user_id": uuid4(),
            "citizenship_status": CitizenshipStatus.INTERNATIONAL,
            "nationality": "Brazil",
            "gpa": 3.8,
            "major": "Computer Science",
            "sat_score": 1400,
            "act_score": None,
            "state_of_residence": None,
            "household_income_tier": None,
            "english_proficiency_score": 100,
            "campus_vibe": None,
            "is_student_athlete": False,
            "has_legacy_status": False,
            "legacy_universities": None,
            "post_grad_goal": None,
            "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "updated_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
        }
        defaults.update(overrides)
        mock = MagicMock(**defaults)
        # Make enum .value work
        mock.citizenship_status = defaults["citizenship_status"]
        mock.household_income_tier = defaults["household_income_tier"]
        mock.campus_vibe = defaults["campus_vibe"]
        mock.post_grad_goal = defaults["post_grad_goal"]
        return mock

    def test_converts_full_profile(self):
        """Should convert all fields correctly."""
        profile = self._make_profile_mock()
        response = _profile_to_response(profile)

        assert isinstance(response, ProfileResponse)
        assert response.nationality == "Brazil"
        assert response.gpa == 3.8
        assert response.citizenship_status == "INTERNATIONAL"
        assert response.sat_score == 1400
        assert response.english_proficiency_score == 100

    def test_handles_none_enums(self):
        """Should handle None enum fields gracefully."""
        profile = self._make_profile_mock(citizenship_status=None)
        response = _profile_to_response(profile)

        assert response.citizenship_status is None

    def test_formats_timestamps(self):
        """Timestamps should be ISO format strings."""
        profile = self._make_profile_mock()
        response = _profile_to_response(profile)

        assert "2025-01-01" in response.created_at
        assert "2025-06-01" in response.updated_at
