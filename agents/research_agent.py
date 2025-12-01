
"""
FitForge AI — Research Agent (ADK Multi-Agent Pattern)
=======================================================
Specialized agent for fitness/medical research queries.
Can be used standalone OR as AgentTool by other agents.
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime

# =============================================================================
# ADK IMPORTS
# =============================================================================
ADK_AVAILABLE = False
GOOGLE_SEARCH_AVAILABLE = False
google_search = None

try:
    from google.adk.agents import LlmAgent
    from google.adk.models.google_llm import Gemini
    from google.adk.tools import AgentTool, FunctionTool
    from google.adk.runners import InMemoryRunner, Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    
    ADK_AVAILABLE = True
    
    # google_search is optional - may not be available in all versions
    try:
        from google.adk.tools import google_search as _google_search
        google_search = _google_search
        GOOGLE_SEARCH_AVAILABLE = True
    except ImportError:
        print("⚠️ Research Agent: google_search not available")
    
    print("✅ Research Agent: ADK components ready")
except ImportError as e:
    print(f"⚠️ Research Agent: ADK not available: {e}")

# Custom web search tools
CUSTOM_SEARCH_AVAILABLE = False
DDGS_AVAILABLE = False

try:
    from tools.web_search import (
        web_search,
        search_fitness_research,
        search_injury_protocol,
        search_exercise_info,
        DDGS_AVAILABLE
    )
    CUSTOM_SEARCH_AVAILABLE = True
    print("✅ Research Agent: Custom search tools ready")
except ImportError:
    print("⚠️ Research Agent: Custom search tools not available")

print(f"🔬 Research Agent: ADK={ADK_AVAILABLE}, GoogleSearch={GOOGLE_SEARCH_AVAILABLE}, CustomSearch={CUSTOM_SEARCH_AVAILABLE}")


# =============================================================================
# RETRY CONFIGURATION
# =============================================================================
def get_retry_config():
    """Get standard retry configuration."""
    if not ADK_AVAILABLE:
        return None
    try:
        return types.HttpRetryOptions(
            attempts=5,
            exp_base=7,
            initial_delay=1,
            http_status_codes=[429, 500, 503, 504],
        )
    except:
        return None


# =============================================================================
# RESEARCH TOOL: Comprehensive Injury Research
# =============================================================================
def research_injury_comprehensive(
    injury_description: str,
    body_part: Optional[str] = None,
    activity_type: Optional[str] = None,
    severity: str = "moderate"
) -> Dict[str, Any]:
    """
    Conduct comprehensive research on an injury or pain condition.
    
    Args:
        injury_description: Description of the injury (e.g., "sharp pain in knee when squatting")
        body_part: Specific body part (e.g., "knee", "lower back")
        activity_type: Activity that caused it (e.g., "running", "weightlifting")
        severity: "mild", "moderate", or "severe"
    
    Returns:
        Comprehensive injury research including treatment, recovery, and exercise modifications
    """
    if not injury_description:
        return {"status": "error", "error_message": "No injury description provided"}
    
    results = {
        "injury_description": injury_description,
        "body_part": body_part,
        "activity_type": activity_type,
        "severity": severity,
        "researched_at": datetime.now().isoformat()
    }
    
    # Search for condition information
    if CUSTOM_SEARCH_AVAILABLE:
        condition_query = f"{injury_description} {body_part or ''} causes symptoms diagnosis"
        condition_result = web_search(condition_query, max_results=3, search_type="medical")
        
        if condition_result.get("status") == "success":
            results["condition_info"] = {
                "summary": condition_result.get("summary", ""),
                "sources": condition_result.get("results", [])[:3]
            }
        
        # Treatment protocols
        protocol_result = search_injury_protocol(injury_description, body_part)
        if protocol_result.get("status") == "success":
            results["treatment_protocols"] = {
                "summary": protocol_result.get("summary", ""),
                "sources": protocol_result.get("protocols", [])[:3]
            }
            results["when_to_see_doctor"] = protocol_result.get("when_to_see_doctor", [])
        
        # Exercise modifications
        if activity_type:
            mod_query = f"{injury_description} {body_part or ''} exercise modifications {activity_type}"
            mod_result = web_search(mod_query, max_results=3, search_type="fitness")
            if mod_result.get("status") == "success":
                results["exercise_modifications"] = {
                    "summary": mod_result.get("summary", ""),
                    "activity": activity_type
                }
        
        # Recovery timeline
        recovery_query = f"{injury_description} recovery time healing timeline"
        recovery_result = web_search(recovery_query, max_results=2, search_type="medical")
        if recovery_result.get("status") == "success":
            results["recovery_timeline"] = recovery_result.get("summary", "")
    
    # Severity-based recommendations
    severity_recommendations = {
        "mild": [
            "Rest from aggravating activities for 2-3 days",
            "Apply ice for 15-20 minutes several times daily",
            "Continue gentle movement within pain-free range",
            "Monitor for worsening symptoms"
        ],
        "moderate": [
            "Reduce training volume by 50% or more",
            "Avoid all activities that reproduce pain",
            "Consider seeing a physical therapist",
            "Ice and anti-inflammatory measures as needed",
            "Allow 1-2 weeks before reassessing"
        ],
        "severe": [
            "STOP all training immediately",
            "See a doctor or physical therapist ASAP",
            "Do not attempt to 'push through' the pain",
            "Document symptoms for medical appointment",
            "Complete rest until professional evaluation"
        ]
    }
    
    results["severity_recommendations"] = severity_recommendations.get(severity, severity_recommendations["moderate"])
    
    # Prevention tips
    results["prevention_tips"] = [
        "Proper warm-up before activity",
        "Gradual progression in training load (10% rule)",
        "Adequate recovery between sessions",
        "Address muscle imbalances and mobility issues",
        "Use proper form and technique",
        "Listen to early warning signs"
    ]
    
    # Medical disclaimer
    results["disclaimer"] = (
        "⚠️ IMPORTANT: This information is for educational purposes only and is not "
        "a substitute for professional medical advice, diagnosis, or treatment. "
        "Always consult a qualified healthcare provider for injury assessment."
    )
    
    results["status"] = "success"
    return results


# =============================================================================
# RESEARCH TOOL: Training Methodology Research
# =============================================================================
def research_training_method(
    method_name: str,
    goal: Optional[str] = None,
    experience_level: str = "intermediate"
) -> Dict[str, Any]:
    """
    Research a specific training methodology or program.
    
    Args:
        method_name: Training method (e.g., "5/3/1", "PPL", "Starting Strength", "HIIT")
        goal: Training goal (e.g., "strength", "hypertrophy", "endurance")
        experience_level: "beginner", "intermediate", or "advanced"
    
    Returns:
        Evidence-based information about the training method
    """
    if not method_name:
        return {"status": "error", "error_message": "No training method specified"}
    
    results = {
        "method_name": method_name,
        "goal": goal,
        "experience_level": experience_level,
        "researched_at": datetime.now().isoformat()
    }
    
    # Search for method information
    if CUSTOM_SEARCH_AVAILABLE:
        overview_result = search_fitness_research(
            f"{method_name} training program explanation",
            focus_area="general"
        )
        if overview_result.get("status") == "success":
            results["method_overview"] = overview_result.get("summary", "")
            results["evidence_quality"] = overview_result.get("evidence_quality", "unknown")
        
        effectiveness_result = search_fitness_research(
            f"{method_name} effectiveness results study",
            focus_area="strength" if goal in ["strength", "hypertrophy"] else "general"
        )
        if effectiveness_result.get("status") == "success":
            results["effectiveness"] = effectiveness_result.get("summary", "")
        
        impl_query = f"{method_name} how to start implement {experience_level}"
        impl_result = web_search(impl_query, max_results=3, search_type="fitness")
        if impl_result.get("status") == "success":
            results["implementation"] = impl_result.get("summary", "")
    
    # Common training method templates
    method_templates = {
        "5/3/1": {
            "type": "Strength",
            "frequency": "3-4 days/week",
            "suitable_for": ["intermediate", "advanced"],
            "pros": ["Sustainable progression", "Flexible assistance work", "Built-in deload"],
            "cons": ["Slow progression for beginners", "Requires tracking"],
        },
        "ppl": {
            "type": "Hypertrophy/Strength",
            "frequency": "6 days/week",
            "suitable_for": ["intermediate", "advanced"],
            "pros": ["High frequency per muscle", "Balanced development"],
            "cons": ["Time commitment", "May be too much for beginners"],
        },
        "starting strength": {
            "type": "Strength (Beginner)",
            "frequency": "3 days/week",
            "suitable_for": ["beginner"],
            "pros": ["Simple", "Fast progression", "Compound focused"],
            "cons": ["Limited upper body volume", "Progression stalls quickly"],
        },
        "hiit": {
            "type": "Conditioning/Fat Loss",
            "frequency": "2-4 sessions/week",
            "suitable_for": ["beginner", "intermediate", "advanced"],
            "pros": ["Time efficient", "Improves conditioning", "Burns calories"],
            "cons": ["High recovery demand", "Not for building muscle"],
        },
    }
    
    # Check if we have a template
    method_lower = method_name.lower()
    for key, template in method_templates.items():
        if key in method_lower or method_lower in key:
            results["template_info"] = template
            results["pros_cons"] = {
                "pros": template.get("pros", []),
                "cons": template.get("cons", [])
            }
            results["suitable_for"] = template.get("suitable_for", [])
            break
    
    # Experience-based recommendations
    experience_notes = {
        "beginner": "Focus on learning proper form and building consistency. Simpler programs work best.",
        "intermediate": "You can handle more volume and complexity. Periodization becomes more important.",
        "advanced": "Specialized programming may be needed. Consider working with a coach."
    }
    results["experience_note"] = experience_notes.get(experience_level, experience_notes["intermediate"])
    
    results["status"] = "success"
    return results


# =============================================================================
# RESEARCH TOOL: Supplement Research
# =============================================================================
def research_supplement(
    supplement_name: str,
    purpose: Optional[str] = None
) -> Dict[str, Any]:
    """
    Research a supplement for evidence-based information.
    
    Args:
        supplement_name: Name of supplement (e.g., "creatine", "protein powder", "caffeine")
        purpose: Intended purpose (e.g., "muscle building", "performance", "recovery")
    
    Returns:
        Scientific evidence on effectiveness, dosing, and safety
    """
    if not supplement_name:
        return {"status": "error", "error_message": "No supplement specified"}
    
    results = {
        "supplement": supplement_name,
        "purpose": purpose,
        "researched_at": datetime.now().isoformat()
    }
    
    # Search for evidence
    if CUSTOM_SEARCH_AVAILABLE:
        evidence_result = search_fitness_research(
            f"{supplement_name} supplement research evidence effectiveness",
            focus_area="nutrition"
        )
        if evidence_result.get("status") == "success":
            results["evidence_summary"] = evidence_result.get("summary", "")
            results["evidence_quality"] = evidence_result.get("evidence_quality", "unknown")
            results["sources"] = evidence_result.get("findings", [])[:3]
        
        safety_query = f"{supplement_name} safety side effects dosage"
        safety_result = web_search(safety_query, max_results=2, search_type="medical")
        if safety_result.get("status") == "success":
            results["safety_info"] = safety_result.get("summary", "")
    
    # Known supplement database
    supplement_db = {
        "creatine": {
            "effectiveness": "Very High",
            "evidence": "Strong - One of the most researched supplements",
            "dose": "3-5g daily",
            "timing": "Any time, consistency matters more than timing",
            "safety": "Very safe for healthy individuals",
            "verdict": "✅ RECOMMENDED - Proven effective for strength and muscle"
        },
        "protein": {
            "effectiveness": "High",
            "evidence": "Strong - Essential for muscle building",
            "dose": "20-40g per serving, 1.6-2.2g/kg bodyweight daily",
            "timing": "Post-workout and throughout day",
            "safety": "Safe, whole foods preferred when possible",
            "verdict": "✅ RECOMMENDED if diet is lacking protein"
        },
        "caffeine": {
            "effectiveness": "High",
            "evidence": "Strong - Proven performance enhancer",
            "dose": "3-6mg/kg bodyweight, 30-60 min before exercise",
            "timing": "Pre-workout, avoid within 6 hours of sleep",
            "safety": "Safe in moderate doses",
            "verdict": "✅ RECOMMENDED for performance"
        },
        "beta-alanine": {
            "effectiveness": "Moderate",
            "evidence": "Good - Benefits for high-intensity endurance",
            "dose": "3-5g daily",
            "timing": "Any time, takes 2-4 weeks to build up",
            "safety": "Safe, may cause tingling (paresthesia)",
            "verdict": "⚠️ SITUATIONAL - Best for 1-4 min efforts"
        },
        "bcaa": {
            "effectiveness": "Low",
            "evidence": "Weak - Unnecessary if protein intake is adequate",
            "dose": "5-10g if used",
            "timing": "During fasted training only",
            "safety": "Safe but expensive",
            "verdict": "❌ NOT RECOMMENDED - Whole protein is better"
        },
        "vitamin d": {
            "effectiveness": "High (if deficient)",
            "evidence": "Strong for deficiency",
            "dose": "1000-5000 IU daily depending on blood levels",
            "timing": "With fat-containing meal",
            "safety": "Safe at recommended doses",
            "verdict": "✅ RECOMMENDED to test levels and supplement if low"
        },
        "fish oil": {
            "effectiveness": "Moderate",
            "evidence": "Good for health, mixed for performance",
            "dose": "2-3g EPA+DHA daily",
            "timing": "With meals",
            "safety": "Safe",
            "verdict": "⚠️ SITUATIONAL - Good for health"
        }
    }
    
    # Check database
    supp_lower = supplement_name.lower()
    for key, info in supplement_db.items():
        if key in supp_lower or supp_lower in key:
            results["database_info"] = info
            results["effectiveness_rating"] = info.get("effectiveness")
            results["recommended_dose"] = info.get("dose")
            results["verdict"] = info.get("verdict")
            break
    
    if "database_info" not in results:
        results["note"] = "Supplement not in database. Web search results provided."
    
    results["disclaimer"] = (
        "Supplements are not regulated like drugs. Quality varies by brand. "
        "Consult a healthcare provider before starting any supplement."
    )
    
    results["status"] = "success"
    return results


# =============================================================================
# CALLBACK: Log Research Activity
# =============================================================================
async def log_research_activity(callback_context) -> None:
    """Callback to log research agent activity."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"🔬 [{timestamp}] Research query completed")
    except Exception as e:
        print(f"⚠️ Research logging failed: {e}")


