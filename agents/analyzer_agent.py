# # agents/analyzer_agent.py
# """
# FitForge AI — Performance & Recovery Analyzer Agent
# ADK-Integrated Analysis System

# Features:
# - Readiness Score 0–100 with smart calculations
# - ISO week-based consistency tracking  
# - Adaptive recommendations engine
# - Full ToolContext integration for state management
# - Cross-session memory support via ADK MemoryService

# Based on Kaggle ADK Course - Capstone Project
# """

# import statistics
# from datetime import datetime, timedelta
# from typing import Dict, Any, List, Optional, Tuple

# # =============================================================================
# # ADK IMPORTS — Graceful Fallback
# # =============================================================================
# try:
#     from google.adk.agents import Agent
#     from google.adk.tools.tool_context import ToolContext
#     from google.adk.tools import load_memory, preload_memory
#     from google.adk.runners import Runner
#     from google.genai import types
#     ADK_AVAILABLE = True
# except ImportError:
#     ADK_AVAILABLE = False
#     ToolContext = None  # Will use mock in tests

# # =============================================================================
# # LOCAL IMPORTS — Optional Dependencies
# # =============================================================================
# try:
#     from memory.session_manager import (
#         FitForgeMemoryManager,
#         save_analysis_results,
#         get_latest_analysis,
#         APP_NAME
#     )
#     MEMORY_MANAGER_AVAILABLE = True
# except ImportError:
#     MEMORY_MANAGER_AVAILABLE = False
#     APP_NAME = "fitforge_ai"

# try:
#     from tools.training_calculator import calculate_training_load
#     TRAINING_CALCULATOR_AVAILABLE = True
# except ImportError:
#     TRAINING_CALCULATOR_AVAILABLE = False

# # =============================================================================
# # CONFIGURATION — Tunable Parameters
# # =============================================================================
# ANALYZER_CONFIG = {
#     "app_name": APP_NAME,
#     "default_window_days": 28,
#     "min_samples_for_averages": 4,
#     "target_workouts_per_week": 3,
#     "optimal_sleep_hours": 7.5,
#     "fatigue_warning_threshold": 4,
#     "risk_weight": 60,
#     "sleep_weight": 10,
#     "fatigue_weight": 9,
#     "consistency_bonus": 30,
# }

# # Readiness thresholds and labels
# READINESS_LEVELS = {
#     "peak": {"min": 90, "label": "PEAK", "emoji": "🟢", "color": "green"},
#     "strong": {"min": 75, "label": "STRONG", "emoji": "🟢", "color": "green"},
#     "moderate": {"min": 60, "label": "MODERATE", "emoji": "🟡", "color": "yellow"},
#     "recover": {"min": 40, "label": "RECOVER", "emoji": "🟡", "color": "yellow"},
#     "rest": {"min": 0, "label": "REST NOW", "emoji": "🔴", "color": "red"},
# }

# # Consistency labels
# CONSISTENCY_LABELS = {
#     90: "Elite",
#     75: "Excellent",
#     50: "Strong",
#     25: "Building",
#     0: "Getting Started",
# }

# # =============================================================================
# # MOTIVATIONAL QUOTES DATABASE
# # =============================================================================
# MOTIVATIONAL_QUOTES = {
#     (90, 101): "You're not training — you're forging a legend. 🔥",
#     (75, 90): "Strong body, stronger mind. Keep stacking wins. 💪",
#     (60, 75): "Progress > perfection. You're still moving forward. 🚀",
#     (40, 60): "Rest is training too. The comeback is always stronger. 🌟",
#     (0, 40): "Recovery is where champions are made. Honor your body. 🧘",
# }

# DEFAULT_QUOTE = "Every champion was once tired. Keep going. 💫"


# # =============================================================================
# # HELPER FUNCTIONS — Date Utilities
# # =============================================================================
# def get_iso_week_key(date_str: str) -> str:
#     """
#     Convert date string to ISO week key.
    
#     Args:
#         date_str: Date in YYYY-MM-DD format (can include time)
        
#     Returns:
#         ISO week key (e.g., "2025-W01")
#     """
#     dt = datetime.fromisoformat(date_str[:10])
#     return dt.strftime("%G-W%V")  # %G = ISO year, %V = ISO week number


# def parse_date(date_str: str) -> datetime:
#     """Parse date string to datetime object."""
#     return datetime.fromisoformat(date_str[:10])


# def get_readiness_level(score: int) -> Dict[str, Any]:
#     """
#     Get readiness level details from score.
    
#     Args:
#         score: Readiness score 0-100
        
#     Returns:
#         Dictionary with label, emoji, color
#     """
#     for level_name, level_data in READINESS_LEVELS.items():
#         if score >= level_data["min"]:
#             return {
#                 "level": level_name,
#                 "label": level_data["label"],
#                 "emoji": level_data["emoji"],
#                 "color": level_data["color"]
#             }
#     return READINESS_LEVELS["rest"]


# def get_consistency_label(percent: int) -> str:
#     """Get consistency label from percentage."""
#     for threshold, label in sorted(CONSISTENCY_LABELS.items(), reverse=True):
#         if percent >= threshold:
#             return label
#     return "Getting Started"


# def get_motivational_quote(readiness: int) -> str:
#     """Get motivational quote based on readiness level."""
#     for (low, high), quote in MOTIVATIONAL_QUOTES.items():
#         if low <= readiness < high:
#             return quote
#     return DEFAULT_QUOTE


# # =============================================================================
# # CORE ANALYSIS FUNCTIONS
# # =============================================================================
# def calculate_consistency(
#     workouts: List[Dict[str, Any]],
#     target_per_week: int = 3
# ) -> Tuple[int, int, str]:
#     """
#     Calculate weekly workout consistency.
    
#     A "good week" is one where the user completed at least
#     the target number of workouts.
    
#     Args:
#         workouts: List of workout dictionaries with 'date' key
#         target_per_week: Minimum workouts for a "good" week
        
#     Returns:
#         Tuple of (consistency_percent, total_weeks, consistency_label)
#     """
#     if not workouts:
#         return 0, 0, "New"

