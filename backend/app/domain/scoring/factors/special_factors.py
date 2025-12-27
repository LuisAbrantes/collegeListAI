"""
Special Factors (Legacy, Athlete)

Optional scoring factors that only apply when student has special circumstances.
These factors are NOT applicable for all students and their weight gets
redistributed to core factors when not applicable.
"""

from app.domain.scoring.interfaces import (
    BaseScoringFactor,
    StudentContext,
    UniversityData,
)


class SpecialFactors(BaseScoringFactor):
    """
    Special circumstances scoring factor.
    
    Weight: 10% base - ONLY IF APPLICABLE
    
    Includes:
    - Legacy status (has family attended)
    - Student athlete status
    
    If neither applies, this factor is excluded and
    weight is redistributed via dynamic normalization.
    """
    
    @property
    def name(self) -> str:
        return "special_factors"
    
    @property
    def base_weight(self) -> float:
        return 0.10
    
    def is_applicable(self, context: StudentContext) -> bool:
        """
        Only applicable if student has legacy or athlete status.
        
        Returns False to trigger weight redistribution when not applicable.
        """
        return context.has_legacy or context.is_athlete
    
    def calculate(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float:
        """
        Calculate special factors score.
        
        Returns 0-100 based on:
        - Legacy at this specific university: big boost
        - Athlete status: moderate boost (depends on program)
        """
        scores = []
        
        # Legacy advantage
        if context.has_legacy:
            legacy_score = self._legacy_score(context, university)
            scores.append(legacy_score)
        
        # Athlete advantage
        if context.is_athlete:
            athlete_score = self._athlete_score(context, university)
            scores.append(athlete_score)
        
        if not scores:
            return 0.0  # Should not reach here if is_applicable works
        
        # Return best advantage (these don't really stack)
        return max(scores)
    
    def _legacy_score(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float:
        """Score for legacy status."""
        if not context.legacy_universities:
            return 70.0  # Has legacy somewhere but no specific schools listed
        
        # Check if this university is in legacy list
        university_name_lower = university.name.lower()
        
        for legacy_uni in context.legacy_universities:
            if legacy_uni.lower() in university_name_lower or \
               university_name_lower in legacy_uni.lower():
                return 95.0  # Strong legacy boost at THIS university
        
        # Legacy elsewhere - slight advantage in admissions culture
        return 65.0
    
    def _athlete_score(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float:
        """Score for student athlete status."""
        # In a full implementation, this would check if university
        # has strong athletic program, D1/D2/D3 status, etc.
        
        # For now, provide a moderate boost
        # Athletes can have significant admission advantages
        return 80.0
