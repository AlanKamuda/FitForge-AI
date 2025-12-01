
"""
FitForge AI — FastAPI Backend (Fixed & Cleaned)
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# IMPORTS — Agents & Memory
# =============================================================================
try:
    from memory.session_manager import FitForgeMemoryManager
    MEMORY_MANAGER = FitForgeMemoryManager(use_persistent_sessions=True)
    MEMORY_AVAILABLE = True
except ImportError as e:
    print(f"❌ Memory Manager Failed: {e}")
    MEMORY_AVAILABLE = False
    MEMORY_MANAGER = None

try:
    from agents.orchestrator import (
        route_message, run_full_cycle, detect_intent, UserIntent,
        ORCHESTRATOR_CONFIG
    )
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False
    
    # Define fallback UserIntent
    from enum import Enum
    class UserIntent(Enum):
        LOG_WORKOUT = "log_workout"
        LOG_MEAL = "log_meal"
        GET_PLAN = "get_plan"
        UNKNOWN = "unknown"
    
    def detect_intent(msg):
        return UserIntent.UNKNOWN, 0.0

try:
    from agents.analyzer_agent import analyze_performance, get_readiness_quick, get_consistency_report
    ANALYZER_READY = True
except ImportError:
    ANALYZER_READY = False

try:
    from agents.planner_agent import generate_training_plan, get_today_session, approve_current_plan
    PLANNER_READY = True
except ImportError:
    PLANNER_READY = False

try:
    from agents.nutrition_agent import (
        log_meal, get_daily_nutrition_summary, 
        get_macro_targets, get_recovery_nutrition_score
    )
    NUTRITION_READY = True
except ImportError:
    NUTRITION_READY = False

try:
    from agents.extraction_agent import extract_from_image, extract_from_text, build_workout_record
    EXTRACTION_READY = True
except ImportError:
    EXTRACTION_READY = False

try:
    from agents.coach_agent import get_motivation, get_fitness_status
    COACH_READY = True
except ImportError:
    COACH_READY = False

try:
    from agents.research_agent import (
        research_injury_comprehensive, 
        research_training_method, 
        research_supplement
    )
    RESEARCH_READY = True
except ImportError:
    RESEARCH_READY = False


# =============================================================================
# PYDANTIC MODELS
# =============================================================================
class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"


class ChatResponse(BaseModel):
    reply: str
    intent: Optional[str] = None
    confidence: Optional[float] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class WorkoutSubmitRequest(BaseModel):
    """JSON body for text-only workout submissions."""
    user_comment: str = ""
    csv_text: str = ""
    sleep_hours: str = "7"
    nutrition_text: str = ""
    goal: str = "general_fitness"
    user_id: str = "default"


class WorkoutSubmitResponse(BaseModel):
    success: bool
    workout: Dict[str, Any]
    analysis: Dict[str, Any]
    nutrition: Optional[Dict[str, Any]] = None
    plan: Optional[Dict[str, Any]] = None
    overall_message: str
    timestamp: str


class AnalysisResponse(BaseModel):
    status: str
    readiness_score: int
    readiness_label: str
    readiness_emoji: str
    ctl: float
    atl: float
    form: float
    risk_level: float
    consistency_percent: int
    recommendations: List[str]
    motivational_quote: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class PlanResponse(BaseModel):
    status: str
    focus: str
    goal: str
    training_plan: List[Dict[str, Any]]
    coach_explanation: Optional[str] = None
    motivational_message: str
    deload_recommended: bool = False
    requires_approval: bool = False
    approval_reasons: List[str] = []
    approved: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class NutritionLogRequest(BaseModel):
    meal_description: str
    meal_type: Optional[str] = None
    user_id: str = "default"


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    weight_kg: Optional[float] = None
    goal: Optional[str] = None
    user_id: str = "default"


class ProfileStatsResponse(BaseModel):
    total_workouts: int
    total_distance_km: float
    current_streak_days: int
    avg_weekly_workouts: float
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class HealthResponse(BaseModel):
    status: str
    system: str
    agents: Dict[str, bool]
    timestamp: str


# =============================================================================
# APP SETUP
# =============================================================================
app = FastAPI(
    title="FitForge AI API",
    version="2.2.0",
    description="Multi-Agent Fitness Assistant Backend"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
async def get_user_context(user_id: str):
    """Gets a persistent context backed by SQLite."""
    if MEMORY_AVAILABLE and MEMORY_MANAGER:
        return await MEMORY_MANAGER.get_tool_context(user_id)
    else:
        # Fallback Mock
        return type("MockCtx", (), {"state": {}})()


async def safe_save(ctx):
    """Safely save context without crashing request."""
    if MEMORY_AVAILABLE and MEMORY_MANAGER:
        try:
            await MEMORY_MANAGER.save_context(ctx)
        except Exception as e:
            print(f"⚠️ Save Context Warning: {e}")


def get_default_analysis() -> Dict[str, Any]:
    """Return default analysis when agents unavailable."""
    return {
        "status": "default",
        "readiness_score": 70,
        "readiness_label": "Ready",
        "readiness_emoji": "🟢",
        "ctl": 40,
        "atl": 35,
        "form": 5,
        "risk_level": 0.2,
        "consistency_percent": 60,
        "recommendations": ["Keep training consistently!"],
        "motivational_quote": "Every workout counts!"
    }


def get_default_plan(goal: str) -> Dict[str, Any]:
    """Return default plan when agents unavailable."""
    return {
        "status": "default",
        "week_focus": f"{goal.replace('_', ' ').title()} Focus",
        "weekly_plan": [],
        "motivational_message": "System offline, keep moving.",
        "requires_approval": False,
        "approved": True
    }


def generate_feedback_message(readiness: int, workout: dict) -> str:
    """Generate human-like feedback based on workout and readiness."""
    distance = workout.get("distance_km", 0)
    duration = workout.get("duration_min", 0)
    
    if readiness >= 85:
        messages = [
            "Sniper Mode Activated! 🎯 Perfect execution today.",
            "You're operating at peak performance! 💪",
            "Elite-level session! Your consistency is paying off."
        ]
    elif readiness >= 70:
        messages = [
            "Solid work! You're building momentum. 🚀",
            "Smart training today. Keep this rhythm going!",
            "Good session logged. You're on track! 🎯"
        ]
    elif readiness >= 50:
        messages = [
            "Workout logged! Listen to your body tomorrow. 🧘",
            "You showed up — that's what matters. Rest well tonight.",
            "Pushing through! Make sure to prioritize recovery."
        ]
    else:
        messages = [
            "Beast mode! But your body needs recovery now. 🛡️",
            "High effort detected. Schedule a rest day soon.",
            "Warrior session! Time to focus on sleep and nutrition."
        ]
    
    import random
    base_msg = random.choice(messages)
    
    # Add workout-specific details
    if distance and distance > 5:
        base_msg += f" Great distance: {distance}km!"
    elif duration and duration > 45:
        base_msg += f" Impressive {duration} minutes!"
    
    return base_msg


# =============================================================================
# CORE WORKOUT PROCESSING
# =============================================================================
async def process_workout_submission(
    user_comment: str,
    csv_text: str,
    sleep_hours: str,
    nutrition_text: str,
    goal: str,
    user_id: str,
    image_path: Optional[str] = None
) -> WorkoutSubmitResponse:
    """
    Core workout processing logic used by both JSON and Form endpoints.
    """
    print(f"\n{'='*50}")
    print(f"📥 WORKOUT SUBMISSION - User: {user_id}")
    print(f"   Comment: {user_comment[:50]}..." if user_comment else "   Comment: (none)")
    print(f"   CSV: {csv_text[:30]}..." if csv_text else "   CSV: (none)")
    print(f"   Image: {image_path}" if image_path else "   Image: (none)")
    print(f"{'='*50}")
    
    ctx = await get_user_context(user_id)
    
    # Store sleep context
    try:
        ctx.state["temp:sleep_hours"] = float(sleep_hours)
    except (ValueError, TypeError):
        ctx.state["temp:sleep_hours"] = 7.0

    workout_processed = False
    extracted_workout = None

    # =================================================================
    # STEP 1: EXTRACT WORKOUT DATA
    # =================================================================
    
    # Handle Image Upload
    if image_path and EXTRACTION_READY:
        try:
            print(f"📸 Processing image: {image_path}")
            res = extract_from_image(ctx, image_path)
            
            if res.get("status") == "success":
                workout_processed = True
                extracted_workout = res.get("workout_record", {})
                print("✅ Image extraction successful")
            else:
                print(f"⚠️ Image extraction failed: {res.get('error_message')}")
        except Exception as e:
            print(f"❌ Image error: {e}")

    # Handle Text Input (if no image or image failed)
    if (user_comment or csv_text) and not workout_processed:
        combined_input = f"{user_comment} {csv_text}".strip()
        
        if ORCHESTRATOR_AVAILABLE:
            print(f"📝 Processing text input: {combined_input[:50]}...")
            try:
                result = run_full_cycle(
                    ctx,
                    workout_input=combined_input,
                    meal_input=nutrition_text if nutrition_text else None,
                    goal=goal
                )
                workout_processed = True
                extracted_workout = result.get("workout", {})
                print("✅ Text processing successful")
            except Exception as e:
                print(f"⚠️ Orchestrator error: {e}")
        
        # Fallback: Manual extraction if orchestrator failed
        if not workout_processed and EXTRACTION_READY:
            print("📝 Using direct extraction agent...")
            try:
                res = extract_from_text(ctx, combined_input)
                if res.get("status") == "success":
                    workout_processed = True
                    extracted_workout = res.get("workout_record", {})
                    print("✅ Direct extraction successful")
            except Exception as e:
                print(f"⚠️ Direct extraction error: {e}")

    # Get the current workout from state or extracted data
    current_workout = ctx.state.get("temp:current_workout") or extracted_workout or {}
    
    # =================================================================
    # STEP 2: RUN ANALYZER
    # =================================================================
    analysis_result = get_default_analysis()
    
    if ANALYZER_READY and workout_processed:
        print("📊 Running performance analysis...")
        try:
            analysis_result = analyze_performance(ctx, window_days=28)
            print(f"✅ Analysis: Readiness = {analysis_result.get('readiness_score')}/100")
        except Exception as e:
            print(f"⚠️ Analysis error: {e}")
    
    # =================================================================
    # STEP 3: GENERATE HUMAN-LIKE FEEDBACK
    # =================================================================
    human_commentary = ""
    current_plan = ctx.state.get("app:current_plan", {})

    if COACH_READY and current_workout:
        print("💬 Generating Coach Feedback...")
        try:
            from agents.coach_agent import generate_post_workout_commentary
            
            coach_context = {
                "fatigue_level": analysis_result.get("fatigue_level", "moderate"),
                "sleep_hours": ctx.state.get("temp:sleep_hours", 7),
                "readiness_score": analysis_result.get("readiness_score", 70),
                "risk_level": analysis_result.get("risk_level", 0.3),
                "recommendations": analysis_result.get("recommendations", [])
            }
            
            human_commentary = await generate_post_workout_commentary(
                current_workout, 
                current_plan, 
                coach_context
            )
            print(f"💬 AI Feedback: {human_commentary[:50]}...")
            
        except Exception as e:
            print(f"⚠️ Coach feedback error: {e}")

    # Fallback to generated feedback
    if not human_commentary:
        readiness = analysis_result.get("readiness_score", 70)
        workout_details = current_workout.get("workout", current_workout)
        human_commentary = generate_feedback_message(readiness, workout_details)
        print(f"💬 Fallback Feedback: {human_commentary[:50]}...")

    # =================================================================
    # STEP 4: SAVE WORKOUT TO LOG
    # =================================================================
    if workout_processed and current_workout:
        # Enrich workout with metadata
        current_workout["coach_commentary"] = human_commentary
        current_workout["post_analysis"] = {
            "readiness_score": analysis_result.get("readiness_score"),
            "recommendations": analysis_result.get("recommendations", [])[:2]
        }
        current_workout["logged_at"] = datetime.now().isoformat()
        
        # Add to permanent log
        log = ctx.state.get("user:workout_log", [])
        log.append(current_workout)
        ctx.state["user:workout_log"] = log
        
        # Store as latest
        ctx.state["temp:current_workout"] = current_workout
        ctx.state["app:latest_analysis"] = analysis_result
        
        print(f"💾 Workout saved to log. Total workouts: {len(log)}")

    # =================================================================
    # STEP 5: SAVE & RETURN
    # =================================================================
    await safe_save(ctx)
    
    # Extract workout details for response
    workout_data = current_workout.get("workout", current_workout) if current_workout else {}
    
    return WorkoutSubmitResponse(
        success=workout_processed,
        workout=workout_data,
        analysis={
            "status": analysis_result.get("status", "success"),
            "readiness_score": analysis_result.get("readiness_score", 70),
            "readiness_label": analysis_result.get("readiness_label", "Ready"),
            "readiness_emoji": analysis_result.get("readiness_emoji", "🟢"),
            "risk_level": analysis_result.get("risk_level", 0.3),
            "recommendations": analysis_result.get("recommendations", []),
            "consistency_percent": analysis_result.get("consistency_percent", 50),
            "motivational_quote": analysis_result.get("motivational_quote", "Keep going!")
        },
        nutrition=None,
        plan=current_plan if current_plan else None,
        overall_message=human_commentary,
        timestamp=datetime.now().isoformat()
    )


# =============================================================================
# ENDPOINTS
# =============================================================================

# -----------------------------------------------------------------------------
# Health & Root
# -----------------------------------------------------------------------------
@app.get("/")
async def root():
    """Root endpoint for health checking."""
    return {
        "status": "online",
        "system": "FitForge AI",
        "version": "2.2.0",
        "docs": "/docs",
        "agents": {
            "orchestrator": ORCHESTRATOR_AVAILABLE,
            "analyzer": ANALYZER_READY,
            "planner": PLANNER_READY,
            "nutrition": NUTRITION_READY,
            "extraction": EXTRACTION_READY,
            "coach": COACH_READY,
            "research": RESEARCH_READY
        }
    }


@app.get("/api/v1/health")
async def api_health():
    """Detailed health check endpoint."""
    return {
        "status": "online",
        "agents": {
            "orchestrator": ORCHESTRATOR_AVAILABLE,
            "analyzer": ANALYZER_READY,
            "planner": PLANNER_READY,
            "nutrition": NUTRITION_READY,
            "extraction": EXTRACTION_READY,
            "coach": COACH_READY
        },
        "memory": MEMORY_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }


# -----------------------------------------------------------------------------
# Workout Submission (Dual Endpoint for JSON and Form)
# -----------------------------------------------------------------------------
@app.post("/api/v1/workout/submit", response_model=WorkoutSubmitResponse)
async def submit_workout_form(
    user_comment: str = Form(""),
    csv_text: str = Form(""),
    sleep_hours: str = Form("7"),
    nutrition_text: str = Form(""),
    screenshot: Optional[UploadFile] = File(None),
    goal: str = Form("general_fitness"),
    user_id: str = Form("default")
):
    """
    Submit workout via Form data (supports file uploads).
    Use this endpoint when uploading images.
    """
    image_path = None
    
    # Handle image upload
    if screenshot:
        try:
            suffix = os.path.splitext(screenshot.filename)[1] or ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                shutil.copyfileobj(screenshot.file, tmp)
                image_path = tmp.name
        except Exception as e:
            print(f"❌ File save error: {e}")
    
    try:
        result = await process_workout_submission(
            user_comment=user_comment,
            csv_text=csv_text,
            sleep_hours=sleep_hours,
            nutrition_text=nutrition_text,
            goal=goal,
            user_id=user_id,
            image_path=image_path
        )
        return result
    finally:
        # Cleanup temp file
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except:
                pass


@app.post("/api/v1/workout/submit/json", response_model=WorkoutSubmitResponse)
async def submit_workout_json(request: WorkoutSubmitRequest):
    """
    Submit workout via JSON body (text-only submissions).
    """
    return await process_workout_submission(
        user_comment=request.user_comment,
        csv_text=request.csv_text,
        sleep_hours=request.sleep_hours,
        nutrition_text=request.nutrition_text,
        goal=request.goal,
        user_id=request.user_id,
        image_path=None
    )


# -----------------------------------------------------------------------------
# Analysis
# -----------------------------------------------------------------------------
@app.get("/api/v1/trends/analysis", response_model=AnalysisResponse)
async def get_analysis(
    window_days: int = Query(28, ge=7, le=90),
    user_id: str = Query("default")
):
    """Get performance analysis and trends."""
    ctx = await get_user_context(user_id)
    
    if ANALYZER_READY:
        result = analyze_performance(ctx, window_days=window_days)
    else:
        result = get_default_analysis()
    
    return AnalysisResponse(
        status=result.get("status", "success"),
        readiness_score=result.get("readiness_score", 70),
        readiness_label=result.get("readiness_label", "Ready"),
        readiness_emoji=result.get("readiness_emoji", "🟢"),
        ctl=result.get("ctl", 40),
        atl=result.get("atl", 35),
        form=result.get("form", 5),
        risk_level=result.get("risk_level", 0.2),
        consistency_percent=result.get("consistency_percent", 60),
        recommendations=result.get("recommendations", []),
        motivational_quote=result.get("motivational_quote", "Keep going!")
    )


# -----------------------------------------------------------------------------
# Planner
# -----------------------------------------------------------------------------
@app.get("/api/v1/planner/active")
async def get_active_plan(user_id: str = Query("default")):
    """Get currently active training plan."""
    ctx = await get_user_context(user_id)
    plan = ctx.state.get("app:current_plan") or ctx.state.get("app:pending_plan")
    
    if plan:
        return {
            "status": "success",
            "found": True,
            "week_focus": plan.get("week_focus", "General"),
            "goal": plan.get("goal", "fitness"),
            "training_plan": plan.get("weekly_plan", []),
            "coach_explanation": plan.get("coach_explanation"),
            "motivational_message": plan.get("motivational_message", "Welcome back!"),
            "requires_approval": plan.get("requires_approval", False),
            "approved": plan.get("approved", True),
            "deload_recommended": False
        }
    
    return {"status": "no_plan", "found": False}


@app.get("/api/v1/planner/week-plan", response_model=PlanResponse)
async def get_week_plan(
    goal: str = Query("general_fitness"),
    custom_request: Optional[str] = Query(None),
    user_id: str = Query("default")
):
    """Generate a weekly training plan."""
    ctx = await get_user_context(user_id)
    
    print(f"\n📅 PLAN REQUEST: Goal='{goal}', Custom='{custom_request}'")
    
    try:
        if not PLANNER_READY:
            result = get_default_plan(goal)
        elif custom_request and len(custom_request) > 3:
            # Route to AI planner for custom requests
            print("👉 Routing to AI Planner")
            try:
                from agents.planner_agent import generate_plan_with_ai
                result = generate_plan_with_ai(ctx, goal, custom_request)
            except ImportError:
                print("⚠️ AI Planner not available, using template")
                result = generate_training_plan(ctx, goal=goal)
        else:
            # Use template planner
            print("👉 Routing to Template Planner")
            result = generate_training_plan(ctx, goal=goal)
        
        await safe_save(ctx)
        
        print(f"📤 Plan Generated: Requires Approval={result.get('requires_approval')}")

        return PlanResponse(
            status=result.get("status", "success"),
            focus=result.get("week_focus", "Fitness"),
            goal=goal,
            training_plan=result.get("weekly_plan", []),
            coach_explanation=result.get("coach_explanation"),
            motivational_message=result.get("motivational_message", "Let's go!"),
            requires_approval=result.get("requires_approval", False),
            approval_reasons=result.get("approval_reasons", []),
            approved=result.get("approved", False)
        )
        
    except Exception as e:
        print(f"❌ Plan Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/planner/approve")
async def approve_plan(user_id: str = Query("default")):
    """Approve a pending high-risk plan."""
    ctx = await get_user_context(user_id)
    
    if PLANNER_READY:
        res = approve_current_plan(ctx)
        await safe_save(ctx)
        return res
    
    return {"status": "approved", "message": "Plan approved"}


@app.get("/api/v1/planner/today")
async def get_today(user_id: str = Query("default")):
    """Get today's scheduled workout."""
    ctx = await get_user_context(user_id)
    
    if PLANNER_READY:
        return get_today_session(ctx)
    
    return {"status": "no_plan", "message": "No plan available"}


