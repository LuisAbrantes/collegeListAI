#!/usr/bin/env python3
"""
Seed Universities Script

Pre-populates the database with top universities for instant UX.
Run once before launch or after database reset.

Usage:
    python -m scripts.seed_universities
"""

import asyncio
import logging
from datetime import datetime

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.infrastructure.db.database import get_session_context, init_db
from app.infrastructure.db.repositories.college_repository import (
    CollegeRepository,
    CollegeMajorStatsRepository,
)
from app.infrastructure.services.college_search_service import CollegeSearchService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Top majors to seed (cover most common student interests)
SEED_MAJORS = [
    "Computer Science",
    "Business Administration",
    "Economics",
    "Biology",
    "Psychology",
    "Engineering",
    "Pre-Med",
    "Mathematics",
    "Political Science",
    "Communications",
]


async def seed_database() -> dict:
    """
    Seed the database with top universities for each major.
    
    Strategy:
    1. For each popular major
    2. Run hybrid_search with force_refresh
    3. This auto-populates the cache with ~20 universities per major
    
    Returns:
        Dict with seeding statistics
    """
    stats = {
        "started_at": datetime.utcnow().isoformat(),
        "majors_seeded": [],
        "total_universities": 0,
        "failed_majors": [],
    }
    
    logger.info(f"Starting database seed with {len(SEED_MAJORS)} majors...")
    
    # Initialize database
    await init_db()
    
    async with get_session_context() as session:
        college_repo = CollegeRepository(session)
        stats_repo = CollegeMajorStatsRepository(session)
        search_service = CollegeSearchService(college_repo, stats_repo)
        
        for major in SEED_MAJORS:
            try:
                logger.info(f"Seeding data for major: {major}...")
                
                # Force refresh to get fresh data from web
                universities = await search_service.hybrid_search(
                    major=major,
                    profile={},
                    student_type="international",
                    limit=20,
                    force_refresh=True
                )
                
                stats["majors_seeded"].append(major)
                stats["total_universities"] += len(universities)
                
                logger.info(f"  ✓ {major}: {len(universities)} universities cached")
                
                # Rate limiting: wait between majors to avoid API limits
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"  ✗ Failed to seed {major}: {e}")
                stats["failed_majors"].append(major)
        
        await session.commit()
    
    stats["completed_at"] = datetime.utcnow().isoformat()
    
    logger.info(f"Seeding complete: {stats}")
    return stats


async def main():
    print("\n=== College Database Seed Script ===")
    print(f"Majors to seed: {', '.join(SEED_MAJORS)}")
    print("This may take a few minutes...\n")
    
    stats = await seed_database()
    
    print("\n=== Seed Complete ===")
    print(f"Majors seeded: {len(stats['majors_seeded'])}")
    print(f"Total universities: {stats['total_universities']}")
    print(f"Failed majors: {len(stats['failed_majors'])}")
    
    if stats['failed_majors']:
        print(f"  - {', '.join(stats['failed_majors'])}")


if __name__ == "__main__":
    asyncio.run(main())
