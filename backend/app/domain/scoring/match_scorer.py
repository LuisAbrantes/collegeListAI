"""
Match Scorer

Central scoring engine that aggregates all factor scores.
Implements dynamic weight normalization when factors are not applicable.
"""

from typing import List, Dict
from dataclasses import dataclass

from app.domain.scoring.interfaces import (
    StudentContext,
    UniversityData,
    ScoredUniversity,
    ScoreBreakdown,
    ScoringFactor,
    AdmissionLabel,
)
from app.domain.scoring.factors import (
    AcademicFitFactor,
    MajorStrengthFactor,
    FinancialFitFactor,
    FitFactor,
    SpecialFactors,
)
from app.domain.scoring.label_classifier import LabelClassifier


class MatchScorer:
    """
    University match scoring engine.
    
    Follows Single Responsibility - only calculates scores.
    Uses Strategy pattern for pluggable factors.
    Implements dynamic weight normalization.
    """
    
    # Minimum match score threshold - nothing below this gets recommended
    MIN_MATCH_THRESHOLD = 60.0
    
    def __init__(self, factors: List[ScoringFactor] | None = None):
        """
        Initialize scorer with factors.
        
        Args:
            factors: List of scoring factors. If None, uses defaults.
        """
        self._factors = factors or self._default_factors()
        self._label_classifier = LabelClassifier()
    
    def _default_factors(self) -> List[ScoringFactor]:
        """Get default scoring factors."""
        return [
            AcademicFitFactor(),
            MajorStrengthFactor(),
            FinancialFitFactor(),
            FitFactor(),
            SpecialFactors(),
        ]
    
    def score_university(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> ScoredUniversity:
        """
        Score a single university for the student.
        
        Args:
            context: Student profile context
            university: University data
            
        Returns:
            ScoredUniversity with match score, breakdown, and label
        """
        # Get applicable factors and their normalized weights
        applicable_factors = self._get_applicable_factors(context)
        normalized_weights = self._normalize_weights(applicable_factors)
        
        # Calculate each factor's score
        factor_scores: Dict[str, float] = {}
        for factor in applicable_factors:
            score = factor.calculate(context, university)
            factor_scores[factor.name] = score
        
        # Calculate weighted total
        total_score = sum(
            factor_scores[f.name] * normalized_weights[f.name]
            for f in applicable_factors
        )
        
        # Build score breakdown
        breakdown = ScoreBreakdown(
            academic_fit=factor_scores.get("academic_fit", 0.0),
            major_strength=factor_scores.get("major_strength", 0.0),
            financial_fit=factor_scores.get("financial_fit", 0.0),
            location_fit=factor_scores.get("location_fit", 0.0),
            career_alignment=factor_scores.get("career_alignment", 0.0),
            special_factors=factor_scores.get("special_factors", 0.0),
            weights_used=normalized_weights,
        )
        
        # Calculate admission probability
        admission_prob = self._label_classifier.calculate_admission_probability(
            context, university
        )
        
        # Classify as Reach/Target/Safety
        label = self._label_classifier.classify(context, university)
        
        return ScoredUniversity(
            university=university,
            match_score=total_score,
            admission_probability=admission_prob,
            score_breakdown=breakdown,
            label=label,
        )
    
    def score_universities(
        self,
        context: StudentContext,
        universities: List[UniversityData]
    ) -> List[ScoredUniversity]:
        """
        Score multiple universities.
        
        Args:
            context: Student profile context
            universities: List of university data
            
        Returns:
            List of ScoredUniversity sorted by match score (descending)
        """
        scored = [
            self.score_university(context, uni)
            for uni in universities
        ]
        
        # Sort by match score descending
        return sorted(scored, key=lambda s: s.match_score, reverse=True)
    
    def select_recommendations(
        self,
        context: StudentContext,
        universities: List[UniversityData],
        count: int = 5
    ) -> List[ScoredUniversity]:
        """
        Select the best university recommendations.
        
        Ensures distribution: 2 Safety, 2 Target, 1 Reach
        Only includes universities above MIN_MATCH_THRESHOLD.
        
        Args:
            context: Student profile context
            universities: List of university data
            count: Number of recommendations (default 5)
            
        Returns:
            List of 5 recommendations with proper distribution
        """
        # Score all universities
        all_scored = self.score_universities(context, universities)
        
        # Separate by label BEFORE threshold filtering (needed for Safety guarantee)
        all_reaches = [s for s in all_scored if s.label == AdmissionLabel.REACH]
        all_targets = [s for s in all_scored if s.label == AdmissionLabel.TARGET]
        all_safeties = [s for s in all_scored if s.label == AdmissionLabel.SAFETY]
        
        # Filter by minimum threshold for Reach/Target only
        viable_reaches = [s for s in all_reaches if s.match_score >= self.MIN_MATCH_THRESHOLD]
        viable_targets = [s for s in all_targets if s.match_score >= self.MIN_MATCH_THRESHOLD]
        # Safety schools: lower threshold (50) to ensure we always have options
        viable_safeties = [s for s in all_safeties if s.match_score >= 50.0]
        
        # If not enough Safety schools, take best from all_safeties regardless of threshold
        if len(viable_safeties) < 2 and len(all_safeties) > len(viable_safeties):
            viable_safeties = sorted(all_safeties, key=lambda s: s.match_score, reverse=True)[:2]
        
        # Build final list: 1 Reach, 2 Target, 2 Safety
        recommendations: List[ScoredUniversity] = []
        
        # Add reach (1 best match score)
        for reach in viable_reaches[:1]:
            recommendations.append(reach)
        
        # Add targets (2)
        for target in viable_targets[:2]:
            recommendations.append(target)
        
        # Add safeties (2 highest match score)
        for safety in viable_safeties[:2]:
            recommendations.append(safety)
        
        # If we don't have enough, fill from remaining
        remaining_needed = count - len(recommendations)
        if remaining_needed > 0:
            # Get all scored schools not yet selected
            selected_names = {r.university.name for r in recommendations}
            remaining = [
                s for s in all_scored 
                if s.university.name not in selected_names and s.match_score >= 50.0
            ]
            remaining.sort(key=lambda s: s.match_score, reverse=True)
            
            # Add best remaining
            for extra in remaining[:remaining_needed]:
                recommendations.append(extra)
        
        # Sort final list by label order: Reach, Target, Safety
        label_order = {
            AdmissionLabel.REACH: 0,
            AdmissionLabel.TARGET: 1,
            AdmissionLabel.SAFETY: 2,
        }
        recommendations.sort(key=lambda r: (label_order[r.label], -r.match_score))
        
        return recommendations
    
    def _get_applicable_factors(
        self, 
        context: StudentContext
    ) -> List[ScoringFactor]:
        """Get factors that apply to this student."""
        return [f for f in self._factors if f.is_applicable(context)]
    
    def _normalize_weights(
        self, 
        factors: List[ScoringFactor]
    ) -> Dict[str, float]:
        """
        Normalize weights so they sum to 1.0.
        
        Dynamic normalization: if a factor doesn't apply,
        its weight is redistributed proportionally.
        """
        total_weight = sum(f.base_weight for f in factors)
        
        if total_weight == 0:
            # Shouldn't happen, but handle gracefully
            equal_weight = 1.0 / len(factors) if factors else 0
            return {f.name: equal_weight for f in factors}
        
        return {
            f.name: f.base_weight / total_weight
            for f in factors
        }