# -----------------------------------------------------------------------------
# Chat
# -----------------------------------------------------------------------------
@app.post("/api/v1/chat/ask", response_model=ChatResponse)
async def chat_ask(request: ChatRequest):
    """Chat with the AI coach."""
    user_id = request.user_id
    ctx = await get_user_context(user_id)
    message = request.message.strip()
    
    if not message:
        return ChatResponse(reply="Hi! How can I help you today?", intent="greeting", confidence=1.0)
    
    # Detect intent
    intent = UserIntent.UNKNOWN
    confidence = 0.0
    
    if ORCHESTRATOR_AVAILABLE:
        intent, confidence = detect_intent(message)
    
    reply = ""
    
    # Handle specific intents
    intent_handlers = {
        UserIntent.LOG_WORKOUT: "Please use the **Log** tab to record workouts.",
        UserIntent.LOG_MEAL: "Please use the **Nutrition** tab to log meals.",
        UserIntent.GET_PLAN: "Head to the **Plan** tab to generate your schedule."
    }
    
    if intent in intent_handlers:
        reply = intent_handlers[intent]
    else:
        # General conversation
        user_data = {
            "profile": {
                "name": ctx.state.get("user:name", "Athlete"),
                "goal": ctx.state.get("user:fitness_goal", "Fitness")
            },
            "analysis": ctx.state.get("app:latest_analysis", {})
        }
        
        if COACH_READY:
            try:
                from agents.coach_agent import chat_with_coach
                reply = await chat_with_coach(message, user_data, user_id)
            except Exception as e:
                print(f"⚠️ Coach error: {e}")
                reply = "I'm here to help! What would you like to know about your training?"
        else:
            reply = "FitForge Coach is currently in limited mode. Check back soon!"

    await safe_save(ctx)
    
    return ChatResponse(
        reply=reply,
        intent=intent.value if hasattr(intent, 'value') else str(intent),
        confidence=confidence
    )


