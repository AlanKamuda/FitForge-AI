
"""
FitForge AI — Coach Agent (ADK Conversational Agent)
=====================================================
A fitness coaching agent with full memory integration.
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime

# =============================================================================
# ADK IMPORTS
# =============================================================================
ADK_AVAILABLE = False
Runner = None
InMemoryRunner = None
InMemorySessionService = None
InMemoryMemoryService = None

try:
    from google.adk.agents import LlmAgent
    from google.adk.models.google_llm import Gemini
    from google.adk.tools import load_memory, preload_memory, FunctionTool
    from google.adk.tools.tool_context import ToolContext
    from google.adk.runners import Runner, InMemoryRunner
    from google.adk.sessions import InMemorySessionService
    from google.adk.memory import InMemoryMemoryService
    from google.genai import types

    ADK_AVAILABLE = True
    print("✅ Coach Agent: ADK components ready")
except ImportError as e:
    print(f"⚠️ Coach Agent: ADK not available: {e}")

# Import memory manager
MEMORY_MANAGER_AVAILABLE = False
try:
    from memory.session_manager import (
        FitForgeMemoryManager,
        get_user_profile,
        save_user_profile,
        get_latest_analysis,
        auto_save_to_memory,
        MEMORY_TOOLS
    )
    MEMORY_MANAGER_AVAILABLE = True
except ImportError:
    print("⚠️ Coach Agent: Memory manager not available")

# Import research agent for delegation
RESEARCH_AGENT_AVAILABLE = False
try:
    from agents.research_agent import get_research_agent_tool
    RESEARCH_AGENT_AVAILABLE = True
except ImportError:
    pass


# =============================================================================
# GLOBAL SESSION & MEMORY SERVICES (Singleton Pattern)
# =============================================================================
class SessionManager:
    """
    Manages a single shared session service for the entire application.
    This ensures sessions persist across multiple chat requests.
    """
    _instance = None
    _session_service = None
    _memory_service = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not SessionManager._initialized and ADK_AVAILABLE:
            SessionManager._session_service = InMemorySessionService()
            SessionManager._memory_service = InMemoryMemoryService()
            SessionManager._initialized = True
            print("✅ Session Manager initialized")
    
    @property
    def session_service(self):
        return SessionManager._session_service
    
    @property
    def memory_service(self):
        return SessionManager._memory_service
    
    async def get_or_create_session(
        self, 
        user_id: str, 
        app_name: str = "fitforge",
        initial_state: Optional[Dict] = None
    ):
        """Get existing session or create a new one."""
        if not self.session_service:
            return None
            
        session_id = f"session_{user_id}"
        
        try:
            # Try to get existing session
            session = await self.session_service.get_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id
            )
            
            if session:
                # Update state with new data if provided
                if initial_state:
                    for key, value in initial_state.items():
                        session.state[key] = value
                print(f"📂 Retrieved existing session: {session_id}")
                return session
                
        except Exception as e:
            print(f"⚠️ Could not retrieve session: {e}")
        
        # Create new session
        try:
            session = await self.session_service.create_session(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                state=initial_state or {}
            )
            print(f"✨ Created new session: {session_id}")
            return session
        except Exception as e:
            print(f"❌ Failed to create session: {e}")
            return None


# Global session manager instance
_session_manager = SessionManager()


# =============================================================================
# RETRY CONFIGURATION
# =============================================================================
def get_retry_config():
    """Get standard retry configuration."""
    if not ADK_AVAILABLE:
        return None
    return types.HttpRetryOptions(
        attempts=5,
        exp_base=7,
        initial_delay=1,
        http_status_codes=[429, 500, 503, 504],
    )


# =============================================================================
# SAFE EVENT TEXT EXTRACTION (THE KEY FIX!)
# =============================================================================
def extract_text_from_event(event) -> Optional[str]:
    """
    Safely extract text content from an ADK event.
    Handles function calls, empty events, and various response formats.
    
    Args:
        event: An ADK runner event
        
    Returns:
        Extracted text or None
    """
    try:
        # Method 1: Direct text attribute
        if hasattr(event, 'text') and event.text:
            return event.text
        
        # Method 2: Check for model_response first
        if hasattr(event, 'model_response') and event.model_response:
            if hasattr(event.model_response, 'text') and event.model_response.text:
                return event.model_response.text
        
        # Method 3: content.parts - with careful null checking
        if not hasattr(event, 'content'):
            return None
            
        content = event.content
        if content is None:
            return None
            
        if not hasattr(content, 'parts'):
            return None
            
        parts = content.parts
        if parts is None:
            return None
        
        # Extract text from parts, skipping function calls
        text_parts = []
        for part in parts:
            # Skip None parts
            if part is None:
                continue
            
            # Skip function call parts
            if hasattr(part, 'function_call') and part.function_call:
                continue
            
            # Skip function response parts
            if hasattr(part, 'function_response') and part.function_response:
                continue
            
            # Extract text
            if hasattr(part, 'text') and part.text:
                text = part.text.strip()
                if text:
                    text_parts.append(text)
        
        if text_parts:
            return " ".join(text_parts)
        
        return None
        
    except Exception as e:
        print(f"⚠️ Event extraction warning: {e}")
        return None


def is_final_text_response(event) -> bool:
    """Check if this event is the final text response (not a tool call)."""
    try:
        # Check for is_final_response method/property
        if hasattr(event, 'is_final_response'):
            if callable(event.is_final_response):
                return event.is_final_response()
            else:
                return bool(event.is_final_response)
        
        # Check author - tool responses have author like "tool:function_name"
        if hasattr(event, 'author') and event.author:
            author = str(event.author)
            if author.startswith('tool:'):
                return False
            if 'function' in author.lower():
                return False
        
        # Check if content has only function parts (not final)
        if hasattr(event, 'content') and event.content:
            if hasattr(event.content, 'parts') and event.content.parts:
                has_text = False
                for part in event.content.parts:
                    if part and hasattr(part, 'text') and part.text:
                        has_text = True
                        break
                return has_text
        
        return False
    except:
        return False


# =============================================================================
# COACH TOOLS: Get Current Fitness Status
# =============================================================================
def get_fitness_status(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get the user's current fitness status and readiness.
    
    Retrieves the latest analysis data from session state, including
    readiness score, fatigue levels, and training recommendations.
    """
    if not hasattr(tool_context, 'state'):
        return {"status": "error", "error_message": "Session state unavailable"}
    
    analysis = tool_context.state.get("app:latest_analysis")
    
    if analysis:
        return {
            "status": "success",
            "readiness_score": analysis.get("readiness_score", 75),
            "readiness_label": _get_readiness_label(analysis.get("readiness_score", 75)),
            "fatigue_level": analysis.get("fatigue_level", "moderate"),
            "fitness_level": analysis.get("ctl", 50),
            "acute_load": analysis.get("atl", 50),
            "form": analysis.get("form", 0),
            "risk_factors": analysis.get("risk_factors", []),
            "recommendations": analysis.get("recommendations", []),
            "last_updated": analysis.get("analyzed_at", "Unknown")
        }
    else:
        return {
            "status": "no_data",
            "message": "No workout data analyzed yet. Log some workouts first!",
            "readiness_score": None,
            "recommendations": [
                "Log your first workout to get personalized insights",
                "Tell me about your fitness goals so I can help you better"
            ]
        }


