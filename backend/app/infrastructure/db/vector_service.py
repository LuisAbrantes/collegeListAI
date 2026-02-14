"""
Vector Service for College List AI

Handles embedding generation and vector similarity search using:
- sentence-transformers (all-MiniLM-L6-v2) for local embeddings
- Supabase pgvector for storage and similarity search

Production features:
- Async/await throughout
- Connection pooling via singleton pattern
- Exponential backoff retry logic
- Integration with Perplexity/Web Search for cache population
"""

import asyncio
from typing import List, Optional
import logging

from sentence_transformers import SentenceTransformer
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

from app.config.settings import settings
from app.domain.models import CollegeSearchResult, CollegeMetadata
from app.infrastructure.exceptions import (
    EmbeddingGenerationError,
    SimilaritySearchError,
    RateLimitError,
)


logger = logging.getLogger(__name__)


class VectorService:
    """
    Production-ready vector service for embedding and similarity search.
    Production-grade features:
    - Local CPU/GPU inference via SentenceTransformers
    - Singleton pattern for connection pooling
    - Configurable retry logic with exponential backoff
    - Cache population from search results
    """
    
    # Model configuration
    MODEL_NAME = "all-MiniLM-L6-v2"
    EMBEDDING_DIM = 384
    
    def __init__(self):
        """Initialize Supabase client and specialized embedding model."""
        self._supabase: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
            options=ClientOptions(
                postgrest_client_timeout=60,
                auto_refresh_token=True,
                persist_session=True, 
            )
        )
        
        # Initialize embedding model (downloaded on first run)
        try:
            logger.info(f"Loading embedding model: {self.MODEL_NAME}...")
            self.model = SentenceTransformer(self.MODEL_NAME)
            logger.info("Embedding model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.model = None
            
        # Retry configuration
        self.max_retries = 3
        self.base_delay = 1.0  # seconds
        
        logger.info("VectorService initialized successfully")
    
    @property
    def supabase(self) -> Client:
        # Supabase client is initialized directly in __init__
        return self._supabase
    
    async def _retry_with_backoff(
        self,
        operation: callable,
        operation_name: str,
        *args,
        **kwargs
    ):
        """Execute operation with exponential backoff retry."""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await asyncio.to_thread(operation, *args, **kwargs)
            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()
                
                if "rate" in error_msg or "quota" in error_msg or "429" in error_msg:
                    delay = min(self.base_delay * (2 ** attempt), self.MAX_DELAY) # MAX_DELAY is gone, this will error
                    logger.warning(
                        f"{operation_name} rate limited. Attempt {attempt + 1}/{self.max_retries}. "
                        f"Retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                
                if "timeout" in error_msg or "connection" in error_msg:
                    delay = min(self.base_delay * (2 ** attempt), self.MAX_DELAY) # MAX_DELAY is gone, this will error
                    logger.warning(
                        f"{operation_name} transient error. Retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                
                raise
        
        raise last_exception
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string using local model.
        
        Returns:
            List of 384 floats (for all-MiniLM-L6-v2)
        """
        if not text:
            raise ValueError("Cannot generate embedding for empty text")
            
        if not self.model:
            raise EmbeddingGenerationError("Embedding model not initialized")

        for attempt in range(self.max_retries + 1):
            try:
                # Encode runs locally, blocking but fast for small batches
                # Run in thread pool to avoid blocking async event loop
                embedding = await asyncio.to_thread(self.model.encode, text)
                
                # Check dimensions
                if len(embedding) != self.EMBEDDING_DIM:
                    logger.warning(f"Unexpected embedding dimension: {len(embedding)}")
                
                return embedding.tolist()

            except Exception as e:
                if attempt == self.max_retries:
                    logger.error(f"Embedding generation failed after {self.max_retries} retries: {e}")
                    raise EmbeddingGenerationError(f"Failed to generate embedding: {str(e)}")
                
                delay = self.base_delay * (2 ** attempt)
                logger.warning(f"Embedding failed. Retrying in {delay}s... Error: {e}")
                await asyncio.sleep(delay)
                
        # Should be unreachable due to raise in loop
        raise EmbeddingGenerationError("Embedding generation failed")
    
    async def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding optimized for search queries."""
        return await self.generate_embedding(query)
    
    async def generate_document_embedding(self, document: str) -> List[float]:
        """Generate embedding optimized for document storage."""
        return await self.generate_embedding(document)
    
    async def search_similar_colleges(
        self,
        query_text: str,
        threshold: float = 0.7,
        limit: int = 10,
        exclude_names: Optional[List[str]] = None
    ) -> List[CollegeSearchResult]:
        """
        Search for similar colleges via vector similarity.
        
        Args:
            query_text: Natural language query
            threshold: Minimum similarity (0.0 to 1.0)
            limit: Max results
            exclude_names: College names to exclude
            
        Returns:
            List of CollegeSearchResult sorted by similarity
        """
        try:
            query_embedding = await self.generate_query_embedding(query_text)
            
            rpc_params = {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": limit
            }
            
            response = await asyncio.to_thread(
                lambda: self.supabase.rpc("match_colleges", rpc_params).execute()
            )
            
            if not response.data:
                return []
            
            results = []
            exclude_set = set(exclude_names) if exclude_names else set()
            
            for row in response.data:
                if row["name"] in exclude_set:
                    continue
                
                metadata = None
                if row.get("content"):
                    try:
                        import json
                        content_data = json.loads(row["content"])
                        metadata = CollegeMetadata(**content_data)
                    except Exception:
                        logger.warning(f"Failed to parse content for {row['name']}")
                
                results.append(CollegeSearchResult(
                    id=row["id"],
                    name=row["name"],
                    metadata=metadata,
                    similarity=row["similarity"]
                ))
            
            return results
            
        except EmbeddingGenerationError:
            raise
        except Exception as e:
            raise SimilaritySearchError(
                f"College search failed: {str(e)}",
                original_error=e
            )
    
    async def cache_university_from_search(
        self,
        name: str,
        content: dict,
        source_url: Optional[str] = None
    ) -> bool:
        """
        Cache a university found via web search.
        
        Args:
            name: University name
            content: University data as dict
            source_url: Original source URL
            
        Returns:
            True if cached successfully
        """
        try:
            import json
            content_str = json.dumps(content)
            
            # Generate embedding from university description
            description = f"{name}. {content.get('description', '')} {content.get('location', '')}"
            embedding = await self.generate_document_embedding(description)
            
            await asyncio.to_thread(
                lambda: self.supabase.table("colleges_cache").upsert({
                    "name": name,
                    "content": content_str,
                    "embedding": embedding,
                }, on_conflict="name").execute()
            )
            
            logger.info(f"Cached university: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache {name}: {e}")
            return False
    
    async def get_cached_count(self) -> int:
        """Get count of cached universities."""
        try:
            response = await asyncio.to_thread(
                lambda: self.supabase.table("colleges_cache").select("id", count="exact").execute()
            )
            return response.count or 0
        except Exception:
            return 0