# -----------------------------------------------------------------------------
# Nutrition
# -----------------------------------------------------------------------------
@app.post("/api/v1/nutrition/log")
async def log_nutrition(request: NutritionLogRequest):
    """Log a meal."""
    ctx = await get_user_context(request.user_id)
    
    if NUTRITION_READY:
        res = log_meal(ctx, request.meal_description, request.meal_type)
        await safe_save(ctx)
        return res
    
    return {
        "status": "success",
        "meal_type": request.meal_type or "meal",
        "message": "Meal logged (limited mode)",
        "macros": {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}
    }


@app.get("/api/v1/nutrition/summary")
async def get_nutrition_summary(user_id: str = Query("default")):
    """Get daily nutrition summary."""
    ctx = await get_user_context(user_id)
    
    if NUTRITION_READY:
        return get_daily_nutrition_summary(ctx)
    
    return {
        "status": "no_data",
        "totals": {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0},
        "progress": {}
    }


@app.get("/api/v1/nutrition/targets")
async def get_targets(
    weight_kg: float = Query(75, ge=30, le=200),
    goal: str = Query("maintenance"),
    user_id: str = Query("default")
):
    """Get personalized macro targets."""
    ctx = await get_user_context(user_id)
    
    ctx.state["user:weight_kg"] = weight_kg
    ctx.state["user:fitness_goal"] = goal
    await safe_save(ctx)
    
    if NUTRITION_READY:
        return get_macro_targets(ctx)
    
    # Calculate basic targets
    protein = int(weight_kg * 1.6)
    calories = int(weight_kg * 30)
    
    return {
        "daily_targets": {
            "calories": calories,
            "protein_g": protein,
            "carbs_g": int(calories * 0.4 / 4),
            "fat_g": int(calories * 0.25 / 9)
        }
    }


