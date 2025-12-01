"""
FitForge AI — Planner Agent (with Trap)
===================================================
- Standard Path: Uses Templates (Safe, Auto-Approved)
- Custom Path: Uses Gemini AI (Creative, May Need Approval)
- Demo Trap: Trigger words force human-in-the-loop approval
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import uuid

# =============================================================================
# ADK IMPORTS
# =============================================================================
ADK_AVAILABLE = False
try:
    from google.adk.agents import Agent, LlmAgent
    from google.adk.tools import FunctionTool, load_memory
    from google.adk.tools.tool_context import ToolContext
    from google.adk.runners import Runner
    from google.genai import types as adk_types
    ADK_AVAILABLE = True
except ImportError:
    ToolContext = Any  # Fallback type

# Local Tools
APPROVAL_READY = False
try:
    from tools.plan_approval import assess_plan_risk, APPROVAL_THRESHOLDS
    APPROVAL_READY = True
except ImportError:
    pass

# Gemini Setup
GEMINI_READY = False
CLIENT = None
try:
    from google import genai
    from google.genai import types
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        CLIENT = genai.Client(api_key=api_key)
        GEMINI_READY = True
except ImportError:
    pass

print(f"📋 Planner Agent: ADK={ADK_AVAILABLE}, Gemini={GEMINI_READY}, Approval={APPROVAL_READY}")

# =============================================================================
# CONFIGURATION
# =============================================================================
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Demo trap trigger words (for human-in-the-loop demonstration)
DEMO_TRIGGER_WORDS = [
    "marathon", "10 days", "no rest", "crazy", "insane", 
    "hard", "extreme", "max", "intense", "beast mode"
]

# =============================================================================
# SESSION TEMPLATES (The Safe Path)
# =============================================================================
SESSION_TEMPLATES = {
    "easy_run": {
        "name": "Easy Run", 
        "intensity_zone": "Zone 2", 
        "duration_min": 30, 
        "emoji": "🏃",
        "description": "Conversational pace run"
    },
    "tempo": {
        "name": "Tempo Run", 
        "intensity_zone": "Zone 3-4", 
        "duration_min": 40, 
        "emoji": "🔥",
        "description": "Comfortably hard effort"
    },
    "long_run": {
        "name": "Long Run",
        "intensity_zone": "Zone 2",
        "duration_min": 60,
        "emoji": "🏔️",
        "description": "Extended aerobic session"
    },
    "strength": {
        "name": "Strength Training", 
        "intensity_zone": "Moderate", 
        "duration_min": 45, 
        "emoji": "💪",
        "description": "Full body resistance training"
    },
    "hiit": {
        "name": "HIIT Session", 
        "intensity_zone": "High", 
        "duration_min": 25, 
        "emoji": "⚡",
        "description": "High intensity intervals"
    },
    "recovery": {
        "name": "Active Recovery",
        "intensity_zone": "Zone 1",
        "duration_min": 20,
        "emoji": "🧘",
        "description": "Light movement and stretching"
    },
    "rest": {
        "name": "Rest Day", 
        "intensity_zone": "None", 
        "duration_min": 0, 
        "emoji": "😴",
        "description": "Complete rest for recovery"
    }
}

# Goal-based session patterns
GOAL_PATTERNS = {
    "general_fitness": ["strength", "easy_run", "rest", "hiit", "easy_run", "strength", "rest"],
    "strength": ["strength", "rest", "strength", "recovery", "strength", "rest", "rest"],
    "endurance": ["easy_run", "tempo", "rest", "easy_run", "recovery", "long_run", "rest"],
    "fat_loss": ["hiit", "strength", "easy_run", "rest", "hiit", "strength", "rest"],
    "race_prep": ["easy_run", "tempo", "rest", "easy_run", "rest", "long_run", "rest"],
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def _get_start_date() -> datetime:
    """Get the start date for the plan (next Monday or today if Monday)."""
    today = datetime.now()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0 and today.hour < 12:
        return today
    return today + timedelta(days=days_until_monday if days_until_monday > 0 else 0)


def _generate_template_plan(goal: str, days: int = 7) -> List[Dict[str, Any]]:
    """Generate a deterministic template-based plan."""
    pattern = GOAL_PATTERNS.get(goal.lower().replace(" ", "_"), GOAL_PATTERNS["general_fitness"])
    
    plan = []
    start_date = datetime.now()
    
    for i in range(days):
        day_index = i % len(pattern)
        session_type = pattern[day_index]
        template = SESSION_TEMPLATES.get(session_type, SESSION_TEMPLATES["rest"])
        
        session_date = start_date + timedelta(days=i)
        
        plan.append({
            "day": session_date.strftime("%A"),
            "day_number": i + 1,
            "date": session_date.strftime("%b %d"),
            "iso_date": session_date.strftime("%Y-%m-%d"),
            "name": template["name"],
            "session_type": session_type,
            "intensity_zone": template["intensity_zone"],
            "duration_min": template["duration_min"],
            "emoji": template["emoji"],
            "description": template["description"],
            "notes": ""
        })
    
    return plan


def _calculate_metrics(sessions: List[Dict]) -> Dict[str, Any]:
    """Calculate plan metrics."""
    total_duration = sum(s.get("duration_min", 0) for s in sessions)
    training_days = sum(1 for s in sessions if s.get("duration_min", 0) > 0)
    rest_days = len(sessions) - training_days
    
    # Calculate max intensity
    max_intensity = 0
    for s in sessions:
        zone = str(s.get("intensity_zone", "")).lower()
        if "high" in zone or "max" in zone or "zone 5" in zone:
            score = 9
        elif "zone 4" in zone:
            score = 8
        elif "moderate" in zone or "zone 3" in zone:
            score = 6
        elif "zone 2" in zone:
            score = 4
        else:
            score = 2
        max_intensity = max(max_intensity, score)
    
    return {
        "total_duration_min": total_duration,
        "training_days": training_days,
        "rest_days": rest_days,
        "avg_session_duration": total_duration // max(training_days, 1),
        "max_intensity_rpe": max_intensity
    }


def _check_approval_needed(
    sessions: List[Dict], 
    metrics: Dict, 
    specific_request: str = ""
) -> Dict[str, Any]:
    """
    Check if plan needs human approval.
    Includes DEMO TRAP for demonstration purposes.
    """
    requires_approval = False
    reasons = []
    
    # ==========================================================
    # 🪤 DEMO TRAP: Force approval for trigger words
    # ==========================================================
    if specific_request:
        request_lower = specific_request.lower()
        triggered = [word for word in DEMO_TRIGGER_WORDS if word in request_lower]
        
        if triggered:
            print(f"🚨 DEMO TRAP TRIGGERED: {triggered}")
            requires_approval = True
            reasons.append(f"⚠️ SAFETY PROTOCOL: High-risk request detected")
            reasons.append(f"⚠️ Triggered by: {', '.join(triggered)}")
    
    # ==========================================================
    # Real Safety Checks
    # ==========================================================
    
    # 1. High intensity check
    if metrics.get("max_intensity_rpe", 0) >= 8:
        requires_approval = True
        reasons.append("🔥 High intensity sessions planned (RPE 8+)")
    
    # 2. No rest days check
    if metrics.get("rest_days", 0) == 0:
        requires_approval = True
        reasons.append("😰 No rest days scheduled - injury risk!")
    
    # 3. Excessive volume check
    if metrics.get("total_duration_min", 0) > 420:  # 7+ hours
        requires_approval = True
        reasons.append("📈 High weekly volume (7+ hours)")
    
    # 4. Too many training days
    if metrics.get("training_days", 0) >= 7:
        requires_approval = True
        reasons.append("⚠️ Training every day - recovery needed!")
    
    return {
        "requires_approval": requires_approval,
        "reasons": reasons,
        "risk_level": "high" if requires_approval else "low"
    }


def _get_motivational_message(goal: str, requires_approval: bool) -> str:
    """Get appropriate motivational message."""
    if requires_approval:
        return "⚠️ This plan needs your approval before activation. Safety first!"
    
    messages = {
        "strength": "💪 Time to build that strength! Progressive overload is the key.",
        "endurance": "🏃 Let's build that aerobic engine! Consistency wins.",
        "fat_loss": "🔥 Burn it up! Remember, nutrition is 80% of the battle.",
        "race_prep": "🏁 Race day is coming! Trust the process.",
        "general_fitness": "🎯 Balance is everything. Let's get after it!"
    }
    return messages.get(goal.lower().replace(" ", "_"), "Let's crush this week! 💪")


# =============================================================================
# MAIN TOOL FUNCTIONS
# =============================================================================
def generate_training_plan(
    tool_context: Any,
    goal: str = "general_fitness",
    days: int = 7,
    custom_notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a training plan using safe templates.
    
    This is the standard path - uses proven templates that are
    automatically approved (no human-in-the-loop needed).
    
    Args:
        tool_context: Session context for state management
        goal: Training goal (general_fitness, strength, endurance, fat_loss, race_prep)
        days: Number of days to plan (default 7)
        custom_notes: Any specific notes to include
    
    Returns:
        Complete training plan dictionary
    """
    print(f"📋 Generating template plan: goal={goal}, days={days}")
    
    # Generate sessions from templates
    sessions = _generate_template_plan(goal, days)
    
    # Calculate metrics
    metrics = _calculate_metrics(sessions)
    
    # Templates are always safe - auto-approved
    plan = {
        "status": "success",
        "plan_id": f"tpl_{uuid.uuid4().hex[:8]}",
        "plan_name": f"{goal.replace('_', ' ').title()} - Week Plan",
        "week_focus": f"{goal.replace('_', ' ').title()} Development",
        "goal": goal,
        "days_planned": days,
        "weekly_plan": sessions,
        "coach_explanation": _get_coach_explanation(goal, metrics),
        "motivational_message": _get_motivational_message(goal, False),
        "custom_notes": custom_notes,
        "metrics": metrics,
        "requires_approval": False,
        "approval_reasons": [],
        "approved": True,  # Templates are pre-approved
        "generated_by": "template",
        "created_at": datetime.now().isoformat()
    }
    
    # Save to state
    if hasattr(tool_context, 'state'):
        tool_context.state["app:current_plan"] = plan
        tool_context.state["app:plan_status"] = "active"
        print(f"✅ Template plan saved to state: {plan['plan_name']}")
    
    return plan


