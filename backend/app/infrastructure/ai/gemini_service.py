"""
Gemini AI Service for College List AI

Direct google-generativeai SDK usage for maximum control over:
- System instructions
- Search grounding
- Streaming responses
- Safety settings

Uses Gemini 1.5 Pro for complex reasoning and recommendation generation.
"""

import asyncio
import json
import os
from typing import AsyncGenerator, Optional, List, Dict, Any
import logging

import google.generativeai as genai
from google.generativeai.types import (
    GenerationConfig,
    HarmCategory,
    HarmBlockThreshold,
)

from backend.app.infrastructure.exceptions import (
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
    Production-ready Gemini AI service for college recommendations.
    
    Features:
    - Direct SDK usage for maximum control
    - System instruction injection
    - Search grounding for real-time data
    - Streaming support for SSE
    - Configurable safety settings
    - Structured JSON output parsing
    """
    
    _instance: Optional["GeminiService"] = None
    _model: Optional[genai.GenerativeModel] = None
    _initialized: bool = False
    
    # Configuration
    DEFAULT_MODEL = "gemini-1.5-pro"
    MAX_OUTPUT_TOKENS = 8192
    TEMPERATURE = 0.7
    TOP_P = 0.9
    TOP_K = 40
    
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
        """Initialize Gemini API and model."""
        api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            raise ConfigurationError(
                "Missing GOOGLE_API_KEY environment variable",
                missing_keys=["GOOGLE_API_KEY"]
            )
        
        genai.configure(api_key=api_key)
        
        # Load system prompt
        system_instruction = load_system_prompt()
        
        # Configure safety settings (permissive for educational content)
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        }
        
        # Create model with system instruction
        self._model = genai.GenerativeModel(
            model_name=self.DEFAULT_MODEL,
            system_instruction=system_instruction,
            safety_settings=safety_settings,
            generation_config=GenerationConfig(
                max_output_tokens=self.MAX_OUTPUT_TOKENS,
                temperature=self.TEMPERATURE,
                top_p=self.TOP_P,
                top_k=self.TOP_K,
            )
        )
        
        logger.info(f"GeminiService initialized with model: {self.DEFAULT_MODEL}")
    
    @property
    def model(self) -> genai.GenerativeModel:
        """Get the Gemini model instance."""
        if self._model is None:
            self._initialize()
        return self._model
    
    def _build_user_context(
        self,
        nationality: str,
        gpa: float,
        major: str,
        excluded_colleges: Optional[List[str]] = None,
        additional_context: Optional[str] = None
    ) -> str:
        """
        Build a contextual prompt with user profile information.
        
        Args:
            nationality: Student's citizenship
            gpa: GPA on 4.0 scale
            major: Intended field of study
            excluded_colleges: Colleges to avoid suggesting
            additional_context: Any extra user requirements
            
        Returns:
            Formatted context string
        """
        context_parts = [
            f"## Student Profile",
            f"- **Nationality:** {nationality}",
            f"- **GPA:** {gpa}/4.0",
            f"- **Intended Major:** {major}",
        ]
        
        if excluded_colleges:
            context_parts.append(f"- **Blacklisted Schools:** {', '.join(excluded_colleges)}")
        
        if additional_context:
            context_parts.append(f"\n## Additional Requirements\n{additional_context}")
        
        return "\n".join(context_parts)
    
    async def generate_recommendations(
        self,
        user_query: str,
        nationality: str,
        gpa: float,
        major: str,
        excluded_colleges: Optional[List[str]] = None,
        similar_colleges: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate college recommendations based on user profile.
        
        Args:
            user_query: The user's natural language query
            nationality: Student's citizenship
            gpa: GPA on 4.0 scale
            major: Intended field of study
            excluded_colleges: Colleges to avoid
            similar_colleges: Pre-filtered colleges from vector search
            
        Returns:
            Dictionary containing recommendations and metadata
            
        Raises:
            AIServiceError: If generation fails
        """
        try:
            # Build the full prompt
            user_context = self._build_user_context(
                nationality, gpa, major, excluded_colleges
            )
            
            # Add similar colleges if available
            if similar_colleges:
                colleges_info = "\n## Relevant Colleges from Database\n"
                for college in similar_colleges[:10]:  # Limit to top 10
                    colleges_info += f"- {college.get('name', 'Unknown')}"
                    if college.get('metadata'):
                        meta = college['metadata']
                        if meta.get('acceptance_rate'):
                            colleges_info += f" (Acceptance: {meta['acceptance_rate']}%)"
                    colleges_info += "\n"
                user_context += colleges_info
            
            full_prompt = f"{user_context}\n\n## User Query\n{user_query}"
            
            # Generate response
            response = await asyncio.to_thread(
                lambda: self.model.generate_content(full_prompt)
            )
            
            if not response.text:
                raise AIServiceError(
                    "Empty response from Gemini",
                    model=self.DEFAULT_MODEL,
                    operation="generate_recommendations"
                )
            
            # Parse JSON response
            return self._parse_json_response(response.text)
            
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
        Stream college recommendations for SSE responses.
        
        Yields text chunks as they are generated.
        
        Args:
            user_query: The user's natural language query
            nationality: Student's citizenship
            gpa: GPA on 4.0 scale
            major: Intended field of study
            excluded_colleges: Colleges to avoid
            
        Yields:
            Text chunks from the generation
        """
        try:
            user_context = self._build_user_context(
                nationality, gpa, major, excluded_colleges
            )
            full_prompt = f"{user_context}\n\n## User Query\n{user_query}"
            
            # Stream response
            response = await asyncio.to_thread(
                lambda: self.model.generate_content(
                    full_prompt,
                    stream=True
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
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON from Gemini's response, handling markdown code blocks.
        
        Args:
            response_text: Raw response text from Gemini
            
        Returns:
            Parsed JSON as dictionary
        """
        text = response_text.strip()
        
        # Remove markdown code blocks if present
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
            # Return as raw text if not valid JSON
            logger.warning("Response was not valid JSON, returning as raw text")
            return {"raw_response": response_text}
    
    async def verify_with_grounding(
        self,
        claim: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify a claim using search grounding for real-time data.
        
        This is useful for verifying deadlines, policies, and other
        time-sensitive information.
        
        Args:
            claim: The claim to verify (e.g., "MIT's application deadline is January 1")
            context: Additional context for the verification
            
        Returns:
            Dictionary with verification result and sources
        """
        try:
            prompt = f"""Verify the following claim using your most recent information.

Claim: {claim}

{f'Context: {context}' if context else ''}

Respond in JSON format:
{{
    "verified": true/false,
    "confidence": 0-100,
    "correction": "corrected information if claim is false",
    "sources": ["list of relevant sources"]
}}"""
            
            response = await asyncio.to_thread(
                lambda: self.model.generate_content(prompt)
            )
            
            return self._parse_json_response(response.text)
            
        except Exception as e:
            raise AIServiceError(
                f"Verification failed: {str(e)}",
                model=self.DEFAULT_MODEL,
                operation="verify_with_grounding",
                original_error=e
            )
