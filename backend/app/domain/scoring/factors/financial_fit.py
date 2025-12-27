"""
Financial Fit Factor

Calculates financial compatibility between student and university.
Different logic for domestic vs international students.
"""

from app.domain.scoring.interfaces import (
    BaseScoringFactor,
    StudentContext,
    UniversityData,
)


class FinancialFitFactor(BaseScoringFactor):
    """
    Financial fit scoring factor.
    
    Weight: 20% base
    
    Domestic students:
    - Prioritize in-state tuition for public universities
    - Consider Pell Grant eligibility
    - Evaluate merit scholarship likelihood
    
    International students:
    - Weight need-blind admission heavily
    - Consider international scholarship availability
    - Evaluate meets-full-need policies
    """
    
    @property
    def name(self) -> str:
        return "financial_fit"
    
    @property
    def base_weight(self) -> float:
        return 0.20
    
    def calculate(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float:
        """
        Calculate financial fit score.
        
        Returns 0-100 score where higher = better affordability.
        """
        if context.is_domestic:
            return self._calculate_domestic(context, university)
        else:
            return self._calculate_international(context, university)
    
    def _calculate_domestic(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float:
        """Calculate financial fit for domestic students."""
        scores = []
        
        # In-state advantage
        in_state_score = self._in_state_advantage(context, university)
        if in_state_score is not None:
            scores.append(in_state_score * 1.5)  # Weighted higher
        
        # Aid generosity
        aid_score = self._aid_generosity_score(context, university)
        scores.append(aid_score)
        
        # First-gen advantage
        if context.is_first_gen:
            scores.append(75.0)  # Bonus for first-gen friendly schools
        
        if not scores:
            return 60.0  # Neutral
        
        return min(100, sum(scores) / len(scores))
    
    def _calculate_international(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float:
        """Calculate financial fit for international students."""
        # Need-blind is critical for low/medium income internationals
        if context.income_tier in ["LOW", "MEDIUM"]:
            if university.need_blind_international:
                base_score = 95.0  # Excellent - need-blind
            elif university.meets_full_need:
                base_score = 80.0  # Good - meets need but aware
            else:
                base_score = 50.0  # Average - limited aid
        else:
            # HIGH income - need-blind less critical
            base_score = 70.0
        
        # Adjust for known scholarship availability
        if university.avg_aid_package is not None:
            if university.avg_aid_package >= 50000:
                base_score = min(100, base_score + 15)
            elif university.avg_aid_package >= 30000:
                base_score = min(100, base_score + 8)
        
        return base_score
    
    def _in_state_advantage(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float | None:
        """Calculate in-state tuition advantage."""
        if context.state_of_residence is None:
            return None
        
        if university.state is None:
            return None
        
        # Check if student's state matches university state
        if context.state_of_residence.upper() == university.state.upper():
            # In-state: calculate savings advantage
            if (university.tuition_in_state is not None and 
                university.tuition_out_of_state is not None):
                savings_ratio = 1 - (university.tuition_in_state / 
                                     university.tuition_out_of_state)
                # More savings = better score
                return min(100, 70 + savings_ratio * 60)
            return 85.0  # Assume in-state benefit
        else:
            # Out-of-state: neutral
            return 60.0
    
    def _aid_generosity_score(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float:
        """Score based on aid generosity relative to income tier."""
        if context.income_tier == "LOW":
            # Low income needs maximum aid
            if university.meets_full_need:
                return 95.0
            elif university.avg_aid_package and university.avg_aid_package >= 40000:
                return 80.0
            return 55.0
        
        elif context.income_tier == "MEDIUM":
            # Medium income benefits from merit + need combo
            if university.meets_full_need:
                return 85.0
            elif university.avg_aid_package and university.avg_aid_package >= 25000:
                return 70.0
            return 55.0
        
        else:  # HIGH
            # High income focuses on merit
            return 65.0  # Neutral for wealthy families