def _get_coach_explanation(goal: str, metrics: Dict) -> str:
    """Generate coach explanation for the plan."""
    explanations = {
        "general_fitness": (
            f"This balanced plan includes {metrics['training_days']} training days "
            f"with {metrics['rest_days']} rest days. We're mixing strength and cardio "
            "for well-rounded fitness development."
        ),
        "strength": (
            f"Focus on progressive overload across {metrics['training_days']} sessions. "
            "Adequate rest between sessions allows for muscle recovery and growth."
        ),
        "endurance": (
            f"Building your aerobic base with {metrics['total_duration_min']} minutes "
            "of training. The long run on the weekend is key for endurance gains."
        ),
        "fat_loss": (
            "Combining HIIT and strength training maximizes calorie burn and "
            "metabolic boost. The mix keeps things interesting and effective."
        ),
        "race_prep": (
            "Periodized approach with tempo work and a long run. "
            "We're building race-specific fitness while managing fatigue."
        )
    }
    return explanations.get(goal.lower().replace(" ", "_"), 
                          f"Balanced plan with {metrics['training_days']} training days.")


def generate_plan_with_ai(
    tool_context: Any,
    goal: str = "general_fitness",
    specific_request: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a custom training plan using Gemini AI.
    
    This is the creative path - AI generates personalized plans,
    but they may require human approval for safety.
    
    Includes DEMO TRAP: Certain trigger words force the approval workflow
    for demonstration purposes.
    
    Args:
        tool_context: Session context for state management
        goal: Training goal
        specific_request: Specific user requirements (e.g., "marathon prep in 10 weeks")
    
    Returns:
        Training plan that may require approval
    """
    print(f"🤖 AI Planner: goal={goal}, request='{specific_request}'")
    
    # Fallback to templates if Gemini not available
    if not GEMINI_READY or not CLIENT:
        print("⚠️ Gemini not available, falling back to templates")
        return generate_training_plan(tool_context, goal, custom_notes=specific_request)
    
    # Get user context for personalization
    readiness = 70
    user_name = "Athlete"
    if hasattr(tool_context, 'state'):
        analysis = tool_context.state.get("app:latest_analysis", {})
        readiness = analysis.get("readiness_score", 70)
        user_name = tool_context.state.get("user:name", "Athlete")
    
    # Build AI prompt
    prompt = f"""
Act as an Elite Fitness Coach creating a personalized 7-Day Training Plan.

ATHLETE CONTEXT:
- Name: {user_name}
- Primary Goal: {goal}
- Specific Request: "{specific_request or 'Standard plan'}"
- Current Readiness: {readiness}/100

INSTRUCTIONS:
1. Create exactly 7 days of training (Monday-Sunday)
2. Match intensity to the athlete's readiness level
3. Include appropriate rest/recovery days
4. Make it specific to their request

Return ONLY valid JSON matching this exact structure:
{{
    "week_focus": "Theme for the week",
    "coach_explanation": "2-3 sentences explaining why you built it this way",
    "weekly_plan": [
        {{
            "day": "Monday",
            "name": "Session Name",
            "session_type": "easy_run|tempo|strength|hiit|long_run|recovery|rest",
            "intensity_zone": "Zone 1|Zone 2|Zone 3|Zone 4|Zone 5|Low|Moderate|High",
            "duration_min": 45,
            "description": "What to do",
            "notes": "Specific coaching tips",
            "emoji": "🏃"
        }}
    ]
}}

IMPORTANT: Return ONLY the JSON, no other text.
"""

    try:
        response = CLIENT.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7
            )
        )
        
        ai_data = json.loads(response.text)
        sessions = ai_data.get("weekly_plan", [])
        
        # Add dates and day numbers
        start_date = datetime.now()
        for i, session in enumerate(sessions):
            session_date = start_date + timedelta(days=i)
            session["day_number"] = i + 1
            session["date"] = session_date.strftime("%b %d")
            session["iso_date"] = session_date.strftime("%Y-%m-%d")
            if "emoji" not in session:
                session["emoji"] = "📅"
        
        # Calculate metrics
        metrics = _calculate_metrics(sessions)
        
        # Check if approval needed (includes demo trap)
        approval_check = _check_approval_needed(sessions, metrics, specific_request or "")
        
        # Determine status
        requires_approval = approval_check["requires_approval"]
        status = "pending_approval" if requires_approval else "success"
        
        plan = {
            "status": status,
            "plan_id": f"ai_{uuid.uuid4().hex[:8]}",
            "plan_name": f"Custom: {goal.replace('_', ' ').title()}",
            "week_focus": ai_data.get("week_focus", f"{goal.title()} Focus"),
            "goal": goal,
            "days_planned": 7,
            "weekly_plan": sessions,
            "coach_explanation": ai_data.get("coach_explanation", "AI-generated custom plan."),
            "motivational_message": _get_motivational_message(goal, requires_approval),
            "custom_notes": specific_request,
            "metrics": metrics,
            "requires_approval": requires_approval,
            "approval_reasons": approval_check["reasons"],
            "approved": not requires_approval,
            "generated_by": "gemini_ai",
            "created_at": datetime.now().isoformat()
        }
        
        # Save to appropriate state key
        if hasattr(tool_context, 'state'):
            if requires_approval:
                tool_context.state["app:pending_plan"] = plan
                tool_context.state["app:plan_status"] = "pending_approval"
                print(f"⚠️ Plan requires approval: {approval_check['reasons']}")
            else:
                tool_context.state["app:current_plan"] = plan
                tool_context.state["app:plan_status"] = "active"
                print(f"✅ AI plan auto-approved and saved")
        
        return plan
        
    except json.JSONDecodeError as e:
        print(f"❌ AI response parsing failed: {e}")
        return generate_training_plan(tool_context, goal, custom_notes=specific_request)
    except Exception as e:
        print(f"❌ AI plan generation failed: {e}")
        return generate_training_plan(tool_context, goal, custom_notes=specific_request)


def approve_current_plan(
    tool_context: Any,
    approval_notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Approve a pending training plan (Human-in-the-Loop).
    
    Call this when user confirms they want to proceed with a
    high-risk plan that was flagged for approval.
    
    Args:
        tool_context: Session context
        approval_notes: Optional notes about why approved
    
    Returns:
        Approval status
    """
    if not hasattr(tool_context, 'state'):
        return {"status": "error", "message": "No context available"}
    
    pending_plan = tool_context.state.get("app:pending_plan")
    
    if not pending_plan:
        # Check if there's already an active plan
        current = tool_context.state.get("app:current_plan")
        if current:
            return {
                "status": "already_active",
                "message": "You already have an active plan!",
                "plan_name": current.get("plan_name")
            }
        return {
            "status": "error",
            "message": "No pending plan to approve. Generate a plan first!"
        }
    
    # Approve the plan
    pending_plan["approved"] = True
    pending_plan["approved_at"] = datetime.now().isoformat()
    pending_plan["approval_notes"] = approval_notes
    pending_plan["status"] = "success"
    
    # Move to active
    tool_context.state["app:current_plan"] = pending_plan
    tool_context.state["app:pending_plan"] = None
    tool_context.state["app:plan_status"] = "active"
    
    print(f"✅ Plan approved: {pending_plan['plan_name']}")
    
    return {
        "status": "approved",
        "message": f"✅ '{pending_plan['plan_name']}' is now ACTIVE!",
        "plan_name": pending_plan["plan_name"],
        "week_focus": pending_plan.get("week_focus"),
        "training_days": pending_plan.get("metrics", {}).get("training_days", 0),
        "next_steps": [
            "Check today's session with 'What's my workout today?'",
            "Log your workouts after each session",
            "Listen to your body - adjust if needed"
        ]
    }


def reject_current_plan(
    tool_context: Any,
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Reject a pending training plan.
    
    Args:
        tool_context: Session context
        reason: Why the plan was rejected
    
    Returns:
        Rejection status
    """
    if not hasattr(tool_context, 'state'):
        return {"status": "error", "message": "No context available"}
    
    pending_plan = tool_context.state.get("app:pending_plan")
    
    if not pending_plan:
        return {"status": "error", "message": "No pending plan to reject."}
    
    plan_name = pending_plan.get("plan_name", "Unknown")
    
    # Clear pending plan
    tool_context.state["app:pending_plan"] = None
    tool_context.state["app:plan_status"] = None
    
    print(f"❌ Plan rejected: {plan_name}")
    
    return {
        "status": "rejected",
        "message": f"Plan '{plan_name}' was rejected.",
        "reason": reason,
        "next_steps": [
            "Tell me what you'd like instead",
            "Try a safer goal like 'general fitness'",
            "Ask for a modified version"
        ]
    }


def get_today_session(tool_context: Any) -> Dict[str, Any]:
    """
    Get today's planned workout from the active training plan.
    
    Args:
        tool_context: Session context
    
    Returns:
        Today's session details or appropriate message
    """
    if not hasattr(tool_context, 'state'):
        return {"status": "error", "message": "No context available"}
    
    # Check for pending plan first
    pending = tool_context.state.get("app:pending_plan")
    if pending:
        return {
            "status": "pending_approval",
            "message": "⚠️ You have a plan waiting for approval!",
            "plan_name": pending.get("plan_name"),
            "requires_action": True,
            "next_steps": ["Approve or reject the pending plan first"]
        }
    
    # Get active plan
    current_plan = tool_context.state.get("app:current_plan")
    
    if not current_plan:
        return {
            "status": "no_plan",
            "message": "📋 No active training plan. Let's create one!",
            "next_steps": [
                "Tell me your goal (strength, endurance, fat loss)",
                "Or just say 'Create a training plan'"
            ]
        }
    
    # Find today's session
    today = datetime.now()
    today_iso = today.strftime("%Y-%m-%d")
    today_name = today.strftime("%A")
    
    sessions = current_plan.get("weekly_plan", [])
    today_session = None
    
    # Try to find by ISO date first
    for session in sessions:
        if session.get("iso_date") == today_iso:
            today_session = session
            break
    
    # Fall back to day name
    if not today_session:
        for session in sessions:
            if session.get("day", "").lower() == today_name.lower():
                today_session = session
                break
    
    # Still not found - use day of week index
    if not today_session and sessions:
        day_index = today.weekday()  # Monday = 0
        if day_index < len(sessions):
            today_session = sessions[day_index]
    
    if not today_session:
        return {
            "status": "not_found",
            "message": f"No session found for {today_name}.",
            "plan_name": current_plan.get("plan_name")
        }
    
    # Check if rest day
    if today_session.get("session_type", "").lower() == "rest":
        return {
            "status": "rest_day",
            "session": today_session,
            "message": f"😴 **REST DAY** - {today_session.get('description', 'Take it easy!')}",
            "suggestions": [
                "Light stretching or yoga",
                "Focus on nutrition and hydration",
                "Get quality sleep tonight"
            ]
        }
    
    # Build warm-up/cool-down based on session type
    session_type = today_session.get("session_type", "")
    intensity = today_session.get("intensity_zone", "")
    
    if "hiit" in session_type.lower() or "Zone 4" in intensity or "Zone 5" in intensity:
        warm_up = "10-15 min progressive warm-up with dynamic stretches"
        cool_down = "10 min easy movement + stretching"
    elif "strength" in session_type.lower():
        warm_up = "5 min cardio + dynamic movements + warm-up sets"
        cool_down = "5 min walking + full body stretching"
    else:
        warm_up = "5-10 min easy movement"
        cool_down = "5 min cool-down + stretching"
    
    return {
        "status": "success",
        "day": today_session.get("day"),
        "date": today_session.get("date"),
        "session": today_session,
        "warm_up": warm_up,
        "cool_down": cool_down,
        "plan_name": current_plan.get("plan_name"),
        "message": (
            f"{today_session.get('emoji', '🏋️')} **Today: {today_session['name']}** "
            f"({today_session.get('duration_min', 0)} min)\n"
            f"_{today_session.get('description', '')}_"
        )
    }


def get_plan_summary(tool_context: Any) -> Dict[str, Any]:
    """
    Get a summary of the current or pending training plan.
    
    Args:
        tool_context: Session context
    
    Returns:
        Plan summary
    """
    if not hasattr(tool_context, 'state'):
        return {"status": "error", "message": "No context available"}
    
    current_plan = tool_context.state.get("app:current_plan")
    pending_plan = tool_context.state.get("app:pending_plan")
    
    plan = current_plan or pending_plan
    
    if not plan:
        return {
            "status": "no_plan",
            "message": "No training plan available. Let's create one!"
        }
    
    # Build summary
    sessions = plan.get("weekly_plan", [])
    summary_lines = []
    
    for session in sessions:
        emoji = session.get("emoji", "📅")
        day = session.get("day", "Day")
        name = session.get("name", "Session")
        duration = session.get("duration_min", 0)
        
        if duration > 0:
            summary_lines.append(f"{emoji} **{day}**: {name} ({duration}m)")
        else:
            summary_lines.append(f"{emoji} **{day}**: {name}")
    
    status = "pending_approval" if pending_plan and not current_plan else "active"
    
    return {
        "status": status,
        "plan_name": plan.get("plan_name"),
        "week_focus": plan.get("week_focus"),
        "goal": plan.get("goal"),
        "summary": "\n".join(summary_lines),
        "metrics": plan.get("metrics", {}),
        "coach_explanation": plan.get("coach_explanation"),
        "motivational_message": plan.get("motivational_message"),
        "requires_approval": plan.get("requires_approval", False)
    }


def adjust_plan_intensity(
    tool_context: Any,
    adjustment: str = "reduce",
    reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Adjust the current plan's intensity.
    
    Args:
        tool_context: Session context
        adjustment: "reduce", "increase", or "maintain"
        reason: Why adjusting
    
    Returns:
        Adjustment result
    """
    if not hasattr(tool_context, 'state'):
        return {"status": "error", "message": "No context available"}
    
    current_plan = tool_context.state.get("app:current_plan")
    
    if not current_plan:
        return {
            "status": "error",
            "message": "No active plan to adjust.",
            "next_steps": ["Generate a plan first"]
        }
    
    adjustment = adjustment.lower()
    modified_days = []
    
    for session in current_plan.get("weekly_plan", []):
        if session.get("session_type") in ["rest", "recovery"]:
            continue
        
        original_duration = session.get("duration_min", 0)
        
        if adjustment == "reduce":
            session["duration_min"] = int(original_duration * 0.8)
            # Reduce intensity zones
            zone = session.get("intensity_zone", "")
            session["intensity_zone"] = zone.replace("Zone 4", "Zone 3").replace("Zone 5", "Zone 4")
            session["notes"] = f"[Reduced] Was {original_duration}m. {reason or ''}"
            modified_days.append(session["day"])
            
        elif adjustment == "increase":
            session["duration_min"] = int(original_duration * 1.15)
            session["notes"] = f"[Increased] Was {original_duration}m. {reason or ''}"
            modified_days.append(session["day"])
    
    # Record modification
    mods = current_plan.get("modifications", [])
    mods.append({
        "type": adjustment,
        "reason": reason,
        "days": modified_days,
        "timestamp": datetime.now().isoformat()
    })
    current_plan["modifications"] = mods
    
    # Save
    tool_context.state["app:current_plan"] = current_plan
    
    emoji = "🔽" if adjustment == "reduce" else "🔼"
    
    return {
        "status": "adjusted",
        "adjustment": adjustment,
        "days_modified": modified_days,
        "message": f"{emoji} Intensity {adjustment}d for {len(modified_days)} sessions.",
        "reason": reason
    }


def calculate_plan_metrics(
    tool_context: Any,
    weight_kg: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate detailed metrics for the current plan.
    
    Args:
        tool_context: Session context
        weight_kg: User weight for calorie calculations
    
    Returns:
        Calculated metrics
    """
    if not hasattr(tool_context, 'state'):
        return {"status": "error", "message": "No context available"}
    
    current_plan = tool_context.state.get("app:current_plan")
    
    if not current_plan:
        return {"status": "no_plan", "message": "No active plan to analyze."}
    
    weight = weight_kg or tool_context.state.get("user:weight_kg", 70)
    
    sessions = current_plan.get("weekly_plan", [])
    total_calories = 0
    session_breakdown = []
    
    for session in sessions:
        duration = session.get("duration_min", 0)
        if duration <= 0:
            continue
        
        # Estimate calories (rough MET-based estimation)
        session_type = session.get("session_type", "easy_run")
        met_values = {
            "easy_run": 7.0,
            "tempo": 9.0,
            "long_run": 8.0,
            "hiit": 12.0,
            "strength": 5.0,
            "recovery": 3.0
        }
        met = met_values.get(session_type, 6.0)
        calories = int((met * weight * duration) / 60)
        
        total_calories += calories
        session_breakdown.append({
            "day": session.get("day"),
            "name": session.get("name"),
            "duration": duration,
            "calories": calories
        })
    
    return {
        "status": "success",
        "plan_name": current_plan.get("plan_name"),
        "total_calories": total_calories,
        "avg_daily_calories": total_calories // 7,
        "session_breakdown": session_breakdown,
        "weight_used_kg": weight,
        "message": f"🔥 This week burns approximately {total_calories} calories!"
    }


# =============================================================================
# ADK AGENT FACTORY
# =============================================================================
def create_planner_agent(
    use_memory_preload: bool = False
) -> Optional[Any]:
    """
    Create an ADK Agent for training plan generation.
    
    Args:
        use_memory_preload: If True, uses preload_memory tool
    
    Returns:
        Configured LlmAgent or None if ADK unavailable
    """
    if not ADK_AVAILABLE:
        print("⚠️ ADK not available. Cannot create planner agent.")
        return None
    
    from google.adk.agents import LlmAgent
    from google.adk.models.google_llm import Gemini
    from google.adk.tools import FunctionTool
    
    tools = [
        FunctionTool(func=generate_training_plan),
        FunctionTool(func=generate_plan_with_ai),
        FunctionTool(func=approve_current_plan),
        FunctionTool(func=reject_current_plan),
        FunctionTool(func=get_today_session),
        FunctionTool(func=get_plan_summary),
        FunctionTool(func=adjust_plan_intensity),
        FunctionTool(func=calculate_plan_metrics),
    ]
    
    if use_memory_preload:
        tools.append(load_memory)
    
    agent = LlmAgent(
        name="FitForgePlanner",
        model=Gemini(model="gemini-2.5-flash-lite"),
        description="Training plan generator for FitForge AI",
        instruction="""You are FitForge's training plan expert.

CAPABILITIES:
- Generate personalized weekly training plans
- Create AI-powered custom plans for specific goals
- Handle plan approval workflow for high-risk plans
- Provide today's workout details
- Adjust plans based on user feedback

WORKFLOW:
1. Use generate_training_plan for safe, template-based plans
2. Use generate_plan_with_ai for custom/specific requests
3. If plan requires approval, explain why and wait for user confirmation
4. Use approve_current_plan when user agrees
5. Use get_today_session to show daily workouts

SAFETY:
- High-risk plans (intense, no rest days) require approval
- Always explain the risks before proceeding
- Respect user's decision to reject plans

Be encouraging but prioritize safety!""",
        tools=tools,
        output_key="planner_response"
    )
    
    print(f"✅ Planner Agent created with {len(tools)} tools")
    return agent


# =============================================================================
# EXPORTS
# =============================================================================
__all__ = [
    # Main tools
    "generate_training_plan",
    "generate_plan_with_ai",
    "approve_current_plan",
    "reject_current_plan",
    "get_today_session",
    "get_plan_summary",
    "adjust_plan_intensity",
    "calculate_plan_metrics",
    
    # Agent factory
    "create_planner_agent",
    
    # Config
    "SESSION_TEMPLATES",
    "GOAL_PATTERNS",
    "DEMO_TRIGGER_WORDS",
    
    # Flags
    "ADK_AVAILABLE",
    "GEMINI_READY",
    "APPROVAL_READY",
]