# =============================================================================
# CREATE RESEARCH AGENT
# =============================================================================
def create_research_agent(
    include_google_search: bool = True,
    include_custom_search: bool = True
) -> Optional[Any]:
    """
    Create the Research Agent with all research tools.
    
    Args:
        include_google_search: Include ADK's google_search tool
        include_custom_search: Include custom search tools
    
    Returns:
        LlmAgent configured for research tasks
    """
    if not ADK_AVAILABLE:
        print("❌ ADK not available. Cannot create research agent.")
        return None
    
    # Build tool list
    tools = [
        FunctionTool(func=research_injury_comprehensive),
        FunctionTool(func=research_training_method),
        FunctionTool(func=research_supplement),
    ]
    
    # Custom web search tools
    if include_custom_search and CUSTOM_SEARCH_AVAILABLE:
        tools.extend([
            FunctionTool(func=search_fitness_research),
            FunctionTool(func=search_injury_protocol),
            FunctionTool(func=search_exercise_info),
        ])
    
    # ADK Google Search (if available)
    if include_google_search and GOOGLE_SEARCH_AVAILABLE and google_search:
        tools.append(google_search)
    
    research_agent = LlmAgent(
        name="FitnessResearchAgent",
        model=Gemini(model="gemini-2.5-flash-lite", retry_options=get_retry_config()),
        description=(
            "Specialized research agent for fitness, training, nutrition, and injury topics. "
            "Provides evidence-based information from scientific sources."
        ),
        instruction="""You are an expert fitness research assistant providing 
accurate, evidence-based information on:

1. **Injuries & Pain**: Use research_injury_comprehensive
   - Always include the medical disclaimer
   - Recommend seeing a professional for serious issues
   
2. **Training Methods**: Use research_training_method
   - Consider the user's experience level
   - Explain pros and cons
   
3. **Supplements**: Use research_supplement
   - Focus on evidence-based recommendations
   - Be honest about what works and what doesn't

GUIDELINES:
- Ground answers in research, not opinion
- Acknowledge uncertainty when evidence is limited
- For medical topics, always recommend professional consultation
- Be specific with dosages, sets/reps, and protocols
- Explain the "why" behind recommendations""",
        tools=tools,
        after_agent_callback=log_research_activity,
        output_key="research_findings"
    )
    
    print(f"✅ Research Agent created with {len(tools)} tools")
    return research_agent