#     # Group workouts by ISO week
#     week_counts: Dict[str, int] = {}
#     for workout in workouts:
#         date_str = workout.get("date") or workout.get("timestamp", "")
#         if date_str:
#             week_key = get_iso_week_key(date_str[:10])
#             week_counts[week_key] = week_counts.get(week_key, 0) + 1

#     total_weeks = len(week_counts)
#     if total_weeks == 0:
#         return 0, 0, "New"

#     # Count weeks that meet the target
#     good_weeks = sum(1 for count in week_counts.values() if count >= target_per_week) 
   
#     consistency_pct = round((good_weeks  / (total_weeks)) * 100) ###
    
#     return consistency_pct, total_weeks, get_consistency_label(consistency_pct)


# def calculate_biometric_averages(
#     workouts: List[Dict[str, Any]],
#     min_samples: int = 4
# ) -> Tuple[Optional[float], Optional[float]]:
#     """
#     Extract sleep and fatigue averages from workout context.
    
#     Only returns averages if minimum sample threshold is met,
#     ensuring statistical reliability.
    
#     Args:
#         workouts: List of workout dictionaries with 'context' key
#         min_samples: Minimum data points required
        
#     Returns:
#         Tuple of (avg_sleep_hours, avg_fatigue_level)
#         Either may be None if insufficient data
#     """
#     sleep_vals = []
#     fatigue_vals = []
    
#     for w in workouts:
#         context = w.get("context") or {}
        
#         sleep = context.get("sleep_hours")
#         if sleep is not None:
#             try:
#                 sleep_vals.append(float(sleep))
#             except (ValueError, TypeError):
#                 pass
                
#         fatigue = context.get("fatigue_level")
#         if fatigue is not None:
#             try:
#                 fatigue_vals.append(float(fatigue))
#             except (ValueError, TypeError):
#                 pass

#     avg_sleep = (
#         round(statistics.mean(sleep_vals), 1)
#         if len(sleep_vals) >= min_samples
#         else None
#     )

#     avg_fatigue = (
#         round(statistics.mean(fatigue_vals), 1)
#         if len(fatigue_vals) >= min_samples
#         else None
#     )

#     return avg_sleep, avg_fatigue


# def calculate_readiness_score(
#     risk: float = 0.0,
#     avg_sleep: Optional[float] = None,
#     avg_fatigue: Optional[float] = None,
#     consistency_pct: int = 0,
#     config: Dict[str, Any] = None
# ) -> Tuple[int, str, str]:
#     """
#     Calculate comprehensive readiness score (0-100).
    
#     The score is computed using:
#     - Base score of 100
#     - Risk penalty (up to -60 points)
#     - Sleep deficit penalty (up to -25 points)
#     - Fatigue penalty (up to -54 points)
#     - Consistency bonus (up to +30 points)
    
#     Args:
#         risk: Overtraining risk factor (0.0-1.0)
#         avg_sleep: Average sleep hours (or None)
#         avg_fatigue: Average fatigue level 1-10 (or None)
#         consistency_pct: Consistency percentage (0-100)
#         config: Optional config overrides
        
#     Returns:
#         Tuple of (readiness_score, readiness_label, readiness_emoji)
#     """
#     cfg = config or ANALYZER_CONFIG
#     readiness = 100.0

#     # === Penalties ===
#     # Risk penalty
#     readiness -= risk * cfg["risk_weight"]

#     # Sleep deficit penalty
#     if avg_sleep is not None:
#         sleep_deficit = max(0, cfg["optimal_sleep_hours"] - avg_sleep)
#         readiness -= sleep_deficit * cfg["sleep_weight"]

#     # Fatigue penalty
#     if avg_fatigue is not None:
#         fatigue_excess = max(0, avg_fatigue - cfg["fatigue_warning_threshold"])
#         readiness -= fatigue_excess * cfg["fatigue_weight"]

#     # === Bonus ===
#     readiness += (consistency_pct / 100) * cfg["consistency_bonus"]

#     # Clamp to valid range
#     readiness = max(5, min(100, int(readiness)))

#     # Get level details
#     level = get_readiness_level(readiness)
    
#     return readiness, level["label"], level["emoji"]


# def generate_recommendations(
#     readiness: int,
#     risk: float = 0.0,
#     avg_sleep: Optional[float] = None,
#     avg_fatigue: Optional[float] = None,
#     consistency_pct: int = 0
# ) -> List[str]:
#     """
#     Generate smart, context-aware recommendations.
    
#     Recommendations are prioritized:
#     1. Critical safety warnings
#     2. Training guidance
#     3. Sleep optimization
#     4. Fatigue management
#     5. Consistency encouragement
    
#     Args:
#         readiness: Calculated readiness score
#         risk: Overtraining risk factor
#         avg_sleep: Average sleep hours
#         avg_fatigue: Average fatigue level
#         consistency_pct: Consistency percentage
        
#     Returns:
#         List of recommendation strings with emojis
#     """
#     recs: List[str] = []

#     # === Priority 1: Safety & Critical Warnings ===
#     if readiness < 45:
#         recs.append(
#             "🔴 CRITICAL: Full rest or active recovery only. "
#             "Your body needs time to recover."
#         )
#     elif risk > 0.85:
#         recs.append(
#             "⚠️ Overtraining risk very high → "
#             "48h easy or complete rest recommended."
#         )
#     # === Priority 2: Training Guidance ===
#     elif readiness >= 88 and consistency_pct >= 80:
#         recs.append(
#             "🟢 PEAK READINESS → This is your supercompensation window. "
#             "Perfect day for a hard session!"
#         )
#     elif risk > 0.6:
#         recs.append(
#             "🟡 Moderate risk → Stick to Zone 2 cardio or technique work today."
#         )
#     elif readiness >= 75:
#         recs.append(
#             "🟢 Good to train → Push intensity, but listen to your body."
#         )
#     else:
#         recs.append(
#             "🟡 Light training day → Focus on movement quality over intensity."
#         )

