# agents/orchestrator.py
"""
FitForge AI — Ultimate Orchestrator (ADK Multi-Agent System)
==============================================================
The brain of FitForge AI - coordinates all agents for seamless user experience.
"""

import os
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

# =============================================================================
# ADK IMPORTS — Graceful Fallback
# =============================================================================
try:
    from google.adk.agents import Agent, LlmAgent
    from google.adk.tools import AgentTool, FunctionTool, load_memory, preload_memory
    from google.adk.tools.tool_context import ToolContext
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService, DatabaseSessionService
    from google.genai import types
    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    ToolContext = None

# =============================================================================
# LOCAL IMPORTS — Agents
# =============================================================================

# --- COACH AGENT (Crucial for Chat) ---
try:
    from agents.coach_agent import (
        create_coach_agent,
        get_fitness_status,
        get_workout_summary,
        get_motivation,
        log_coaching_note,
        handle_chat,  # <--- THE BRIDGE FUNCTION
        ADK_AVAILABLE as COACH_AVAILABLE
    )
    COACH_AGENT_READY = True
except ImportError:
    COACH_AGENT_READY = False
    # Fallback if handle_chat missing
    def handle_chat(msg, ctx=None): return "Coach agent offline."

try:
    from agents.analyzer_agent import (
        create_analyzer_agent,
        analyze_performance,
        get_readiness_quick,
        get_training_recommendations,
        get_consistency_report,
        log_workout_for_analysis,
        ADK_AVAILABLE as ANALYZER_AVAILABLE
    )
    ANALYZER_AGENT_READY = True
except ImportError:
    ANALYZER_AGENT_READY = False

try:
    from agents.extraction_agent import (
        create_extraction_agent,
        extract_from_text,
        process_user_comment,
        build_workout_record,
        ADK_AVAILABLE as EXTRACTION_AVAILABLE
    )
    EXTRACTION_AGENT_READY = True
except ImportError:
    EXTRACTION_AGENT_READY = False

try:
    from agents.planner_agent import (
        create_planner_agent,
        generate_training_plan,
        get_today_session,
        get_plan_summary,
        ADK_AVAILABLE as PLANNER_AVAILABLE
    )
    PLANNER_AGENT_READY = True
except ImportError:
    PLANNER_AGENT_READY = False

try:
    from agents.nutrition_agent import (
        create_nutrition_agent,
        log_meal,
        get_daily_nutrition_summary,
        suggest_next_meal,
        get_recovery_nutrition_score,
        ADK_AVAILABLE as NUTRITION_AVAILABLE
    )
    NUTRITION_AGENT_READY = True
except ImportError:
    NUTRITION_AGENT_READY = False

try:
    from agents.research_agent import (
        create_research_agent,
        get_research_agent_tool,
        research_injury_comprehensive,
        ADK_AVAILABLE as RESEARCH_AVAILABLE
    )
    RESEARCH_AGENT_READY = True
except ImportError:
    RESEARCH_AGENT_READY = False

# Memory Manager
try:
    from memory.session_manager import (
        FitForgeMemoryManager,
        APP_NAME
    )
    MEMORY_MANAGER_AVAILABLE = True
except ImportError:
    MEMORY_MANAGER_AVAILABLE = False
    APP_NAME = "fitforge_ai"

# =============================================================================
# CONFIGURATION
# =============================================================================
ORCHESTRATOR_CONFIG = {
    "app_name": APP_NAME,
    "default_model": "gemini-2.0-flash",
    "log_agent_thoughts": True,
}

# Intent categories
class UserIntent(Enum):
    GREETING = "greeting"
    LOG_WORKOUT = "log_workout"
    LOG_MEAL = "log_meal"
    CHECK_STATUS = "check_status"
    GET_PLAN = "get_plan"
    TODAY_SESSION = "today_session"
    INJURY_QUESTION = "injury_question"
    RESEARCH_QUESTION = "research_question"
    NUTRITION_QUESTION = "nutrition_question"
    MOTIVATION = "motivation"
    SETTINGS = "settings"
    HELP = "help"
    UNKNOWN = "unknown"

