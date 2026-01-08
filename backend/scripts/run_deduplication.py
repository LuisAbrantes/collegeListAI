"""
Script to clean up duplicate colleges in the database.
Run this once to remove legacy duplicates.
"""

import asyncio
import sys
sys.path.insert(0, '/Users/luisabrantes/Documents/Code/collegeListAI/backend')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config.settings import settings
from app.infrastructure.services.deduplication_service import UniversityDeduplicator


async def main():
    """Run deduplication."""
    print("Starting deduplication...")
    
    # Create async engine
    engine = create_async_engine(settings.supabase_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        dedup = UniversityDeduplicator(session)
        
        # Find duplicates
        duplicates = await dedup.find_duplicates()
        
        if not duplicates:
            print("No duplicates found!")
            return
        
        print(f"\nFound {len(duplicates)} colleges with duplicates:")
        for auth, dupes in duplicates:
            print(f"\n  KEEP: {auth.name} (IPEDS: {auth.ipeds_id})")
            for d in dupes:
                print(f"    DELETE: {d.name}")
        
        # Confirm
        print("\nDeleting duplicates...")
        deleted = await dedup.merge_and_delete_duplicates()
        print(f"Deleted {deleted} duplicate records.")

if __name__ == "__main__":
    asyncio.run(main())
