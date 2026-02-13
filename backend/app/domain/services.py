"""
User Profile Service — DEPRECATED

This module has been replaced by the SQLAlchemy-based UserProfileRepository
at app.infrastructure.db.repositories.user_profile_repository.

The profiles router now injects UserProfileRepoDep directly,
eliminating the Supabase HTTP client dependency.

This file is kept empty to avoid breaking any stale imports during migration.
Remove this file entirely once all references are confirmed cleared.
"""