# Keywords for intent detection
INTENT_KEYWORDS = {
    UserIntent.GREETING: ["hello", "hi", "hey", "good morning", "coach"],
    UserIntent.LOG_WORKOUT: ["logged", "did", "completed", "finished", "ran", "lifted", "trained", "workout", "exercise", "gym", "miles", "km", "5k"],
    UserIntent.LOG_MEAL: ["ate", "had", "eating", "meal", "breakfast", "lunch", "dinner", "snack", "food", "calories", "protein", "drink"],
    UserIntent.CHECK_STATUS: ["how am i", "status", "readiness", "recovery", "fatigue", "how's my", "check", "doing"],
    UserIntent.GET_PLAN: ["plan", "schedule", "program", "week", "training plan", "workout plan", "create plan"],
    UserIntent.TODAY_SESSION: ["today", "what should i do", "today's workout", "what's on", "session today"],
    UserIntent.INJURY_QUESTION: ["injury", "pain", "hurt", "sore", "ache", "pulled", "strain", "sprain", "doctor", "knee", "back"],
    UserIntent.RESEARCH_QUESTION: ["research", "study", "evidence", "does", "work", "effective"],
    UserIntent.NUTRITION_QUESTION: ["macro", "protein", "carbs", "fat", "diet", "nutrition", "supplement", "eat"],
    UserIntent.MOTIVATION: ["motivate", "motivation", "tired", "don't feel like", "struggling", "unmotivated"],
    UserIntent.SETTINGS: ["settings", "profile", "update"],
    UserIntent.HELP: ["help", "how do i", "commands"],
}

# =============================================================================
# LEGACY COMPATIBILITY WRAPPER (Paste at bottom of agents/orchestrator.py)
# =============================================================================

class MockToolContext:
    """Mock Context for API usage."""
    def __init__(self):
        self.state = {}

