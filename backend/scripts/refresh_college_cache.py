"""
Refresh College Cache Script

Updates existing cached colleges with fresh tuition and test score data
from College Scorecard API.

Usage:
    cd backend
    python scripts/refresh_college_cache.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config.settings import settings
from app.infrastructure.db.database import get_session_context
from app.infrastructure.db.repositories.college_repository import CollegeRepository
from app.infrastructure.services.college_scorecard_service import CollegeScorecardService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def refresh_college_data():
    """Refresh all cached colleges with data from Scorecard API."""
    
    async with get_session_context() as session:
        repo = CollegeRepository(session)
        scorecard = CollegeScorecardService()
        
        # Get all colleges in cache
        from sqlalchemy import select
        from app.infrastructure.db.models.college import College
        
        result = await session.execute(select(College))
        colleges = result.scalars().all()
        
        logger.info(f"Found {len(colleges)} colleges in cache to refresh")
        
        updated = 0
        failed = 0
        
        for college in colleges:
            logger.info(f"Refreshing: {college.name}")
            
            try:
                # Use IPEDS ID if available (more reliable)
                if college.ipeds_id:
                    data = await scorecard.get_by_ipeds_id(college.ipeds_id)
                else:
                    data = await scorecard.search_by_name(college.name)
                
                if data:
                    # Update all fields
                    college.acceptance_rate = data.acceptance_rate or college.acceptance_rate
                    college.sat_25th = data.sat_25th or college.sat_25th
                    college.sat_75th = data.sat_75th or college.sat_75th
                    college.act_25th = data.act_25th or college.act_25th
                    college.act_75th = data.act_75th or college.act_75th
                    college.city = data.city or college.city
                    college.state = data.state or college.state
                    college.student_size = data.student_size or college.student_size
                    college.campus_setting = data.campus_setting or college.campus_setting
                    
                    # Tuition data
                    college.tuition_in_state = data.tuition_in_state or college.tuition_in_state
                    college.tuition_out_of_state = data.tuition_out_of_state or college.tuition_out_of_state
                    
                    # Use out_of_state as proxy for international
                    if not college.tuition_international and data.tuition_out_of_state:
                        college.tuition_international = data.tuition_out_of_state
                    
                    # Set IPEDS ID if we found it
                    if data.ipeds_id and not college.ipeds_id:
                        college.ipeds_id = data.ipeds_id
                    
                    session.add(college)
                    updated += 1
                    logger.info(f"  ✓ Updated with tuition: ${data.tuition_out_of_state:,.0f}" if data.tuition_out_of_state else f"  ✓ Updated (no tuition)")
                else:
                    failed += 1
                    logger.warning(f"  ✗ No Scorecard data found")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                failed += 1
                logger.error(f"  ✗ Error: {e}")
        
        await session.commit()
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Refresh complete!")
        logger.info(f"  Updated: {updated}")
        logger.info(f"  Failed:  {failed}")
        logger.info(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(refresh_college_data())
