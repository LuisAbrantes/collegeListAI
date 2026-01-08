#!/usr/bin/env python3
"""
Seed script to populate need-blind admission policies with VERIFIED data.

Sources:
- https://www.collegetransitions.com/blog/need-blind-schools-international-students/
- https://www.nerdwallet.com/article/loans/student-loans/need-blind-schools
- Individual university financial aid websites

Run: python scripts/seed_need_blind.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import update
from app.infrastructure.db.database import get_session_context
from app.infrastructure.db.models.college import College


# ============== VERIFIED NEED-BLIND DATA ==============
# Last Updated: January 2025

# Schools that are NEED-BLIND for BOTH domestic AND international students
NEED_BLIND_ALL = [
    "Harvard University",
    "Yale University", 
    "Princeton University",
    "Massachusetts Institute of Technology",
    "MIT",
    "Amherst College",
    "Bowdoin College",
    "Dartmouth College",
]

# Schools that are NEED-BLIND for DOMESTIC students ONLY
NEED_BLIND_DOMESTIC_ONLY = [
    "Stanford University",
    "Columbia University",
    "University of Pennsylvania",
    "Duke University",
    "Northwestern University",
    "Brown University",
    "Cornell University",
    "University of Chicago",
    "Rice University",
    "Vanderbilt University",
    "Washington University in St. Louis",
    "Emory University",
    "University of Notre Dame",
    "Georgetown University",
    "University of Southern California",
    "Boston College",
    "Tufts University",
    "Williams College",
    "Swarthmore College",
    "Wellesley College",
    "Pomona College",
    "Middlebury College",
    "Claremont McKenna College",
    "Davidson College",
    "Grinnell College",
    "Hamilton College",
    "Haverford College",
    "Vassar College",
    "Colby College",
    "Colgate University",
    "Barnard College",
    # Public universities (need-blind for in-state domestic)
    "University of California, Berkeley",
    "University of California, Los Angeles",
    "University of Michigan",
    "University of Virginia",
    "University of North Carolina at Chapel Hill",
]

# Schools that are explicitly NEED-AWARE for international students
# (This is the default for most schools, but listing notable ones)
NEED_AWARE_INTERNATIONAL = [
    "California Institute of Technology",
    "Johns Hopkins University",
    "Carnegie Mellon University",
    "University of Rochester",
    "Case Western Reserve University",
    "Northeastern University",
    "Boston University",
    "New York University",
    "University of Miami",
    "Pennsylvania State University",
    "Penn State",
    "Ohio State University",
    "Purdue University",
    "University of Illinois Urbana-Champaign",
    "University of Texas at Austin",
    "Georgia Institute of Technology",
    "Georgia Tech",
    "University of Washington",
    "University of Wisconsin-Madison",
    "University of Minnesota",
    "Arizona State University",
    "University of Florida",
    "University of Maryland",
]


async def seed_need_blind_data():
    """Update colleges table with verified need-blind data."""
    
    async with get_session_context() as session:
        updated_count = 0
        
        # Update NEED-BLIND for ALL students
        for school in NEED_BLIND_ALL:
            result = await session.execute(
                update(College)
                .where(College.name.ilike(f"%{school}%"))
                .values(need_blind_domestic=True, need_blind_international=True)
            )
            if result.rowcount > 0:
                print(f"✓ {school}: need-blind for ALL")
                updated_count += result.rowcount
        
        # Update NEED-BLIND for DOMESTIC only
        for school in NEED_BLIND_DOMESTIC_ONLY:
            result = await session.execute(
                update(College)
                .where(College.name.ilike(f"%{school}%"))
                .values(need_blind_domestic=True, need_blind_international=False)
            )
            if result.rowcount > 0:
                print(f"✓ {school}: need-blind DOMESTIC only")
                updated_count += result.rowcount
        
        # Update NEED-AWARE for INTERNATIONAL (explicit false)
        for school in NEED_AWARE_INTERNATIONAL:
            result = await session.execute(
                update(College)
                .where(College.name.ilike(f"%{school}%"))
                .values(need_blind_international=False)
            )
            if result.rowcount > 0:
                print(f"✓ {school}: need-AWARE for international")
                updated_count += result.rowcount
        
        await session.commit()
        print(f"\n✅ Updated {updated_count} college records with verified need-blind data")


if __name__ == "__main__":
    print("🎓 Seeding Need-Blind Admission Data...")
    print("=" * 50)
    asyncio.run(seed_need_blind_data())
