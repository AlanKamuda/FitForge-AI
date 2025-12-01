# tools/web_search.py
"""
FitForge AI — Web Search Tool (ADK Compatible)
===============================================
Performs web searches to ground AI advice in current information.
Supports multiple search backends:
  1. DuckDuckGo (default, no API key needed)
  2. Google Search (ADK built-in, requires API key)

ADK Tool Format: Function with docstring + type hints + dict return
"""

import os
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

# =============================================================================
# SEARCH BACKENDS
# =============================================================================

# DuckDuckGo (no API key required)
DDGS_AVAILABLE = False
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
    print("✅ Web Search: DuckDuckGo ready")
except ImportError:
    print("⚠️ Web Search: duckduckgo-search not installed (pip install duckduckgo-search)")

# Google Search (ADK built-in)
GOOGLE_SEARCH_AVAILABLE = False
try:
    from google.adk.tools import google_search
    GOOGLE_SEARCH_AVAILABLE = True
    print("✅ Web Search: Google Search (ADK) ready")
except ImportError:
    print("⚠️ Web Search: ADK google_search not available")


# =============================================================================
# FITNESS-SPECIFIC SEARCH PREFIXES
# =============================================================================

FITNESS_SEARCH_CONTEXTS = {
    "injury": "sports medicine treatment protocol",
    "pain": "physical therapy rehabilitation exercise",
    "nutrition": "sports nutrition science research",
    "recovery": "athletic recovery methods evidence-based",
    "training": "exercise science training methodology",
    "strength": "strength training programming research",
    "endurance": "endurance training cardiovascular fitness",
    "flexibility": "stretching mobility exercise science",
    "supplement": "sports supplement research evidence",
    "sleep": "sleep recovery athletic performance",
    "hydration": "hydration sports performance",
    "warmup": "dynamic warmup injury prevention",
    "cooldown": "cooldown recovery exercise",
}


# =============================================================================
# HELPER: Enhance Query for Fitness Context
# =============================================================================

def _enhance_fitness_query(query: str) -> str:
    """
    Enhance a query with fitness/health context for better results.
    """
    query_lower = query.lower()
    
    # Check for fitness-related keywords
    for keyword, context in FITNESS_SEARCH_CONTEXTS.items():
        if keyword in query_lower:
            # Don't add if context already present
            if context.split()[0] not in query_lower:
                return f"{query} {context}"
    
    # Default: add general fitness context if none detected
    fitness_keywords = ["workout", "exercise", "fitness", "training", "health", "muscle", "cardio"]
    if any(kw in query_lower for kw in fitness_keywords):
        return query  # Already fitness-related
    
    return query  # Return as-is if not fitness-related


def _extract_key_info(text: str, max_length: int = 300) -> str:
    """Extract key information from search result text."""
    if not text:
        return ""
    
    # Clean up the text
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Truncate if too long
    if len(text) > max_length:
        # Try to cut at sentence boundary
        truncated = text[:max_length]
        last_period = truncated.rfind('.')
        if last_period > max_length * 0.5:
            return truncated[:last_period + 1]
        return truncated + "..."
    
    return text


# =============================================================================
# MAIN ADK TOOL: web_search
# =============================================================================

