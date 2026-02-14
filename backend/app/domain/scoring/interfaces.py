"""
Scoring Interfaces for College List AI

Defines protocols and data models for the scoring engine.
Follows Interface Segregation and Dependency Inversion principles.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Protocol, runtime_checkable
from enum import Enum


class AdmissionLabel(Enum):
    """Classification labels for universities."""
    REACH = "Reach"
    TARGET = "Target"
    SAFETY = "Safety"


@dataclass
class UniversityData:
    """
    Verified university data for scoring.
    
    Combines data from universities_master table and real-time search.
    """
    name: str
    
    # Admission statistics
    acceptance_rate: Optional[float] = None  # 0.0-1.0
    median_gpa: Optional[float] = None  # 0.0-4.0
    sat_25th: Optional[int] = None  # 400-1600
    sat_75th: Optional[int] = None  # 400-1600
    
    # Tuition
    tuition_in_state: Optional[float] = None
    tuition_out_of_state: Optional[float] = None
    tuition_international: Optional[float] = None
    
    # Major/Department info
    major_ranking: Optional[int] = None  # 1-based ranking for student's specific major
    has_major: bool = True  # Whether university offers student's intended major
    major_strength_description: Optional[str] = None
    student_major: Optional[str] = None  # The student's intended major (for context)
    
    # Financial aid
    need_blind_international: bool = False
    need_blind_domestic: bool = True
    avg_aid_package: Optional[float] = None
    meets_full_need: bool = False
    
    # Location/Fit
    campus_setting: Optional[str] = None  # URBAN, SUBURBAN, RURAL
    state: Optional[str] = None
    
    # Metadata
    data_source: str = "unknown"  # IPEDS, Common_Data_Set, Verified_Web_Source
    last_verified_at: Optional[str] = None
    official_url: Optional[str] = None
    
    # Raw similarity from vector search
    vector_similarity: float = 0.0


@dataclass
class ScoreBreakdown:
    """
    Transparent breakdown of match score factors.
    
    Returned to user for transparency.
    """
    academic_fit: float = 0.0
    major_strength: float = 0.0
    financial_fit: float = 0.0
    location_fit: float = 0.0
    career_alignment: float = 0.0
    special_factors: float = 0.0  # Legacy, athlete, etc.
    
    # Weights used (after normalization)
    weights_used: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for API response."""
        return {
            "academic_fit": round(self.academic_fit, 1),
            "major_strength": round(self.major_strength, 1),
            "financial_fit": round(self.financial_fit, 1),
            "location_fit": round(self.location_fit, 1),
            "career_alignment": round(self.career_alignment, 1),
            "special_factors": round(self.special_factors, 1),
        }


@dataclass
class ScoredUniversity:
    """
    University with calculated scores and labels.
    
    Final output ready for recommendation.
    """
    university: UniversityData
    
    # Scores
    match_score: float  # 0-100 total match
    admission_probability: float  # 0-100 chance of admission
    score_breakdown: ScoreBreakdown
    
    # Classification
    label: AdmissionLabel
    
    # Reasoning
    reasoning: str = ""
    financial_aid_summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            "name": self.university.name,
            "label": self.label.value,
            "match_score": round(self.match_score, 1),
            "admission_probability": round(self.admission_probability, 1),
            "match_transparency": self.score_breakdown.to_dict(),
            "reasoning": self.reasoning,
            "financial_aid_summary": self.financial_aid_summary,
            "official_url": self.university.official_url,
        }


@dataclass
class StudentContext:
    """
    Student profile context for scoring.
    
    Normalized view of profile for scoring factors.
    """
    # Identification
    is_domestic: bool
    citizenship_status: str
    nationality: Optional[str] = None
    state_of_residence: Optional[str] = None
    
    # Academic
    gpa: float = 0.0
    sat_score: Optional[int] = None
    act_score: Optional[int] = None
    ap_count: int = 0
    
    # Major
    intended_major: str = "Undeclared"
    
    # Financial
    income_tier: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    is_first_gen: bool = False
    
    # Preferences
    campus_preference: Optional[str] = None  # URBAN, SUBURBAN, RURAL
    post_grad_goal: Optional[str] = None
    
    # Special factors (optional)
    is_athlete: bool = False
    has_legacy: bool = False
    legacy_universities: List[str] = field(default_factory=list)


@runtime_checkable
class ScoringFactor(Protocol):
    """
    Protocol for scoring factors.
    
    Each factor calculates a 0-100 score for a specific aspect.
    Follows Open/Closed principle - new factors can be added easily.
    """
    
    @property
    def name(self) -> str:
        """Factor name for transparency."""
        ...
    
    @property
    def base_weight(self) -> float:
        """Base weight (0.0-1.0) before normalization."""
        ...
    
    def is_applicable(self, context: StudentContext) -> bool:
        """Check if this factor applies to the student."""
        ...
    
    def calculate(
        self, 
        context: StudentContext, 
        university: UniversityData
    ) -> float:
        """
        Calculate score for this factor.
        
        Returns: Score from 0-100
        """
        ...


class BaseScoringFactor(ABC):
    """Base class for scoring factors with common functionality."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def base_weight(self) -> float:
        pass
    
    def is_applicable(self, context: StudentContext) -> bool:
        """Default: always applicable. Override for optional factors."""
        return True
    
    @abstractmethod
    def calculate(
        self, 
        context: StudentContext, 
        university: UniversityData
    ) -> float:
        pass
