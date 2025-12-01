"""
FitForge AI — Performance & Recovery Analyzer Agent
====================================================
ADK-Integrated Analysis System with Readiness Scoring
"""

import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

# =============================================================================
# ADK IMPORTS — Graceful Fallback
# =============================================================================
ADK_AVAILABLE = False
try:
    from google.adk.agents import LlmAgent
    from google.adk.tools.tool_context import ToolContext
    from google.adk.tools import load_memory, preload_memory, FunctionTool
    from google.adk.runners import Runner
    from google.adk.models.google_llm import Gemini
    from google.genai import types
    ADK_AVAILABLE = True
    print("✅ Analyzer Agent: ADK components ready")
except ImportError as e:
    print(f"⚠️ Analyzer Agent: ADK not available: {e}")
    ToolContext = Any  # Fallback type

# =============================================================================
# LOCAL IMPORTS — Optional Dependencies
# =============================================================================
MEMORY_MANAGER_AVAILABLE = False
try:
    from memory.session_manager import (
        FitForgeMemoryManager,
        save_analysis_results,
        get_latest_analysis,
        APP_NAME
    )
    MEMORY_MANAGER_AVAILABLE = True
except ImportError:
    APP_NAME = "fitforge_ai"

TRAINING_CALCULATOR_AVAILABLE = False
try:
    from tools.training_calculator import calculate_training_load
    TRAINING_CALCULATOR_AVAILABLE = True
except ImportError:
    pass

print(f"📊 Analyzer: Memory={MEMORY_MANAGER_AVAILABLE}, Calculator={TRAINING_CALCULATOR_AVAILABLE}")

# =============================================================================
# CONFIGURATION — Tunable Parameters
# =============================================================================
ANALYZER_CONFIG = {
    "app_name": APP_NAME,
    "default_window_days": 28,
    "min_samples_for_averages": 4,
    "target_workouts_per_week": 3,
    "optimal_sleep_hours": 7.5,
    "fatigue_warning_threshold": 4,
    "risk_weight": 60,
    "sleep_weight": 10,
    "fatigue_weight": 9,
    "consistency_bonus": 30,
}

# Readiness thresholds and labels
READINESS_LEVELS = {
    "peak": {"min": 90, "label": "PEAK", "emoji": "🟢", "color": "green"},
    "strong": {"min": 75, "label": "STRONG", "emoji": "🟢", "color": "green"},
    "moderate": {"min": 60, "label": "MODERATE", "emoji": "🟡", "color": "yellow"},
    "recover": {"min": 40, "label": "RECOVER", "emoji": "🟡", "color": "yellow"},
    "rest": {"min": 0, "label": "REST NOW", "emoji": "🔴", "color": "red"},
}

# Consistency labels
CONSISTENCY_LABELS = {
    90: "Elite",
    75: "Excellent",
    50: "Strong",
    25: "Building",
    0: "Getting Started",
}

# Motivational quotes
MOTIVATIONAL_QUOTES = {
    (90, 101): "You're not training — you're forging a legend. 🔥",
    (75, 90): "Strong body, stronger mind. Keep stacking wins. 💪",
    (60, 75): "Progress > perfection. You're still moving forward. 🚀",
    (40, 60): "Rest is training too. The comeback is always stronger. 🌟",
    (0, 40): "Recovery is where champions are made. Honor your body. 🧘",
}