def _get_readiness_label(score: int) -> str:
    """Convert readiness score to human-readable label."""
    if score >= 90:
        return "🟢 Peak Performance"
    elif score >= 75:
        return "🟢 Ready to Train Hard"
    elif score >= 60:
        return "🟡 Moderate - Train Smart"
    elif score >= 40:
        return "🟠 Fatigued - Consider Recovery"
    else:
        return "🔴 Rest Recommended"


# =============================================================================
# COACH TOOLS: Get Workout History Summary
# =============================================================================
def get_workout_summary(
    tool_context: ToolContext,
    days: int = 7
) -> Dict[str, Any]:
    """Get a summary of recent workouts from session state."""
    if not hasattr(tool_context, 'state'):
        return {"status": "error", "error_message": "Session state unavailable"}
    
    # Check both possible locations for workout history
    history = tool_context.state.get("user:workout_log", [])
    if not history:
        history = tool_context.state.get("temp:workout_history", [])
    
    if not history:
        return {
            "status": "no_data",
            "message": "No workouts logged yet.",
            "total_workouts": 0,
            "suggestions": [
                "Log a workout to start tracking",
                "Tell me about your last training session"
            ]
        }
    
    total_duration = sum(w.get("duration", 0) for w in history)
    workout_types = list(set(w.get("type", "unknown") for w in history))
    last_workout = history[-1] if history else None
    
    return {
        "status": "success",
        "total_workouts": len(history),
        "total_duration_min": total_duration,
        "workout_types": workout_types,
        "last_workout": last_workout,
        "period_days": days,
        "retrieved_at": datetime.now().isoformat()
    }


