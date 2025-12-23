"""
Academic Fit Factor

Calculates how well the student's academic profile matches the university.
Uses Z-score comparison for mathematically sound scoring.

REFACTORED: Uses Z-score approach instead of linear penalty.
- Being at median = 80% (competitive candidate)
- Above median = higher scores
- Below median = lower scores, but not harsh penalties
"""

from app.domain.scoring.interfaces import (
    BaseScoringFactor,
    StudentContext,
    UniversityData,
)


class AcademicFitFactor(BaseScoringFactor):
    """
    Academic fit scoring factor using Z-score comparison.
    
    Weight: 30% base
    
    Calculates based on:
    - GPA relative to university median (Z-score approach)
    - SAT/ACT relative to 25th-75th percentile range
    
    Key insight: A student at 3.8 GPA with school median 3.9
    should score ~80% (competitive), NOT 49% (penalty).
    """
    
    # Assumed standard deviations (typical for admitted students)
    ASSUMED_GPA_STDEV = 0.12
    ASSUMED_SAT_STDEV = 80  # Points
    
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
        Calculate academic fit score using Z-scores.
        
        Returns 0-100 score where:
        - 90+ = student well above university stats (overqualified)
        - 75-90 = strong match (competitive)
        - 60-75 = moderate match (within range)
        - <60 = reach territory (below typical admits)
        """
        scores = []
        
        # GPA component (Z-score based)
        gpa_score = self._calculate_gpa_fit(context.gpa, university)
        if gpa_score is not None:
            scores.append(gpa_score)
        
        # Test score component (percentile-based)
        test_score = self._calculate_test_fit(context, university)
        if test_score is not None:
            scores.append(test_score)
        
        # If no data available, return neutral score
        if not scores:
            return 75.0  # Neutral when no data
        
        # Weight SAT/ACT more than GPA (40/60) - test scores have more predictive power
        if len(scores) == 2:
            return scores[0] * 0.40 + scores[1] * 0.60
        
        return scores[0]
    
    def _calculate_gpa_fit(
        self,
        student_gpa: float,
        university: UniversityData
    ) -> float | None:
        """
        Calculate GPA fit score using Z-score comparison.
        
        Z-score formula: z = (student_gpa - median_gpa) / std_dev
        
        Score mapping (CALIBRATED for less punishment):
        - Z = 0 (at median) → 82% (competitive candidate)
        - Z = +1 (above median) → 92%
        - Z = -1 (slightly below) → 72%
        - Z = -2 (significantly below) → 62%
        """
        if university.median_gpa is None:
            return None
        
        median = university.median_gpa
        diff = student_gpa - median
        z_score = diff / self.ASSUMED_GPA_STDEV
        
        # Map Z-score to 0-100 range
        # Base of 82 at median, +10 per standard deviation
        base_score = 82 + (z_score * 10)
        
        # Clamp to reasonable range
        return max(45, min(98, base_score))
    
    def _calculate_test_fit(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float | None:
        """
        Calculate test score fit using percentile position.
        
        Uses the 25th-75th percentile range to determine position:
        - At 75th percentile → 85%
        - At 50th percentile (midpoint) → 75%
        - At 25th percentile → 65%
        - Below 25th → decreasing rapidly
        """
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
        
        # Calculate percentile position within the school's range
        # CALIBRATION: Students within 25th-75th must score >= 75%
        if student_sat >= sat_75:
            # Above 75th percentile - strong candidate
            excess_z = (student_sat - sat_75) / self.ASSUMED_SAT_STDEV
            return min(98, 88 + excess_z * 5)
        
        elif student_sat >= sat_mid:
            # Between midpoint and 75th (50th-75th percentile)
            ratio = (student_sat - sat_mid) / (sat_75 - sat_mid)
            return 80 + ratio * 8  # 80 to 88
        
        elif student_sat >= sat_25:
            # Between 25th and midpoint (25th-50th percentile)
            # CALIBRATION: This range must score >= 75%
            ratio = (student_sat - sat_25) / (sat_mid - sat_25)
            return 75 + ratio * 5  # 75 to 80
        
        else:
            # Below 25th percentile - reach territory
            deficit_z = (sat_25 - student_sat) / self.ASSUMED_SAT_STDEV
            return max(40, 70 - deficit_z * 12)
    
    def _act_to_sat(self, act_score: int) -> int:
        """Convert ACT to SAT equivalent."""
        conversions = {
            36: 1600, 35: 1560, 34: 1520, 33: 1490,
            32: 1450, 31: 1420, 30: 1390, 29: 1350,
            28: 1310, 27: 1280, 26: 1240, 25: 1210,
            24: 1180, 23: 1140, 22: 1110, 21: 1080,
            20: 1040, 19: 1010, 18: 970, 17: 930,
            16: 890, 15: 850, 14: 800, 13: 760,
        }
        return conversions.get(act_score, 400 + act_score * 40)
