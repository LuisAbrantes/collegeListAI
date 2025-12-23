"""
Gemini AI Service for College List AI

Uses the new google.genai SDK for:
- Search grounding for real-time university data
- Streaming responses via SSE
- Embedding generation for vector search

The service fetches live university info via Google Search,
then caches results in pgvector to reduce API costs.
"""

import asyncio
import json
import os
from typing import AsyncGenerator, Optional, List, Dict, Any
import logging

from google import genai
from google.genai import types

from app.infrastructure.exceptions import (
    AIServiceError,
    RateLimitError,
    ConfigurationError,
)


logger = logging.getLogger(__name__)


# Load system prompt from file
SYSTEM_PROMPT_PATH = os.path.join(
    os.path.dirname(__file__), 
    "SYSTEM_PROMPT.md"
)


def load_system_prompt() -> str:
    """Load the system prompt from the markdown file."""
    try:
        with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning(f"System prompt not found at {SYSTEM_PROMPT_PATH}")
        return "You are a helpful college admissions advisor."


class GeminiService:
    """
    Production-ready Gemini AI service with Google Search grounding.
    
    Features:
    - New google.genai SDK
    - Search grounding for real-time university data
    - Streaming support for SSE
    - Structured JSON output parsing
    """
    
    _instance: Optional["GeminiService"] = None
    _client: Optional[genai.Client] = None
    _initialized: bool = False
    
    # Configuration
    DEFAULT_MODEL = "gemini-2.5-flash"
    EMBEDDING_MODEL = "text-embedding-004"
    MAX_OUTPUT_TOKENS = 8192
    TEMPERATURE = 0.7
    
    def __new__(cls) -> "GeminiService":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialize()
            GeminiService._initialized = True
    
    def _initialize(self) -> None:
        """Initialize Gemini client."""
        api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            raise ConfigurationError(
                "Missing GOOGLE_API_KEY environment variable",
                missing_keys=["GOOGLE_API_KEY"]
            )
        
        # Initialize the new genai client
        self._client = genai.Client(api_key=api_key)
        self._system_prompt = load_system_prompt()
        
        logger.info(f"GeminiService initialized with model: {self.DEFAULT_MODEL}")
    
    @property
    def client(self) -> genai.Client:
        """Get the Gemini client instance."""
        if self._client is None:
            self._initialize()
        return self._client
    
    def _build_user_context(
        self,
        nationality: str,
        gpa: float,
        major: str,
        excluded_colleges: Optional[List[str]] = None,
    ) -> str:
        """Build contextual prompt with user profile."""
        context_parts = [
            f"## Student Profile",
            f"- **Nationality:** {nationality}",
            f"- **GPA:** {gpa}/4.0",
            f"- **Intended Major:** {major}",
        ]
        
        if excluded_colleges:
            context_parts.append(f"- **Blacklisted Schools (DO NOT SUGGEST):** {', '.join(excluded_colleges)}")
        
        return "\n".join(context_parts)
    
    async def generate_recommendations_with_search(
        self,
        user_query: str,
        nationality: str,
        gpa: float,
        major: str,
        excluded_colleges: Optional[List[str]] = None,
        cached_colleges: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate recommendations using Google Search grounding.
        
        This uses Gemini's search capability to find real-time
        university information, then formats as recommendations.
        
        Args:
            user_query: User's natural language query
            nationality: Student's citizenship
            gpa: GPA on 4.0 scale
            major: Intended field of study
            excluded_colleges: Colleges to avoid
            cached_colleges: Pre-cached colleges from vector DB
            
        Returns:
            Dict with recommendations and grounding metadata
        """
        try:
            user_context = self._build_user_context(
                nationality, gpa, major, excluded_colleges
            )
            
            # Add cached colleges context if available
            cache_context = ""
            if cached_colleges:
                cache_context = "\n\n## Previously Researched Universities\n"
                for college in cached_colleges[:5]:
                    cache_context += f"- {college.get('name', 'Unknown')}\n"
            
            full_prompt = f"""{self._system_prompt}

{user_context}
{cache_context}

## User Query
{user_query}

Based on the student's profile, use Google Search to find universities that match.
For each university, determine if it's a Reach, Target, or Safety school.

Respond in JSON format:
{{
    "recommendations": [
        {{
            "name": "University Name",
            "label": "Reach|Target|Safety",
            "match_score": 0-100,
            "reasoning": "Why this fits the student",
            "financial_aid_info": "Specific to nationality",
            "official_url": "https://..."
        }}
    ],
    "search_queries_used": ["list of search queries"]
}}"""

            # Call Gemini with Google Search grounding
            response = await asyncio.to_thread(
                lambda: self.client.models.generate_content(
                    model=self.DEFAULT_MODEL,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        temperature=self.TEMPERATURE,
                        max_output_tokens=self.MAX_OUTPUT_TOKENS,
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )
            )
            
            if not response.text:
                raise AIServiceError(
                    "Empty response from Gemini",
                    model=self.DEFAULT_MODEL,
                    operation="generate_recommendations"
                )
            
            # Extract grounding metadata
            grounding_metadata = None
            sources = []
            search_queries = []
            
            if response.candidates and response.candidates[0].grounding_metadata:
                metadata = response.candidates[0].grounding_metadata
                search_queries = metadata.web_search_queries or []
                
                if metadata.grounding_chunks:
                    for chunk in metadata.grounding_chunks:
                        if hasattr(chunk, 'web') and chunk.web:
                            sources.append({
                                "title": chunk.web.title,
                                "url": chunk.web.uri
                            })
            
            # Parse JSON response
            result = self._parse_json_response(response.text)
            result["grounding_sources"] = sources
            result["search_queries"] = search_queries
            
            return result
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if "rate" in error_msg or "quota" in error_msg:
                raise RateLimitError(
                    "Gemini API rate limit exceeded",
                    original_error=e
                )
            
            raise AIServiceError(
                f"Failed to generate recommendations: {str(e)}",
                model=self.DEFAULT_MODEL,
                operation="generate_recommendations",
                original_error=e
            )
    
    async def stream_recommendations(
        self,
        user_query: str,
        nationality: str,
        gpa: float,
        major: str,
        excluded_colleges: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream recommendations via SSE with search grounding.
        """
        try:
            user_context = self._build_user_context(
                nationality, gpa, major, excluded_colleges
            )
            full_prompt = f"{self._system_prompt}\n\n{user_context}\n\n## User Query\n{user_query}"
            
            # Use streaming with search grounding
            response = self.client.models.generate_content_stream(
                model=self.DEFAULT_MODEL,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    temperature=self.TEMPERATURE,
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            error_msg = str(e).lower()
            
            if "rate" in error_msg or "quota" in error_msg:
                raise RateLimitError(
                    "Gemini API rate limit exceeded",
                    original_error=e
                )
            
            raise AIServiceError(
                f"Streaming failed: {str(e)}",
                model=self.DEFAULT_MODEL,
                operation="stream_recommendations",
                original_error=e
            )
    
    async def generate_embedding(
        self,
        text: str
    ) -> List[float]:
        """
        Generate an embedding vector for text.
        
        Args:
            text: Text to embed (max 10k chars recommended)
            
        Returns:
            List of floats (768 dimensions)
        """
        if not text or not text.strip():
            raise AIServiceError(
                "Cannot generate embedding for empty text",
                model=self.EMBEDDING_MODEL,
                operation="embed"
            )
        
        # Truncate if too long
        text = text[:10000]
        
        try:
            result = await asyncio.to_thread(
                lambda: self.client.models.embed_content(
                    model=self.EMBEDDING_MODEL,
                    contents=text
                )
            )
            
            return result.embeddings[0].values
            
        except Exception as e:
            raise AIServiceError(
                f"Embedding generation failed: {str(e)}",
                model=self.EMBEDDING_MODEL,
                operation="embed",
                original_error=e
            )
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from response, handling markdown code blocks."""
        text = response_text.strip()
        
        # Remove markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Response was not valid JSON, returning as raw text")
            return {"raw_response": response_text}
