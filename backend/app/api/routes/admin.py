"""
Admin Routes for Database Maintenance

Includes deduplication endpoint for cleaning university records.
Protected by API key authentication.
"""

import logging
import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.infrastructure.db.database import get_session
from app.infrastructure.services.deduplication_service import UniversityDeduplicator

logger = logging.getLogger(__name__)


# =============================================================================
# Admin API Key Authentication
# =============================================================================

async def verify_admin_api_key(
    x_admin_key: str = Header(..., description="Admin API key for protected operations")
) -> bool:
    """
    Verify admin API key from header.
    
    The admin key should be set in environment variable ADMIN_API_KEY.
    """
    from app.config.settings import settings
    
    expected_key = settings.admin_api_key
    
    if not expected_key:
        logger.error("ADMIN_API_KEY environment variable not set")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin authentication not configured"
        )
    
    # Use secrets.compare_digest for timing-attack resistance
    if not secrets.compare_digest(x_admin_key, expected_key):
        logger.warning("Invalid admin API key attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key"
        )
    
    return True


router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_api_key)]  # Protect ALL admin routes
)


class DeduplicationResult(BaseModel):
    """Response from deduplication endpoint."""
    success: bool
    duplicates_found: int
    records_deleted: int
    message: str


@router.post("/deduplicate", response_model=DeduplicationResult)
async def run_deduplication(
    delete_all_no_ipeds: bool = False,
    session = Depends(get_session),
):
    """
    Run university deduplication.
    
    This endpoint:
    1. Finds duplicate university records (same school, different names)
    2. Keeps records with IPEDS ID (official Scorecard data)
    3. Deletes legacy records without IPEDS
    
    Args:
        delete_all_no_ipeds: If True, deletes ALL records without IPEDS ID
    """
    try:
        deduplicator = UniversityDeduplicator(session)
        
        # Find duplicates first
        duplicates = await deduplicator.find_duplicates()
        duplicates_count = sum(len(legacy) for _, legacy in duplicates)
        
        logger.info(f"Found {len(duplicates)} universities with {duplicates_count} total duplicates")
        
        if delete_all_no_ipeds:
            # Aggressive cleanup - delete all without IPEDS
            deleted = await deduplicator.delete_all_without_ipeds()
        else:
            # Smart cleanup - only delete matched duplicates
            deleted = await deduplicator.merge_and_delete_duplicates()
        
        return DeduplicationResult(
            success=True,
            duplicates_found=duplicates_count,
            records_deleted=deleted,
            message=f"Successfully cleaned {deleted} duplicate records"
        )
        
    except Exception as e:
        logger.error(f"Deduplication failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/duplicates")
async def list_duplicates(
    session = Depends(get_session),
):
    """
    List potential duplicate universities WITHOUT deleting.
    
    Returns pairs of (authoritative, duplicates) for review.
    """
    deduplicator = UniversityDeduplicator(session)
    duplicates = await deduplicator.find_duplicates()
    
    result = []
    for authoritative, legacy_records in duplicates:
        result.append({
            "keep": {
                "id": str(authoritative.id),
                "name": authoritative.name,
                "ipeds_id": authoritative.ipeds_id,
                "acceptance_rate": authoritative.acceptance_rate,
            },
            "delete": [
                {
                    "id": str(leg.id),
                    "name": leg.name,
                    "ipeds_id": leg.ipeds_id,
                }
                for leg in legacy_records
            ]
        })
    
    return {
        "total_duplicates": sum(len(d["delete"]) for d in result),
        "duplicate_groups": result,
    }