DEFAULT_QUOTE = "Every champion was once tired. Keep going. 💫"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def get_iso_week_key(date_str: str) -> str:
    """Convert date string to ISO week key (e.g., '2025-W01')."""
    try:
        dt = datetime.fromisoformat(date_str[:10])
        return dt.strftime("%G-W%V")
    except (ValueError, TypeError):
        return datetime.now().strftime("%G-W%V")


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime object."""
    try:
        return datetime.fromisoformat(date_str[:10])
    except (ValueError, TypeError):
        return datetime.now()


def get_readiness_level(score: int) -> Dict[str, Any]:
    """Get readiness level details from score."""
    for level_name, level_data in READINESS_LEVELS.items():
        if score >= level_data["min"]:
            return {
                "level": level_name,
                "label": level_data["label"],
                "emoji": level_data["emoji"],
                "color": level_data["color"]
            }
    return {"level": "rest", "label": "REST NOW", "emoji": "🔴", "color": "red"}


def get_consistency_label(percent: int) -> str:
    """Get consistency label from percentage."""
    for threshold, label in sorted(CONSISTENCY_LABELS.items(), reverse=True):
        if percent >= threshold:
            return label
    return "Getting Started"


def get_motivational_quote(readiness: int) -> str:
    """Get motivational quote based on readiness level."""
    for (low, high), quote in MOTIVATIONAL_QUOTES.items():
        if low <= readiness < high:
            return quote
    return DEFAULT_QUOTE


# =============================================================================
# CORE ANALYSIS FUNCTIONS
# =============================================================================
def calculate_consistency(
    workouts: List[Dict[str, Any]],
    target_per_week: int = 3
) -> Tuple[int, int, str]:
    """
    Calculate weekly workout consistency.
    
    Returns:
        Tuple of (consistency_percent, total_weeks, consistency_label)
    """
    if not workouts:
        return 0, 0, "New"

    # Group workouts by ISO week
    week_counts: Dict[str, int] = {}
    for workout in workouts:
        date_str = workout.get("date") or workout.get("timestamp", "")
        if date_str:
            try:
                week_key = get_iso_week_key(date_str[:10])
                week_counts[week_key] = week_counts.get(week_key, 0) + 1
            except:
                pass

    total_weeks = len(week_counts)
    if total_weeks == 0:
        return 0, 0, "New"

    # Count weeks that meet the target
    good_weeks = sum(1 for count in week_counts.values() if count >= target_per_week)
    consistency_pct = round((good_weeks / total_weeks) * 100)
    
    return consistency_pct, total_weeks, get_consistency_label(consistency_pct)


def calculate_biometric_averages(
    workouts: List[Dict[str, Any]],
    min_samples: int = 4
) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract sleep and fatigue averages from workout context.
    
    Returns:
        Tuple of (avg_sleep_hours, avg_fatigue_level)
    """
    sleep_vals = []
    fatigue_vals = []
    
    for w in workouts:
        # Check multiple possible locations for context data
        context = w.get("context") or {}
        
        # Also check top-level workout data
        workout_data = w.get("workout", w)
        
        # Sleep
        sleep = context.get("sleep_hours") or workout_data.get("sleep_hours")
        if sleep is not None:
            try:
                sleep_vals.append(float(sleep))
            except (ValueError, TypeError):
                pass
        
        # Fatigue
        fatigue = context.get("fatigue_level") or workout_data.get("fatigue_level")
        if fatigue is not None:
            try:
                fatigue_vals.append(float(fatigue))
            except (ValueError, TypeError):
                pass

    avg_sleep = (
        round(statistics.mean(sleep_vals), 1)
        if len(sleep_vals) >= min_samples
        else None
    )

    avg_fatigue = (
        round(statistics.mean(fatigue_vals), 1)
        if len(fatigue_vals) >= min_samples
        else None
    )

    return avg_sleep, avg_fatigue


def calculate_readiness_score(
    risk: float = 0.0,
    avg_sleep: Optional[float] = None,
    avg_fatigue: Optional[float] = None,
    consistency_pct: int = 0,
    config: Dict[str, Any] = None
) -> Tuple[int, str, str]:
    """
    Calculate comprehensive readiness score (0-100).
    
    Returns:
        Tuple of (readiness_score, readiness_label, readiness_emoji)
    """
    cfg = config or ANALYZER_CONFIG
    readiness = 100.0

    # === Penalties ===
    readiness -= risk * cfg["risk_weight"]

    if avg_sleep is not None:
        sleep_deficit = max(0, cfg["optimal_sleep_hours"] - avg_sleep)
        readiness -= sleep_deficit * cfg["sleep_weight"]

    if avg_fatigue is not None:
        fatigue_excess = max(0, avg_fatigue - cfg["fatigue_warning_threshold"])
        readiness -= fatigue_excess * cfg["fatigue_weight"]

    # === Bonus ===
    readiness += (consistency_pct / 100) * cfg["consistency_bonus"]

    # Clamp to valid range
    readiness = max(5, min(100, int(readiness)))

    level = get_readiness_level(readiness)
    return readiness, level["label"], level["emoji"]