#     # === Priority 3: Sleep Recommendations ===
#     if avg_sleep is not None:
#         if avg_sleep < 6.0:
#             recs.append(
#                 f"🚨 Sleep critical: {avg_sleep}h average is concerning → "
#                 "Prioritize 8+ hours tonight. Sleep is your #1 recovery tool."
#             )
#         elif avg_sleep < 7.0:
#             recs.append(
#                 f"😴 Sleep alert: {avg_sleep}h average → "
#                 "Try going to bed 30–60 min earlier."
#             )
#         elif avg_sleep >= 8.0:
#             recs.append("💤 Excellent sleep habits → Recovery is supercharged!")

#     # === Priority 4: Fatigue Management ===
#     if avg_fatigue is not None:
#         if avg_fatigue >= 8:
#             recs.append(
#                 "😰 Fatigue is critically high → Consider a mandatory deload week."
#             )
#         elif avg_fatigue >= 7:
#             recs.append(
#                 "😓 Fatigue is elevated → Schedule a deload day soon."
#             )
#         elif avg_fatigue <= 3:
#             recs.append(
#                 "⚡ Low fatigue detected → You have capacity for harder training."
#             )

#     # === Priority 5: Consistency Encouragement ===
#     if consistency_pct < 30 and readiness >= 60:
#         recs.append(
#             "📅 Consistency tip: Start with just 2-3 workouts/week to build the habit."
#         )
#     elif consistency_pct < 50 and readiness >= 60:
#         recs.append(
#             "📅 Building momentum: Aim for 3+ workouts/week for best results."
#         )
#     elif consistency_pct >= 90:
#         recs.append(
#             "🏆 Elite consistency! You're in the top tier of dedicated athletes."
#         )
#     elif consistency_pct >= 75:
#         recs.append(
#             "🌟 Great consistency! You're building serious fitness foundations."
#         )

#     return recs


# # =============================================================================
# # ADK TOOL FUNCTIONS — For Agent Integration
# # =============================================================================
# def analyze_performance(
#     tool_context: ToolContext,
#     window_days: int = 28
# ) -> Dict[str, Any]:
#     """
#     Analyze user's workout performance and recovery status.
    
#     Call this tool when user asks about:
#     - Their readiness to train
#     - Recovery status
#     - Training load analysis
#     - Performance trends
#     - Workout consistency
#     - "How am I doing?"
#     - "Should I train today?"
    
#     Args:
#         tool_context: ADK ToolContext with session state
#         window_days: Number of days to analyze (default: 28)
        
#     Returns:
#         Dictionary with comprehensive analysis including:
#         - readiness_score: 0-100 score indicating training readiness
#         - readiness_label: PEAK, STRONG, MODERATE, RECOVER, or REST NOW
#         - readiness_emoji: 🟢, 🟡, or 🔴
#         - recommendations: List of actionable training recommendations
#         - consistency_percent: Weekly workout consistency
#         - consistency_label: Elite, Excellent, Strong, Building, or Getting Started
#         - avg_sleep_hours: Average sleep (or null if insufficient data)
#         - avg_fatigue: Average fatigue level (or null if insufficient data)
#         - risk_level: Overtraining risk 0.0-1.0
#         - active_weeks: Number of weeks with logged workouts
        
#     Example:
#         User: "How's my recovery looking?"
#         → Call analyze_performance(tool_context, window_days=14)
#     """
#     # Get workout history from session state
#     workouts = tool_context.state.get("temp:workout_history", [])
    
#     # Try to get workouts from user's persistent data
#     user_workouts = tool_context.state.get("user:workout_log", [])
#     if user_workouts:
#         workouts = workouts + user_workouts
    
#     # Handle empty data
#     if not workouts:
#         result = {
#             "status": "no_data",
#             "analysis_window_days": window_days,
#             "readiness_score": 50,
#             "readiness_label": "Unknown",
#             "readiness_emoji": "⚪",
#             "risk_level": 0.0,
#             "consistency_percent": 0,
#             "consistency_label": "New",
#             "active_weeks": 0,
#             "avg_sleep_hours": None,
#             "avg_fatigue": None,
#             "recommendations": [
#                 "🏁 Log your first workout to get personalized analysis!",
#                 "💡 Include sleep hours and fatigue level for better insights.",
#                 "📊 Use 'log workout' to start tracking your training."
#             ],
#             "motivational_quote": "Every journey begins with a single step. 🚀",
#             "analyzed_at": datetime.now().isoformat()
#         }
#         tool_context.state["app:latest_analysis"] = result
#         return result
    
#     # Filter workouts to window
#     cutoff_date = datetime.now() - timedelta(days=window_days)
#     filtered_workouts = []
#     for w in workouts:
#         date_str = w.get("date") or w.get("timestamp", "")
#         if date_str:
#             try:
#                 workout_date = parse_date(date_str)
#                 if workout_date >= cutoff_date:
#                     filtered_workouts.append(w)
#             except (ValueError, TypeError):
#                 filtered_workouts.append(w)  # Include if can't parse date
    
#     # If all workouts filtered out, use what we have
#     if not filtered_workouts and workouts:
#         filtered_workouts = workouts[-10:]  # Last 10 workouts
    
#     # Calculate metrics
#     consistency_pct, total_weeks, consistency_label = calculate_consistency(
#         filtered_workouts,
#         target_per_week=ANALYZER_CONFIG["target_workouts_per_week"]
#     )
    
#     avg_sleep, avg_fatigue = calculate_biometric_averages(
#         filtered_workouts,
#         min_samples=ANALYZER_CONFIG["min_samples_for_averages"]
#     )
    
#     # Calculate risk from workout patterns
#     risk = _estimate_risk_from_workouts(filtered_workouts)
    
#     # Calculate readiness
#     readiness, readiness_label, readiness_emoji = calculate_readiness_score(
#         risk=risk,
#         avg_sleep=avg_sleep,
#         avg_fatigue=avg_fatigue,
#         consistency_pct=consistency_pct
#     )
    
#     # Generate recommendations
#     recommendations = generate_recommendations(
#         readiness=readiness,
#         risk=risk,
#         avg_sleep=avg_sleep,
#         avg_fatigue=avg_fatigue,
#         consistency_pct=consistency_pct
#     )
    