# =============================================================================
# COACH TOOLS: Provide Motivation
# =============================================================================
def get_motivation(
    tool_context: ToolContext,
    context: str = "general"
) -> Dict[str, Any]:
    """Get personalized motivational message based on user's status."""
    user_name = "Champion"
    fitness_goal = "general fitness"
    
    if hasattr(tool_context, 'state'):
        user_name = tool_context.state.get("user:name", "Champion")
        fitness_goal = tool_context.state.get("user:fitness_goal", "general fitness")
    
    status = get_fitness_status(tool_context)
    readiness = status.get("readiness_score", 75)
    
    # Context-based motivation
    if readiness and readiness >= 60:
        message = f"You're in great shape, {user_name}! Your readiness is {readiness}/100 - let's make today count! 💪"
    else:
        message = f"Recovery is training too, {user_name}. Your body is adapting. Trust the process."
    
    tips = {
        "strength": "Focus on progressive overload - add weight or reps when you can.",
        "muscle building": "Prioritize protein intake and sleep for optimal gains.",
        "fat loss": "Consistency with nutrition matters more than perfection.",
        "endurance": "Build your base with easy miles before adding intensity.",
        "general fitness": "Variety keeps things interesting - try something new this week!",
    }
    
    tip = tips.get(fitness_goal.lower(), tips["general fitness"])
    
    return {
        "status": "success",
        "message": message,
        "tip": tip,
        "context": context,
        "personalized_for": user_name,
        "readiness_aware": True
    }


# =============================================================================
# COACH TOOLS: Log Quick Note
# =============================================================================
def log_coaching_note(
    tool_context: ToolContext,
    note: str,
    category: str = "general"
) -> Dict[str, Any]:
    """Log a coaching note or observation about the user."""
    if not hasattr(tool_context, 'state'):
        return {"status": "error", "error_message": "Session state unavailable"}
    
    notes = tool_context.state.get("coach:notes", [])
    
    new_note = {
        "note": note,
        "category": category,
        "logged_at": datetime.now().isoformat()
    }
    notes.append(new_note)
    
    tool_context.state["coach:notes"] = notes
    
    if category == "goal":
        tool_context.state["user:stated_goal"] = note
    elif category == "limitation":
        existing_limitations = tool_context.state.get("user:limitations", [])
        existing_limitations.append(note)
        tool_context.state["user:limitations"] = existing_limitations
    
    return {
        "status": "success",
        "message": f"Noted! I'll remember: {note[:50]}...",
        "category": category,
        "total_notes": len(notes)
    }