def generate_recommendations(
    readiness: int,
    risk: float = 0.0,
    avg_sleep: Optional[float] = None,
    avg_fatigue: Optional[float] = None,
    consistency_pct: int = 0
) -> List[str]:
    """Generate smart, context-aware recommendations."""
    recs: List[str] = []

    # Priority 1: Safety
    if readiness < 45:
        recs.append("🔴 CRITICAL: Full rest or active recovery only.")
    elif risk > 0.85:
        recs.append("⚠️ Overtraining risk very high → 48h rest recommended.")
    elif readiness >= 88 and consistency_pct >= 80:
        recs.append("🟢 PEAK READINESS → Perfect day for a hard session!")
    elif risk > 0.6:
        recs.append("🟡 Moderate risk → Stick to Zone 2 cardio or technique work.")
    elif readiness >= 75:
        recs.append("🟢 Good to train → Push intensity, but listen to your body.")
    else:
        recs.append("🟡 Light training day → Focus on movement quality.")

    # Sleep recommendations
    if avg_sleep is not None:
        if avg_sleep < 6.0:
            recs.append(f"🚨 Sleep critical: {avg_sleep}h average → Prioritize 8+ hours tonight.")
        elif avg_sleep < 7.0:
            recs.append(f"😴 Sleep alert: {avg_sleep}h average → Try going to bed earlier.")
        elif avg_sleep >= 8.0:
            recs.append("💤 Excellent sleep habits!")

    # Fatigue recommendations
    if avg_fatigue is not None:
        if avg_fatigue >= 8:
            recs.append("😰 Fatigue critically high → Consider a deload week.")
        elif avg_fatigue >= 7:
            recs.append("😓 Fatigue elevated → Schedule a deload day soon.")
        elif avg_fatigue <= 3:
            recs.append("⚡ Low fatigue → You have capacity for harder training.")

    # Consistency
    if consistency_pct < 30 and readiness >= 60:
        recs.append("📅 Start with 2-3 workouts/week to build the habit.")
    elif consistency_pct >= 90:
        recs.append("🏆 Elite consistency! You're in the top tier.")

    return recs


def _estimate_risk_from_workouts(workouts: List[Dict[str, Any]]) -> float:
    """Estimate overtraining risk from workout patterns."""
    if not workouts:
        return 0.0
    
    risk = 0.0
    
    # Factor 1: High intensity frequency
    high_intensity_count = sum(
        1 for w in workouts[-7:]
        if str(w.get("intensity", "")).lower() in ["high", "max", "hard", "intense"]
    )
    if high_intensity_count >= 5:
        risk += 0.4
    elif high_intensity_count >= 3:
        risk += 0.2
    
    # Factor 2: Workout density (last 7 days)
    recent_dates = set()
    for w in workouts:
        date_str = w.get("date") or w.get("timestamp", "")
        if date_str:
            try:
                workout_date = parse_date(date_str)
                if workout_date >= datetime.now() - timedelta(days=7):
                    recent_dates.add(workout_date.date())
            except:
                pass
    
    if len(recent_dates) >= 7:
        risk += 0.3
    elif len(recent_dates) >= 6:
        risk += 0.15
    
    # Factor 3: Recent fatigue
    recent_fatigue = []
    for w in workouts[-5:]:
        context = w.get("context") or {}
        fatigue = context.get("fatigue_level")
        if fatigue is not None:
            try:
                recent_fatigue.append(float(fatigue))
            except:
                pass
    
    if recent_fatigue:
        avg_recent = statistics.mean(recent_fatigue)
        if avg_recent >= 8:
            risk += 0.3
        elif avg_recent >= 6:
            risk += 0.15
    
    return min(1.0, risk)