#     # Build result
#     result = {
#         "status": "success",
#         "analysis_window_days": window_days,
#         "total_workouts_analyzed": len(filtered_workouts),
#         "readiness_score": readiness,
#         "readiness_label": readiness_label,
#         "readiness_emoji": readiness_emoji,
#         "risk_level": round(risk, 3),
#         "consistency_percent": consistency_pct,
#         "consistency_label": consistency_label,
#         "active_weeks": total_weeks,
#         "avg_sleep_hours": avg_sleep,
#         "avg_fatigue": avg_fatigue,
#         "recommendations": recommendations,
#         "motivational_quote": get_motivational_quote(readiness),
#         "analyzed_at": datetime.now().isoformat()
#     }
    
#     # Save to session state for other agents
#     tool_context.state["app:latest_analysis"] = result
#     tool_context.state["app:analysis_timestamp"] = datetime.now().isoformat()
    
#     return result


# def _estimate_risk_from_workouts(workouts: List[Dict[str, Any]]) -> float:
#     """
#     Estimate overtraining risk from workout patterns.
    
#     Factors considered:
#     - Recent workout intensity
#     - Workout frequency
#     - Rest days
#     - Progressive overload patterns
#     """
#     if not workouts:
#         return 0.0
    
#     risk = 0.0
    
#     # Factor 1: High intensity frequency
#     high_intensity_count = sum(
#         1 for w in workouts[-7:]  # Last 7 workouts
#         if w.get("intensity", "").lower() in ["high", "max", "hard", "intense"]
#     )
#     if high_intensity_count >= 5:
#         risk += 0.4
#     elif high_intensity_count >= 3:
#         risk += 0.2
    
#     # Factor 2: Recent workout density (last 7 days)
#     recent_dates = set()
#     for w in workouts:
#         date_str = w.get("date") or w.get("timestamp", "")
#         if date_str:
#             try:
#                 workout_date = parse_date(date_str)
#                 if workout_date >= datetime.now() - timedelta(days=7):
#                     recent_dates.add(workout_date.date())
#             except (ValueError, TypeError):
#                 pass
    
#     if len(recent_dates) >= 7:  # Training every day
#         risk += 0.3
#     elif len(recent_dates) >= 6:
#         risk += 0.15
    
#     # Factor 3: Average fatigue from recent workouts
#     recent_fatigue = []
#     for w in workouts[-5:]:  # Last 5 workouts
#         context = w.get("context") or {}
#         fatigue = context.get("fatigue_level")
#         if fatigue is not None:
#             try:
#                 recent_fatigue.append(float(fatigue))
#             except (ValueError, TypeError):
#                 pass
    
#     if recent_fatigue:
#         avg_recent_fatigue = statistics.mean(recent_fatigue)
#         if avg_recent_fatigue >= 8:
#             risk += 0.3
#         elif avg_recent_fatigue >= 6:
#             risk += 0.15
    
#     return min(1.0, risk)  # Cap at 1.0


# def get_readiness_quick(tool_context: ToolContext) -> Dict[str, Any]:
#     """
#     Get quick readiness check without full analysis.
    
#     Call this for a fast readiness status when user asks:
#     - "Am I ready to train?"
#     - "Should I work out today?"
#     - "Quick status check"
#     - "How's my recovery?"
    
#     Uses cached analysis if available and recent (< 4 hours old).
    
#     Args:
#         tool_context: ADK ToolContext with session state
        
#     Returns:
#         Dictionary with:
#         - status: "cached" or "fresh"
#         - readiness_score: 0-100
#         - readiness_label: Current readiness level
#         - readiness_emoji: Visual indicator
#         - top_recommendation: Most important action item
#         - quick_summary: One-line summary
        
#     Example:
#         User: "Quick check - should I train?"
#         → Call get_readiness_quick(tool_context)
#     """
#     # Check for cached analysis (less than 4 hours old)
#     cached = tool_context.state.get("app:latest_analysis")
#     timestamp = tool_context.state.get("app:analysis_timestamp")
    
#     if cached and timestamp:
#         try:
#             analyzed_time = datetime.fromisoformat(timestamp)
#             age_hours = (datetime.now() - analyzed_time).total_seconds() / 3600
            
#             if age_hours < 4:
#                 score = cached.get("readiness_score", 50)
#                 label = cached.get("readiness_label", "Unknown")
#                 emoji = cached.get("readiness_emoji", "⚪")
#                 recs = cached.get("recommendations", [])
                
#                 # Generate quick summary
#                 if score >= 85:
#                     summary = "You're primed for a great session! 💪"
#                 elif score >= 70:
#                     summary = "Good to train with normal intensity."
#                 elif score >= 55:
#                     summary = "Moderate day - listen to your body."
#                 elif score >= 40:
#                     summary = "Consider lighter training or active recovery."
#                 else:
#                     summary = "Rest day recommended for optimal recovery."
                
#                 return {
#                     "status": "cached",
#                     "readiness_score": score,
#                     "readiness_label": label,
#                     "readiness_emoji": emoji,
#                     "top_recommendation": recs[0] if recs else "Stay active!",
#                     "quick_summary": summary,
#                     "cache_age_hours": round(age_hours, 1),
#                     "full_analysis_available": True
#                 }
#         except (ValueError, TypeError):
#             pass
    
#     # Run fresh analysis
#     result = analyze_performance(tool_context, window_days=14)
    
#     score = result.get("readiness_score", 50)
#     if score >= 85:
#         summary = "You're primed for a great session! 💪"
#     elif score >= 70:
#         summary = "Good to train with normal intensity."
#     elif score >= 55:
#         summary = "Moderate day - listen to your body."
#     elif score >= 40:
#         summary = "Consider lighter training or active recovery."
#     else:
#         summary = "Rest day recommended for optimal recovery."
    
#     return {
#         "status": "fresh",
#         "readiness_score": result.get("readiness_score", 50),
#         "readiness_label": result.get("readiness_label", "Unknown"),
#         "readiness_emoji": result.get("readiness_emoji", "⚪"),
#         "top_recommendation": result["recommendations"][0] if result.get("recommendations") else "Log a workout to get started!",
#         "quick_summary": summary,
#         "full_analysis_available": result.get("status") == "success"
#     }


