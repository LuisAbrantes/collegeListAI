#!/usr/bin/env python3
"""
Background Database Refresh Script

Refreshes stale university data by re-fetching from web sources.
Run as a cron job or manually: python -m scripts.refresh_database

Usage:
    python -m scripts.refresh_database              # Refresh 50 stale entries
    python -m scripts.refresh_database --limit 100  # Refresh 100 stale entries
"""

import asyncio
import argparse
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
from app.config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def refresh_stale_universities(limit: int = 50) -> dict:
    """
    Refresh universities with oldest updated_at timestamps.
    
    Strategy:
    1. Get N oldest entries from database
    2. For each, trigger web search with that university's major
    3. Update cache with fresh data
    
    Args:
        limit: Maximum number of entries to refresh
        
    Returns:
        Dict with refresh statistics
    """
    stats = {
        "started_at": datetime.utcnow().isoformat(),
        "total_stale": 0,
        "refreshed": 0,
        "failed": 0,
        "skipped": 0,
    }
    
    logger.info(f"Starting background refresh (limit: {limit})...")
    
    # Initialize database
    await init_db()
    
    async with get_session_context() as session:
        college_repo = CollegeRepository(session)
        stats_repo = CollegeMajorStatsRepository(session)
        search_service = CollegeSearchService(college_repo, stats_repo)
        
        # Get stale entries
        stale_entries = await stats_repo.get_stale_stats(limit=limit)
        stats["total_stale"] = len(stale_entries)
        
        if not stale_entries:
            logger.info("No stale entries found. Database is fresh!")
            return stats
        
        logger.info(f"Found {len(stale_entries)} stale entries to refresh")
        
        # Group by major to avoid duplicate searches
        majors_refreshed = set()
        
        for entry in stale_entries:
            major = entry.major_name
            
            # Skip if we already refreshed this major
            if major in majors_refreshed:
                stats["skipped"] += 1
                continue
            
            try:
                logger.info(f"Refreshing data for major: {major}")
                
                # Trigger hybrid search with force_refresh
                # This will update all universities for this major
                await search_service.hybrid_search(
                    major=major,
                    profile={},
                    student_type="international",
                    limit=20,
                    force_refresh=True  # Force fresh data
                )
                
                majors_refreshed.add(major)
                stats["refreshed"] += 1
                
                # Rate limiting: wait between refreshes to avoid API limits
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to refresh {major}: {e}")
                stats["failed"] += 1
        
        await session.commit()
    
    stats["completed_at"] = datetime.utcnow().isoformat()
    stats["majors_refreshed"] = list(majors_refreshed)
    
    logger.info(f"Refresh complete: {stats}")
    return stats


async def main():
    parser = argparse.ArgumentParser(description="Refresh stale university data")
    parser.add_argument(
        "--limit", 
        type=int, 
        default=50,
        help="Maximum number of stale entries to refresh (default: 50)"
    )
    args = parser.parse_args()
    
    stats = await refresh_stale_universities(limit=args.limit)
    
    print("\n=== Refresh Complete ===")
    print(f"Total stale: {stats['total_stale']}")
    print(f"Refreshed: {stats['refreshed']}")
    print(f"Failed: {stats['failed']}")
    print(f"Skipped: {stats['skipped']}")


if __name__ == "__main__":
    asyncio.run(main())
