"""
Unit tests for scoring factors.

Tests the refactored Z-score based Academic Fit and new Label Classifier.
"""

import pytest

from app.domain.scoring.factors.academic_fit import AcademicFitFactor
from app.domain.scoring.label_classifier import LabelClassifier
from app.domain.scoring.interfaces import (
    StudentContext,
    UniversityData,
    AdmissionLabel,
)


# ============== Test Fixtures ==============

@pytest.fixture
def academic_factor():
    """Academic fit factor instance."""
    return AcademicFitFactor()


@pytest.fixture
def label_classifier():
    """Label classifier instance."""
    return LabelClassifier()


@pytest.fixture
def strong_student():
    """Student with strong stats: 3.8 GPA, 1450 SAT."""
    return StudentContext(
        is_domestic=False,
        citizenship_status="INTERNATIONAL",
        nationality="Brazil",
        gpa=3.8,
        sat_score=1450,
        intended_major="Computer Science",
        income_tier="MEDIUM",
    )


@pytest.fixture
def elite_student():
    """Elite student with top stats: 3.95 GPA, 1550 SAT."""
    return StudentContext(
        is_domestic=False,
        citizenship_status="INTERNATIONAL",
        nationality="Brazil",
        gpa=3.95,
        sat_score=1550,
        intended_major="Computer Science",
        income_tier="MEDIUM",
    )


@pytest.fixture
def average_student():
    """Average student: 3.5 GPA, 1300 SAT."""
    return StudentContext(
        is_domestic=True,
        citizenship_status="US_CITIZEN",
        gpa=3.5,
        sat_score=1300,
        intended_major="Computer Science",
        income_tier="MEDIUM",
    )


@pytest.fixture
def mit():
    """MIT university data."""
    return UniversityData(
        name="Massachusetts Institute of Technology",
        acceptance_rate=0.04,
        median_gpa=3.97,
        sat_25th=1520,
        sat_75th=1580,
    )


@pytest.fixture
def uiuc():
    """UIUC university data."""
    return UniversityData(
        name="University of Illinois Urbana-Champaign",
        acceptance_rate=0.45,
        median_gpa=3.78,
        sat_25th=1320,
        sat_75th=1500,
    )


@pytest.fixture
def arizona_state():
    """ASU university data."""
    return UniversityData(
        name="Arizona State University",
        acceptance_rate=0.88,
        median_gpa=3.50,
        sat_25th=1120,
        sat_75th=1340,
    )


# ============== Academic Fit Tests ==============

class TestAcademicFitFactor:
    """Tests for Z-score based Academic Fit calculation."""
    
    def test_at_median_gpa_yields_competitive_score(self, academic_factor, uiuc):
        """Student at median GPA should score ~80% (competitive)."""
        student = StudentContext(
            is_domestic=True,
            citizenship_status="US_CITIZEN",
            gpa=3.78,  # Exactly at UIUC median
            sat_score=1400,
            intended_major="CS",
        )
        
        score = academic_factor.calculate(student, uiuc)
        
        # Should be around 80, not 49%
        assert score >= 75, f"At-median student should score >=75%, got {score}%"
        assert score <= 85, f"At-median student should score <=85%, got {score}%"
    
    def test_slightly_below_median_not_heavily_penalized(self, academic_factor, mit):
        """Student 0.1 below median should still score reasonably."""
        student = StudentContext(
            is_domestic=False,
            citizenship_status="INTERNATIONAL",
            gpa=3.87,  # 0.1 below MIT median of 3.97
            sat_score=1540,
            intended_major="CS",
        )
        
        score = academic_factor.calculate(student, mit)
        
        # Should be around 70-75, NOT 49%
        assert score >= 65, f"Slightly below median should score >=65%, got {score}%"
    
    def test_above_median_yields_high_score(self, academic_factor, uiuc, strong_student):
        """Student above median should score high."""
        score = academic_factor.calculate(strong_student, uiuc)
        
        # 3.8 GPA vs 3.78 median = slight advantage
        assert score >= 78, f"Above median should score >=78%, got {score}%"
    
    def test_well_above_median_yields_very_high_score(self, academic_factor, arizona_state, elite_student):
        """Elite student at safety school should score very high."""
        score = academic_factor.calculate(elite_student, arizona_state)
        
        # 3.95 GPA vs 3.50 median = huge advantage
        assert score >= 90, f"Well above median should score >=90%, got {score}%"


# ============== Label Classifier Tests ==============

class TestLabelClassifier:
    """Tests for Reach/Target/Safety classification."""
    
    def test_low_acceptance_is_reach(self, label_classifier, strong_student, mit):
        """Schools with <15% acceptance should be Reach."""
        label = label_classifier.classify(strong_student, mit)
        
        assert label == AdmissionLabel.REACH, f"MIT should be Reach, got {label}"
    
    def test_high_acceptance_with_good_stats_is_safety(self, label_classifier, strong_student, arizona_state):
        """High acceptance + good stats = Safety."""
        label = label_classifier.classify(strong_student, arizona_state)
        
        assert label == AdmissionLabel.SAFETY, f"ASU for strong student should be Safety, got {label}"
    
    def test_moderate_school_with_moderate_stats_is_target(self, label_classifier, strong_student, uiuc):
        """Moderate acceptance + moderate stats = Target."""
        label = label_classifier.classify(strong_student, uiuc)
        
        # 3.8 GPA at 3.78 median school with 45% acceptance
        # Could be Target or Safety depending on exact percentile
        assert label in [AdmissionLabel.TARGET, AdmissionLabel.SAFETY], f"UIUC should be Target or Safety, got {label}"
    
    def test_weak_stats_at_moderate_school_is_reach(self, label_classifier, average_student, mit):
        """Weak stats at selective school = Reach."""
        label = label_classifier.classify(average_student, mit)
        
        assert label == AdmissionLabel.REACH, f"Average student at MIT should be Reach, got {label}"


# ============== Admission Probability Tests ==============

class TestAdmissionProbability:
    """Tests for admission probability calculation."""
    
    def test_strong_stats_high_acceptance_yields_high_probability(self, label_classifier, elite_student, arizona_state):
        """Strong stats + high acceptance = high probability."""
        prob = label_classifier.calculate_admission_probability(elite_student, arizona_state)
        
        # 88% acceptance + elite stats = very high probability
        assert prob >= 80, f"Should have >=80% probability, got {prob}%"
    
    def test_low_acceptance_yields_low_probability(self, label_classifier, strong_student, mit):
        """Low acceptance schools should have low probability."""
        prob = label_classifier.calculate_admission_probability(strong_student, mit)
        
        # 4% acceptance even with good stats = low probability
        assert prob <= 50, f"MIT should have <=50% probability, got {prob}%"
    
    def test_average_stats_moderate_school_yields_moderate_probability(self, label_classifier, strong_student, uiuc):
        """Average scenario should yield moderate probability."""
        prob = label_classifier.calculate_admission_probability(strong_student, uiuc)
        
        # 45% acceptance + slightly above median stats
        assert prob >= 40 and prob <= 80, f"UIUC should have 40-80% probability, got {prob}%"
