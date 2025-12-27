"""
Major Strength Factor

Calculates match based on university's program quality for student's major.
Works universally for any major, not just CS.
"""

from app.domain.scoring.interfaces import (
    BaseScoringFactor,
    StudentContext,
    UniversityData,
)


class MajorStrengthFactor(BaseScoringFactor):
    """
    Major/department strength scoring factor.
    
    Weight: 20% base
    
    Calculates based on:
    - Department ranking (if available)
    - Whether university offers the major
    - Program reputation data from research
    """
    
    @property
    def name(self) -> str:
        return "major_strength"
    
    @property
    def base_weight(self) -> float:
        return 0.20
    
    def calculate(
        self,
        context: StudentContext,
        university: UniversityData
    ) -> float:
        """
        Calculate major strength score based on student's intended major.
        
        Uses context.intended_major to evaluate program fit.
        
        Returns 0-100 score where:
        - 100 = Top 10 program in the country for student's major
        - 80-90 = Top 25 program
        - 60-80 = Good solid program
        - 40-60 = Average program
        - <40 = Weak or no program for student's major
        """
        student_major = context.intended_major
        
        # Check if university offers the student's intended major
        if not university.has_major:
            return 0.0  # Can't attend if major not offered
        
        # Validate major context matches if we have major-specific data
        if university.student_major and student_major:
            # Normalize for comparison (case-insensitive partial match)
            uni_major_lower = university.student_major.lower()
            student_major_lower = student_major.lower()
            
            # If the major data doesn't match student's major, reduce confidence
            if not self._majors_match(student_major_lower, uni_major_lower):
                # Data is for a different major - use neutral score
                return 60.0
        
        # Use ranking if available (for student's specific major)
        if university.major_ranking is not None:
            return self._score_from_ranking(university.major_ranking)
        
        # Fallback: use vector similarity as proxy for relevance
        # Higher similarity to major-related queries = better match
        if university.vector_similarity > 0:
            return self._score_from_similarity(university.vector_similarity)
        
        # Default: neutral score when no major-specific data
        return 65.0
    
    def _majors_match(self, student_major: str, uni_major: str) -> bool:
        """
        Check if the major names match (fuzzy comparison).
        
        Handles variations like:
        - "Computer Science" vs "CS"
        - "Electrical Engineering" vs "EE"
        - "Computer Science and Engineering" vs "Computer Science"
        """
        # Direct substring match
        if student_major in uni_major or uni_major in student_major:
            return True
        
        # Common abbreviation mappings
        abbreviations = {
            "computer science": ["cs", "compsci", "computing"],
            "electrical engineering": ["ee", "eecs"],
            "mechanical engineering": ["me", "mech eng"],
            "chemical engineering": ["che", "chem eng"],
            "biomedical engineering": ["bme", "biomed"],
            "data science": ["ds", "data analytics"],
            "machine learning": ["ml", "ai", "artificial intelligence"],
            "business administration": ["bba", "business", "management"],
            "economics": ["econ"],
            "mathematics": ["math", "maths"],
            "biology": ["bio", "life sciences"],
            "chemistry": ["chem"],
            "physics": ["phys"],
            "psychology": ["psych"],
        }
        
        for full_name, abbrevs in abbreviations.items():
            if student_major in full_name or full_name in student_major:
                if uni_major in abbrevs or any(a in uni_major for a in abbrevs):
                    return True
            if uni_major in full_name or full_name in uni_major:
                if student_major in abbrevs or any(a in student_major for a in abbrevs):
                    return True
        
        return False
    
    def _score_from_ranking(self, ranking: int) -> float:
        """Convert ranking to score."""
        if ranking <= 5:
            return 100 - (ranking - 1) * 2  # 100, 98, 96, 94, 92
        elif ranking <= 10:
            return 90 - (ranking - 5) * 1  # 89, 88, 87, 86, 85
        elif ranking <= 25:
            return 85 - (ranking - 10) * 0.5  # 84.5 -> 77.5
        elif ranking <= 50:
            return 77 - (ranking - 25) * 0.4  # 77 -> 67
        elif ranking <= 100:
            return 67 - (ranking - 50) * 0.3  # 67 -> 52
        else:
            return max(40, 52 - (ranking - 100) * 0.1)
    
    def _score_from_similarity(self, similarity: float) -> float:
        """
        Convert vector similarity to approximate score.
        
        Uses similarity as a proxy when no ranking data.
        """
        # Similarity is typically 0.0-1.0
        # High similarity to major query = stronger program
        if similarity >= 0.9:
            return 85.0
        elif similarity >= 0.8:
            return 75.0
        elif similarity >= 0.7:
            return 65.0
        elif similarity >= 0.6:
            return 55.0
        else:
            return 45.0