# =============================================================================
# MAIN ANALYSIS TOOL FUNCTIONS
# =============================================================================
def analyze_performance(
    tool_context: Any,
    window_days: int = 28
) -> Dict[str, Any]:
    """
    Analyze user's workout performance and recovery status.
    
    Call when user asks about readiness, recovery, or "How am I doing?"
    
    Args:
        tool_context: Context with session state
        window_days: Days to analyze (default 28)
    
    Returns:
        Complete analysis with readiness score, recommendations, etc.
    """
    # Get workout data from state
    workouts = []
    
    if hasattr(tool_context, 'state'):
        # Try multiple sources
        temp_workouts = tool_context.state.get("temp:workout_history", [])
        user_workouts = tool_context.state.get("user:workout_log", [])
        
        # Combine, avoiding duplicates
        seen_dates = set()
        for w in user_workouts + temp_workouts:
            date_key = w.get("date") or w.get("timestamp", "")
            if date_key and date_key not in seen_dates:
                workouts.append(w)
                seen_dates.add(date_key)
    
    # Handle empty data
    if not workouts:
        result = {
            "status": "no_data",
            "analysis_window_days": window_days,
            "readiness_score": 50,
            "readiness_label": "Unknown",
            "readiness_emoji": "⚪",
            "risk_level": 0.0,
            "ctl": 40,  # Default CTL for planner
            "atl": 35,  # Default ATL for planner
            "form": 5,
            "consistency_percent": 0,
            "consistency_label": "New",
            "active_weeks": 0,
            "avg_sleep_hours": None,
            "avg_fatigue": None,
            "fatigue_level": "unknown",
            "recommendations": [
                "🏁 Log your first workout to get personalized analysis!",
                "💡 Include sleep hours and fatigue level for better insights."
            ],
            "motivational_quote": "Every journey begins with a single step. 🚀",
            "analyzed_at": datetime.now().isoformat()
        }
        
        if hasattr(tool_context, 'state'):
            tool_context.state["app:latest_analysis"] = result
        
        return result
    
    # Filter to window
    cutoff_date = datetime.now() - timedelta(days=window_days)
    filtered_workouts = []
    
    for w in workouts:
        date_str = w.get("date") or w.get("timestamp", "")
        if date_str:
            try:
                workout_date = parse_date(date_str)
                if workout_date >= cutoff_date:
                    filtered_workouts.append(w)
            except:
                filtered_workouts.append(w)
    
    if not filtered_workouts:
        filtered_workouts = workouts[-10:]
    
    # Calculate all metrics
    consistency_pct, total_weeks, consistency_label = calculate_consistency(
        filtered_workouts,
        target_per_week=ANALYZER_CONFIG["target_workouts_per_week"]
    )
    
    avg_sleep, avg_fatigue = calculate_biometric_averages(
        filtered_workouts,
        min_samples=ANALYZER_CONFIG["min_samples_for_averages"]
    )
    
    risk = _estimate_risk_from_workouts(filtered_workouts)
    
    readiness, readiness_label, readiness_emoji = calculate_readiness_score(
        risk=risk,
        avg_sleep=avg_sleep,
        avg_fatigue=avg_fatigue,
        consistency_pct=consistency_pct
    )
    
    recommendations = generate_recommendations(
        readiness=readiness,
        risk=risk,
        avg_sleep=avg_sleep,
        avg_fatigue=avg_fatigue,
        consistency_pct=consistency_pct
    )
    
    # Calculate pseudo CTL/ATL for planner
    # CTL = Chronic Training Load (fitness), ATL = Acute Training Load (fatigue)
    total_duration = sum(w.get("duration", 0) or w.get("workout", {}).get("duration", 30) for w in filtered_workouts)
    ctl = min(100, 30 + (total_duration / 60))  # Simplified CTL
    atl = ctl * (1 + (risk * 0.5))  # ATL increases with risk
    form = ctl - atl  # Form = CTL - ATL
    
    # Fatigue level label
    if avg_fatigue:
        if avg_fatigue >= 7:
            fatigue_level = "high"
        elif avg_fatigue >= 4:
            fatigue_level = "moderate"
        else:
            fatigue_level = "low"
    else:
        fatigue_level = "moderate"  # Default
    
    result = {
        "status": "success",
        "analysis_window_days": window_days,
        "total_workouts_analyzed": len(filtered_workouts),
        "readiness_score": readiness,
        "readiness_label": readiness_label,
        "readiness_emoji": readiness_emoji,
        "risk_level": round(risk, 3),
        "ctl": round(ctl, 1),
        "atl": round(atl, 1),
        "form": round(form, 1),
        "consistency_percent": consistency_pct,
        "consistency_label": consistency_label,
        "active_weeks": total_weeks,
        "avg_sleep_hours": avg_sleep,
        "avg_fatigue": avg_fatigue,
        "fatigue_level": fatigue_level,
        "recommendations": recommendations,
        "motivational_quote": get_motivational_quote(readiness),
        "analyzed_at": datetime.now().isoformat()
    }
    
    # Save to state
    if hasattr(tool_context, 'state'):
        tool_context.state["app:latest_analysis"] = result
        tool_context.state["app:analysis_timestamp"] = datetime.now().isoformat()
    
    return result


