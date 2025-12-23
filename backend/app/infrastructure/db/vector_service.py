"""
Vector Service for College List AI

Handles embedding generation and vector similarity search using:
- Google's text-embedding-004 model (via google.genai SDK)
- Supabase pgvector for storage and similarity search

Production features:
- Async/await throughout
- Connection pooling via singleton pattern
- Exponential backoff retry logic
- Integration with Gemini Search for cache population
"""

import asyncio
from typing import List, Optional
import logging

from google import genai
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
    
    Features:
    - New google.genai SDK for embeddings
    - Singleton pattern for connection pooling
    - Configurable retry logic with exponential backoff
    - Cache population from Gemini Search results
    """
    
    _instance: Optional["VectorService"] = None
    _supabase: Optional[Client] = None
    _genai_client: Optional[genai.Client] = None
    _initialized: bool = False
    
    def __new__(cls) -> "VectorService":
        """Singleton pattern for connection pooling."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialize()
            VectorService._initialized = True
    
    def _initialize(self) -> None:
        """Initialize Supabase and GenAI clients using Settings."""
        # Configure Supabase
        options = ClientOptions(
            postgrest_client_timeout=30,
            storage_client_timeout=60,
        )
        self._supabase = create_client(
            settings.supabase_url, 
            settings.supabase_service_role_key, 
            options
        )
        
        # Configure new GenAI client
        self._genai_client = genai.Client(api_key=settings.google_api_key)
        
        logger.info("VectorService initialized successfully")
    
    # Configuration properties from Settings
    @property
    def EMBEDDING_MODEL(self) -> str:
        return settings.embedding_model
    
    @property
    def EMBEDDING_DIMENSION(self) -> int:
        return settings.embedding_dimensions
    
    @property
    def MAX_RETRIES(self) -> int:
        return settings.max_retries
    
    @property
    def BASE_DELAY(self) -> float:
        return settings.retry_base_delay
    
    @property
    def MAX_DELAY(self) -> float:
        return settings.retry_max_delay
    
    @property
    def supabase(self) -> Client:
        if self._supabase is None:
            self._initialize()
        return self._supabase
    
    @property
    def genai(self) -> genai.Client:
        if self._genai_client is None:
            self._initialize()
        return self._genai_client
    
    async def _retry_with_backoff(
        self,
        operation: callable,
        operation_name: str,
        *args,
        **kwargs
    ):
        """Execute operation with exponential backoff retry."""
        last_exception = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                return await asyncio.to_thread(operation, *args, **kwargs)
            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()
                
                if "rate" in error_msg or "quota" in error_msg or "429" in error_msg:
                    delay = min(self.BASE_DELAY * (2 ** attempt), self.MAX_DELAY)
                    logger.warning(
                        f"{operation_name} rate limited. Attempt {attempt + 1}/{self.MAX_RETRIES}. "
                        f"Retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                
                if "timeout" in error_msg or "connection" in error_msg:
                    delay = min(self.BASE_DELAY * (2 ** attempt), self.MAX_DELAY)
                    logger.warning(
                        f"{operation_name} transient error. Retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                
                raise
        
        raise last_exception
    
    def _generate_embedding_sync(self, text: str) -> List[float]:
        """Synchronous embedding generation."""
        result = self.genai.models.embed_content(
            model=self.EMBEDDING_MODEL,
            contents=text
        )
        return result.embeddings[0].values
    
    async def generate_embedding(
        self,
        text: str,
        task_type: str = "retrieval_document"
    ) -> List[float]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Text to embed (max 10k chars)
            task_type: "retrieval_document" or "retrieval_query"
            
        Returns:
            List of 768 floats
        """
        if not text or not text.strip():
            raise EmbeddingGenerationError(
                "Cannot generate embedding for empty text",
                model=self.EMBEDDING_MODEL
            )
        
        text = text[:10000]
        
        try:
            embedding = await self._retry_with_backoff(
                self._generate_embedding_sync,
                "Embedding generation",
                text
            )
            
            if len(embedding) != self.EMBEDDING_DIMENSION:
                logger.warning(
                    f"Unexpected embedding dimension: {len(embedding)}"
                )
            
            return embedding
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "rate" in error_msg or "quota" in error_msg:
                raise RateLimitError(
                    "Embedding API rate limit exceeded",
                    original_error=e
                )
            
            raise EmbeddingGenerationError(
                f"Failed to generate embedding: {str(e)}",
                model=self.EMBEDDING_MODEL,
                original_error=e
            )
    
    async def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding optimized for search queries."""
        return await self.generate_embedding(query, task_type="retrieval_query")
    
    async def generate_document_embedding(self, document: str) -> List[float]:
        """Generate embedding optimized for document storage."""
        return await self.generate_embedding(document, task_type="retrieval_document")
    
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
        Cache a university found via Gemini Search.
        
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