# =============================================================================
# CALLBACK: Log Coaching Interaction
# =============================================================================
async def log_coaching_interaction(callback_context) -> None:
    """Callback to log coaching interactions and auto-save to memory."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"🏋️ [{timestamp}] Coach interaction completed")
    except Exception as e:
        print(f"⚠️ Coaching callback error: {e}")


# =============================================================================
# CREATE COACH AGENT
# =============================================================================
def create_coach_agent(
    use_memory_preload: bool = False,
    include_research: bool = True
) -> Optional[Any]:
    """Create the FitForge Coach Agent."""
    if not ADK_AVAILABLE:
        print("❌ ADK not available. Cannot create coach agent.")
        return None
    
    # Build tool list
    tools = [
        FunctionTool(func=get_fitness_status),
        FunctionTool(func=get_workout_summary),
        FunctionTool(func=get_motivation),
        FunctionTool(func=log_coaching_note),
    ]
    
    # Memory tools from session manager
    if MEMORY_MANAGER_AVAILABLE:
        tools.extend([
            FunctionTool(func=get_user_profile),
            FunctionTool(func=save_user_profile),
            FunctionTool(func=get_latest_analysis),
        ])
    
    # Add memory search tool
    if use_memory_preload:
        tools.append(preload_memory)
    else:
        tools.append(load_memory)
    
    # Add research agent for complex queries
    if include_research and RESEARCH_AGENT_AVAILABLE:
        try:
            research_tool = get_research_agent_tool()
            if research_tool:
                tools.append(research_tool)
        except Exception as e:
            print(f"⚠️ Research agent not added: {e}")
    
    # Create the agent
    coach_agent = LlmAgent(
        name="FitForgeCoach",
        model=Gemini(model="gemini-2.5-flash-lite", retry_options=get_retry_config()),
        description=(
            "Elite fitness coach providing personalized training advice, motivation, "
            "and support. Remembers user preferences and adapts to their fitness journey."
        ),
        instruction="""You are FitForge AI, an elite human performance coach with deep expertise in:
- Strength training and muscle building
- Endurance and cardiovascular fitness
- Recovery and injury prevention
- Sports nutrition
- Mental performance and motivation

## YOUR PERSONALITY
- Supportive but honest - you encourage while keeping it real
- Knowledgeable but accessible - explain things clearly without jargon
- Motivating but not pushy - understand when rest is needed
- Professional but warm - build genuine rapport with users

## CONVERSATION GUIDELINES

### Starting Conversations
- Greet returning users warmly and reference past context if available
- For new users, ask about their fitness goals and experience level
- Use get_user_profile to check if you already know them

### Answering Questions
1. **First**, check the user's current status with get_fitness_status
2. **Consider** their readiness when giving training advice
3. **Use** load_memory to recall relevant past conversations
4. **Delegate** complex research (injuries, protocols) to FitnessResearchAgent

### Giving Advice
- Tailor recommendations to their readiness score
- If readiness is LOW (<60): Suggest recovery, lighter work, rest
- If readiness is HIGH (>75): They're ready for challenging sessions
- Always explain the "why" behind your recommendations

### Important Information to Note
When users share important info, use log_coaching_note to remember:
- Goals and aspirations → category="goal"
- Preferences (time, equipment, style) → category="preference"  
- Injuries or limitations → category="limitation"
- Achievements and PRs → category="achievement"

