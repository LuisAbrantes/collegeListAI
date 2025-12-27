# Scoring factors submodule
from app.domain.scoring.factors.academic_fit import AcademicFitFactor
from app.domain.scoring.factors.major_strength import MajorStrengthFactor
from app.domain.scoring.factors.financial_fit import FinancialFitFactor
from app.domain.scoring.factors.fit_factor import FitFactor
from app.domain.scoring.factors.special_factors import SpecialFactors

__all__ = [
    "AcademicFitFactor",
    "MajorStrengthFactor",
    "FinancialFitFactor",
    "FitFactor",
    "SpecialFactors",
]
