"""
Vector Service for College List AI

Handles embedding generation and vector similarity search using:
- Google's text-embedding-004 model for embeddings
- Supabase pgvector for storage and similarity search

Production features:
- Async/await throughout
- Connection pooling via singleton pattern
- Exponential backoff retry logic
- Proper error handling with custom exceptions
- Type hints with Pydantic models
"""

import asyncio
import os
from typing import List, Optional
import logging

import google.generativeai as genai
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

from backend.app.domain.models import CollegeSearchResult, CollegeMetadata
from backend.app.infrastructure.exceptions import (
    EmbeddingGenerationError,
    SimilaritySearchError,
    ConfigurationError,
    RateLimitError,
)


logger = logging.getLogger(__name__)


class VectorService:
    """
    Production-ready vector service for embedding generation and similarity search.
    
    Features:
    - Singleton pattern for connection pooling
    - Configurable retry logic with exponential backoff
    - Support for both document and query embeddings
    - Proper error handling and logging
    """
    
    _instance: Optional["VectorService"] = None
    _supabase: Optional[Client] = None
    _initialized: bool = False
    
    # Configuration
    EMBEDDING_MODEL = "models/text-embedding-004"
    EMBEDDING_DIMENSION = 768
    MAX_RETRIES = 3
    BASE_DELAY = 1.0  # seconds
    MAX_DELAY = 10.0  # seconds
    
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
        """Initialize Supabase client and Gemini API."""
        # Validate configuration
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        google_api_key = os.getenv("GOOGLE_API_KEY")
        
        missing_keys = []
        if not supabase_url:
            missing_keys.append("SUPABASE_URL")
        if not supabase_key:
            missing_keys.append("SUPABASE_SERVICE_ROLE_KEY")
        if not google_api_key:
            missing_keys.append("GOOGLE_API_KEY")
        
        if missing_keys:
            raise ConfigurationError(
                "Missing required environment variables",
                missing_keys=missing_keys
            )
        
        # Configure Supabase with connection pooling options
        options = ClientOptions(
            postgrest_client_timeout=30,
            storage_client_timeout=60,
        )
        self._supabase = create_client(supabase_url, supabase_key, options)
        
        # Configure Gemini
        genai.configure(api_key=google_api_key)
        
        logger.info("VectorService initialized successfully")
    
    @property
    def supabase(self) -> Client:
        """Get the Supabase client instance."""
        if self._supabase is None:
            self._initialize()
        return self._supabase
    
    async def _retry_with_backoff(
        self,
        operation: callable,
        operation_name: str,
        *args,
        **kwargs
    ):
        """
        Execute an operation with exponential backoff retry logic.
        
        Args:
            operation: The callable to execute
            operation_name: Name for logging purposes
            *args, **kwargs: Arguments to pass to the operation
            
        Returns:
            The result of the operation
            
        Raises:
            The last exception if all retries fail
        """
        last_exception = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                return await asyncio.to_thread(operation, *args, **kwargs)
            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()
                
                # Check for rate limit errors
                if "rate" in error_msg or "quota" in error_msg or "429" in error_msg:
                    delay = min(self.BASE_DELAY * (2 ** attempt), self.MAX_DELAY)
                    logger.warning(
                        f"{operation_name} rate limited. Attempt {attempt + 1}/{self.MAX_RETRIES}. "
                        f"Retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                
                # Check for transient errors
                if "timeout" in error_msg or "connection" in error_msg:
                    delay = min(self.BASE_DELAY * (2 ** attempt), self.MAX_DELAY)
                    logger.warning(
                        f"{operation_name} transient error. Attempt {attempt + 1}/{self.MAX_RETRIES}. "
                        f"Retrying in {delay:.1f}s. Error: {e}"
                    )
                    await asyncio.sleep(delay)
                    continue
                
                # Non-retryable error
                raise
        
        # All retries exhausted
        raise last_exception
    
    def _generate_embedding_sync(
        self,
        text: str,
        task_type: str = "retrieval_document"
    ) -> List[float]:
        """
        Synchronous embedding generation (called via asyncio.to_thread).
        
        Args:
            text: The text to embed
            task_type: Either "retrieval_document" or "retrieval_query"
            
        Returns:
            List of floats representing the embedding vector
        """
        result = genai.embed_content(
            model=self.EMBEDDING_MODEL,
            content=text,
            task_type=task_type
        )
        return result['embedding']
    
    async def generate_embedding(
        self,
        text: str,
        task_type: str = "retrieval_document"
    ) -> List[float]:
        """
        Generate an embedding vector for the given text.
        
        Args:
            text: The text to embed (max 10,000 chars recommended)
            task_type: Either "retrieval_document" (for storing) or 
                      "retrieval_query" (for searching)
            
        Returns:
            List of 768 floats representing the embedding
            
        Raises:
            EmbeddingGenerationError: If embedding generation fails after retries
        """
        if not text or not text.strip():
            raise EmbeddingGenerationError(
                "Cannot generate embedding for empty text",
                model=self.EMBEDDING_MODEL
            )
        
        # Truncate if too long (text-embedding-004 has token limits)
        text = text[:10000]
        
        try:
            embedding = await self._retry_with_backoff(
                self._generate_embedding_sync,
                "Embedding generation",
                text,
                task_type
            )
            
            if len(embedding) != self.EMBEDDING_DIMENSION:
                logger.warning(
                    f"Unexpected embedding dimension: {len(embedding)} "
                    f"(expected {self.EMBEDDING_DIMENSION})"
                )
            
            return embedding
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "rate" in error_msg or "quota" in error_msg:
                raise RateLimitError(
                    "Embedding API rate limit exceeded after retries",
                    original_error=e
                )
            
            raise EmbeddingGenerationError(
                f"Failed to generate embedding: {str(e)}",
                model=self.EMBEDDING_MODEL,
                retry_count=self.MAX_RETRIES,
                original_error=e
            )
    
    async def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate an embedding optimized for similarity search queries.
        
        This uses task_type="retrieval_query" which is optimized for
        comparing against stored document embeddings.
        
        Args:
            query: The search query text
            
        Returns:
            List of 768 floats representing the query embedding
        """
        return await self.generate_embedding(query, task_type="retrieval_query")
    
    async def generate_document_embedding(self, document: str) -> List[float]:
        """
        Generate an embedding optimized for document storage.
        
        This uses task_type="retrieval_document" which is optimized for
        being searched against query embeddings.
        
        Args:
            document: The document text to embed
            
        Returns:
            List of 768 floats representing the document embedding
        """
        return await self.generate_embedding(document, task_type="retrieval_document")
    
    async def search_similar_colleges(
        self,
        query_text: str,
        threshold: float = 0.7,
        limit: int = 10,
        exclude_ids: Optional[List[str]] = None
    ) -> List[CollegeSearchResult]:
        """
        Search for colleges similar to the query text.
        
        Uses the Supabase RPC function `match_colleges` for efficient
        cosine similarity search via pgvector.
        
        Args:
            query_text: Natural language description of desired college attributes
            threshold: Minimum similarity score (0.0 to 1.0, default 0.7)
            limit: Maximum number of results (default 10)
            exclude_ids: List of college IDs to exclude (e.g., blacklisted)
            
        Returns:
            List of CollegeSearchResult ordered by similarity (descending)
            
        Raises:
            SimilaritySearchError: If the search fails
        """
        try:
            # Generate query embedding
            query_embedding = await self.generate_query_embedding(query_text)
            
            # Call Supabase RPC function
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
            
            # Filter out excluded colleges and convert to models
            results = []
            exclude_set = set(exclude_ids) if exclude_ids else set()
            
            for row in response.data:
                if str(row["id"]) in exclude_set:
                    continue
                
                # Parse metadata if present
                metadata = None
                if row.get("metadata"):
                    try:
                        metadata = CollegeMetadata(**row["metadata"])
                    except Exception:
                        # Log but don't fail on metadata parsing errors
                        logger.warning(f"Failed to parse metadata for college {row['id']}")
                
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
                f"College similarity search failed: {str(e)}",
                original_error=e
            )
    
    async def upsert_college_embedding(
        self,
        college_id: str,
        name: str,
        description: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Insert or update a college's embedding in the cache.
        
        Generates an embedding from the college description and stores it.
        
        Args:
            college_id: Unique identifier for the college
            name: College name
            description: Text description for embedding generation
            metadata: Optional metadata to store with the college
            
        Returns:
            True if successful
            
        Raises:
            EmbeddingGenerationError: If embedding generation fails
            SimilaritySearchError: If database operation fails
        """
        try:
            # Generate document embedding
            embedding = await self.generate_document_embedding(description)
            
            # Upsert to database
            await asyncio.to_thread(
                lambda: self.supabase.table("colleges_cache").upsert({
                    "id": college_id,
                    "name": name,
                    "embedding": embedding,
                    "metadata": metadata or {}
                }, on_conflict="id").execute()
            )
            
            logger.info(f"Upserted embedding for college: {name}")
            return True
            
        except EmbeddingGenerationError:
            raise
        except Exception as e:
            raise SimilaritySearchError(
                f"Failed to upsert college embedding: {str(e)}",
                original_error=e
            )