# def get_training_recommendations(
#     tool_context: ToolContext,
#     focus: Optional[str] = None
# ) -> Dict[str, Any]:
#     """
#     Get training recommendations based on current analysis.
    
#     Call this when user asks for advice on:
#     - What to train today
#     - How hard to push
#     - Recovery suggestions
#     - Workout planning
#     - "What should I do today?"
    
#     Args:
#         tool_context: ADK ToolContext with session state
#         focus: Optional focus area - "strength", "cardio", "recovery", 
#                "flexibility", "hiit", or None for general
        
#     Returns:
#         Dictionary with:
#         - status: "success" or "no_data"
#         - readiness_score: Current readiness
#         - general_recommendations: Base recommendations from analysis
#         - focus_recommendations: Specific to requested focus
#         - suggested_workout_type: Recommended workout type for today
#         - intensity_recommendation: Suggested intensity level
#         - duration_recommendation: Suggested workout length
        
#     Example:
#         User: "What should my strength workout look like today?"
#         → Call get_training_recommendations(tool_context, focus="strength")
#     """
#     # Get or run analysis
#     cached = tool_context.state.get("app:latest_analysis")
    
#     if not cached or cached.get("status") == "no_data":
#         cached = analyze_performance(tool_context, window_days=28)

#     readiness = cached.get("readiness_score", 50)
#     risk = cached.get("risk_level", 0.0)
#     general_recs = cached.get("recommendations", [])
    
#     # Focus-specific recommendations
#     focus_recs = []
#     suggested_type = "moderate"
#     intensity_rec = "moderate"
#     duration_rec = "45-60 min"
    
#     if focus:
#         focus = focus.lower().strip()
        
#         if focus == "strength":
#             if readiness >= 80:
#                 focus_recs.append("💪 Great day for strength! Focus on compound movements with progressive overload.")
#                 focus_recs.append("🎯 Target: 3-5 sets of 4-8 reps at 75-85% max.")
#                 intensity_rec = "high"
#                 duration_rec = "60-75 min"
#             elif readiness >= 60:
#                 focus_recs.append("💪 Moderate strength session. Focus on form and controlled tempo.")
#                 focus_recs.append("🎯 Target: 3 sets of 8-12 reps at 65-75% max.")
#                 intensity_rec = "moderate"
#                 duration_rec = "45-60 min"
#             else:
#                 focus_recs.append("💪 Light strength work only. Bodyweight or light weights.")
#                 focus_recs.append("🎯 Focus on movement quality and muscle activation.")
#                 intensity_rec = "low"
#                 duration_rec = "30-40 min"
#             suggested_type = "strength"
                
#         elif focus == "cardio":
#             if readiness >= 80:
#                 focus_recs.append("🏃 Ready for cardio intensity! Include intervals or tempo work.")
#                 focus_recs.append("🎯 Try: 30-40 min with Zone 4 intervals.")
#                 intensity_rec = "high"
#                 duration_rec = "40-60 min"
#             elif readiness >= 60:
#                 focus_recs.append("🏃 Steady-state cardio is perfect today.")
#                 focus_recs.append("🎯 Target: Zone 2-3 for 30-45 minutes.")
#                 intensity_rec = "moderate"
#                 duration_rec = "30-45 min"
#             else:
#                 focus_recs.append("🏃 Light cardio only - walking, easy cycling, or swimming.")
#                 focus_recs.append("🎯 Keep heart rate in Zone 1-2.")
#                 intensity_rec = "low"
#                 duration_rec = "20-30 min"
#             suggested_type = "cardio"
                
#         elif focus == "recovery" or focus == "rest":
#             focus_recs.append("🧘 Active recovery focus - mobility, stretching, light movement.")
#             focus_recs.append("💆 Consider: yoga, foam rolling, walking, or swimming.")
#             focus_recs.append("🛁 Recovery boosters: contrast showers, massage, extra sleep.")
#             suggested_type = "recovery"
#             intensity_rec = "very low"
#             duration_rec = "20-40 min"
            
#         elif focus == "flexibility" or focus == "mobility":
#             focus_recs.append("🧘 Great choice! Flexibility work supports all training.")
#             focus_recs.append("🎯 Focus areas: hip flexors, thoracic spine, ankles, shoulders.")
#             focus_recs.append("⏱️ Hold stretches 30-60 seconds, 2-3 rounds each.")
#             suggested_type = "mobility"
#             intensity_rec = "low"
#             duration_rec = "20-30 min"
            
#         elif focus == "hiit":
#             if readiness >= 80 and risk < 0.5:
#                 focus_recs.append("🔥 HIIT approved! You have the capacity for high intensity.")
#                 focus_recs.append("🎯 Protocol: 20-30s work / 40-60s rest, 6-10 rounds.")
#                 intensity_rec = "very high"
#                 duration_rec = "25-35 min"
#             elif readiness >= 65:
#                 focus_recs.append("🔥 Modified HIIT - longer rest periods recommended.")
#                 focus_recs.append("🎯 Protocol: 20s work / 90s rest, 4-6 rounds.")
#                 intensity_rec = "moderate-high"
#                 duration_rec = "25-30 min"
#             else:
#                 focus_recs.append("⚠️ HIIT not recommended today. Switch to steady-state or recovery.")
#                 focus_recs.append("💡 Alternative: Low-intensity steady state (LISS) cardio.")
#                 suggested_type = "cardio"
#                 intensity_rec = "low"
#                 duration_rec = "30 min"
#             if suggested_type != "cardio":
#                 suggested_type = "hiit"
#     else:
#         # General recommendation based on readiness
#         if readiness >= 85:
#             suggested_type = "strength or intervals"
#             intensity_rec = "high"
#             duration_rec = "60-75 min"
#             focus_recs.append("🌟 Peak day - perfect for your hardest training!")
#         elif readiness >= 70:
#             suggested_type = "strength or cardio"
#             intensity_rec = "moderate-high"
#             duration_rec = "45-60 min"
#             focus_recs.append("💪 Solid day for quality training.")
#         elif readiness >= 55:
#             suggested_type = "cardio or technique"
#             intensity_rec = "moderate"
#             duration_rec = "30-45 min"
#             focus_recs.append("🎯 Focus on skill work or steady cardio.")
#         else:
#             suggested_type = "recovery or rest"
#             intensity_rec = "low"
#             duration_rec = "20-30 min"
#             focus_recs.append("🧘 Prioritize recovery today.")

