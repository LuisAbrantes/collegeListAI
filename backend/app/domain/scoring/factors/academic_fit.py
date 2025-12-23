"""
Academic Fit Factor

Calculates how well the student's academic profile matches the university.
Compares GPA and test scores to university percentiles.
"""

from app.domain.scoring.interfaces import (
    BaseScoringFactor,
    StudentContext,
    UniversityData,
)


class AcademicFitFactor(BaseScoringFactor):
    """
    Academic fit scoring factor.
    
    Weight: 30% base
    
    Calculates based on:
    - GPA relative to university median
    - SAT/ACT relative to 25th-75th percentile range
    """
    
    @property
    def name(self) -> str:
        return "academic_fit"
    
    @property
    def base_weight(self) -> float:
        return 0.30
    
    def calculate(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float:
        """
        Calculate academic fit score.
        
        Returns 0-100 score where:
        - 100 = student well above university stats
        - 70-85 = solid match
        - 50-70 = competitive
        - <50 = reach territory
        """
        scores = []
        
        # GPA component
        gpa_score = self._calculate_gpa_fit(context.gpa, university)
        if gpa_score is not None:
            scores.append(gpa_score)
        
        # Test score component (SAT or ACT)
        test_score = self._calculate_test_fit(context, university)
        if test_score is not None:
            scores.append(test_score)
        
        # If no data available, return neutral score
        if not scores:
            return 70.0  # Neutral when no data
        
        # Weight GPA slightly more than tests (60/40)
        if len(scores) == 2:
            return scores[0] * 0.6 + scores[1] * 0.4
        
        return scores[0]
    
    def _calculate_gpa_fit(
        self,
        student_gpa: float,
        university: UniversityData
    ) -> float | None:
        """Calculate GPA fit score."""
        if university.median_gpa is None:
            return None
        
        median = university.median_gpa
        
        # Score based on distance from median
        # Above median: bonus points
        # At median: 75 points
        # Below median: penalty
        
        diff = student_gpa - median
        
        if diff >= 0.3:
            return min(100, 85 + (diff - 0.3) * 50)  # Well above
        elif diff >= 0:
            return 75 + diff * 33  # Slightly above to at median
        elif diff >= -0.3:
            return 75 + diff * 50  # Slightly below median
        else:
            return max(30, 60 + diff * 30)  # Significantly below
    
    def _calculate_test_fit(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float | None:
        """Calculate test score fit (SAT or ACT)."""
        student_sat = context.sat_score
        
        # Convert ACT to SAT if needed
        if student_sat is None and context.act_score is not None:
            student_sat = self._act_to_sat(context.act_score)
        
        if student_sat is None:
            return None
        
        if university.sat_25th is None or university.sat_75th is None:
            return None
        
        sat_25 = university.sat_25th
        sat_75 = university.sat_75th
        sat_mid = (sat_25 + sat_75) / 2
        
        if student_sat >= sat_75:
            # Above 75th percentile
            excess = student_sat - sat_75
            return min(100, 85 + excess / 20)
        elif student_sat >= sat_mid:
            # Between midpoint and 75th
            ratio = (student_sat - sat_mid) / (sat_75 - sat_mid)
            return 70 + ratio * 15
        elif student_sat >= sat_25:
            # Between 25th and midpoint
            ratio = (student_sat - sat_25) / (sat_mid - sat_25)
            return 55 + ratio * 15
        else:
            # Below 25th percentile
            deficit = sat_25 - student_sat
            return max(20, 55 - deficit / 10)
    
    def _act_to_sat(self, act_score: int) -> int:
        """Convert ACT to SAT equivalent."""
        # Approximate conversion table
        conversions = {
            36: 1600, 35: 1560, 34: 1520, 33: 1490,
            32: 1450, 31: 1420, 30: 1390, 29: 1350,
            28: 1310, 27: 1280, 26: 1240, 25: 1210,
            24: 1180, 23: 1140, 22: 1110, 21: 1080,
            20: 1040, 19: 1010, 18: 970, 17: 930,
            16: 890, 15: 850, 14: 800, 13: 760,
        }
        return conversions.get(act_score, 400 + act_score * 40)