# -----------------------------------------------------------------------------
# Profile
# -----------------------------------------------------------------------------
@app.get("/api/v1/profile")
async def get_profile(user_id: str = Query("default")):
    """Get user profile."""
    ctx = await get_user_context(user_id)
    
    return {
        "name": ctx.state.get("user:name", "Athlete"),
        "weight_kg": ctx.state.get("user:weight_kg", 75),
        "goal": ctx.state.get("user:fitness_goal", "general_fitness")
    }


@app.post("/api/v1/profile/update")
async def update_profile(request: ProfileUpdateRequest):
    """Update user profile."""
    ctx = await get_user_context(request.user_id)
    
    if request.name:
        ctx.state["user:name"] = request.name
    if request.weight_kg:
        ctx.state["user:weight_kg"] = request.weight_kg
    if request.goal:
        ctx.state["user:fitness_goal"] = request.goal
    
    await safe_save(ctx)
    
    return {
        "status": "updated",
        "profile": {
            "name": ctx.state.get("user:name"),
            "weight_kg": ctx.state.get("user:weight_kg"),
            "goal": ctx.state.get("user:fitness_goal")
        }
    }


@app.get("/api/v1/profile/stats", response_model=ProfileStatsResponse)
async def get_profile_stats(user_id: str = Query("default")):
    """Get user workout statistics."""
    ctx = await get_user_context(user_id)
    
    workouts = ctx.state.get("user:workout_log", [])
    total_w = len(workouts)
    
    # Calculate total distance
    total_dist = 0.0
    dates = set()
    
    for w in workouts:
        # Handle both flat and nested workout structure
        details = w.get("workout", w)
        dist = details.get("distance_km") or details.get("distance") or 0
        
        try:
            total_dist += float(dist)
        except (ValueError, TypeError):
            pass
        
        # Collect dates for streak calculation
        date = w.get("date") or w.get("logged_at", "")[:10]
        if date:
            dates.add(date)

    # Simple streak calculation
    streak = min(len(dates), 7) if dates else 0
    
    return ProfileStatsResponse(
        total_workouts=total_w,
        total_distance_km=round(total_dist, 1),
        current_streak_days=streak,
        avg_weekly_workouts=max(1.0, total_w / max(1, len(dates) // 7 + 1))
    )


# -----------------------------------------------------------------------------
# Daily Summary
# -----------------------------------------------------------------------------
@app.get("/api/v1/daily/summary")
async def get_daily_summary(user_id: str = Query("default")):
    """Get a holistic AI summary of the day."""
    ctx = await get_user_context(user_id)
    
    todays_date = datetime.now().strftime("%Y-%m-%d")
    
    # Get today's workouts
    all_workouts = ctx.state.get("user:workout_log", [])
    todays_workouts = [
        w for w in all_workouts 
        if w.get("date") == todays_date or 
           (w.get("logged_at", "")[:10] == todays_date)
    ]
    
    # Get today's nutrition
    nutrition_log = ctx.state.get(f"nutrition:{todays_date}", {})
    nutrition_totals = {
        "calories": nutrition_log.get("total_calories", 0),
        "protein_g": nutrition_log.get("total_protein_g", 0)
    }
    
    # Build context
    user_context = {
        "profile": {
            "name": ctx.state.get("user:name", "Athlete")
        },
        "analysis": ctx.state.get("app:latest_analysis", {}),
        "nutrition": {"totals": nutrition_totals},
        "workouts": todays_workouts,
        "sleep": ctx.state.get("temp:sleep_hours", 7.5)
    }
    
    if COACH_READY:
        try:
            from agents.coach_agent import generate_daily_summary
            summary = await generate_daily_summary(user_context)
            return {"status": "success", "summary": summary}
        except Exception as e:
            print(f"⚠️ Summary error: {e}")
    
    # Fallback summary
    workout_count = len(todays_workouts)
    summary = f"Today: {workout_count} workout(s) logged. "
    
    if nutrition_totals["calories"] > 0:
        summary += f"Nutrition: {nutrition_totals['calories']} calories, {nutrition_totals['protein_g']}g protein. "
    
    summary += "Keep up the great work!"
    
    return {"status": "success", "summary": summary}


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("🚀 FITFORGE AI API v2.2.0")
    print("=" * 50)
    print(f"📊 Agents Status:")
    print(f"   • Orchestrator: {'✅' if ORCHESTRATOR_AVAILABLE else '❌'}")
    print(f"   • Analyzer:     {'✅' if ANALYZER_READY else '❌'}")
    print(f"   • Planner:      {'✅' if PLANNER_READY else '❌'}")
    print(f"   • Nutrition:    {'✅' if NUTRITION_READY else '❌'}")
    print(f"   • Extraction:   {'✅' if EXTRACTION_READY else '❌'}")
    print(f"   • Coach:        {'✅' if COACH_READY else '❌'}")
    print(f"   • Memory:       {'✅' if MEMORY_AVAILABLE else '❌'}")
    print("=" * 50)
    print("🔗 API Docs: http://localhost:8000/docs")
    print("=" * 50 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)