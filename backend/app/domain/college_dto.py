"""
College Domain DTOs

Data Transfer Objects for clean separation between layers.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class CollegeDTO:
    """
    Complete college data for agent responses and UI.
    
    This DTO aggregates data from multiple sources:
    - College Scorecard API (primary)
    - Local cache
    - Perplexity fallback
    """
    
    # Identifiers
    ipeds_id: Optional[int] = None
    name: str = ""
    
    # Location
    state: Optional[str] = None
    city: Optional[str] = None
    campus_setting: Optional[str] = None  # URBAN, SUBURBAN, RURAL
    
    # Admissions
    acceptance_rate: Optional[float] = None
    sat_25th: Optional[int] = None
    sat_75th: Optional[int] = None
    act_25th: Optional[int] = None
    act_75th: Optional[int] = None
    
    # Costs
    tuition_in_state: Optional[float] = None
    tuition_out_of_state: Optional[float] = None
    tuition_international: Optional[float] = None
    
    # Student Body
    student_size: Optional[int] = None
    
    # Financial Aid Policies
    need_blind_domestic: bool = True
    need_blind_international: bool = False
    meets_full_need: bool = False
    
    # Metadata
    data_source: str = "unknown"
    updated_at: Optional[datetime] = None
    is_fresh: bool = False
    
    @property
    def sat_range(self) -> Optional[str]:
        """Format SAT range as string."""
        if self.sat_25th and self.sat_75th:
            return f"{self.sat_25th}-{self.sat_75th}"
        return None
    
    @property
    def act_range(self) -> Optional[str]:
        """Format ACT range as string."""
        if self.act_25th and self.act_75th:
            return f"{self.act_25th}-{self.act_75th}"
        return None
    
    @property
    def acceptance_rate_percent(self) -> Optional[str]:
        """Format acceptance rate as percentage."""
        if self.acceptance_rate:
            return f"{self.acceptance_rate * 100:.0f}%"
        return None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "ipeds_id": self.ipeds_id,
            "name": self.name,
            "state": self.state,
            "city": self.city,
            "campus_setting": self.campus_setting,
            "acceptance_rate": self.acceptance_rate,
            "acceptance_rate_display": self.acceptance_rate_percent,
            "sat_range": self.sat_range,
            "sat_25th": self.sat_25th,
            "sat_75th": self.sat_75th,
            "act_range": self.act_range,
            "act_25th": self.act_25th,
            "act_75th": self.act_75th,
            "tuition_in_state": self.tuition_in_state,
            "tuition_out_of_state": self.tuition_out_of_state,
            "tuition_international": self.tuition_international,
            "student_size": self.student_size,
            "need_blind_domestic": self.need_blind_domestic,
            "need_blind_international": self.need_blind_international,
            "meets_full_need": self.meets_full_need,
            "data_source": self.data_source,
            "is_fresh": self.is_fresh,
        }
