"""
Label Classifier

Classifies universities as Reach, Target, or Safety.
Uses strict criteria based on acceptance rates and student stats.
"""

from app.domain.scoring.interfaces import (
    StudentContext,
    UniversityData,
    AdmissionLabel,
)


class LabelClassifier:
    """
    University label classifier.
    
    Strict classification criteria:
    - Reach: Acceptance Rate < 15% OR student stats below 25th percentile
    - Target: Stats between 25th-75th percentile
    - Safety: Stats above 75th percentile AND Acceptance Rate > 35%
    """
    
    # Acceptance rate thresholds
    REACH_ACCEPTANCE_THRESHOLD = 0.15  # Below 15% = Reach
    SAFETY_ACCEPTANCE_THRESHOLD = 0.35  # Above 35% + high stats = Safety
    
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
        # Get admission probability for classification
        probability = self.calculate_admission_probability(context, university)
        
        # Get acceptance rate classification
        acceptance_rate = university.acceptance_rate
        
        # Rule 1: Very low acceptance rate = Reach regardless of stats
        if acceptance_rate is not None and acceptance_rate < self.REACH_ACCEPTANCE_THRESHOLD:
            # Even with great stats, sub-15% schools are reaches
            if probability >= 70:
                return AdmissionLabel.TARGET  # Strong candidate at hard school
            return AdmissionLabel.REACH
        
        # Rule 2: Student stats below 25th percentile = Reach
        percentile_position = self._get_percentile_position(context, university)
        
        if percentile_position is not None:
            if percentile_position < 25:
                return AdmissionLabel.REACH
            elif percentile_position > 75:
                # Above 75th AND acceptance rate > 35% = Safety
                if acceptance_rate is None or acceptance_rate > self.SAFETY_ACCEPTANCE_THRESHOLD:
                    return AdmissionLabel.SAFETY
                else:
                    return AdmissionLabel.TARGET  # High stats but selective
            else:
                return AdmissionLabel.TARGET  # Between 25th-75th
        
        # Rule 3: Fall back to admission probability
        if probability >= 70:
            return AdmissionLabel.SAFETY
        elif probability >= 30:
            return AdmissionLabel.TARGET
        else:
            return AdmissionLabel.REACH
    
    def calculate_admission_probability(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float:
        """
        Estimate admission probability (0-100).
        
        Combines acceptance rate with student's relative position.
        """
        base_probability = 50.0  # Neutral starting point
        
        # Factor 1: University acceptance rate
        if university.acceptance_rate is not None:
            # Transform acceptance rate to probability contribution
            # Higher acceptance rate = higher base probability
            acceptance_contribution = university.acceptance_rate * 100
            base_probability = acceptance_contribution
        
        # Factor 2: Student's academic position relative to admits
        percentile = self._get_percentile_position(context, university)
        
        if percentile is not None:
            # Adjust probability based on where student falls
            if percentile >= 75:
                # Above 75th percentile: strong candidate
                base_probability = min(95, base_probability * 1.3 + 20)
            elif percentile >= 50:
                # Above median: solid candidate
                base_probability = min(85, base_probability * 1.1 + 10)
            elif percentile >= 25:
                # Between 25th-50th: competitive but below median
                base_probability = base_probability * 0.9
            else:
                # Below 25th: weak academic profile
                base_probability = max(5, base_probability * 0.5 - 10)
        
        # Factor 3: Special circumstances boost
        if context.has_legacy and self._has_legacy_at(context, university):
            base_probability = min(95, base_probability + 15)
        
        if context.is_athlete:
            base_probability = min(95, base_probability + 10)
        
        if context.is_first_gen:
            base_probability = min(95, base_probability + 3)
        
        return max(5, min(95, base_probability))
    
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
        """
        positions = []
        
        # GPA position
        if university.median_gpa is not None:
            gpa_diff = context.gpa - university.median_gpa
            # Convert GPA difference to percentile estimate
            # +0.3 GPA = roughly at 75th, -0.3 = roughly at 25th
            gpa_percentile = 50 + (gpa_diff / 0.3) * 25
            gpa_percentile = max(0, min(100, gpa_percentile))
            positions.append(gpa_percentile)
        
        # SAT position
        student_sat = context.sat_score
        if student_sat is None and context.act_score is not None:
            student_sat = self._act_to_sat(context.act_score)
        
        if student_sat is not None and university.sat_25th and university.sat_75th:
            sat_25 = university.sat_25th
            sat_75 = university.sat_75th
            
            if student_sat <= sat_25:
                sat_percentile = 25 * (student_sat / sat_25)
            elif student_sat >= sat_75:
                excess = student_sat - sat_75
                sat_percentile = 75 + min(25, excess / 50 * 25)
            else:
                # Between 25th and 75th
                ratio = (student_sat - sat_25) / (sat_75 - sat_25)
                sat_percentile = 25 + ratio * 50
            
            positions.append(sat_percentile)
        
        if not positions:
            return None
        
        # Average positions (GPA weighted slightly more)
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
