"""
Label Classifier

Classifies universities as Reach, Target, or Safety.
Uses acceptance rates and student stats.

CLASSIFICATION RULES:
- Reach: Acceptance rate < 20% (CMU, Michigan, Harvard...)
- Target: Acceptance rate 20-50%
- Safety: Acceptance rate > 50%

Student stats also affect classification (can bump up/down one tier).
"""

from app.domain.scoring.interfaces import (
    StudentContext,
    UniversityData,
    AdmissionLabel,
)


class LabelClassifier:
    """
    University label classifier.
    
    Classification Criteria:
    - REACH: Acceptance Rate < 20% OR student stats below 25th percentile
    - TARGET: Acceptance Rate 20-50% with reasonable stats
    - SAFETY: Acceptance Rate > 50% OR stats above 75th percentile
    """
    
    # Acceptance rate thresholds
    REACH_ACCEPTANCE_THRESHOLD = 0.20    # Below 20% = Reach (CMU, Michigan, etc)
    TARGET_ACCEPTANCE_THRESHOLD = 0.70   # 20-70% = Target, Above 70% = Safety
    
    def classify(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> AdmissionLabel:
        """
        Classify university for this student.
        
        Returns Reach, Target, or Safety based on:
        1. University acceptance rate
        2. Student's stats relative to university percentiles
        """
        acceptance_rate = university.acceptance_rate
        percentile = self._get_percentile_position(context, university)
        
        # Rule 1: Very low acceptance rate (<20%) = Reach
        if acceptance_rate is not None and acceptance_rate < self.REACH_ACCEPTANCE_THRESHOLD:
            return AdmissionLabel.REACH
        
        # Rule 2: Student in bottom 25% of stats = Reach (even at easier schools)
        if percentile is not None and percentile < 25:
            return AdmissionLabel.REACH
        
        # Rule 3: High acceptance rate (>50%) = Safety
        if acceptance_rate is not None and acceptance_rate > self.TARGET_ACCEPTANCE_THRESHOLD:
            return AdmissionLabel.SAFETY
        
        # Rule 4: Student in top 25% with moderate acceptance = Safety
        if percentile is not None and percentile >= 75:
            if acceptance_rate is None or acceptance_rate >= 0.30:
                return AdmissionLabel.SAFETY
        
        # Default: Target (20-50% acceptance with reasonable stats)
        return AdmissionLabel.TARGET
    
    def calculate_admission_probability(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float:
        """
        Estimate admission probability (0-100).
        
        Formula: P(Admit) = f(Acceptance_Rate, Percentile_Position)
        
        - Base = Acceptance Rate × 100
        - Adjust by percentile position:
          - Top 25% of stats: +30 points
          - Top 50%: +15 points  
          - Bottom 25%: -20 points
        """
        # Start with acceptance rate as base
        base = 50.0  # Default if no data
        
        if university.acceptance_rate is not None:
            base = university.acceptance_rate * 100
        
        # Adjust by student's percentile position
        percentile = self._get_percentile_position(context, university)
        
        if percentile is not None:
            if percentile >= 75:
                # Top 25% of stats - strong candidate
                adjustment = 30 + (percentile - 75) * 0.5
            elif percentile >= 50:
                # Above median - solid candidate
                adjustment = 15 + (percentile - 50) * 0.6
            elif percentile >= 25:
                # Between 25th-50th - competitive but below median
                adjustment = (percentile - 25) * 0.6
            else:
                # Below 25th - weak academic profile for this school
                adjustment = -20 - (25 - percentile) * 0.5
            
            base = base + adjustment
        
        # Special circumstances boost
        if context.has_legacy and self._has_legacy_at(context, university):
            base = min(95, base + 12)
        
        if context.is_athlete:
            base = min(95, base + 8)
        
        if context.is_first_gen:
            base = min(95, base + 3)
        
        return max(5, min(95, base))
    
    def _get_percentile_position(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float | None:
        """
        Get student's percentile position relative to university admits.
        
        Returns 0-100 where:
        - 0 = far below 25th percentile
        - 25 = at 25th percentile
        - 50 = at median
        - 75 = at 75th percentile
        - 100 = well above 75th
        
        Uses weighted average of GPA and SAT positions.
        """
        positions = []
        
        # GPA position (Z-score to percentile)
        if university.median_gpa is not None:
            gpa_diff = context.gpa - university.median_gpa
            # Assume std dev of 0.12 for admitted students
            z_score = gpa_diff / 0.12
            # Convert Z-score to percentile (Z=0 → 50, Z=1 → 84, Z=-1 → 16)
            gpa_percentile = 50 + z_score * 34
            gpa_percentile = max(0, min(100, gpa_percentile))
            positions.append(gpa_percentile)
        
        # SAT position
        student_sat = context.sat_score
        if student_sat is None and context.act_score is not None:
            student_sat = self._act_to_sat(context.act_score)
        
        if student_sat is not None and university.sat_25th and university.sat_75th:
            sat_25 = university.sat_25th
            sat_75 = university.sat_75th
            sat_mid = (sat_25 + sat_75) / 2
            
            if student_sat <= sat_25:
                # Below 25th percentile
                deficit = sat_25 - student_sat
                sat_percentile = max(0, 25 - deficit / 5)
            elif student_sat >= sat_75:
                # Above 75th percentile
                excess = student_sat - sat_75
                sat_percentile = min(100, 75 + excess / 5)
            else:
                # Between 25th and 75th
                if student_sat <= sat_mid:
                    ratio = (student_sat - sat_25) / (sat_mid - sat_25)
                    sat_percentile = 25 + ratio * 25
                else:
                    ratio = (student_sat - sat_mid) / (sat_75 - sat_mid)
                    sat_percentile = 50 + ratio * 25
            
            positions.append(sat_percentile)
        
        if not positions:
            return None
        
        # Weighted average (GPA 55%, SAT 45%)
        if len(positions) == 2:
            return positions[0] * 0.55 + positions[1] * 0.45
        
        return positions[0]
    
    def _has_legacy_at(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> bool:
        """Check if student has legacy at this specific university."""
        if not context.legacy_universities:
            return False
        
        uni_name_lower = university.name.lower()
        for legacy in context.legacy_universities:
            if legacy.lower() in uni_name_lower or uni_name_lower in legacy.lower():
                return True
        
        return False
    
    def _act_to_sat(self, act_score: int) -> int:
        """Convert ACT to SAT equivalent."""
        conversions = {
            36: 1600, 35: 1560, 34: 1520, 33: 1490,
            32: 1450, 31: 1420, 30: 1390, 29: 1350,
            28: 1310, 27: 1280, 26: 1240, 25: 1210,
            24: 1180, 23: 1140, 22: 1110, 21: 1080,
            20: 1040, 19: 1010, 18: 970, 17: 930,
        }
        return conversions.get(act_score, 400 + act_score * 40)