def get_readiness_quick(tool_context: Any) -> Dict[str, Any]:
    """
    Quick readiness check - uses cache if available.
    
    Call for fast "Should I train?" questions.
    """
    # Check cache
    if hasattr(tool_context, 'state'):
        cached = tool_context.state.get("app:latest_analysis")
        timestamp = tool_context.state.get("app:analysis_timestamp")
        
        if cached and timestamp:
            try:
                analyzed_time = datetime.fromisoformat(timestamp)
                age_hours = (datetime.now() - analyzed_time).total_seconds() / 3600
                
                if age_hours < 4:  # Use cache if < 4 hours old
                    score = cached.get("readiness_score", 50)
                    
                    if score >= 85:
                        summary = "You're primed for a great session! 💪"
                    elif score >= 70:
                        summary = "Good to train with normal intensity."
                    elif score >= 55:
                        summary = "Moderate day - listen to your body."
                    elif score >= 40:
                        summary = "Consider lighter training."
                    else:
                        summary = "Rest day recommended."
                    
                    return {
                        "status": "cached",
                        "readiness_score": score,
                        "readiness_label": cached.get("readiness_label", "Unknown"),
                        "readiness_emoji": cached.get("readiness_emoji", "⚪"),
                        "quick_summary": summary,
                        "top_recommendation": cached.get("recommendations", ["Stay active!"])[0],
                        "cache_age_hours": round(age_hours, 1)
                    }
            except:
                pass
    
    # Run fresh analysis
    result = analyze_performance(tool_context, window_days=14)
    score = result.get("readiness_score", 50)
    
    if score >= 85:
        summary = "You're primed for a great session! 💪"
    elif score >= 70:
        summary = "Good to train with normal intensity."
    elif score >= 55:
        summary = "Moderate day - listen to your body."
    elif score >= 40:
        summary = "Consider lighter training."
    else:
        summary = "Rest day recommended."
    
    return {
        "status": "fresh",
        "readiness_score": score,
        "readiness_label": result.get("readiness_label", "Unknown"),
        "readiness_emoji": result.get("readiness_emoji", "⚪"),
        "quick_summary": summary,
        "top_recommendation": result.get("recommendations", ["Log a workout!"])[0]
    }