# =============================================================================
# GET RESEARCH AGENT AS TOOL
# =============================================================================
def get_research_agent_tool() -> Optional[Any]:
    """
    Get Research Agent wrapped as AgentTool for use by other agents.
    
    Returns:
        AgentTool wrapping the Research Agent
    """
    if not ADK_AVAILABLE:
        return None
    
    research_agent = create_research_agent()
    if research_agent:
        return AgentTool(agent=research_agent)
    return None


# =============================================================================
# QUICK RESEARCH (Direct use without runner)
# =============================================================================
async def quick_research(query: str, research_type: str = "general") -> Dict[str, Any]:
    """
    Quick research without setting up a full agent.
    
    Args:
        query: Research query
        research_type: "injury", "training", "supplement", or "general"
    
    Returns:
        Research results
    """
    if research_type == "injury":
        return research_injury_comprehensive(query)
    elif research_type == "training":
        return research_training_method(query)
    elif research_type == "supplement":
        return research_supplement(query)
    else:
        if CUSTOM_SEARCH_AVAILABLE:
            return search_fitness_research(query, focus_area="general")
        else:
            return {"status": "error", "error_message": "Search tools not available"}


# =============================================================================
# EXPORTS
# =============================================================================
__all__ = [
    # Agent creation
    "create_research_agent",
    "get_research_agent_tool",
    
    # Research tools
    "research_injury_comprehensive",
    "research_training_method",
    "research_supplement",
    
    # Utilities
    "quick_research",
    "log_research_activity",
    
    # Flags
    "ADK_AVAILABLE",
    "GOOGLE_SEARCH_AVAILABLE",
    "CUSTOM_SEARCH_AVAILABLE",
]