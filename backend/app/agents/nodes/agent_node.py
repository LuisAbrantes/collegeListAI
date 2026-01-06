"""
Agent Node for College List AI

Single intelligent agent that uses function calling to decide what to do.
Replaces the multi-node intent classification approach.

Design:
- LLM analyzes query → decides which tool to call → responds naturally
- No rigid templates, no intent classification
"""

import json
import logging
from typing import Dict, Any, List, Optional

import httpx

from app.config.settings import settings
from app.agents.state import RecommendationAgentState
from app.agents.tools import TOOL_DEFINITIONS, ToolExecutor
from app.domain.scoring.match_scorer import MatchScorer
from app.infrastructure.services.college_search_service import CollegeSearchService
from app.infrastructure.db.repositories.college_repository import (
    CollegeRepository,
    CollegeMajorStatsRepository,
)
from app.infrastructure.db.database import get_session_context

logger = logging.getLogger(__name__)


# System prompt for the agent
SYSTEM_PROMPT = """You are an expert college advisor helping students build and manage their college list.

AVAILABLE TOOLS:
- search_colleges: Get a NEW scored list of college recommendations
- get_college_info: Get DETAILED info about a specific college (auto-discovers via web if not in database)
- get_student_profile: Get the student's current profile data
- add_to_college_list: Save a college to the student's list
- remove_from_college_list: Remove a college from the student's list
- exclude_college: Block a college from future recommendations
- get_my_college_list: Show the student's saved college list

TOOL SELECTION RULES (STRICT PRIORITY ORDER):
1. If user asks about a SPECIFIC SCHOOL by name (e.g., "tell me about Stetson University", "info on Reed College"):
   → ALWAYS use get_college_info - it will automatically search the web if not in database

2. If user asks for RECOMMENDATIONS (e.g., "give me colleges", "recommend schools"):
   → Use search_colleges with appropriate counts

3. If user wants to ADD to their list (e.g., "add MIT to my list", "save Stanford"):
   → Use add_to_college_list

4. If user wants to REMOVE from list (e.g., "remove Harvard from my list"):
   → Use remove_from_college_list

5. If user wants to EXCLUDE/BLOCK (e.g., "never show me Yale", "I'm not interested in X"):
   → Use exclude_college

6. If user asks to SEE their list (e.g., "show my list", "what's in my college list"):
   → Use get_my_college_list

7. For general questions that don't require data:
   → Respond directly without tools

RESPONSE FORMATTING FOR RECOMMENDATIONS:
When presenting college recommendations, YOU MUST include metrics for EACH school:
- Name and category (Reach/Target/Safety)
- Match Score (e.g., "78% match")
- Acceptance Rate (e.g., "18% acceptance rate")
- Academic Info (SAT range, median GPA if available)
- Financial Aid info (if relevant to the student's profile)

Example format for each school:
**MIT** - 🎯 Reach (72% match)
- Acceptance Rate: 4%
- SAT Range: 1520-1580
- Financial Aid: Need-blind admissions

DO NOT just list school names without metrics. The metrics are critical for decision-making.

REMEMBER: You're helping students build THEIR college list - a central tool for their application journey."""


async def agent_node(state: RecommendationAgentState) -> Dict[str, Any]:
    """
    Single agent node that handles all queries via function calling.
    
    Flow:
    1. Send query + history + tools to LLM
    2. LLM decides which tool to call (or responds directly)
    3. Execute tool, send result back to LLM
    4. LLM generates final response
    """
    try:
        user_query = state.get("user_query", "")
        profile = state.get("profile", {})
        student_type = state.get("student_type", "domestic")
        conversation_history = state.get("conversation_history", [])
        
        logger.info(f"[AGENT] Processing query: '{user_query[:50]}...'")
        
        # Build messages for LLM
        messages = _build_messages(user_query, profile, conversation_history)
        
        # Call LLM with tools
        response = await _call_llm_with_tools(messages)
        
        if not response:
            return {"stream_content": ["I apologize, I encountered an issue. Please try again."]}
        
        # Check if LLM wants to call a tool
        tool_calls = response.get("tool_calls", [])
        
        if tool_calls:
            # Execute tools and get final response
            final_response = await _execute_tools_and_respond(
                tool_calls, messages, profile, student_type
            )
        else:
            # LLM responded directly (no tool needed)
            final_response = response.get("content", "")
        
        logger.info("[AGENT] Response generated successfully")
        
        return {
            "stream_content": [final_response],
            "recommendations": [],  # Could parse from response if needed
        }
        
    except Exception as e:
        logger.error(f"[AGENT] Error: {e}")
        return {
            "stream_content": ["I apologize, something went wrong. Please try again."],
            "recommendations": [],
        }