def web_search(
    query: str,
    max_results: int = 5,
    search_type: str = "general",
    include_sources: bool = True
) -> Dict[str, Any]:
    """
    Search the web for current information on any topic.
    
    Use this tool when you need up-to-date information that may not be
    in your training data, such as:
    - Latest research on training methods
    - Current medical/injury treatment protocols
    - Recent nutrition science findings
    - Specific exercise techniques or form guides
    
    Args:
        query: The search query. Be specific for better results.
               Example: "best exercises for lower back pain relief"
        max_results: Maximum number of results to return (1-10, default 5)
        search_type: Type of search context:
                    - "general": Standard web search
                    - "fitness": Adds fitness/exercise context
                    - "medical": Adds medical/health context
                    - "nutrition": Adds nutrition science context
                    - "research": Adds scientific research context
        include_sources: If True, includes source URLs for citation
    
    Returns:
        Dictionary with search results:
        - status: "success", "partial", or "error"
        - query: The (possibly enhanced) query used
        - results: List of result dictionaries with title, snippet, url
        - summary: Formatted text summary of all results
        - result_count: Number of results found
        - search_engine: Which search backend was used
        - searched_at: Timestamp of search
    
    Example:
        >>> result = web_search("knee pain running prevention", search_type="fitness")
        >>> print(result["summary"])
    """
    
    # -------------------------------------------------------------------------
    # Input Validation
    # -------------------------------------------------------------------------
    if not query:
        return {
            "status": "error",
            "error_message": "No search query provided"
        }
    
    query = query.strip()
    if len(query) < 3:
        return {
            "status": "error",
            "error_message": "Query too short. Please provide more details."
        }
    
    # Clamp max_results
    max_results = max(1, min(10, max_results))
    
    # -------------------------------------------------------------------------
    # Enhance Query Based on Search Type
    # -------------------------------------------------------------------------
    enhanced_query = query
    
    if search_type == "fitness":
        enhanced_query = _enhance_fitness_query(query)
    elif search_type == "medical":
        if "treatment" not in query.lower() and "protocol" not in query.lower():
            enhanced_query = f"{query} medical treatment evidence-based"
    elif search_type == "nutrition":
        if "nutrition" not in query.lower():
            enhanced_query = f"{query} nutrition science research"
    elif search_type == "research":
        if "study" not in query.lower() and "research" not in query.lower():
            enhanced_query = f"{query} scientific study research"
    
    # -------------------------------------------------------------------------
    # Perform Search (DuckDuckGo)
    # -------------------------------------------------------------------------
    results = []
    search_engine = "none"
    
    if DDGS_AVAILABLE:
        try:
            ddg = DDGS()
            raw_results = ddg.text(enhanced_query, max_results=max_results)
            
            for r in raw_results:
                results.append({
                    "title": r.get("title", "No title"),
                    "snippet": _extract_key_info(r.get("body", "")),
                    "url": r.get("href", r.get("link", ""))
                })
            
            search_engine = "DuckDuckGo"
            
        except Exception as e:
            print(f"⚠️ DuckDuckGo search failed: {e}")
    
    # -------------------------------------------------------------------------
    # Fallback: Return error if no results
    # -------------------------------------------------------------------------
    if not results:
        return {
            "status": "error",
            "error_message": "Search failed. Please try again or rephrase your query.",
            "query": enhanced_query,
            "search_engine": search_engine
        }
    
    # -------------------------------------------------------------------------
    # Format Results
    # -------------------------------------------------------------------------
    summary_parts = []
    for i, r in enumerate(results, 1):
        title = r["title"]
        snippet = r["snippet"]
        url = r["url"]
        
        if include_sources and url:
            summary_parts.append(f"{i}. **{title}**\n   {snippet}\n   Source: {url}\n")
        else:
            summary_parts.append(f"{i}. **{title}**\n   {snippet}\n")
    
    summary = "\n".join(summary_parts)
    
    return {
        "status": "success",
        "query": enhanced_query,
        "original_query": query,
        "results": results if include_sources else [{"title": r["title"], "snippet": r["snippet"]} for r in results],
        "summary": summary,
        "result_count": len(results),
        "search_engine": search_engine,
        "search_type": search_type,
        "searched_at": datetime.now().isoformat()
    }


# =============================================================================
# SPECIALIZED TOOL: Fitness Research Search
# =============================================================================