def get_training_recommendations(
    tool_context: Any,
    focus: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get training recommendations based on current analysis.
    
    Args:
        tool_context: Session context
        focus: Optional - "strength", "cardio", "recovery", "hiit"
    """
    # Get or run analysis
    cached = None
    if hasattr(tool_context, 'state'):
        cached = tool_context.state.get("app:latest_analysis")
    
    if not cached or cached.get("status") == "no_data":
        cached = analyze_performance(tool_context, window_days=28)

    readiness = cached.get("readiness_score", 50)
    risk = cached.get("risk_level", 0.0)
    general_recs = cached.get("recommendations", [])
    
    # Focus-specific recommendations
    focus_recs = []
    suggested_type = "moderate"
    intensity_rec = "moderate"
    duration_rec = "45-60 min"
    
    if focus:
        focus = focus.lower().strip()
        
        if focus == "strength":
            if readiness >= 80:
                focus_recs.append("💪 Great day for strength! Progressive overload time.")
                intensity_rec = "high"
                duration_rec = "60-75 min"
            elif readiness >= 60:
                focus_recs.append("💪 Moderate strength - focus on form.")
                intensity_rec = "moderate"
                duration_rec = "45-60 min"
            else:
                focus_recs.append("💪 Light strength only - bodyweight or light weights.")
                intensity_rec = "low"
                duration_rec = "30-40 min"
            suggested_type = "strength"
                
        elif focus == "cardio":
            if readiness >= 80:
                focus_recs.append("🏃 Ready for cardio intensity! Include intervals.")
                intensity_rec = "high"
            elif readiness >= 60:
                focus_recs.append("🏃 Steady-state cardio is perfect today.")
                intensity_rec = "moderate"
            else:
                focus_recs.append("🏃 Light cardio only - walking or easy cycling.")
                intensity_rec = "low"
            suggested_type = "cardio"
                
        elif focus in ["recovery", "rest"]:
            focus_recs.append("🧘 Active recovery - mobility, stretching, light movement.")
            suggested_type = "recovery"
            intensity_rec = "very low"
            duration_rec = "20-40 min"
            
        elif focus == "hiit":
            if readiness >= 80 and risk < 0.5:
                focus_recs.append("🔥 HIIT approved! Go hard.")
                intensity_rec = "very high"
            else:
                focus_recs.append("⚠️ HIIT not recommended today. Try steady-state.")
                suggested_type = "cardio"
                intensity_rec = "moderate"
    else:
        # General recommendation
        if readiness >= 85:
            suggested_type = "strength or intervals"
            intensity_rec = "high"
            focus_recs.append("🌟 Peak day - perfect for hard training!")
        elif readiness >= 70:
            suggested_type = "strength or cardio"
            intensity_rec = "moderate-high"
            focus_recs.append("💪 Solid day for quality training.")
        elif readiness >= 55:
            suggested_type = "cardio or technique"
            intensity_rec = "moderate"
            focus_recs.append("🎯 Focus on skill work or steady cardio.")
        else:
            suggested_type = "recovery or rest"
            intensity_rec = "low"
            focus_recs.append("🧘 Prioritize recovery today.")

    return {
        "status": "success",
        "readiness_score": readiness,
        "risk_level": risk,
        "general_recommendations": general_recs,
        "focus_recommendations": focus_recs,
        "suggested_workout_type": suggested_type,
        "intensity_recommendation": intensity_rec,
        "duration_recommendation": duration_rec
    }


def get_consistency_report(
    tool_context: Any,
    weeks: int = 4
) -> Dict[str, Any]:
    """Get detailed consistency report."""
    workouts = []
    
    if hasattr(tool_context, 'state'):
        workouts = tool_context.state.get("user:workout_log", [])
        temp = tool_context.state.get("temp:workout_history", [])
        workouts = workouts + temp
    
    if not workouts:
        return {
            "status": "no_data",
            "message": "No workout data found.",
            "weeks_analyzed": 0,
            "consistency_percent": 0,
            "consistency_label": "New",
            "total_workouts": 0
        }
    
    # Filter to window
    window_days = weeks * 7
    cutoff_date = datetime.now() - timedelta(days=window_days)
    
    filtered = []
    for w in workouts:
        date_str = w.get("date") or w.get("timestamp", "")
        if date_str:
            try:
                if parse_date(date_str) >= cutoff_date:
                    filtered.append(w)
            except:
                filtered.append(w)
    
    if not filtered:
        return {
            "status": "no_data",
            "message": f"No workouts in the last {weeks} weeks.",
            "weeks_analyzed": weeks,
            "consistency_percent": 0,
            "total_workouts": 0
        }
    
    # Group by week
    week_counts: Dict[str, int] = {}
    for w in filtered:
        date_str = w.get("date") or w.get("timestamp", "")
        if date_str:
            try:
                week_key = get_iso_week_key(date_str)
                week_counts[week_key] = week_counts.get(week_key, 0) + 1
            except:
                pass
    
    consistency_pct, total_weeks, label = calculate_consistency(
        filtered, target_per_week=ANALYZER_CONFIG["target_workouts_per_week"]
    )
    
    return {
        "status": "success",
        "weeks_analyzed": total_weeks,
        "consistency_percent": consistency_pct,
        "consistency_label": label,
        "weekly_breakdown": dict(sorted(week_counts.items())),
        "total_workouts": len(filtered),
        "avg_workouts_per_week": round(len(filtered) / max(total_weeks, 1), 1),
        "target_per_week": ANALYZER_CONFIG["target_workouts_per_week"]
    }


def log_workout_for_analysis(
    tool_context: Any,
    workout_type: str,
    duration_minutes: int,
    intensity: str = "moderate",
    sleep_hours: Optional[float] = None,
    fatigue_level: Optional[int] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Log a workout for analysis tracking.
    
    Call when user reports completing a workout.
    """
    workout = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "type": workout_type.lower(),
        "duration": duration_minutes,
        "intensity": intensity.lower(),
        "context": {},
        "notes": notes
    }
    
    if sleep_hours is not None:
        workout["context"]["sleep_hours"] = sleep_hours
    if fatigue_level is not None:
        workout["context"]["fatigue_level"] = fatigue_level
    
    if hasattr(tool_context, 'state'):
        # Add to history
        history = tool_context.state.get("temp:workout_history", [])
        history.append(workout)
        tool_context.state["temp:workout_history"] = history
        
        # Also to user log
        user_log = tool_context.state.get("user:workout_log", [])
        user_log.append(workout)
        tool_context.state["user:workout_log"] = user_log
        
        # Set current workout
        tool_context.state["temp:current_workout"] = workout
        
        # Invalidate cache
        tool_context.state["app:latest_analysis"] = None
    
    return {
        "status": "success",
        "message": f"✅ {workout_type.title()} logged: {duration_minutes} min at {intensity} intensity.",
        "workout_recorded": workout
    }


