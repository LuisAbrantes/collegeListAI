# Scoring module for College List AI
from app.domain.scoring.interfaces import (
    UniversityData,
    ScoreBreakdown,
    ScoredUniversity,
    StudentContext,
    ScoringFactor,
    BaseScoringFactor,
    AdmissionLabel,
)
from app.domain.scoring.match_scorer import MatchScorer
from app.domain.scoring.label_classifier import LabelClassifier

__all__ = [
    "UniversityData",
    "ScoreBreakdown", 
    "ScoredUniversity",
    "StudentContext",
    "ScoringFactor",
    "BaseScoringFactor",
    "AdmissionLabel",
    "MatchScorer",
    "LabelClassifier",
]