def search_fitness_research(
    topic: str,
    focus_area: str = "general"
) -> Dict[str, Any]:
    """
    Search for fitness and exercise science research on a specific topic.
    
    Optimized for finding evidence-based information about training,
    recovery, nutrition, and injury prevention.
    
    Args:
        topic: The fitness topic to research.
               Examples: "progressive overload", "HIIT vs steady state cardio"
        focus_area: Specific focus area:
                   - "general": General fitness research
                   - "strength": Strength training and hypertrophy
                   - "endurance": Cardio and endurance training
                   - "recovery": Recovery and regeneration
                   - "injury": Injury prevention and rehabilitation
                   - "nutrition": Sports nutrition
    
    Returns:
        Dictionary with research findings:
        - status: "success" or "error"
        - topic: The research topic
        - findings: List of research findings
        - summary: Formatted summary
        - evidence_quality: Assessment of evidence quality
    
    Example:
        >>> result = search_fitness_research("creatine benefits", focus_area="strength")
    """
    
    if not topic:
        return {
            "status": "error",
            "error_message": "No research topic provided"
        }
    
    # Build research-focused query
    focus_contexts = {
        "general": "exercise science research study",
        "strength": "strength training hypertrophy research",
        "endurance": "endurance cardiovascular training study",
        "recovery": "athletic recovery regeneration research",
        "injury": "injury prevention rehabilitation physical therapy",
        "nutrition": "sports nutrition supplementation research",
    }
    
    context = focus_contexts.get(focus_area, focus_contexts["general"])
    research_query = f"{topic} {context}"
    
    # Perform search
    search_result = web_search(
        query=research_query,
        max_results=5,
        search_type="research",
        include_sources=True
    )
    
    if search_result["status"] != "success":
        return search_result
    
    # Assess evidence quality based on sources
    results = search_result.get("results", [])
    evidence_indicators = {
        "high": ["pubmed", "nih.gov", "ncbi", "journal", "study", "research", ".edu"],
        "medium": ["healthline", "webmd", "mayoclinic", "medical", "science"],
        "low": ["blog", "forum", "reddit", "quora"]
    }
    
    quality_score = 0
    for r in results:
        url = r.get("url", "").lower()
        snippet = r.get("snippet", "").lower()
        combined = url + " " + snippet
        
        if any(ind in combined for ind in evidence_indicators["high"]):
            quality_score += 3
        elif any(ind in combined for ind in evidence_indicators["medium"]):
            quality_score += 2
        elif any(ind in combined for ind in evidence_indicators["low"]):
            quality_score += 1
        else:
            quality_score += 1
    
    avg_quality = quality_score / max(len(results), 1)
    
    if avg_quality >= 2.5:
        evidence_quality = "high"
        quality_note = "Results include scientific/medical sources"
    elif avg_quality >= 1.5:
        evidence_quality = "medium"
        quality_note = "Results are from reputable health sources"
    else:
        evidence_quality = "low"
        quality_note = "Consider verifying with medical professionals"
    
    return {
        "status": "success",
        "topic": topic,
        "focus_area": focus_area,
        "findings": results,
        "summary": search_result["summary"],
        "evidence_quality": evidence_quality,
        "quality_note": quality_note,
        "result_count": len(results),
        "searched_at": datetime.now().isoformat()
    }


# =============================================================================
# SPECIALIZED TOOL: Injury/Pain Research
# =============================================================================