## RESPONSE STYLE
- Keep responses concise (2-4 sentences) unless detail is requested
- Use emojis sparingly but effectively 💪🏃‍♂️🎯
- End with a clear next step or question when appropriate
- Match the user's energy - casual if they're casual, focused if they're serious
""",
        tools=tools,
        after_agent_callback=log_coaching_interaction,
        output_key="coach_response"
    )
    
    return coach_agent


# =============================================================================
# MAIN CHAT FUNCTION (FIXED!)
# =============================================================================
async def chat_with_coach(
    message: str, 
    user_context: Dict[str, Any], 
    user_id: str = "default"
) -> str:
    """
    Main chat handler with proper session management and safe event extraction.
    
    Args:
        message: User's message
        user_context: Dict with 'profile' and 'analysis' data
        user_id: Unique user identifier
    
    Returns:
        Coach's response string
    """
    if not ADK_AVAILABLE:
        return "Coach is offline (ADK not available)."

    agent = create_coach_agent(use_memory_preload=False)
    if not agent:
        return "Coach initialization failed."

    profile = user_context.get("profile", {})
    analysis = user_context.get("analysis", {})
    name = profile.get("name", "Athlete")
    goal = profile.get("goal", "general fitness")
    readiness = analysis.get("readiness_score", "unknown")
    
    initial_state = {
        "app:latest_analysis": analysis,
        "user:name": name,
        "user:fitness_goal": goal
    }

    try:
        session = await _session_manager.get_or_create_session(
            user_id=user_id,
            app_name="fitforge",
            initial_state=initial_state
        )
        
        if not session:
            return "Could not initialize session. Please try again."
        
        runner = Runner(
            agent=agent,
            app_name="fitforge",
            session_service=_session_manager.session_service,
            memory_service=_session_manager.memory_service
        )
        
        system_context = f"Context: Talking to {name}, readiness {readiness}/100, goal: {goal}."
        content = types.Content(
            role="user", 
            parts=[types.Part.from_text(text=f"{system_context}\n\nUser: {message}")]
        )

        # Collect all events
        all_events = []
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content
        ):
            all_events.append(event)
        
        # ✅ FIXED: Process events with safe extraction
        response_texts = []
        for event in all_events:
            text = extract_text_from_event(event)
            if text:
                response_texts.append(text)
        
        # Deduplicate while preserving order
        seen = set()
        unique_texts = []
        for text in response_texts:
            # Normalize for comparison
            normalized = text.strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_texts.append(normalized)
        
        # Join and clean
        final_answer = " ".join(unique_texts).strip()
        final_answer = " ".join(final_answer.split())  # Normalize whitespace
        
        if final_answer:
            return final_answer
        else:
            return "I'm here to help! What would you like to know about your training?"

    except Exception as e:
        print(f"❌ Chat Logic Error: {e}")
        import traceback
        traceback.print_exc()
        return "I'm having a little trouble right now, but I'm here! What's on your mind?"


# =============================================================================
# QUICK CHAT FOR TESTING
# =============================================================================
async def quick_chat(message: str, session_id: str = "test_session") -> str:
    """Quick chat with the coach for testing."""
    return await chat_with_coach(
        message=message,
        user_context={"profile": {"name": "Tester"}, "analysis": {}},
        user_id="test_user"
    )


def handle_chat(message: str, tool_context: Any = None) -> str:
    """
    Synchronous wrapper for the Coach.
    Used by the Orchestrator when no specific intent is found.
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in async context, create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, quick_chat(message))
                return future.result(timeout=30)
        else:
            return asyncio.run(quick_chat(message))
    except Exception as e:
        print(f"Coach Error: {e}")
        return f"I'm here to help, but I'm having trouble right now. (Error: {str(e)[:50]})"