class Orchestrator:
    """
    Legacy wrapper so api/app.py can use the new ADK logic.
    """
    def __init__(self, memory=None):
        self.memory = memory
        self._context = MockToolContext()
        
    def ingest(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapper for process_workout_input"""
        txt = payload.get("workout_text") or payload.get("user_comment", "")
        return process_workout_input(self._context, txt)

    def full_cycle(self, payload: Dict[str, Any], goal: str = "general_fitness") -> Dict[str, Any]:
        """Wrapper for run_full_cycle"""
        # Map API payload keys to function args
        w_txt = payload.get("workout_text") or payload.get("user_comment")
        n_txt = payload.get("nutrition_text")
        
        result = run_full_cycle(
            self._context, 
            workout_input=w_txt, 
            meal_input=n_txt, 
            goal=goal
        )
        
        # Ensure the API gets the keys it expects
        return {
            "success": True,
            "timestamp": result.get("timestamp"),
            "workout": result.get("workout", {}),
            "analysis": result.get("analysis", {}),
            "plan": result.get("plan", {}),
            "nutrition": result.get("nutrition", {}),
            "overall_message": result.get("overall_message", "")
        }

    def analyze(self, window_days=28):
        if ANALYZER_AGENT_READY:
            return analyze_performance(self._context, window_days)
        return {"error": "Analyzer offline"}

    def plan(self, goal="general_fitness"):
        if PLANNER_AGENT_READY:
            return generate_training_plan(self._context, goal)
        return {"error": "Planner offline"}



# =============================================================================
# INTENT DETECTION (FIXED LOGIC)
# =============================================================================
def detect_intent(message: str) -> Tuple[UserIntent, float]:
    """
    Detect user intent with Logic for Future vs Past tense.
    Fixes the "Suggest a run logs a workout" bug.
    """
    if not message:
        return UserIntent.UNKNOWN, 0.0
    
    message_lower = message.lower().strip()
    
    # --- 1. CHECK FOR REQUEST/PLANNING WORDS FIRST ---
    # If these exist, it is likely a Question or Plan, NOT a Log.
    request_keywords = ["suggest", "recommend", "create", "give me", "plan", "what should", "how to", "can you", "help"]
    is_request = any(req in message_lower for req in request_keywords)
    
    # --- 2. CALCULATE RAW SCORES ---
    scores = {}
    for intent, keywords in INTENT_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in message_lower)
        if matches > 0:
            scores[intent] = matches

    if not scores:
        if len(message.split()) > 2:
             return UserIntent.GREETING, 0.5 
        return UserIntent.UNKNOWN, 0.0
    
    # --- 3. APPLY LOGIC RULES ---
    
    # Rule A: If it's a "Request" (future tense), kill the LOG intents
    if is_request:
        scores.pop(UserIntent.LOG_WORKOUT, None)
        scores.pop(UserIntent.LOG_MEAL, None)
        
        if "eat" in message_lower or "food" in message_lower:
            scores[UserIntent.NUTRITION_QUESTION] = scores.get(UserIntent.NUTRITION_QUESTION, 0) + 5
        else:
            scores[UserIntent.GET_PLAN] = scores.get(UserIntent.GET_PLAN, 0) + 5

    # Rule B: Priority Overrule (If NOT a request, Workout/Meal > Greeting)
    elif scores.get(UserIntent.LOG_WORKOUT, 0) > 0:
        scores.pop(UserIntent.GREETING, None)
        scores.pop(UserIntent.GET_PLAN, None) # "I did the plan" is a log
        
    elif scores.get(UserIntent.LOG_MEAL, 0) > 0:
        scores.pop(UserIntent.GREETING, None)

    # --- 4. PICK WINNER ---
    if not scores:
        return UserIntent.GREETING, 0.5

    best_intent = max(scores, key=scores.get)
    
    # Confidence calculation
    raw_score = scores[best_intent]
    confidence = min(1.0, 0.4 + (raw_score * 0.3))
    
    return best_intent, confidence


# =============================================================================
# MAIN ROUTER (FIXED LOGIC)
# =============================================================================
def route_request(
    message: str,
    tool_context: Any = None
) -> Dict[str, Any]:
    """
    Main Orchestrator Function (formerly route_message).
    Routes the message AND executes the handler for chat interactions.
    """
    # 1. Detect Intent
    intent, confidence = detect_intent(message)
    print(f"🚦 Orchestrator: Detected '{intent.value}' ({confidence:.2f})")
    
    # Log thought
    if tool_context and hasattr(tool_context, 'state'):
        thoughts = tool_context.state.get("orchestrator:thoughts", [])
        thoughts.append({
            "timestamp": datetime.now().isoformat(),
            "message": message[:50],
            "intent": intent.value
        })
        tool_context.state["orchestrator:thoughts"] = thoughts[-10:]

    # 2. ROUTING LOGIC
    
    # --- ACTION: LOG WORKOUT ---
    if intent == UserIntent.LOG_WORKOUT:
        return {
            "action": "trigger_extraction",
            "reply": "I see you did a workout! Processing your data now... 🏃‍♂️",
            "intent": intent.value
        }

    # --- ACTION: LOG MEAL ---
    if intent == UserIntent.LOG_MEAL:
         return {
            "action": "trigger_nutrition",
            "reply": "Logging your meal... 🍎",
            "intent": intent.value
        }

    # --- ACTION: INJURY (Safety) ---
    if intent == UserIntent.INJURY_QUESTION:
        return {
            "reply": "⚠️ **Safety First:** Please consult a medical professional for any pain. "
                     "I can search for general recovery protocols, but I cannot diagnose injuries.",
            "intent": intent.value,
            "agent": "system"
        }

    # --- CHAT: ALL OTHER INTENTS (Coach, Planner, Analyzer) ---
    # This fixes the "Generic Help" bug. We pass everything else to the LLM Coach.
    # The Coach Agent has tools (get_plan, get_status) to handle these requests.
    
    try:
        # Use the Bridge Function to talk to Gemini
        reply = handle_chat(message, tool_context)
        
        return {
            "reply": reply,
            "intent": intent.value,
            "confidence": confidence,
            "agent": "coach"
        }
    except Exception as e:
        print(f"❌ Orchestrator Error: {e}")
        return {
            "reply": "I'm having trouble connecting to the Coach Agent right now. Try 'Log a run' or 'Check status'.",
            "intent": "error",
            "agent": "system"
        }

# Alias for backward compatibility
route_message = route_request

# =============================================================================
# WORKFLOW HELPERS (Kept from your original file)
# =============================================================================

def process_workout_input(
    tool_context: ToolContext,
    workout_description: str,
    additional_context: Optional[str] = None
) -> Dict[str, Any]:
    """Process and log a workout input through the full pipeline."""
    results = {"stage": "processing", "timestamp": datetime.now().isoformat()}
    
    # Extraction
    if EXTRACTION_AGENT_READY:
        extraction = extract_from_text(tool_context, workout_description)
        results["extraction"] = extraction
        
        # Add context
        if additional_context:
            process_user_comment(tool_context, additional_context)
            
        # Build Record
        extracted = tool_context.state.get("temp:current_extraction", {}) or {}
        context = tool_context.state.get("temp:current_context", {}) or {}
        
        record = build_workout_record(
            tool_context,
            workout_type=extracted.get("workout_type"),
            duration_minutes=extracted.get("duration_min"),
            distance_km=extracted.get("distance_km"),
            intensity=extracted.get("intensity"),
            sleep_hours=context.get("sleep_hours"),
            fatigue_level=context.get("fatigue_level"),
            notes=workout_description[:200]
        )
        results["workout_record"] = record
    
    # Analysis
    if ANALYZER_AGENT_READY:
        quick = get_readiness_quick(tool_context)
        results["quick_analysis"] = quick
    
    # Feedback
    results["feedback"] = _generate_workout_feedback(
        results.get("workout_record", {}),
        results.get("quick_analysis", {})
    )
    
    results["status"] = "success"
    return results

def _generate_workout_feedback(workout: Dict, analysis: Dict) -> str:
    readiness = analysis.get("readiness_score", 70)
    if readiness >= 85: return "💪 Excellent work! Peak form."
    if readiness >= 70: return "✅ Great consistency!"
    return "🧘 Good job. Focus on recovery now."

def run_full_cycle(
    tool_context: ToolContext,
    workout_input: Optional[str] = None,
    meal_input: Optional[str] = None,
    goal: str = "general_fitness"
) -> Dict[str, Any]:
    """Run complete cycle: Log -> Analyze -> Plan."""
    result = {"timestamp": datetime.now().isoformat()}
    
    if workout_input:
        result["workout"] = process_workout_input(tool_context, workout_input)
    
    if meal_input and NUTRITION_AGENT_READY:
        result["nutrition"] = log_meal(tool_context, meal_input)
    
    if ANALYZER_AGENT_READY:
        result["analysis"] = analyze_performance(tool_context, window_days=28)
    
    if PLANNER_AGENT_READY:
        result["plan"] = generate_training_plan(tool_context, goal=goal)
    
    # Overall Message
    msgs = []
    if result.get("workout", {}).get("status") == "success": msgs.append("✅ Workout logged")
    if result.get("nutrition", {}).get("status") == "success": msgs.append("🍽️ Meal logged")
    
    result["overall_message"] = " | ".join(msgs) if msgs else "Cycle complete"
    return result

def get_full_status(tool_context: ToolContext) -> Dict[str, Any]:
    """Get comprehensive status."""
    status = {}
    if ANALYZER_AGENT_READY:
        status["readiness"] = analyze_performance(tool_context, window_days=14)
    if PLANNER_AGENT_READY:
        status["training"] = get_plan_summary(tool_context)
    return status

def handle_injury_question(tool_context: ToolContext, description: str) -> Dict[str, Any]:
    """Handle injury questions."""
    return {
        "safety_warning": "Please consult a doctor for pain.",
        "recommendation": "Rest and ice are generally recommended for acute pain."
    }

def get_help_info(tool_context: ToolContext) -> Dict[str, Any]:
    """Return help info."""
    return {
        "features": ["Log Workout", "Check Status", "Get Plan"],
        "tips": ["Be consistent", "Log your sleep"]
    }

# =============================================================================
# ADK AGENT CREATION
# =============================================================================
def create_orchestrator_agent(include_sub_agents=True, use_memory_preload=True):
    if not ADK_AVAILABLE: return None
    
    tools = [route_request, process_workout_input, get_full_status, run_full_cycle, handle_injury_question]
    
    # Add direct tools
    if ANALYZER_AGENT_READY: tools.extend([analyze_performance, get_readiness_quick])
    if PLANNER_AGENT_READY: tools.extend([generate_training_plan, get_today_session])
    if COACH_AGENT_READY: tools.extend([get_motivation])

    orchestrator = Agent(
        name="fitforge_orchestrator",
        model="gemini-2.0-flash",
        description="Main orchestrator for FitForge AI.",
        instruction="You are the FitForge AI Orchestrator. Route requests and coordinate agents.",
        tools=tools
    )
    return orchestrator

def create_orchestrator_with_runner(persistent_memory=True):
    orchestrator = create_orchestrator_agent()
    if not orchestrator: return None, None, None
    
    from google.adk.sessions import InMemorySessionService
    runner = Runner(agent=orchestrator, session_service=InMemorySessionService())
    return orchestrator, runner, None

# =============================================================================
# EXPORTS
# =============================================================================
__all__ = [
    "create_orchestrator_agent",
    "route_request",
    "detect_intent",
    "process_workout_input",
    "run_full_cycle",
    "handle_chat",
    "UserIntent",
    "ORCHESTRATOR_CONFIG"
]
# Add Orchestrator to exports so the API can find it
__all__.append("Orchestrator")