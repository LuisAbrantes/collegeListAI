"""
Fit Factor (Location & Campus)

Calculates how well the university matches student's lifestyle preferences.
"""

from app.domain.scoring.interfaces import (
    BaseScoringFactor,
    StudentContext,
    UniversityData,
)


class FitFactor(BaseScoringFactor):
    """
    Location and campus fit scoring factor.
    
    Weight: 10% base
    
    Calculates based on:
    - Campus setting preference (urban/suburban/rural)
    - Geographic location
    - Career alignment with post-grad goals
    """
    
    @property
    def name(self) -> str:
        return "location_fit"
    
    @property
    def base_weight(self) -> float:
        return 0.10
    
    def calculate(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float:
        """
        Calculate location and campus fit score.
        
        Returns 0-100 score where:
        - 100 = Perfect match with preferences
        - 70 = Neutral (no preference or unknown)
        - 40 = Mismatch with stated preference
        """
        scores = []
        
        # Campus setting match
        campus_score = self._campus_setting_score(context, university)
        if campus_score is not None:
            scores.append(campus_score)
        
        # Career alignment
        career_score = self._career_alignment_score(context, university)
        if career_score is not None:
            scores.append(career_score)
        
        if not scores:
            return 70.0  # Neutral
        
        return sum(scores) / len(scores)
    
    def _campus_setting_score(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float | None:
        """Score based on campus setting preference match."""
        if context.campus_preference is None:
            return None  # No preference expressed
        
        if university.campus_setting is None:
            return 70.0  # Unknown setting
        
        pref = context.campus_preference.upper()
        setting = university.campus_setting.upper()
        
        # Direct match
        if pref == setting:
            return 95.0
        
        # Adjacent match (suburban works for urban/rural seekers somewhat)
        adjacent_matches = {
            ("URBAN", "SUBURBAN"): 75.0,
            ("SUBURBAN", "URBAN"): 75.0,
            ("SUBURBAN", "RURAL"): 75.0,
            ("RURAL", "SUBURBAN"): 75.0,
        }
        
        if (pref, setting) in adjacent_matches:
            return adjacent_matches[(pref, setting)]
        
        # Complete mismatch (urban vs rural)
        return 45.0
    
    def _career_alignment_score(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float | None:
        """Score based on post-grad goal alignment."""
        if context.post_grad_goal is None or context.post_grad_goal == "UNDECIDED":
            return None
        
        goal = context.post_grad_goal.upper()
        
        # Note: In a full implementation, this would use university
        # career outcome data. For now, use location proxies.
        
        if goal == "JOB_PLACEMENT":
            # Urban schools often have better job placement
            if university.campus_setting and university.campus_setting.upper() == "URBAN":
                return 85.0
            return 70.0
        
        elif goal == "GRADUATE_SCHOOL":
            # Research universities excellence
            # Would check research ranking in full impl
            return 75.0
        
        elif goal == "ENTREPRENEURSHIP":
            # Innovation hubs
            if university.campus_setting and university.campus_setting.upper() == "URBAN":
                return 80.0
            return 70.0
        
        return 70.0  # Neutral for other goals