def _build_messages(
    query: str,
    profile: Dict[str, Any],
    history: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """Build message list for LLM."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add profile context
    profile_context = f"""
STUDENT PROFILE:
- GPA: {profile.get('gpa', 'N/A')}
- Major: {profile.get('major', 'Undeclared')}
- SAT: {profile.get('sat_score', 'N/A')}
- Citizenship: {profile.get('citizenship_status', 'international')}
- Nationality: {profile.get('nationality', 'N/A')}
"""
    messages.append({"role": "system", "content": profile_context})
    
    # Add conversation history (last 6 messages)
    for msg in history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add current query
    messages.append({"role": "user", "content": query})
    
    return messages


async def _call_llm_with_tools(messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    """Call LLM with function calling support."""
    
    if settings.synthesis_provider == "groq":
        return await _call_groq_with_tools(messages)
    elif settings.synthesis_provider == "perplexity":
        return await _call_perplexity_with_tools(messages)
    else:  # ollama - no native function calling, use prompt-based
        return await _call_ollama_with_tools(messages)


async def _call_groq_with_tools(messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    """Call Groq API with function calling."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.groq_model,
                    "messages": messages,
                    "tools": TOOL_DEFINITIONS,
                    "tool_choice": "auto",
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            data = response.json()
            
            choice = data["choices"][0]["message"]
            
            return {
                "content": choice.get("content", ""),
                "tool_calls": choice.get("tool_calls", []),
            }
            
    except Exception as e:
        logger.error(f"Groq API error: {e}")
        return None


async def _call_perplexity_with_tools(messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    """
    Call Perplexity API.
    
    Note: Perplexity doesn't support function calling natively.
    We use prompt-based tool selection instead.
    """
    # Perplexity doesn't have native function calling
    # Fall back to prompt-based approach
    return await _call_ollama_with_tools(messages)


async def _call_ollama_with_tools(messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    """
    Call Ollama without native function calling.
    
    Uses prompt-based tool selection.
    """
    # Add tool selection instruction to prompt
    tool_prompt = """
Based on the user's query, decide which tool to use:
1. search_colleges - if user wants recommendations
2. get_college_info - if user asks about a specific school
3. none - if you can answer directly

Respond with JSON: {"tool": "tool_name", "args": {...}} or {"tool": "none", "response": "..."}
"""
    
    enhanced_messages = messages.copy()
    enhanced_messages.append({"role": "system", "content": tool_prompt})
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Combine messages into single prompt for Ollama
            prompt = "\n".join([f"{m['role']}: {m['content']}" for m in enhanced_messages])
            
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            text = data.get("response", "")
            
            # Parse tool call from response
            try:
                parsed = json.loads(text)
                if parsed.get("tool") and parsed["tool"] != "none":
                    return {
                        "content": "",
                        "tool_calls": [{
                            "function": {
                                "name": parsed["tool"],
                                "arguments": json.dumps(parsed.get("args", {}))
                            }
                        }],
                    }
                else:
                    return {"content": parsed.get("response", text), "tool_calls": []}
            except json.JSONDecodeError:
                return {"content": text, "tool_calls": []}
                
    except Exception as e:
        logger.error(f"Ollama API error: {e}")
        return None


async def _execute_tools_and_respond(
    tool_calls: List[Dict[str, Any]],
    messages: List[Dict[str, str]],
    profile: Dict[str, Any],
    student_type: str
) -> str:
    """Execute tool calls and generate final response."""
    
    # Get database session and create services
    async with get_session_context() as session:
        college_repo = CollegeRepository(session)
        stats_repo = CollegeMajorStatsRepository(session)
        search_service = CollegeSearchService(college_repo, stats_repo)
        scorer = MatchScorer()
        
        executor = ToolExecutor(search_service, college_repo, stats_repo, scorer)
        
        # Execute all tool calls
        tool_results = []
        for tool_call in tool_calls:
            func = tool_call.get("function", {})
            tool_name = func.get("name", "")
            
            try:
                args = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            
            result = await executor.execute(tool_name, args, profile, student_type)
            tool_results.append({
                "name": tool_name,
                "result": result
            })
    
    # Send tool results back to LLM for final response
    messages_with_results = messages.copy()
    
    for tool_result in tool_results:
        messages_with_results.append({
            "role": "assistant",
            "content": f"Tool {tool_result['name']} returned: {json.dumps(tool_result['result'], indent=2)}"
        })
    
    messages_with_results.append({
        "role": "user",
        "content": "Based on the tool results above, provide a helpful response to the student."
    })
    
    # Get final response
    final = await _call_llm_for_response(messages_with_results)
    
    return final or "I found some results but couldn't format them properly. Please try again."


async def _call_llm_for_response(messages: List[Dict[str, str]]) -> Optional[str]:
    """Call LLM for final response (no tools)."""
    
    if settings.synthesis_provider == "groq":
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.groq_model,
                        "messages": messages,
                        "temperature": 0.7,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Groq final response error: {e}")
            return None
    
    else:  # Ollama fallback
        try:
            prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{settings.ollama_base_url}/api/generate",
                    json={
                        "model": settings.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except Exception as e:
            logger.error(f"Ollama final response error: {e}")
            return None