async def generate_post_workout_commentary(
    workout: Dict, 
    plan: Dict, 
    context: Dict
) -> str:
    """Generate human-like post-workout feedback using direct Gemini API."""
    
    # Extract workout details
    workout_details = workout.get("workout", workout)
    workout_type = workout_details.get("type", "workout")
    duration = workout_details.get("duration", 0)
    intensity = workout_details.get("intensity", "moderate")
    
    # Extract context
    readiness = context.get("readiness_score", 70)
    fatigue = context.get("fatigue_level", "moderate")
    sleep = context.get("sleep_hours", 7)
    
    # Find planned session
    today_name = datetime.now().strftime("%A")
    planned_session = "Rest Day"
    for s in plan.get("weekly_plan", []):
        if s.get("day") == today_name:
            planned_session = f"{s.get('name')} ({s.get('duration_min')}m)"
            break

    # Try direct Gemini API (no session needed)
    try:
        import os
        from google import genai
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return _generate_fallback_commentary(workout_type, duration, readiness)
        
        client = genai.Client(api_key=api_key)
        
        prompt = f"""You are an elite fitness coach giving brief post-workout feedback.

WORKOUT: {workout_type}, {duration} min, {intensity} intensity
CONTEXT: Readiness {readiness}/100, Fatigue {fatigue}, Sleep {sleep}h
PLANNED: {planned_session}

Write 2 sentences: acknowledge the workout, give one recovery tip.
Use 1-2 emojis. Be encouraging and specific."""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt]
        )
        
        if response and hasattr(response, 'text') and response.text:
            return response.text.strip()
        else:
            return _generate_fallback_commentary(workout_type, duration, readiness)
            
    except Exception as e:
        print(f"⚠️ Commentary generation error: {e}")
        return _generate_fallback_commentary(workout_type, duration, readiness)


def _generate_fallback_commentary(workout_type: str, duration: int, readiness: int) -> str:
    """Fallback when Gemini unavailable."""
    if readiness >= 75:
        return f"💪 Great {workout_type}! {duration} minutes of solid work. Keep the momentum going!"
    elif readiness >= 50:
        return f"✅ Good work on that {workout_type}! Consider extra recovery tonight."
    else:
        return f"🧘 {workout_type.title()} logged! Rest up - your body needs recovery."

async def generate_daily_summary(user_context: Dict[str, Any]) -> str:
    """Generate daily summary using direct Gemini API."""
    
    profile = user_context.get("profile", {})
    analysis = user_context.get("analysis", {})
    nutrition = user_context.get("nutrition", {})
    workouts = user_context.get("workouts", [])
    
    name = profile.get("name", "Athlete")
    readiness = analysis.get("readiness_score", "Unknown")
    
    # Format workout
    workout_text = "Rest Day"
    if workouts:
        w = workouts[-1]
        workout_details = w.get("workout", w)
        workout_text = f"{workout_details.get('type')} ({workout_details.get('duration')} min)"

    # Format nutrition
    nutrition_text = "No meals logged"
    if nutrition.get("totals"):
        t = nutrition["totals"]
        nutrition_text = f"{t.get('calories')} kcal | {t.get('protein_g')}g Protein"

    try:
        import os
        from google import genai
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return f"Great work today, {name}! Keep focusing on recovery."
        
        client = genai.Client(api_key=api_key)
        
        prompt = f"""You are a supportive fitness coach.
Write a 3-sentence daily summary for {name}:
1. Acknowledge training: {workout_text}
2. Comment on nutrition: {nutrition_text}  
3. One tip for tomorrow based on readiness {readiness}/100

Be encouraging and specific."""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt]
        )
        
        if response and hasattr(response, 'text') and response.text:
            return response.text.strip()
        else:
            return f"Great work today, {name}! Keep focusing on recovery."
            
    except Exception as e:
        print(f"Summary Error: {e}")
        return f"Great work today, {name}! Keep focusing on recovery."

# =============================================================================
# EXPORTS
# =============================================================================
__all__ = [
    # Main agent creation
    "create_coach_agent",
    
    # Chat functions
    "chat_with_coach",
    "quick_chat",
    "handle_chat",
    
    # Coach tools
    "get_fitness_status",
    "get_workout_summary",
    "get_motivation",
    "log_coaching_note",
    
    # Generation functions
    "generate_post_workout_commentary",
    "generate_daily_summary",
    
    # Utilities
    "extract_text_from_event",
    "is_final_text_response",
    
    # Callbacks
    "log_coaching_interaction",

    # Availability flags
    "ADK_AVAILABLE",
    "MEMORY_MANAGER_AVAILABLE",
    "RESEARCH_AGENT_AVAILABLE",
]