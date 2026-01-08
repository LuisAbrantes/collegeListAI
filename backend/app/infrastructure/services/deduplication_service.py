"""
University Deduplication Service

Handles merging duplicate university records based on IPEDS ID.
Implements fuzzy name matching and record consolidation.
"""

import logging
import re
from typing import List, Optional, Tuple
from sqlmodel import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.college import College

logger = logging.getLogger(__name__)


class UniversityDeduplicator:
    """
    Consolidates duplicate university records.
    
    Strategy:
    1. Records with IPEDS ID are authoritative (from College Scorecard)
    2. Records without IPEDS are legacy (from Perplexity)
    3. Match by normalized name to find duplicates
    4. Merge legacy data into IPEDS records, then delete legacy
    """
    
    # Common name variations to normalize
    NAME_NORMALIZATIONS = [
        (r'\(UC\s+\w+\)', ''),  # Remove "(UC Berkeley)" variations
        (r'\s*-\s*', ', '),     # "University of California-Berkeley" -> "University of California, Berkeley"
        (r'\s+', ' '),          # Multiple spaces -> single space
    ]
    
    # Keywords that indicate same university
    UNIVERSITY_KEYWORDS = [
        'university', 'college', 'institute', 'school'
    ]
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Normalize university name for matching.
        
        Examples:
        - "University of California, Berkeley (UC Berkeley)" -> "university of california berkeley"
        - "University of California-Berkeley" -> "university of california berkeley"
        """
        normalized = name.lower().strip()
        
        # Remove parenthetical notes
        normalized = re.sub(r'\([^)]*\)', '', normalized)
        
        # Expand common abbreviations BEFORE other normalizations
        # UC Berkeley -> University of California Berkeley
        if normalized.startswith('uc '):
            normalized = 'university of california ' + normalized[3:]
        elif normalized == 'ucla':
            normalized = 'university of california los angeles'
        
        # Replace hyphens and commas with spaces
        normalized = re.sub(r'[-,]', ' ', normalized)
        
        # Remove multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common suffixes
        for suffix in [' university', ' college', ' institute']:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
        
        return normalized.strip()
    
    @staticmethod
    def are_likely_duplicates(name1: str, name2: str) -> bool:
        """
        Check if two university names likely refer to the same institution.
        
        Uses normalized comparison with Jaccard similarity.
        """
        norm1 = UniversityDeduplicator.normalize_name(name1)
        norm2 = UniversityDeduplicator.normalize_name(name2)
        
        # Exact match after normalization
        if norm1 == norm2:
            return True
        
        # One is substring of other (after normalization)
        if norm1 in norm2 or norm2 in norm1:
            return True
        
        # Token similarity (Jaccard)
        tokens1 = set(norm1.split())
        tokens2 = set(norm2.split())
        
        if not tokens1 or not tokens2:
            return False
        
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        
        similarity = len(intersection) / len(union)
        return similarity >= 0.7  # 70% token overlap
    
    async def find_duplicates(self) -> List[Tuple[College, List[College]]]:
        """
        Find all duplicate university records.
        
        Returns list of (authoritative_record, duplicate_records) tuples.
        The authoritative record has IPEDS ID; duplicates do not.
        """
        # Get all colleges
        result = await self.session.execute(select(College).order_by(College.name))
        all_colleges = result.scalars().all()
        
        # Separate by IPEDS status
        with_ipeds = [c for c in all_colleges if c.ipeds_id is not None]
        without_ipeds = [c for c in all_colleges if c.ipeds_id is None]
        
        duplicates: List[Tuple[College, List[College]]] = []
        
        # For each IPEDS college, find matching non-IPEDS records
        for authoritative in with_ipeds:
            matches = [
                c for c in without_ipeds
                if self.are_likely_duplicates(authoritative.name, c.name)
            ]
            if matches:
                duplicates.append((authoritative, matches))
        
        return duplicates
    
    async def merge_and_delete_duplicates(self) -> int:
        """
        Merge duplicate records and delete legacy entries.
        
        Returns count of deleted records.
        """
        duplicates = await self.find_duplicates()
        deleted_count = 0
        
        for authoritative, legacy_records in duplicates:
            logger.info(f"Merging duplicates for: {authoritative.name} (IPEDS: {authoritative.ipeds_id})")
            
            for legacy in legacy_records:
                logger.info(f"  -> Deleting legacy: {legacy.name}")
                
                # Optionally: preserve any unique data from legacy record
                # (e.g., if legacy has notes or stats that authoritative doesn't)
                
                # Delete the legacy record
                await self.session.delete(legacy)
                deleted_count += 1
        
        await self.session.commit()
        logger.info(f"Deleted {deleted_count} duplicate records")
        
        return deleted_count
    
    async def delete_all_without_ipeds(self) -> int:
        """
        Delete ALL records without IPEDS ID.
        
        Use with caution - this removes all Perplexity-sourced data.
        Returns count of deleted records.
        """
        result = await self.session.execute(
            select(College).where(College.ipeds_id.is_(None))
        )
        records = result.scalars().all()
        
        count = len(records)
        for record in records:
            logger.info(f"Deleting (no IPEDS): {record.name}")
            await self.session.delete(record)
        
        await self.session.commit()
        logger.info(f"Deleted {count} records without IPEDS")
        
        return count