#     return {
#         "status": "success",
#         "readiness_score": readiness,
#         "risk_level": risk,
#         "general_recommendations": general_recs,
#         "focus_recommendations": focus_recs,
#         "suggested_workout_type": suggested_type,
#         "intensity_recommendation": intensity_rec,
#         "duration_recommendation": duration_rec,
#         "analysis_summary": {
#             "label": cached.get("readiness_label"),
#             "emoji": cached.get("readiness_emoji"),
#             "consistency": cached.get("consistency_label")
#         }
#     }


# def get_consistency_report(
#     tool_context: ToolContext,
#     weeks: int = 4
# ) -> Dict[str, Any]:
#     """
#     Get detailed consistency report.
    
#     Call this when user asks about:
#     - Their workout frequency
#     - Training consistency
#     - Weekly workout counts
#     - "How consistent have I been?"
#     - "Show me my workout frequency"
    
#     Args:
#         tool_context: ADK ToolContext with session state
#         weeks: Number of weeks to report on (default: 4)
        
#     Returns:
#         Dictionary with:
#         - status: "success" or "no_data"
#         - weeks_analyzed: Number of weeks in report
#         - consistency_percent: Overall consistency percentage
#         - consistency_label: Elite, Excellent, Strong, Building, or Getting Started
#         - weekly_breakdown: Dict of week keys to workout counts
#         - total_workouts: Total workouts in period
#         - avg_workouts_per_week: Average workouts per week
#         - streak_info: Current and best workout streaks
#         - improvement_tips: Suggestions for better consistency
        
#     Example:
#         User: "How consistent have I been this month?"
#         → Call get_consistency_report(tool_context, weeks=4)
#     """
#     # Get workout data
#     workouts = tool_context.state.get("temp:workout_history", [])
#     user_workouts = tool_context.state.get("user:workout_log", [])
#     if user_workouts:
#         workouts = workouts + user_workouts
    
#     if not workouts:
#         return {
#             "status": "no_data",
#             "message": "No workout data found. Start logging to track consistency!",
#             "weeks_analyzed": 0,
#             "consistency_percent": 0,
#             "consistency_label": "New",
#             "total_workouts": 0,
#             "improvement_tips": [
#                 "📝 Log your first workout to start tracking!",
#                 "🎯 Start with a goal of 2-3 workouts per week.",
#                 "📅 Pick specific days for training to build the habit."
#             ]
#         }
    
#     # Filter to requested window
#     window_days = weeks * 7
#     cutoff_date = datetime.now() - timedelta(days=window_days)
    
#     filtered_workouts = []
#     for w in workouts:
#         date_str = w.get("date") or w.get("timestamp", "")
#         if date_str:
#             try:
#                 workout_date = parse_date(date_str)
#                 if workout_date >= cutoff_date:
#                     filtered_workouts.append(w)
#             except (ValueError, TypeError):
#                 filtered_workouts.append(w)
    
#     if not filtered_workouts:
#         return {
#             "status": "no_data",
#             "message": f"No workouts in the last {weeks} weeks.",
#             "weeks_analyzed": weeks,
#             "consistency_percent": 0,
#             "consistency_label": "Inactive",
#             "total_workouts": 0,
#             "improvement_tips": [
#                 "🔄 Time to get back on track!",
#                 "🎯 Start small - even one workout counts.",
#                 "💪 Every session builds momentum."
#             ]
#         }
    
#     # Group by week
#     week_counts: Dict[str, int] = {}
#     workout_dates = []
    
#     for workout in filtered_workouts:
#         date_str = workout.get("date") or workout.get("timestamp", "")
#         if date_str:
#             try:
#                 week_key = get_iso_week_key(date_str)
#                 week_counts[week_key] = week_counts.get(week_key, 0) + 1
#                 workout_dates.append(parse_date(date_str).date())
#             except (ValueError, TypeError):
#                 pass
    
#     # Calculate metrics
#     consistency_pct, total_weeks, label = calculate_consistency(
#         filtered_workouts,
#         target_per_week=ANALYZER_CONFIG["target_workouts_per_week"]
#     )
    
#     total_workouts = len(filtered_workouts)
#     avg_per_week = round(total_workouts / max(total_weeks, 1), 1)
    
#     # Calculate streaks
#     streak_info = _calculate_streaks(workout_dates)
    
#     # Generate improvement tips
#     improvement_tips = []
#     if consistency_pct < 50:
#         improvement_tips.append("📅 Try scheduling workouts like appointments.")
#         improvement_tips.append("🎯 Start with 3 workouts/week - it's the sweet spot for progress.")
#     elif consistency_pct < 75:
#         improvement_tips.append("💪 You're building momentum! Add one more session/week.")
#         improvement_tips.append("🏆 Consistency beats intensity - keep showing up!")
#     else:
#         improvement_tips.append("🌟 Elite consistency! Consider progressive overload now.")
#         improvement_tips.append("🔄 Maybe add variety to prevent plateaus.")
    
#     return {
#         "status": "success",
#         "weeks_analyzed": total_weeks,
#         "consistency_percent": consistency_pct,
#         "consistency_label": label,
#         "weekly_breakdown": dict(sorted(week_counts.items())),
#         "total_workouts": total_workouts,
#         "avg_workouts_per_week": avg_per_week,
#         "target_per_week": ANALYZER_CONFIG["target_workouts_per_week"],
#         "streak_info": streak_info,
#         "improvement_tips": improvement_tips
#     }


# def _calculate_streaks(workout_dates: List) -> Dict[str, Any]:
#     """Calculate current and best workout streaks."""
#     if not workout_dates:
#         return {"current_streak": 0, "best_streak": 0}
    
#     # Sort and dedupe dates
#     unique_dates = sorted(set(workout_dates), reverse=True)
    