# =============================================================================
# ADK AGENT FACTORY
# =============================================================================
def create_analyzer_agent(
    use_memory_preload: bool = False
) -> Optional[Any]:
    """Create an ADK LlmAgent for performance analysis."""
    if not ADK_AVAILABLE:
        print("⚠️ ADK not available. Cannot create agent.")
        return None
    
    tools = [
        FunctionTool(func=analyze_performance),
        FunctionTool(func=get_readiness_quick),
        FunctionTool(func=get_training_recommendations),
        FunctionTool(func=get_consistency_report),
        FunctionTool(func=log_workout_for_analysis),
    ]
    
    if use_memory_preload:
        tools.append(preload_memory)
    else:
        tools.append(load_memory)
    
    agent = LlmAgent(
        name="PerformanceAnalyzer",
        model=Gemini(model="gemini-2.5-flash-lite"),
        description="Expert performance and recovery analyzer for FitForge AI.",
        instruction="""You are a sports science analyst for FitForge AI.

YOUR ROLE:
1. Analyze workout patterns and training load
2. Calculate readiness scores
3. Provide actionable recommendations
4. Monitor for overtraining risks
5. Track consistency

TOOLS:
- analyze_performance: Full analysis (readiness, recovery, status)
- get_readiness_quick: Fast "should I train?" check
- get_training_recommendations: What to do today
- get_consistency_report: Workout frequency tracking
- log_workout_for_analysis: Log new workouts

Be encouraging but honest about recovery needs. Safety first!""",
        tools=tools,
        output_key="analyzer_response"
    )
    
    print(f"✅ Analyzer Agent created with {len(tools)} tools")
    return agent


# =============================================================================
# EXPORTS
# =============================================================================
__all__ = [
    # Main tool functions
    "analyze_performance",
    "get_readiness_quick",
    "get_training_recommendations",
    "get_consistency_report",
    "log_workout_for_analysis",
    
    # Helper functions
    "calculate_consistency",
    "calculate_biometric_averages",
    "calculate_readiness_score",
    "generate_recommendations",
    "get_iso_week_key",
    "get_motivational_quote",
    
    # Agent factory
    "create_analyzer_agent",
    
    # Configuration
    "ANALYZER_CONFIG",
    "READINESS_LEVELS",
    
    # Flags
    "ADK_AVAILABLE",
    "MEMORY_MANAGER_AVAILABLE",
    "TRAINING_CALCULATOR_AVAILABLE",
]