def search_injury_protocol(
    injury_description: str,
    body_part: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search for evidence-based treatment protocols for injuries or pain.
    
    IMPORTANT: This provides general information only. Always consult
    a healthcare professional for actual injuries.
    
    Args:
        injury_description: Description of the injury or pain.
                           Example: "sharp pain in knee when running"
        body_part: Optional specific body part for focused search.
                  Example: "knee", "shoulder", "lower back"
    
    Returns:
        Dictionary with treatment information:
        - status: "success" or "error"
        - protocols: List of treatment protocols found
        - summary: Formatted summary of findings
        - disclaimer: Medical disclaimer
        - when_to_see_doctor: Signs that require professional care
    
    Example:
        >>> result = search_injury_protocol("runner's knee pain", body_part="knee")
    """
    
    if not injury_description:
        return {
            "status": "error",
            "error_message": "No injury description provided"
        }
    
    # Build medical-focused query
    query_parts = [injury_description]
    if body_part:
        query_parts.append(body_part)
    query_parts.append("treatment protocol physical therapy rehabilitation")
    
    medical_query = " ".join(query_parts)
    
    # Perform search
    search_result = web_search(
        query=medical_query,
        max_results=5,
        search_type="medical",
        include_sources=True
    )
    
    if search_result["status"] != "success":
        return search_result
    
    # Add medical disclaimers
    disclaimer = (
        "⚠️ DISCLAIMER: This information is for educational purposes only. "
        "It is not a substitute for professional medical advice, diagnosis, or treatment. "
        "Always seek the advice of a qualified healthcare provider."
    )
    
    when_to_see_doctor = [
        "Severe pain that doesn't improve with rest",
        "Swelling that doesn't reduce after 48-72 hours",
        "Inability to bear weight or use the affected area",
        "Numbness, tingling, or weakness",
        "Visible deformity or unusual appearance",
        "Pain that worsens over time",
        "Signs of infection (fever, redness, warmth)",
    ]
    
    return {
        "status": "success",
        "injury_description": injury_description,
        "body_part": body_part,
        "protocols": search_result.get("results", []),
        "summary": search_result["summary"],
        "disclaimer": disclaimer,
        "when_to_see_doctor": when_to_see_doctor,
        "searched_at": datetime.now().isoformat()
    }


# =============================================================================
# SPECIALIZED TOOL: Exercise Lookup
# =============================================================================

def search_exercise_info(
    exercise_name: str,
    info_type: str = "technique"
) -> Dict[str, Any]:
    """
    Search for detailed information about a specific exercise.
    
    Args:
        exercise_name: Name of the exercise.
                      Example: "deadlift", "pull-up", "Bulgarian split squat"
        info_type: Type of information to find:
                  - "technique": Proper form and execution
                  - "muscles": Target muscles and anatomy
                  - "variations": Exercise variations and progressions
                  - "mistakes": Common mistakes and how to avoid them
                  - "benefits": Benefits and why to include it
    
    Returns:
        Dictionary with exercise information:
        - status: "success" or "error"
        - exercise: The exercise name
        - info_type: The type of info requested
        - information: List of findings
        - summary: Formatted summary
    
    Example:
        >>> result = search_exercise_info("Romanian deadlift", info_type="technique")
    """
    
    if not exercise_name:
        return {
            "status": "error",
            "error_message": "No exercise name provided"
        }
    
    # Build context based on info type
    info_contexts = {
        "technique": "proper form technique execution how to",
        "muscles": "muscles worked target anatomy",
        "variations": "variations progressions alternatives",
        "mistakes": "common mistakes errors avoid",
        "benefits": "benefits advantages why do",
    }
    
    context = info_contexts.get(info_type, info_contexts["technique"])
    exercise_query = f"{exercise_name} exercise {context}"
    
    # Perform search
    search_result = web_search(
        query=exercise_query,
        max_results=4,
        search_type="fitness",
        include_sources=True
    )
    
    if search_result["status"] != "success":
        return search_result
    
    return {
        "status": "success",
        "exercise": exercise_name,
        "info_type": info_type,
        "information": search_result.get("results", []),
        "summary": search_result["summary"],
        "searched_at": datetime.now().isoformat()
    }


# =============================================================================
# ADK GOOGLE SEARCH WRAPPER (If Available)
# =============================================================================

def get_google_search_tool():
    """
    Get the ADK built-in Google Search tool if available.
    
    This is the recommended search tool for ADK agents as it integrates
    directly with the Gemini ecosystem.
    
    Returns:
        The google_search tool if available, None otherwise.
    
    Usage in agent:
        from tools.web_search import get_google_search_tool
        google_tool = get_google_search_tool()
        if google_tool:
            agent = LlmAgent(..., tools=[google_tool])
    """
    if GOOGLE_SEARCH_AVAILABLE:
        return google_search
    return None


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Main search tool
    "web_search",
    
    # Specialized search tools
    "search_fitness_research",
    "search_injury_protocol",
    "search_exercise_info",
    
    # ADK integration
    "get_google_search_tool",
    
    # Availability flags
    "DDGS_AVAILABLE",
    "GOOGLE_SEARCH_AVAILABLE",
]