#     if not unique_dates:
#         return {"current_streak": 0, "best_streak": 0}
    
#     # Calculate streaks (days with workouts in a row, allowing 1 rest day)
#     current_streak = 0
#     best_streak = 0
#     temp_streak = 1
    
#     today = datetime.now().date()
    
#     # Current streak
#     if unique_dates[0] >= today - timedelta(days=1):
#         current_streak = 1
#         for i in range(1, len(unique_dates)):
#             diff = (unique_dates[i-1] - unique_dates[i]).days
#             if diff <= 2:  # Allow 1 rest day
#                 current_streak += 1
#             else:
#                 break
    
#     # Best streak
#     for i in range(1, len(unique_dates)):
#         diff = (unique_dates[i-1] - unique_dates[i]).days
#         if diff <= 2:
#             temp_streak += 1
#             best_streak = max(best_streak, temp_streak)
#         else:
#             temp_streak = 1
    
#     best_streak = max(best_streak, current_streak, 1)
    
#     return {
#         "current_streak": current_streak,
#         "best_streak": best_streak,
#         "last_workout": unique_dates[0].isoformat() if unique_dates else None
#     }


# def log_workout_for_analysis(
#     tool_context: ToolContext,
#     workout_type: str,
#     duration_minutes: int,
#     intensity: str = "moderate",
#     sleep_hours: Optional[float] = None,
#     fatigue_level: Optional[int] = None,
#     notes: Optional[str] = None
# ) -> Dict[str, Any]:
#     """
#     Log a workout for analysis tracking.
    
#     Call this when user reports completing a workout:
#     - "I just did a 45 minute run"
#     - "Finished my strength workout"
#     - "Log my workout"
    
#     Args:
#         tool_context: ADK ToolContext with session state
#         workout_type: Type of workout (strength, cardio, hiit, yoga, etc.)
#         duration_minutes: How long the workout lasted
#         intensity: Perceived intensity (low, moderate, high, max)
#         sleep_hours: Last night's sleep (optional but recommended)
#         fatigue_level: Current fatigue 1-10 (optional but recommended)
#         notes: Any additional notes
        
#     Returns:
#         Dictionary with:
#         - status: "success"
#         - message: Confirmation message
#         - workout_id: ID for this workout
#         - quick_analysis: Brief analysis update
        
#     Example:
#         User: "Just did 60 min strength, slept 7 hours, fatigue is 5"
#         → Call log_workout_for_analysis(tool_context, "strength", 60, "high", 7.0, 5)
#     """
#     # Build workout record
#     workout = {
#         "date": datetime.now().strftime("%Y-%m-%d"),
#         "timestamp": datetime.now().isoformat(),
#         "type": workout_type.lower(),
#         "duration": duration_minutes,
#         "intensity": intensity.lower(),
#         "context": {},
#         "notes": notes
#     }
    
#     if sleep_hours is not None:
#         workout["context"]["sleep_hours"] = sleep_hours
#     if fatigue_level is not None:
#         workout["context"]["fatigue_level"] = fatigue_level
    
#     # Get or create workout history
#     history = tool_context.state.get("temp:workout_history", [])
#     history.append(workout)
#     tool_context.state["temp:workout_history"] = history
    
#     # Also store in user's persistent log
#     user_log = tool_context.state.get("user:workout_log", [])
#     user_log.append(workout)
#     tool_context.state["user:workout_log"] = user_log
    
#     # Update current workout reference
#     tool_context.state["temp:current_workout"] = workout
    
#     # Invalidate cached analysis
#     tool_context.state["app:latest_analysis"] = None
    
#     # Generate quick feedback
#     feedback = _generate_workout_feedback(workout, len(history))
    
#     return {
#         "status": "success",
#         "message": f"✅ {workout_type.title()} workout logged: {duration_minutes} min at {intensity} intensity.",
#         "workout_id": len(history),
#         "workout_recorded": workout,
#         "quick_feedback": feedback,
#         "tip": "Run 'analyze_performance' for full analysis update."
#     }


# def _generate_workout_feedback(workout: Dict, total_count: int) -> str:
#     """Generate quick feedback for logged workout."""
#     workout_type = workout.get("type", "workout")
#     duration = workout.get("duration", 0)
#     intensity = workout.get("intensity", "moderate")
    
#     feedbacks = []
    
#     # Duration feedback
#     if duration >= 60:
#         feedbacks.append("Great session length! 💪")
#     elif duration >= 45:
#         feedbacks.append("Solid workout duration. 👍")
#     elif duration >= 20:
#         feedbacks.append("Every minute counts! 🎯")
    
#     # Intensity feedback
#     if intensity in ["high", "max", "hard"]:
#         feedbacks.append("High intensity logged - remember to recover well.")
    
#     # Milestone feedback
#     if total_count == 1:
#         feedbacks.append("🎉 First workout logged! You're on your way!")
#     elif total_count == 10:
#         feedbacks.append("🏆 10 workouts logged! Consistency building!")
#     elif total_count == 25:
#         feedbacks.append("⭐ 25 workouts! You're committed!")
#     elif total_count == 50:
#         feedbacks.append("🔥 50 workouts! You're a machine!")
#     elif total_count % 10 == 0:
#         feedbacks.append(f"📊 {total_count} workouts tracked!")
    
#     return " ".join(feedbacks) if feedbacks else "Workout logged successfully!"


# # =============================================================================
# # ADK AGENT FACTORY
# # =============================================================================
# def create_analyzer_agent(
#     use_memory_preload: bool = False,
#     include_calculator: bool = True
# ) -> Optional["Agent"]:
#     """
#     Create an ADK Agent configured for performance analysis.
    
#     Args:
#         use_memory_preload: If True, uses preload_memory for automatic context
#         include_calculator: If True, includes training calculator tool
        
#     Returns:
#         Configured Agent instance with all analyzer tools, or None if ADK unavailable
#     """
#     if not ADK_AVAILABLE:
#         print("⚠️ ADK not available. Cannot create agent.")
#         return None
    
#     # Build tools list
#     tools = [
#         analyze_performance,
#         get_readiness_quick,
#         get_training_recommendations,
#         get_consistency_report,
#         log_workout_for_analysis,
#     ]
    
