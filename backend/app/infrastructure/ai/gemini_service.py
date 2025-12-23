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
        # Accept both GOOGLE_API_KEY and GEMINI_API_KEY for flexibility
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise ConfigurationError(
                "Missing GOOGLE_API_KEY or GEMINI_API_KEY environment variable",
                missing_keys=["GOOGLE_API_KEY", "GEMINI_API_KEY"]
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
        citizenship_status: Optional[str] = None,
        nationality: Optional[str] = None,
        gpa: float = 0.0,
        major: str = "",
        sat_score: Optional[int] = None,
        act_score: Optional[int] = None,
        state_of_residence: Optional[str] = None,
        household_income_tier: Optional[str] = None,
        english_proficiency_score: Optional[int] = None,
        english_test_type: Optional[str] = None,
        campus_vibe: Optional[str] = None,
        is_student_athlete: bool = False,
        has_legacy_status: bool = False,
        legacy_universities: Optional[List[str]] = None,
        post_grad_goal: Optional[str] = None,
        is_first_gen: bool = False,
        ap_class_count: Optional[int] = None,
        ap_classes: Optional[List[str]] = None,
        excluded_colleges: Optional[List[str]] = None,
    ) -> str:
        """Build contextual prompt with user profile, branching for US vs International."""
        
        # Determine if domestic or international
        is_domestic = citizenship_status in ["US_CITIZEN", "PERMANENT_RESIDENT", "DACA"]
        
        context_parts = [
            "## Student Profile",
            f"- **Citizenship Status:** {citizenship_status or 'Not specified'}",
        ]
        
        if nationality:
            context_parts.append(f"- **Nationality:** {nationality}")
        
        context_parts.extend([
            f"- **GPA:** {gpa}/4.0",
            f"- **Intended Major:** {major}",
        ])
        
        # First-generation status
        if is_first_gen:
            context_parts.append("- **First-Generation College Student:** Yes")
        
        # AP Classes
        if ap_class_count is not None and ap_class_count > 0:
            context_parts.append(f"- **AP Classes Taken:** {ap_class_count}")
            if ap_classes and len(ap_classes) > 0:
                context_parts.append(f"- **AP Subjects:** {', '.join(ap_classes)}")
        
        # Test scores
        if sat_score:
            context_parts.append(f"- **SAT Score:** {sat_score}/1600")
        if act_score:
            context_parts.append(f"- **ACT Score:** {act_score}/36")
        
        # Branch logic based on citizenship
        if is_domestic:
            context_parts.append("\n### 🇺🇸 Domestic Student Considerations")
            if state_of_residence:
                context_parts.append(f"- **Home State:** {state_of_residence} (prioritize in-state public options)")
            if household_income_tier:
                context_parts.append(f"- **Income Tier:** {household_income_tier}")
                if household_income_tier == "LOW":
                    context_parts.append("- **FAFSA Eligible:** Yes - Emphasize Pell Grant eligibility and need-based aid")
                elif household_income_tier == "MEDIUM":
                    context_parts.append("- **FAFSA Eligible:** Yes - Look for merit + need combination aid")
            context_parts.append("- **Priority:** In-state tuition, federal aid (FAFSA), state grants")
        else:
            context_parts.append("\n### 🌍 International Student Considerations")
            if english_proficiency_score:
                test_type = english_test_type or "TOEFL"
                if test_type == "TOEFL":
                    context_parts.append(f"- **TOEFL iBT Score:** {english_proficiency_score}/120")
                elif test_type == "DUOLINGO":
                    context_parts.append(f"- **Duolingo English Test:** {english_proficiency_score}/160")
                elif test_type == "IELTS":
                    context_parts.append(f"- **IELTS Score:** {english_proficiency_score}/9.0")
                else:
                    context_parts.append(f"- **English Proficiency:** {english_proficiency_score}")
            if nationality:
                context_parts.append(f"- **Check Need-Blind status for:** {nationality}")
            context_parts.append("- **Priority:** Need-Blind/Need-Aware policies, international scholarships, English requirements")
        
        # Fit factors
        if campus_vibe or is_student_athlete or has_legacy_status or post_grad_goal:
            context_parts.append("\n### Fit Preferences")
            if campus_vibe:
                context_parts.append(f"- **Campus Vibe:** {campus_vibe}")
            if is_student_athlete:
                context_parts.append("- **Student Athlete:** Yes - Consider NCAA Division programs and athletic scholarships")
            if has_legacy_status and legacy_universities:
                context_parts.append(f"- **Legacy Status at:** {', '.join(legacy_universities)}")
            if post_grad_goal:
                goal_text = {
                    "JOB_PLACEMENT": "Immediate job placement (prioritize career services, industry connections)",
                    "GRADUATE_SCHOOL": "Graduate/professional school (prioritize research opportunities)",
                    "ENTREPRENEURSHIP": "Entrepreneurship (look for startup ecosystems, incubators)",
                    "UNDECIDED": "Undecided (balanced liberal arts approach)"
                }.get(post_grad_goal, post_grad_goal)
                context_parts.append(f"- **Post-Grad Goal:** {goal_text}")
        
        if excluded_colleges:
            context_parts.append(f"\n- **Blacklisted Schools (DO NOT SUGGEST):** {', '.join(excluded_colleges)}")
        
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
        citizenship_status: Optional[str] = None,
        nationality: Optional[str] = None,
        gpa: float = 0.0,
        major: str = "",
        sat_score: Optional[int] = None,
        act_score: Optional[int] = None,
        state_of_residence: Optional[str] = None,
        household_income_tier: Optional[str] = None,
        english_proficiency_score: Optional[int] = None,
        english_test_type: Optional[str] = None,
        campus_vibe: Optional[str] = None,
        is_student_athlete: bool = False,
        has_legacy_status: bool = False,
        legacy_universities: Optional[List[str]] = None,
        post_grad_goal: Optional[str] = None,
        is_first_gen: bool = False,
        ap_class_count: Optional[int] = None,
        ap_classes: Optional[List[str]] = None,
        excluded_colleges: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream recommendations via SSE with search grounding.
        Uses conversational format for better streaming UX.
        Branches logic for US vs International students.
        """
        try:
            # Build user context with all profile fields
            user_context = self._build_user_context(
                citizenship_status=citizenship_status,
                nationality=nationality,
                gpa=gpa,
                major=major,
                sat_score=sat_score,
                act_score=act_score,
                state_of_residence=state_of_residence,
                household_income_tier=household_income_tier,
                english_proficiency_score=english_proficiency_score,
                english_test_type=english_test_type,
                campus_vibe=campus_vibe,
                is_student_athlete=is_student_athlete,
                has_legacy_status=has_legacy_status,
                legacy_universities=legacy_universities,
                post_grad_goal=post_grad_goal,
                is_first_gen=is_first_gen,
                ap_class_count=ap_class_count,
                ap_classes=ap_classes,
                excluded_colleges=excluded_colleges
            )
            
            # Determine if domestic for prompt customization
            is_domestic = citizenship_status in ["US_CITIZEN", "PERMANENT_RESIDENT", "DACA"]
            
            # Build a focused prompt with branched instructions
            streaming_prompt = f"""{self._system_prompt}

{user_context}

**User Query:** {user_query}

**Instructions:**
- Provide 3-5 universities maximum
- For each: Name, Reach/Target/Safety label, match score, 1-2 sentence fit explanation
{"- Highlight in-state options if available in " + state_of_residence if is_domestic and state_of_residence else "- Include Need-Blind status for international applicants"}
- Be concise and direct
- Use Google Search to verify current info for 2025-2026 cycle

Format each university as:
**[University Name]** (Reach/Target/Safety) - Match: XX%
Brief explanation of fit, key programs, and relevant financial aid info.
"""

            # Use streaming with search grounding
            response = self.client.models.generate_content_stream(
                model=self.DEFAULT_MODEL,
                contents=streaming_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.6,  # Lower for more focused responses
                    max_output_tokens=1500,  # Limit response length
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