#     # Add memory tools
#     if use_memory_preload:
#         tools.append(preload_memory)
#     else:
#         tools.append(load_memory)
    
#     # Add training calculator if available
#     if include_calculator and TRAINING_CALCULATOR_AVAILABLE:
#         tools.append(calculate_training_load)
    
#     agent = Agent(
#         name="performance_analyzer",
#         model="gemini-2.0-flash",
#         description=(
#             "Expert performance and recovery analyzer. "
#             "Analyzes workout patterns to provide readiness scores, "
#             "training recommendations, and consistency insights. "
#             "Helps athletes optimize training and recovery."
#         ),
#         instruction="""You are an expert sports science analyst specializing in 
# training load management and recovery optimization for FitForge AI.

# YOUR ROLE:
# 1. Analyze workout patterns and training load
# 2. Calculate readiness scores based on sleep, fatigue, and consistency
# 3. Provide actionable, personalized recommendations
# 4. Monitor for overtraining risks
# 5. Track consistency and celebrate progress

# APPROACH:
# - Always be encouraging but honest about recovery needs
# - Safety comes first - never recommend training through warning signs
# - Use data to support your recommendations
# - Explain your reasoning in simple terms
# - Celebrate wins and progress, no matter how small

# TOOLS TO USE:
# - analyze_performance: For full analysis when asked about readiness, recovery, or status
# - get_readiness_quick: For quick "should I train?" questions
# - get_training_recommendations: When user asks what to do today
# - get_consistency_report: For workout frequency and habit tracking
# - log_workout_for_analysis: When user reports completing a workout

# Always gather data before making recommendations. When in doubt, prioritize recovery.""",
#         tools=tools,
#         output_key="analyzer_response"
#     )
    
#     print(f"✅ Analyzer Agent created with {len(tools)} tools")
#     return agent


# def create_analyzer_with_runner(
#     persistent_memory: bool = True
# ) -> Tuple[Optional["Agent"], Optional["Runner"], Optional["FitForgeMemoryManager"]]:
#     """
#     Create analyzer agent with full runner and memory setup.
    
#     Args:
#         persistent_memory: If True, uses persistent SQLite storage
        
#     Returns:
#         Tuple of (agent, runner, memory_manager) or (None, None, None)
#     """
#     if not ADK_AVAILABLE:
#         print("⚠️ ADK not available")
#         return None, None, None
    
#     # Create agent
#     agent = create_analyzer_agent(use_memory_preload=True)
#     if not agent:
#         return None, None, None
    
#     # Create memory manager if available
#     memory_manager = None
#     if MEMORY_MANAGER_AVAILABLE:
#         try:
#             memory_manager = FitForgeMemoryManager(
#                 use_persistent_sessions=persistent_memory
#             )
#             runner = memory_manager.create_runner(agent)
#             print("✅ Analyzer with memory manager ready")
#             return agent, runner, memory_manager
#         except Exception as e:
#             print(f"⚠️ Memory manager setup failed: {e}")
    
#     # Fallback to basic runner
#     runner = Runner(
#         agent=agent,
#         app_name=APP_NAME
#     )
#     print("✅ Analyzer with basic runner ready")
#     return agent, runner, None


# # =============================================================================
# # QUICK ANALYSIS FUNCTION
# # =============================================================================
# async def quick_analyze(
#     message: str = "How am I doing?",
#     user_id: str = "default_user",
#     session_id: str = "analyzer_session"
# ) -> str:
#     """
#     Quick analysis for testing or simple queries.
    
#     Args:
#         message: User's question
#         user_id: User identifier
#         session_id: Session identifier
        
#     Returns:
#         Agent's response text
#     """
#     if not ADK_AVAILABLE:
#         return "ADK not available for full analysis."
    
#     agent, runner, memory_manager = create_analyzer_with_runner(persistent_memory=False)
    
#     if not runner:
#         return "Could not create analyzer."
    
#     try:
#         if memory_manager:
#             session = await memory_manager.sessions.get_or_create_session(
#                 user_id=user_id,
#                 session_id=session_id
#             )
        
#         from google.genai import types
#         content = types.Content(
#             role="user",
#             parts=[types.Part(text=message)]
#         )
        
#         response_text = ""
#         async for event in runner.run_async(
#             user_id=user_id,
#             session_id=session_id,
#             new_message=content
#         ):
#             if hasattr(event, 'content') and event.content:
#                 if hasattr(event.content, 'parts'):
#                     for part in event.content.parts:
#                         if hasattr(part, 'text') and part.text:
#                             response_text += part.text
        
#         return response_text or "Analysis complete. Check your readiness score!"
        
#     except Exception as e:
#         return f"Analysis error: {str(e)}"


# # =============================================================================
# # CONVENIENCE EXPORTS
# # =============================================================================
# """
# For easy importing in other files:

# from agents.analyzer_agent import (
#     AnalyzerAgent,
#     analyze_performance,
#     get_readiness_quick,
#     get_training_recommendations,
#     create_analyzer_agent,
#     ANALYZER_CONFIG
# )
# """

# __all__ = [
#     # Tool functions (for ADK agents)
#     "analyze_performance",
#     "get_readiness_quick",
#     "get_training_recommendations",
#     "get_consistency_report",
#     "log_workout_for_analysis",
    
#     # Helper functions
#     "calculate_consistency",
#     "calculate_biometric_averages",
#     "calculate_readiness_score",
#     "generate_recommendations",
#     "get_iso_week_key",
#     "get_motivational_quote",
    
#     # Agent factories
#     "create_analyzer_agent",
#     "create_analyzer_with_runner",
#     "quick_analyze",
    
#     # Configuration
#     "ANALYZER_CONFIG",
#     "READINESS_LEVELS",
#     "CONSISTENCY_LABELS",
#     "MOTIVATIONAL_QUOTES",
    
#     # Availability flags
#     "ADK_AVAILABLE",
#     "MEMORY_MANAGER_AVAILABLE",
#     "TRAINING_CALCULATOR_AVAILABLE",
# ]

# agents/analyzer_agent.py
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