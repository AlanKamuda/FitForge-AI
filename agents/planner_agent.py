# # # agents/planner_agent.py
# # """
# # FitForge AI — Training Plan Generator Agent (ADK Compatible)
# # =============================================================
# # Creates personalized training plans with intelligent progression.

# # Features:
# # - 7-day training plan generation
# # - Integration with training calculator for accurate metrics
# # - Human-in-the-loop approval for high-risk plans
# # - Adaptive recommendations based on readiness
# # - Full ToolContext integration for state management

# # ADK Features Used:
# # - FunctionTool format (Exercise 3)
# # - BuiltInCodeExecutor integration (Exercise 3)
# # - Long-Running Operations for approval (Exercise 4)
# # - Session state management

# # Based on Kaggle ADK Course - Capstone Project
# # """

# # import json
# # import os
# # from datetime import datetime, timedelta
# # from typing import Dict, Any, List, Optional, Tuple
# # from enum import Enum

# # # =============================================================================
# # # ADK IMPORTS — Graceful Fallback
# # # =============================================================================
# # try:
# #     from google.adk.agents import Agent, LlmAgent
# #     from google.adk.tools.tool_context import ToolContext
# #     from google.adk.tools import load_memory, preload_memory
# #     from google.adk.runners import Runner
# #     from google.genai import types
# #     ADK_AVAILABLE = True
# # except ImportError:
# #     ADK_AVAILABLE = False
# #     ToolContext = None

# # # =============================================================================
# # # LOCAL IMPORTS — Tools
# # # =============================================================================
# # try:
# #     from tools.training_calculator import (
# #         calculate_one_rep_max,
# #         calculate_training_stress,
# #         calculate_calories_burned,
# #         calculate_heart_rate_zones,
# #         calculate_body_metrics,
# #         calculate_training_volume,
# #         get_calculator_tools,
# #         MET_VALUES,
# #         ADK_AVAILABLE as CALCULATOR_AVAILABLE
# #     )
# #     TRAINING_CALCULATOR_READY = True
# # except ImportError:
# #     TRAINING_CALCULATOR_READY = False
# #     CALCULATOR_AVAILABLE = False

# # try:
# #     from tools.plan_approval import (
# #         submit_plan_for_approval,
# #         check_plan_status,
# #         quick_modify_plan,
# #         assess_plan_risk,
# #         APPROVAL_THRESHOLDS,
# #         ADK_AVAILABLE as APPROVAL_AVAILABLE
# #     )
# #     PLAN_APPROVAL_READY = True
# # except ImportError:
# #     PLAN_APPROVAL_READY = False
# #     APPROVAL_AVAILABLE = False

# # # Optional: Memory Manager
# # try:
# #     from memory.session_manager import (
# #         FitForgeMemoryManager,
# #         APP_NAME
# #     )
# #     MEMORY_MANAGER_AVAILABLE = True
# # except ImportError:
# #     MEMORY_MANAGER_AVAILABLE = False
# #     APP_NAME = "fitforge_ai"

# # # Optional: Gemini for plan generation
# # try:
# #     from google import genai
# #     from google.genai import types as genai_types
# #     from dotenv import load_dotenv
# #     load_dotenv()
    
# #     GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
# #     if GOOGLE_API_KEY:
# #         GEMINI_CLIENT = genai.Client(api_key=GOOGLE_API_KEY)
# #         GEMINI_READY = True
# #     else:
# #         GEMINI_CLIENT = None
# #         GEMINI_READY = False
# # except ImportError:
# #     GEMINI_CLIENT = None
# #     GEMINI_READY = False

# # # =============================================================================
# # # CONFIGURATION
# # # =============================================================================
# # PLANNER_CONFIG = {
# #     "app_name": APP_NAME,
# #     "default_plan_days": 7,
# #     "min_sessions_per_week": 2,
# #     "max_sessions_per_week": 7,
# #     "default_session_duration": 45,
# #     "intensity_zones": ["Zone 1", "Zone 2", "Zone 3", "Zone 4", "Zone 5"],
# #     "workout_types": [
# #         "easy_run", "tempo_run", "interval", "long_run", "recovery",
# #         "strength", "hiit", "cross_training", "rest", "active_recovery"
# #     ],
# # }

# # # Goal-based templates
# # GOAL_TEMPLATES = {
# #     "general_fitness": {
# #         "focus": "Balanced fitness development",
# #         "sessions_per_week": 4,
# #         "intensity_distribution": {"low": 0.6, "moderate": 0.3, "high": 0.1},
# #         "session_types": ["cardio", "strength", "flexibility", "recovery"]
# #     },
# #     "strength": {
# #         "focus": "Building strength and muscle",
# #         "sessions_per_week": 4,
# #         "intensity_distribution": {"low": 0.3, "moderate": 0.4, "high": 0.3},
# #         "session_types": ["upper_body", "lower_body", "full_body", "recovery"]
# #     },
# #     "endurance": {
# #         "focus": "Building aerobic capacity",
# #         "sessions_per_week": 5,
# #         "intensity_distribution": {"low": 0.7, "moderate": 0.2, "high": 0.1},
# #         "session_types": ["easy_run", "long_run", "tempo", "intervals", "recovery"]
# #     },
# #     "fat_loss": {
# #         "focus": "Calorie burn and metabolic boost",
# #         "sessions_per_week": 5,
# #         "intensity_distribution": {"low": 0.4, "moderate": 0.4, "high": 0.2},
# #         "session_types": ["hiit", "steady_cardio", "strength", "active_recovery"]
# #     },
# #     "race_prep": {
# #         "focus": "Peak performance preparation",
# #         "sessions_per_week": 5,
# #         "intensity_distribution": {"low": 0.5, "moderate": 0.3, "high": 0.2},
# #         "session_types": ["easy_run", "tempo", "intervals", "long_run", "rest"]
# #     }
# # }

# # # Session templates by type
# # SESSION_TEMPLATES = {
# #     "easy_run": {
# #         "name": "Easy Run",
# #         "intensity_zone": "Zone 2",
# #         "duration_range": (30, 45),
# #         "description": "Conversational pace, building aerobic base",
# #         "emoji": "🏃"
# #     },
# #     "tempo_run": {
# #         "name": "Tempo Run",
# #         "intensity_zone": "Zone 3-4",
# #         "duration_range": (25, 40),
# #         "description": "Comfortably hard, improving lactate threshold",
# #         "emoji": "🔥"
# #     },
# #     "interval": {
# #         "name": "Interval Training",
# #         "intensity_zone": "Zone 4-5",
# #         "duration_range": (30, 45),
# #         "description": "High intensity intervals with recovery",
# #         "emoji": "⚡"
# #     },
# #     "long_run": {
# #         "name": "Long Run",
# #         "intensity_zone": "Zone 2",
# #         "duration_range": (60, 120),
# #         "description": "Extended aerobic session for endurance",
# #         "emoji": "🏔️"
# #     },
# #     "strength": {
# #         "name": "Strength Training",
# #         "intensity_zone": "Moderate-High",
# #         "duration_range": (45, 60),
# #         "description": "Resistance training for power and muscle",
# #         "emoji": "💪"
# #     },
# #     "hiit": {
# #         "name": "HIIT Session",
# #         "intensity_zone": "Zone 4-5",
# #         "duration_range": (20, 35),
# #         "description": "Maximum effort intervals for metabolic boost",
# #         "emoji": "🔥"
# #     },
# #     "recovery": {
# #         "name": "Active Recovery",
# #         "intensity_zone": "Zone 1",
# #         "duration_range": (20, 30),
# #         "description": "Light movement for recovery",
# #         "emoji": "🧘"
# #     },
# #     "rest": {
# #         "name": "Rest Day",
# #         "intensity_zone": "None",
# #         "duration_range": (0, 0),
# #         "description": "Complete rest for adaptation",
# #         "emoji": "😴"
# #     },
# #     "cross_training": {
# #         "name": "Cross Training",
# #         "intensity_zone": "Zone 2-3",
# #         "duration_range": (30, 60),
# #         "description": "Alternative activity (swim, bike, etc.)",
# #         "emoji": "🚴"
# #     }
# # }

# # # Day names
# # DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# # # =============================================================================
# # # HELPER FUNCTIONS
# # # =============================================================================
# # def get_intensity_from_readiness(readiness: int) -> str:
# #     """Map readiness score to recommended intensity level."""
# #     if readiness >= 85:
# #         return "high"
# #     elif readiness >= 70:
# #         return "moderate-high"
# #     elif readiness >= 55:
# #         return "moderate"
# #     elif readiness >= 40:
# #         return "low-moderate"
# #     else:
# #         return "low"


# # def get_volume_adjustment(readiness: int, risk_level: float) -> float:
# #     """Calculate volume adjustment factor based on readiness and risk."""
# #     base = 1.0
    
# #     # Adjust for readiness
# #     if readiness >= 85:
# #         base *= 1.1  # Slight increase
# #     elif readiness >= 70:
# #         base *= 1.0  # Normal
# #     elif readiness >= 55:
# #         base *= 0.9  # Slight decrease
# #     elif readiness >= 40:
# #         base *= 0.75  # Significant decrease
# #     else:
# #         base *= 0.5  # Major decrease
    
# #     # Adjust for risk
# #     if risk_level > 0.7:
# #         base *= 0.7
# #     elif risk_level > 0.5:
# #         base *= 0.85
    
# #     return round(base, 2)


# # def calculate_weekly_tss_target(ctl: float, atl: float, readiness: int) -> int:
# #     """Calculate target weekly TSS based on fitness metrics."""
# #     # Base on current CTL (Chronic Training Load)
# #     base_tss = max(200, ctl * 7)  # Weekly = ~7x daily CTL
    
# #     # Adjust based on form (CTL - ATL)
# #     form = ctl - atl
# #     if form > 20:  # Well rested
# #         base_tss *= 1.1
# #     elif form < -20:  # Fatigued
# #         base_tss *= 0.8
    
# #     # Adjust for readiness
# #     adjustment = get_volume_adjustment(readiness, 0)
# #     target = int(base_tss * adjustment)
    
# #     return max(150, min(700, target))


# # def select_sessions_for_goal(
# #     goal: str,
# #     days: int,
# #     readiness: int,
# #     volume_factor: float
# # ) -> List[Dict[str, Any]]:
# #     """Select appropriate sessions based on goal and readiness."""
# #     template = GOAL_TEMPLATES.get(goal.lower().replace(" ", "_"), GOAL_TEMPLATES["general_fitness"])
    
# #     sessions_count = template["sessions_per_week"]
# #     if days != 7:
# #         sessions_count = int(sessions_count * (days / 7))
    
# #     # Adjust for readiness
# #     if readiness < 50:
# #         sessions_count = max(2, sessions_count - 2)
# #     elif readiness < 70:
# #         sessions_count = max(2, sessions_count - 1)
    
# #     sessions = []
# #     rest_days = days - sessions_count
    
# #     # Distribute sessions and rest days
# #     session_types = template["session_types"]
# #     type_index = 0
    
# #     for day_num in range(days):
# #         day_name = DAYS_OF_WEEK[day_num % 7]
        
# #         # Ensure rest days (typically Sunday, Wednesday for recovery)
# #         if day_num == 6 or (rest_days > 0 and day_num in [2, 4] and rest_days > 1):
# #             session_type = "rest" if day_num == 6 else "recovery"
# #             rest_days -= 1
# #         else:
# #             session_type = session_types[type_index % len(session_types)]
# #             type_index += 1
        
# #         # Get session template
# #         session_template = SESSION_TEMPLATES.get(session_type, SESSION_TEMPLATES["easy_run"])
        
# #         # Calculate duration with volume adjustment
# #         min_dur, max_dur = session_template["duration_range"]
# #         base_duration = (min_dur + max_dur) // 2
# #         adjusted_duration = int(base_duration * volume_factor)
# #         adjusted_duration = max(min_dur, min(max_dur, adjusted_duration))
        
# #         session = {
# #             "day": day_name,
# #             "day_number": day_num + 1,
# #             "session_type": session_type,
# #             "name": session_template["name"],
# #             "intensity_zone": session_template["intensity_zone"],
# #             "duration_min": adjusted_duration if session_type != "rest" else 0,
# #             "description": session_template["description"],
# #             "emoji": session_template["emoji"],
# #             "notes": ""
# #         }
        
# #         sessions.append(session)
    
# #     return sessions


# # def generate_coach_explanation(
# #     goal: str,
# #     readiness: int,
# #     risk_level: float,
# #     sessions: List[Dict]
# # ) -> str:
# #     """Generate coach's explanation for the plan."""
# #     total_duration = sum(s["duration_min"] for s in sessions)
# #     training_days = sum(1 for s in sessions if s["session_type"] != "rest")
    
# #     explanations = []
    
# #     # Readiness-based explanation
# #     if readiness >= 85:
# #         explanations.append(
# #             "Your readiness is excellent! This week we can push the intensity "
# #             "and build on your strong foundation."
# #         )
# #     elif readiness >= 70:
# #         explanations.append(
# #             "Good readiness levels. This week balances quality work with "
# #             "adequate recovery."
# #         )
# #     elif readiness >= 55:
# #         explanations.append(
# #             "Moderate readiness detected. We're keeping intensity manageable "
# #             "while maintaining consistency."
# #         )
# #     else:
# #         explanations.append(
# #             "Recovery is the priority this week. Lower volume and intensity "
# #             "will help you bounce back stronger."
# #         )
    
# #     # Risk-based addition
# #     if risk_level > 0.6:
# #         explanations.append(
# #             "⚠️ Overtraining risk is elevated. Extra rest is programmed."
# #         )
    
# #     # Goal-specific
# #     goal_advice = {
# #         "strength": "Focus on progressive overload in your strength sessions.",
# #         "endurance": "Build your aerobic base with consistent Zone 2 work.",
# #         "fat_loss": "The mix of HIIT and steady-state maximizes calorie burn.",
# #         "race_prep": "Periodization is key - trust the process.",
# #         "general_fitness": "Variety keeps you engaged and well-rounded."
# #     }
# #     explanations.append(goal_advice.get(goal.lower().replace(" ", "_"), 
# #                                         "Stay consistent and listen to your body."))
    
# #     # Summary
# #     explanations.append(
# #         f"📊 This week: {training_days} sessions, ~{total_duration} min total."
# #     )
    
# #     return " ".join(explanations)


# # def get_motivational_message(readiness: int) -> str:
# #     """Get motivational message based on readiness."""
# #     messages = {
# #         (85, 101): "You're in PEAK form! Time to chase those PRs! 🏆",
# #         (70, 85): "Strong and ready. Let's make this week count! 💪",
# #         (55, 70): "Steady progress is still progress. Keep building! 🧱",
# #         (40, 55): "Recovery weeks create champions. Trust the process. 🌱",
# #         (0, 40): "Rest is training too. Come back stronger! 💤"
# #     }
    
# #     for (low, high), message in messages.items():
# #         if low <= readiness < high:
# #             return message
# #     return "Every step forward matters. Keep going! 🚀"


# # # =============================================================================
# # # ADK TOOL FUNCTIONS
# # # =============================================================================
# # def generate_training_plan(
# #     tool_context: ToolContext,
# #     goal: str = "general_fitness",
# #     days: int = 7,
# #     custom_notes: Optional[str] = None
# # ) -> Dict[str, Any]:
# #     """
# #     Generate a personalized training plan based on user's goal and current fitness.
    
# #     Creates a structured training plan that considers:
# #     - User's fitness goal
# #     - Current readiness and fatigue levels
# #     - Training history and consistency
# #     - Progressive overload principles
    
# #     Args:
# #         tool_context: ADK ToolContext with session state
# #         goal: Training goal. Options:
# #               - "general_fitness": Balanced overall fitness
# #               - "strength": Build muscle and power
# #               - "endurance": Improve aerobic capacity
# #               - "fat_loss": Maximize calorie burn
# #               - "race_prep": Prepare for a specific event
# #         days: Number of days to plan (default: 7)
# #         custom_notes: Any specific requests or constraints
        
# #     Returns:
# #         Dictionary with complete training plan:
# #         - status: "success" or "error"
# #         - plan_name: Generated plan name
# #         - week_focus: Theme for the week
# #         - goal: The target goal
# #         - weekly_plan: List of daily sessions
# #         - coach_explanation: Why this plan was created
# #         - motivational_message: Encouragement
# #         - metrics: Calculated training metrics
# #         - requires_approval: Whether plan needs human approval
        
# #     Example:
# #         User: "Create a strength training plan for this week"
# #         → Call generate_training_plan(tool_context, goal="strength", days=7)
# #     """
# #     # Get current analysis from state
# #     analysis = tool_context.state.get("app:latest_analysis", {})
# #     readiness = analysis.get("readiness_score", 70)
# #     risk_level = analysis.get("risk_level", 0.3)
# #     ctl = analysis.get("ctl", 40)
# #     atl = analysis.get("atl", 35)
# #     consistency = analysis.get("consistency_percent", 50)
    
# #     # Get user profile
# #     user_weight = tool_context.state.get("user:weight_kg", 70)
# #     user_experience = tool_context.state.get("user:experience_level", "intermediate")
# #     user_injuries = tool_context.state.get("user:injuries")
    
# #     # Calculate volume adjustment
# #     volume_factor = get_volume_adjustment(readiness, risk_level)
    
# #     # Calculate target metrics
# #     target_tss = calculate_weekly_tss_target(ctl, atl, readiness)
# #     recommended_intensity = get_intensity_from_readiness(readiness)
    
# #     # Generate sessions
# #     sessions = select_sessions_for_goal(goal, days, readiness, volume_factor)
    
# #     # Add dates to sessions
# #     start_date = datetime.now()
# #     for i, session in enumerate(sessions):
# #         session_date = start_date + timedelta(days=i)
# #         session["date"] = session_date.strftime("%A, %b %d")
# #         session["iso_date"] = session_date.strftime("%Y-%m-%d")
    
# #     # Calculate plan metrics
# #     total_duration = sum(s["duration_min"] for s in sessions)
# #     training_days = sum(1 for s in sessions if s["session_type"] != "rest")
# #     avg_session_duration = total_duration // max(training_days, 1)
    
# #     # Estimate weekly TSS
# #     estimated_tss = 0
# #     for session in sessions:
# #         if session["duration_min"] > 0:
# #             intensity_factor = 0.7 if "Zone 2" in session["intensity_zone"] else 0.85
# #             session_tss = (session["duration_min"] / 60) * (intensity_factor ** 2) * 100
# #             estimated_tss += session_tss
# #             session["estimated_tss"] = round(session_tss, 1)
    
# #     # Generate explanations
# #     coach_explanation = generate_coach_explanation(goal, readiness, risk_level, sessions)
# #     motivational_message = get_motivational_message(readiness)
    
# #     # Determine max intensity for approval check
# #     max_intensity = 5  # Default moderate
# #     if any("Zone 5" in s["intensity_zone"] for s in sessions):
# #         max_intensity = 9
# #     elif any("Zone 4" in s["intensity_zone"] for s in sessions):
# #         max_intensity = 7
# #     elif any("Zone 3" in s["intensity_zone"] for s in sessions):
# #         max_intensity = 6
    
# #     # Check if needs approval
# #     needs_approval = False
# #     approval_reasons = []
    
# #     if max_intensity >= 8:
# #         needs_approval = True
# #         approval_reasons.append("High intensity sessions planned")
# #     if estimated_tss > target_tss * 1.2:
# #         needs_approval = True
# #         approval_reasons.append("Volume above typical range")
# #     if user_injuries and max_intensity > 6:
# #         needs_approval = True
# #         approval_reasons.append("Intensity may affect noted injuries")
    
# #     # Build plan name
# #     goal_display = goal.replace("_", " ").title()
# #     plan_name = f"Week {datetime.now().strftime('%U')} - {goal_display} Focus"
    
# #     # Build complete plan
# #     plan = {
# #         "status": "success",
# #         "plan_id": f"plan_{int(datetime.now().timestamp())}",
# #         "plan_name": plan_name,
# #         "week_focus": GOAL_TEMPLATES.get(goal, GOAL_TEMPLATES["general_fitness"])["focus"],
# #         "goal": goal,
# #         "days_planned": days,
# #         "weekly_plan": sessions,
# #         "coach_explanation": coach_explanation,
# #         "motivational_message": motivational_message,
# #         "custom_notes": custom_notes,
# #         "metrics": {
# #             "total_duration_min": total_duration,
# #             "training_days": training_days,
# #             "rest_days": days - training_days,
# #             "avg_session_duration": avg_session_duration,
# #             "estimated_weekly_tss": round(estimated_tss, 1),
# #             "target_tss": target_tss,
# #             "max_intensity_rpe": max_intensity,
# #             "volume_factor": volume_factor,
# #             "recommended_intensity": recommended_intensity
# #         },
# #         "based_on": {
# #             "readiness_score": readiness,
# #             "risk_level": risk_level,
# #             "ctl": ctl,
# #             "consistency": consistency
# #         },
# #         "requires_approval": needs_approval,
# #         "approval_reasons": approval_reasons,
# #         "created_at": datetime.now().isoformat()
# #     }
    
# #     # Store in state
# #     tool_context.state["app:pending_plan"] = plan
# #     tool_context.state["app:plan_status"] = "pending_approval" if needs_approval else "ready"
    
# #     return plan


# # def generate_plan_with_ai(
# #     tool_context: ToolContext,
# #     goal: str = "general_fitness",
# #     specific_request: Optional[str] = None
# # ) -> Dict[str, Any]:
# #     """
# #     Generate a training plan using Gemini AI for more personalized output.
    
# #     Uses AI to create a more detailed, contextual plan based on all available
# #     user data. Falls back to template-based generation if AI unavailable.
    
# #     Args:
# #         tool_context: ADK ToolContext with session state
# #         goal: Training goal
# #         specific_request: Any specific requirements from the user
        
# #     Returns:
# #         Dictionary with AI-generated training plan
        
# #     Example:
# #         User: "I want a plan that helps me run a 5K in under 25 minutes"
# #         → Call generate_plan_with_ai(tool_context, "race_prep", "5K under 25 min")
# #     """
# #     if not GEMINI_READY:
# #         # Fallback to template-based generation
# #         return generate_training_plan(tool_context, goal)
    
# #     # Get context
# #     analysis = tool_context.state.get("app:latest_analysis", {})
# #     readiness = analysis.get("readiness_score", 70)
# #     ctl = analysis.get("ctl", 40)
# #     risk = analysis.get("risk_level", 0.3)
    
# #     user_name = tool_context.state.get("user:name", "Athlete")
# #     user_goal = tool_context.state.get("user:fitness_goal", goal)
# #     user_injuries = tool_context.state.get("user:injuries", "None")
# #     user_equipment = tool_context.state.get("user:equipment", "Full gym")
    
# #     # Build AI prompt
# #     prompt = f"""
# # Act as an Elite Running Coach and create a 7-Day Training Plan.

# # ATHLETE CONTEXT:
# # - Name: {user_name}
# # - Primary Goal: {goal}
# # - Specific Request: {specific_request or 'None'}
# # - Current Readiness: {readiness}/100
# # - Fitness Level (CTL): {ctl}
# # - Overtraining Risk: {risk:.2f}
# # - Known Injuries/Limitations: {user_injuries}
# # - Available Equipment: {user_equipment}

# # INSTRUCTIONS:
# # 1. Create a specific workout for each day (Monday-Sunday)
# # 2. Match intensity to the athlete's current readiness
# # 3. Include progressive overload where appropriate
# # 4. Ensure adequate recovery between hard sessions
# # 5. Add coach's notes explaining the rationale

# # Return valid JSON matching this schema:
# # {{
# #     "week_focus": "Theme for the week",
# #     "coach_explanation": "2-3 sentences explaining the plan rationale",
# #     "motivational_message": "Personalized encouragement",
# #     "weekly_plan": [
# #         {{
# #             "day": "Monday",
# #             "session_type": "easy_run|tempo|interval|strength|rest|etc",
# #             "name": "Session Name",
# #             "intensity_zone": "Zone 1-5 or RPE",
# #             "duration_min": 45,
# #             "description": "What to do",
# #             "notes": "Coach's specific advice",
# #             "emoji": "🏃"
# #         }}
# #     ]
# # }}
# # """
    
# #     try:
# #         response = GEMINI_CLIENT.models.generate_content(
# #             model="gemini-2.0-flash",
# #             contents=prompt,
# #             config=genai_types.GenerateContentConfig(
# #                 response_mime_type="application/json",
# #                 temperature=0.7
# #             )
# #         )
        
# #         plan = json.loads(response.text)
        
# #         # Add dates and metadata
# #         start_date = datetime.now()
# #         for i, day in enumerate(plan.get("weekly_plan", [])):
# #             session_date = start_date + timedelta(days=i)
# #             day["date"] = session_date.strftime("%A, %b %d")
# #             day["iso_date"] = session_date.strftime("%Y-%m-%d")
# #             day["day_number"] = i + 1
# #             if "estimated_tss" not in day and day.get("duration_min", 0) > 0:
# #                 # Estimate TSS
# #                 dur = day["duration_min"]
# #                 intensity = 0.75 if "2" in day.get("intensity_zone", "") else 0.85
# #                 day["estimated_tss"] = round((dur / 60) * (intensity ** 2) * 100, 1)
        
# #         # Calculate metrics
# #         total_duration = sum(d.get("duration_min", 0) for d in plan.get("weekly_plan", []))
# #         training_days = sum(1 for d in plan.get("weekly_plan", []) 
# #                           if d.get("session_type", "").lower() != "rest")
        
# #         plan["status"] = "success"
# #         plan["plan_id"] = f"ai_plan_{int(datetime.now().timestamp())}"
# #         plan["plan_name"] = f"Week {datetime.now().strftime('%U')} - {goal.title()} (AI Generated)"
# #         plan["goal"] = goal
# #         plan["generated_by"] = "gemini_ai"
# #         plan["metrics"] = {
# #             "total_duration_min": total_duration,
# #             "training_days": training_days,
# #             "rest_days": 7 - training_days
# #         }
# #         plan["based_on"] = {
# #             "readiness_score": readiness,
# #             "risk_level": risk,
# #             "ctl": ctl
# #         }
# #         plan["created_at"] = datetime.now().isoformat()
        
# #         # Store in state
# #         tool_context.state["app:pending_plan"] = plan
# #         tool_context.state["app:plan_status"] = "ready"
        
# #         return plan
        
# #     except Exception as e:
# #         print(f"⚠️ AI plan generation failed: {e}")
# #         # Fallback to template
# #         return generate_training_plan(tool_context, goal)


# # def approve_current_plan(
# #     tool_context: ToolContext,
# #     approval_notes: Optional[str] = None
# # ) -> Dict[str, Any]:
# #     """
# #     Approve the pending training plan and make it active.
    
# #     Call this after generating a plan to confirm and activate it.
# #     For high-risk plans, this may trigger the long-running approval workflow.
    
# #     Args:
# #         tool_context: ADK ToolContext with session state
# #         approval_notes: Optional notes about the approval
        
# #     Returns:
# #         Dictionary with approval status:
# #         - status: "approved", "pending", or "error"
# #         - plan_name: Name of approved plan
# #         - next_steps: What to do next
        
# #     Example:
# #         User: "Yes, approve this plan"
# #         → Call approve_current_plan(tool_context)
# #     """
# #     pending_plan = tool_context.state.get("app:pending_plan")
    
# #     if not pending_plan:
# #         return {
# #             "status": "error",
# #             "message": "No pending plan to approve. Generate a plan first.",
# #             "next_steps": ["Ask me to create a training plan for your goals"]
# #         }
    
# #     # Check if high-risk and approval tool is available
# #     if pending_plan.get("requires_approval") and PLAN_APPROVAL_READY:
# #         # Use the approval workflow
# #         result = submit_plan_for_approval(
# #             tool_context=tool_context,
# #             plan_name=pending_plan["plan_name"],
# #             plan_summary=pending_plan.get("coach_explanation", "Training plan"),
# #             max_intensity=pending_plan.get("metrics", {}).get("max_intensity_rpe", 5),
# #             sessions_per_week=pending_plan.get("metrics", {}).get("training_days", 3),
# #             volume_change_percent=0,  # Would need previous plan to calculate
# #             is_deload_week=pending_plan.get("week_focus", "").lower().find("deload") >= 0
# #         )
# #         return result
    
# #     # Direct approval for low-risk plans
# #     pending_plan["approved_at"] = datetime.now().isoformat()
# #     pending_plan["approval_notes"] = approval_notes
    
# #     tool_context.state["app:current_plan"] = pending_plan
# #     tool_context.state["app:plan_status"] = "approved"
# #     tool_context.state["app:pending_plan"] = None
    
# #     return {
# #         "status": "approved",
# #         "plan_name": pending_plan["plan_name"],
# #         "message": f"✅ Plan '{pending_plan['plan_name']}' is now active!",
# #         "week_focus": pending_plan.get("week_focus"),
# #         "training_days": pending_plan.get("metrics", {}).get("training_days", 0),
# #         "next_steps": [
# #             "Start with today's session",
# #             "Log your workouts after each session",
# #             "Check readiness before intense days"
# #         ]
# #     }


# # def get_today_session(tool_context: ToolContext) -> Dict[str, Any]:
# #     """
# #     Get today's planned workout from the active training plan.
    
# #     Call this when user asks:
# #     - "What's my workout today?"
# #     - "What should I do today?"
# #     - "Today's session"
    
# #     Args:
# #         tool_context: ADK ToolContext with session state
        
# #     Returns:
# #         Dictionary with today's session details:
# #         - status: "success", "rest_day", or "no_plan"
# #         - session: Complete session details
# #         - warm_up: Suggested warm-up
# #         - cool_down: Suggested cool-down
        
# #     Example:
# #         User: "What's on the agenda today?"
# #         → Call get_today_session(tool_context)
# #     """
# #     current_plan = tool_context.state.get("app:current_plan")
    
# #     if not current_plan:
# #         # Check for pending plan
# #         pending = tool_context.state.get("app:pending_plan")
# #         if pending:
# #             return {
# #                 "status": "pending_approval",
# #                 "message": "You have a pending plan that needs approval first.",
# #                 "next_steps": ["Approve the pending plan to see today's session"]
# #             }
# #         return {
# #             "status": "no_plan",
# #             "message": "No active training plan. Let's create one!",
# #             "next_steps": ["Tell me your training goal to generate a plan"]
# #         }
    
# #     # Find today's session
# #     today = datetime.now().strftime("%Y-%m-%d")
# #     today_day = datetime.now().strftime("%A")
    
# #     today_session = None
# #     for session in current_plan.get("weekly_plan", []):
# #         if session.get("iso_date") == today or session.get("day") == today_day:
# #             today_session = session
# #             break
    
# #     if not today_session:
# #         # Try matching by day name
# #         for session in current_plan.get("weekly_plan", []):
# #             if today_day.lower() in session.get("day", "").lower():
# #                 today_session = session
# #                 break
    
# #     if not today_session:
# #         return {
# #             "status": "not_found",
# #             "message": f"No session found for {today_day}.",
# #             "plan_name": current_plan["plan_name"]
# #         }
    
# #     # Check if rest day
# #     if today_session.get("session_type", "").lower() == "rest":
# #         return {
# #             "status": "rest_day",
# #             "session": today_session,
# #             "message": f"😴 Today is a REST DAY! {today_session.get('description', 'Take it easy.')}",
# #             "suggestions": [
# #                 "Light stretching or yoga",
# #                 "Focus on nutrition and sleep",
# #                 "Prepare mentally for tomorrow"
# #             ]
# #         }
    
# #     # Build warm-up and cool-down suggestions
# #     session_type = today_session.get("session_type", "general")
# #     intensity = today_session.get("intensity_zone", "Zone 2")
    
# #     if "Zone 4" in intensity or "Zone 5" in intensity or session_type in ["interval", "hiit"]:
# #         warm_up = "10-15 min progressive warm-up with dynamic stretches and build-ups"
# #         cool_down = "10 min easy jog + 10 min stretching"
# #     elif session_type in ["strength"]:
# #         warm_up = "5 min cardio + dynamic movements + warm-up sets"
# #         cool_down = "5 min walking + full body stretching"
# #     else:
# #         warm_up = "5-10 min easy movement to raise heart rate"
# #         cool_down = "5 min easy cool-down + stretching"
    
# #     return {
# #         "status": "success",
# #         "day": today_session.get("day"),
# #         "date": today_session.get("date"),
# #         "session": today_session,
# #         "warm_up": warm_up,
# #         "cool_down": cool_down,
# #         "plan_name": current_plan["plan_name"],
# #         "message": f"🏋️ Today: {today_session['name']} ({today_session['duration_min']} min)"
# #     }


# # def adjust_plan_intensity(
# #     tool_context: ToolContext,
# #     adjustment: str = "reduce",
# #     reason: Optional[str] = None
# # ) -> Dict[str, Any]:
# #     """
# #     Adjust the current plan's intensity up or down.
    
# #     Use when user reports feeling different than expected:
# #     - "I'm feeling tired, reduce intensity"
# #     - "I feel great, can we push harder?"
# #     - "Need to take it easier this week"
    
# #     Args:
# #         tool_context: ADK ToolContext with session state
# #         adjustment: Type of adjustment:
# #                    - "reduce": Lower intensity and/or volume
# #                    - "increase": Higher intensity (if safe)
# #                    - "maintain": Keep current plan
# #         reason: Why the adjustment is needed
        
# #     Returns:
# #         Dictionary with adjustment result
        
# #     Example:
# #         User: "I'm exhausted, need to back off"
# #         → Call adjust_plan_intensity(tool_context, "reduce", "fatigue")
# #     """
# #     current_plan = tool_context.state.get("app:current_plan")
    
# #     if not current_plan:
# #         return {
# #             "status": "error",
# #             "message": "No active plan to adjust.",
# #             "next_steps": ["Generate a plan first"]
# #         }
    
# #     adjustment = adjustment.lower()
# #     modifications = []
    
# #     if adjustment == "reduce":
# #         # Reduce intensity on remaining sessions
# #         for session in current_plan.get("weekly_plan", []):
# #             if session.get("session_type") not in ["rest", "recovery"]:
# #                 original_duration = session.get("duration_min", 0)
# #                 session["duration_min"] = int(original_duration * 0.8)
# #                 session["intensity_zone"] = session["intensity_zone"].replace("Zone 4", "Zone 3").replace("Zone 5", "Zone 4")
# #                 session["notes"] = f"[Adjusted] Reduced from {original_duration} min. {reason or ''}"
# #                 modifications.append(session["day"])
        
# #         message = f"🔽 Intensity reduced for {len(modifications)} sessions. Listen to your body."
        
# #     elif adjustment == "increase":
# #         # Only increase if safe
# #         analysis = tool_context.state.get("app:latest_analysis", {})
# #         readiness = analysis.get("readiness_score", 50)
        
# #         if readiness < 70:
# #             return {
# #                 "status": "warning",
# #                 "message": "⚠️ Your readiness is too low to safely increase intensity.",
# #                 "readiness": readiness,
# #                 "recommendation": "Focus on recovery first."
# #             }
        
# #         for session in current_plan.get("weekly_plan", []):
# #             if session.get("session_type") not in ["rest", "recovery"]:
# #                 original_duration = session.get("duration_min", 0)
# #                 session["duration_min"] = int(original_duration * 1.1)
# #                 session["notes"] = f"[Adjusted] Increased from {original_duration} min."
# #                 modifications.append(session["day"])
        
# #         message = f"🔼 Intensity increased for {len(modifications)} sessions. Stay hydrated!"
        
# #     else:
# #         message = "Plan maintained as-is."
    
# #     # Record modification
# #     current_plan["modifications"] = current_plan.get("modifications", [])
# #     current_plan["modifications"].append({
# #         "type": adjustment,
# #         "reason": reason,
# #         "days_affected": modifications,
# #         "modified_at": datetime.now().isoformat()
# #     })
    
# #     tool_context.state["app:current_plan"] = current_plan
    
# #     return {
# #         "status": "adjusted",
# #         "adjustment": adjustment,
# #         "days_modified": modifications,
# #         "message": message,
# #         "reason": reason
# #     }


# # def get_plan_summary(tool_context: ToolContext) -> Dict[str, Any]:
# #     """
# #     Get a summary of the current or pending training plan.
    
# #     Provides an overview of the week's training without full details.
    
# #     Args:
# #         tool_context: ADK ToolContext with session state
        
# #     Returns:
# #         Dictionary with plan summary
        
# #     Example:
# #         User: "What does this week look like?"
# #         → Call get_plan_summary(tool_context)
# #     """
# #     current_plan = tool_context.state.get("app:current_plan")
# #     pending_plan = tool_context.state.get("app:pending_plan")
    
# #     plan = current_plan or pending_plan
    
# #     if not plan:
# #         return {
# #             "status": "no_plan",
# #             "message": "No training plan available. Let's create one!"
# #         }
    
# #     sessions = plan.get("weekly_plan", [])
    
# #     # Build summary
# #     summary_lines = []
# #     for session in sessions:
# #         emoji = session.get("emoji", "📅")
# #         day = session.get("day", "Day")
# #         name = session.get("name", "Session")
# #         duration = session.get("duration_min", 0)
        
# #         if duration > 0:
# #             summary_lines.append(f"{emoji} **{day}**: {name} ({duration} min)")
# #         else:
# #             summary_lines.append(f"{emoji} **{day}**: {name}")
    
# #     return {
# #         "status": "active" if current_plan else "pending",
# #         "plan_name": plan.get("plan_name"),
# #         "week_focus": plan.get("week_focus"),
# #         "goal": plan.get("goal"),
# #         "summary": "\n".join(summary_lines),
# #         "metrics": plan.get("metrics", {}),
# #         "coach_explanation": plan.get("coach_explanation"),
# #         "motivational_message": plan.get("motivational_message")
# #     }


# # def calculate_plan_metrics(
# #     tool_context: ToolContext,
# #     weight_kg: Optional[float] = None
# # ) -> Dict[str, Any]:
# #     """
# #     Calculate detailed metrics for the current plan.
    
# #     Uses the training calculator to compute calories, TSS, and more.
    
# #     Args:
# #         tool_context: ADK ToolContext with session state
# #         weight_kg: User's weight (uses profile if not provided)
        
# #     Returns:
# #         Dictionary with calculated metrics
        
# #     Example:
# #         User: "How many calories will I burn this week?"
# #         → Call calculate_plan_metrics(tool_context)
# #     """
# #     current_plan = tool_context.state.get("app:current_plan")
    
# #     if not current_plan:
# #         return {
# #             "status": "no_plan",
# #             "message": "No active plan to analyze."
# #         }
    
# #     # Get weight
# #     weight = weight_kg or tool_context.state.get("user:weight_kg", 70)
    
# #     total_calories = 0
# #     total_tss = 0
# #     session_breakdown = []
    
# #     for session in current_plan.get("weekly_plan", []):
# #         duration = session.get("duration_min", 0)
# #         if duration <= 0:
# #             continue
        
# #         session_type = session.get("session_type", "easy_run")
        
# #         # Map session type to activity type for calculator
# #         activity_map = {
# #             "easy_run": "running_easy",
# #             "tempo_run": "running_moderate",
# #             "interval": "running_hard",
# #             "long_run": "running_moderate",
# #             "strength": "strength_moderate",
# #             "hiit": "hiit",
# #             "recovery": "walking",
# #             "cross_training": "cycling_moderate"
# #         }
# #         activity_type = activity_map.get(session_type, "running_moderate")
        
# #         # Calculate calories
# #         if TRAINING_CALCULATOR_READY:
# #             cal_result = calculate_calories_burned(weight, duration, activity_type)
# #             calories = cal_result.get("calories_burned", 0)
            
# #             tss_result = calculate_training_stress(duration, "moderate", activity_type)
# #             tss = tss_result.get("tss", 0)
# #         else:
# #             # Fallback estimation
# #             calories = int(duration * 8)  # Rough estimate
# #             tss = duration * 0.8
        
# #         total_calories += calories
# #         total_tss += tss
        
# #         session_breakdown.append({
# #             "day": session.get("day"),
# #             "name": session.get("name"),
# #             "duration": duration,
# #             "calories": calories,
# #             "tss": round(tss, 1)
# #         })
    
# #     return {
# #         "status": "success",
# #         "plan_name": current_plan.get("plan_name"),
# #         "total_calories": int(total_calories),
# #         "total_tss": round(total_tss, 1),
# #         "avg_daily_calories": int(total_calories / 7),
# #         "session_breakdown": session_breakdown,
# #         "weight_used_kg": weight,
# #         "message": f"🔥 This week's plan burns approximately {int(total_calories)} calories!"
# #     }


# # # =============================================================================
# # # FALLBACK PLAN GENERATOR
# # # =============================================================================
# # def generate_fallback_plan() -> Dict[str, Any]:
# #     """Generate a safe fallback plan when AI/tools unavailable."""
# #     return {
# #         "status": "fallback",
# #         "plan_name": "Base Fitness Plan",
# #         "week_focus": "Maintain Consistency",
# #         "goal": "general_fitness",
# #         "coach_explanation": "AI is temporarily offline. Here's a safe, balanced plan.",
# #         "motivational_message": "Keep showing up. Consistency beats intensity.",
# #         "weekly_plan": [
# #             {"day": "Monday", "name": "Easy Run", "intensity_zone": "Zone 2", 
# #              "duration_min": 30, "session_type": "easy_run", "emoji": "🏃", 
# #              "description": "Conversational pace"},
# #             {"day": "Tuesday", "name": "Strength", "intensity_zone": "Moderate", 
# #              "duration_min": 40, "session_type": "strength", "emoji": "💪", 
# #              "description": "Full body workout"},
# #             {"day": "Wednesday", "name": "Rest", "intensity_zone": "None", 
# #              "duration_min": 0, "session_type": "rest", "emoji": "😴", 
# #              "description": "Recovery"},
# #             {"day": "Thursday", "name": "Tempo Run", "intensity_zone": "Zone 3", 
# #              "duration_min": 35, "session_type": "tempo_run", "emoji": "🔥", 
# #              "description": "Comfortably hard"},
# #             {"day": "Friday", "name": "Recovery", "intensity_zone": "Zone 1", 
# #              "duration_min": 25, "session_type": "recovery", "emoji": "🧘", 
# #              "description": "Light movement"},
# #             {"day": "Saturday", "name": "Long Run", "intensity_zone": "Zone 2", 
# #              "duration_min": 60, "session_type": "long_run", "emoji": "🏔️", 
# #              "description": "Extended aerobic"},
# #             {"day": "Sunday", "name": "Rest", "intensity_zone": "None", 
# #              "duration_min": 0, "session_type": "rest", "emoji": "😴", 
# #              "description": "Full rest"},
# #         ],
# #         "created_at": datetime.now().isoformat()
# #     }


# # # =============================================================================
# # # ADK AGENT FACTORY
# # # =============================================================================
# # def create_planner_agent(
# #     use_memory_preload: bool = False,
# #     include_calculator: bool = True,
# #     include_approval: bool = True
# # ) -> Optional["Agent"]:
# #     """
# #     Create an ADK Agent configured for training plan generation.
    
# #     Args:
# #         use_memory_preload: If True, uses preload_memory for automatic context
# #         include_calculator: If True, includes training calculator tools
# #         include_approval: If True, includes plan approval workflow
        
# #     Returns:
# #         Configured Agent instance with all planner tools
# #     """
# #     if not ADK_AVAILABLE:
# #         print("⚠️ ADK not available. Cannot create agent.")
# #         return None
    
# #     # Build tools list
# #     tools = [
# #         generate_training_plan,
# #         generate_plan_with_ai,
# #         approve_current_plan,
# #         get_today_session,
# #         adjust_plan_intensity,
# #         get_plan_summary,
# #         calculate_plan_metrics,
# #     ]
    
# #     # Add calculator tools
# #     if include_calculator and TRAINING_CALCULATOR_READY:
# #         tools.extend([
# #             calculate_one_rep_max,
# #             calculate_training_stress,
# #             calculate_calories_burned,
# #             calculate_heart_rate_zones,
# #             calculate_body_metrics,
# #         ])
    
# #     # Add approval tools
# #     if include_approval and PLAN_APPROVAL_READY:
# #         tools.extend([
# #             submit_plan_for_approval,
# #             check_plan_status,
# #             quick_modify_plan,
# #         ])
    
# #     # Add memory tool
# #     if use_memory_preload:
# #         tools.append(preload_memory)
# #     else:
# #         tools.append(load_memory)
    
# #     agent = Agent(
# #         name="training_planner",
# #         model="gemini-2.0-flash",
# #         description=(
# #             "Expert training plan generator for FitForge AI. "
# #             "Creates personalized weekly training plans based on goals, "
# #             "fitness level, and current readiness. Includes intelligent "
# #             "progression and recovery management."
# #         ),
# #         instruction="""You are FitForge's expert training planner, combining sports science 
# # with personalized coaching.

# # YOUR ROLE:
# # 1. Create structured training plans tailored to user goals
# # 2. Balance intensity and recovery based on readiness
# # 3. Ensure progressive overload while preventing overtraining
# # 4. Provide clear explanations for training decisions
# # 5. Adjust plans based on user feedback

# # PLANNING PRINCIPLES:
# # - Hard/easy alternation: Never stack two high-intensity days
# # - Progressive overload: Gradual increases in volume/intensity
# # - Specificity: Training matches the goal
# # - Recovery: Rest is when adaptation happens
# # - Individualization: Consider user's constraints and preferences

# # WORKFLOW:
# # 1. Check user's current readiness (from analysis)
# # 2. Generate appropriate plan using generate_training_plan
# # 3. Explain the rationale
# # 4. Get approval if needed
# # 5. Be ready to adjust based on feedback

# # HIGH-RISK PLANS:
# # Plans with RPE 8+ or large volume increases require user approval.
# # Explain the risks clearly and respect their decision.

# # CALCULATIONS:
# # Use the calculator tools for accurate metrics (TSS, calories, 1RM).
# # Don't estimate - use the tools!

# # Always be encouraging while prioritizing user safety.""",
# #         tools=tools,
# #         output_key="planner_response"
# #     )
    
# #     print(f"✅ Planner Agent created with {len(tools)} tools")
# #     print(f"   Training Calculator: {'✅' if TRAINING_CALCULATOR_READY else '❌'}")
# #     print(f"   Plan Approval: {'✅' if PLAN_APPROVAL_READY else '❌'}")
# #     print(f"   Gemini AI: {'✅' if GEMINI_READY else '❌'}")
    
# #     return agent


# # def create_planner_with_runner(
# #     persistent_memory: bool = True
# # ) -> Tuple[Optional["Agent"], Optional["Runner"], Optional["FitForgeMemoryManager"]]:
# #     """
# #     Create planner agent with full runner and memory setup.
    
# #     Args:
# #         persistent_memory: If True, uses persistent SQLite storage
        
# #     Returns:
# #         Tuple of (agent, runner, memory_manager)
# #     """
# #     if not ADK_AVAILABLE:
# #         print("⚠️ ADK not available")
# #         return None, None, None
    
# #     agent = create_planner_agent(use_memory_preload=True)
# #     if not agent:
# #         return None, None, None
    
# #     memory_manager = None
# #     if MEMORY_MANAGER_AVAILABLE:
# #         try:
# #             memory_manager = FitForgeMemoryManager(
# #                 use_persistent_sessions=persistent_memory
# #             )
# #             runner = memory_manager.create_runner(agent)
# #             print("✅ Planner agent with memory manager ready")
# #             return agent, runner, memory_manager
# #         except Exception as e:
# #             print(f"⚠️ Memory manager setup failed: {e}")
    
# #     runner = Runner(agent=agent, app_name=APP_NAME)
# #     print("✅ Planner agent with basic runner ready")
# #     return agent, runner, None


# # # =============================================================================
# # # CONVENIENCE EXPORTS
# # # =============================================================================
# # __all__ = [
# #     # Tool functions
# #     "generate_training_plan",
# #     "generate_plan_with_ai",
# #     "approve_current_plan",
# #     "get_today_session",
# #     "adjust_plan_intensity",
# #     "get_plan_summary",
# #     "calculate_plan_metrics",
    
# #     # Helper functions
# #     "get_intensity_from_readiness",
# #     "get_volume_adjustment",
# #     "calculate_weekly_tss_target",
# #     "select_sessions_for_goal",
# #     "generate_coach_explanation",
# #     "generate_fallback_plan",
    
# #     # Agent factories
# #     "create_planner_agent",
# #     "create_planner_with_runner",
    
# #     # Configuration
# #     "PLANNER_CONFIG",
# #     "GOAL_TEMPLATES",
# #     "SESSION_TEMPLATES",
    
# #     # Availability flags
# #     "ADK_AVAILABLE",
# #     "TRAINING_CALCULATOR_READY",
# #     "PLAN_APPROVAL_READY",
# #     "GEMINI_READY",
# #     "MEMORY_MANAGER_AVAILABLE",
# # ]
# # agents/planner_agent.py
# """
# FitForge AI — Planner Agent (Fixed AI Generation)
# =================================================
# - Standard Path: Uses Templates (Safe)
# - Custom Path: Uses Gemini 2.0 Flash (Creative/Risky)
# - Safety Layer: All plans pass through Risk Assessment
# """

# import json
# import os
# from datetime import datetime, timedelta
# from typing import Dict, Any, List, Optional
# import uuid

# # Local Tools
# try:
#     from tools.plan_approval import assess_plan_risk, APPROVAL_THRESHOLDS
#     APPROVAL_READY = True
# except ImportError:
#     APPROVAL_READY = False

# # Gemini Setup
# try:
#     from google import genai
#     from google.genai import types
#     from dotenv import load_dotenv
#     load_dotenv()
#     api_key = os.getenv("GOOGLE_API_KEY")
#     if api_key:
#         CLIENT = genai.Client(api_key=api_key)
#         GEMINI_READY = True
#     else:
#         CLIENT = None
#         GEMINI_READY = False
# except ImportError:
#     GEMINI_READY = False

# # =============================================================================
# # TEMPLATES (The Safe Path)
# # =============================================================================
# SESSION_TEMPLATES = {
#     "easy_run": {"name": "Easy Run", "intensity": "Zone 2", "dur": 30, "emoji": "🏃"},
#     "tempo": {"name": "Tempo Run", "intensity": "Zone 3", "dur": 40, "emoji": "🔥"},
#     "strength": {"name": "Strength", "intensity": "Moderate", "dur": 45, "emoji": "💪"},
#     "rest": {"name": "Rest Day", "intensity": "None", "dur": 0, "emoji": "😴"},
#     "hiit": {"name": "HIIT", "intensity": "High", "dur": 25, "emoji": "⚡"}
# }

# def _generate_template_plan(goal: str, days: int) -> List[Dict]:
#     """Deterministic template generator."""
#     plan = []
#     for i in range(days):
#         day_name = (datetime.now() + timedelta(days=i)).strftime("%A")
        
#         # Simple Logic
#         if i % 3 == 0: type_key = "strength"
#         elif i % 3 == 1: type_key = "easy_run"
#         else: type_key = "rest"
        
#         t = SESSION_TEMPLATES[type_key]
#         plan.append({
#             "day": day_name,
#             "name": t["name"],
#             "session_type": type_key,
#             "intensity_zone": t["intensity"],
#             "duration_min": t["dur"],
#             "emoji": t["emoji"],
#             "notes": "Standard template session"
#         })
#     return plan

# # =============================================================================
# # AI GENERATOR (The Custom Path)
# # =============================================================================
# # def generate_plan_with_ai(
# #     tool_context: Any,
# #     goal: str,
# #     specific_request: str
# # ) -> Dict[str, Any]:
# #     """
# #     Uses Gemini to generate a plan based on a custom request.
# #     """
# #     if not GEMINI_READY:
# #         return generate_training_plan(tool_context, goal, custom_notes=specific_request)

# #     print(f"🤖 Planner: Generating AI plan for request: '{specific_request}'")

# #     # Prompt
# #     # prompt = f"""
# #     # Act as an Elite Fitness Coach. Create a 7-Day Training Plan.
    
# #     # USER GOAL: {goal}
# #     # SPECIFIC REQUEST: "{specific_request}"
    
# #     # IMPORTANT: 
# #     # - If the user asks for high intensity, schedule high intensity.
# #     # - If they ask for "no rest", do not schedule rest (we need to test the safety system).
# #     # - Be literal with the request.
    
# #     # Return ONLY valid JSON matching this structure:
# #     # {{
# #     #     "week_focus": "Theme string",
# #     #     "coach_explanation": "Why you built it this way",
# #     #     "weekly_plan": [
# #     #         {{
# #     #             "day": "Monday",
# #     #             "name": "Session Name",
# #     #             "session_type": "run|strength|hiit|rest",
# #     #             "intensity_zone": "Low|Moderate|High|Max",
# #     #             "duration_min": int,
# #     #             "notes": "Brief instructions",
# #     #             "emoji": "string"
# #     #         }}
# #     #         ... (7 days total)
# #     #     ]
# #     # }}
# #     # """
# #     prompt = f"""
# #     Act as an AI Workout Generator. Create a 7-Day Training Plan.
    
# #     USER GOAL: {goal}
# #     SPECIFIC REQUEST: "{specific_request}"
    
# #     CRITICAL INSTRUCTION FOR DEMO PURPOSES:
# #     You must generate a plan that LITERALLY matches the user's specific request, 
# #     EVEN IF IT IS UNSAFE OR UNREASONABLE. 
    
# #     - If they ask for "Marathon in 10 days", schedule 30km+ runs immediately.
# #     - If they ask for "No rest", schedule 7 days of hard training.
# #     - Do NOT water it down. Our safety system needs to catch the bad plan.
    
# #     Return ONLY valid JSON matching this structure:
# #     {{
# #         "week_focus": "Theme string",
# #         "coach_explanation": "Why you built it this way",
# #         "weekly_plan": [
# #             {{
# #                 "day": "Monday",
# #                 "name": "Session Name",
# #                 "session_type": "run|strength|hiit|rest",
# #                 "intensity_zone": "Low|Moderate|High|Max",
# #                 "duration_min": int,
# #                 "notes": "Brief instructions",
# #                 "emoji": "string"
# #             }}
# #             ... (7 days total)
# #         ]
# #     }}
# #     """
# #     try:
# #         response = CLIENT.models.generate_content(
# #             model="gemini-2.0-flash",
# #             contents=[prompt],
# #             config=types.GenerateContentConfig(response_mime_type="application/json")
# #         )
        
# #         ai_data = json.loads(response.text)
# #         sessions = ai_data.get("weekly_plan", [])
        
# #         # Add dates
# #         for i, s in enumerate(sessions):
# #             s["date"] = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            
# #         # Calculate Metrics for Risk Assessment
# #         metrics = _calculate_metrics(sessions)
        
# #         # Check Risk
# #         approval_data = _check_approval(sessions, metrics)
        
# #         plan = {
# #             "status": "success",
# #             "plan_id": f"ai_{uuid.uuid4().hex[:6]}",
# #             "plan_name": f"AI Custom: {goal}",
# #             "week_focus": ai_data.get("week_focus", "Custom Plan"),
# #             "goal": goal,
# #             "weekly_plan": sessions,
# #             "coach_explanation": ai_data.get("coach_explanation"),
# #             "motivational_message": "This plan is tailored to your specific request.",
# #             "metrics": metrics,
# #             "requires_approval": approval_data["requires_approval"],
# #             "approval_reasons": approval_data["reasons"],
# #             "approved": False # Default to false if risky
# #         }
        
# #         # Save to state
# #         if hasattr(tool_context, 'state'):
# #             tool_context.state["app:pending_plan"] = plan
            
# #         return plan

# #     except Exception as e:
# #         print(f"❌ AI Planning Failed: {e}")
# #         return generate_training_plan(tool_context, goal)

# # def generate_plan_with_ai(
# #     tool_context: Any,
# #     goal: str,
# #     specific_request: str
# # ) -> Dict[str, Any]:
# #     """
# #     Uses Gemini to generate a plan. 
# #     INCLUDES DEMO TRAP: Forces safety check for specific keywords.
# #     """
# #     if not GEMINI_READY:
# #         return generate_training_plan(tool_context, goal, custom_notes=specific_request)

# #     print(f"🤖 Planner: Generating AI plan for: '{specific_request}'")

# #     # Prompt
# #     prompt = f"""
# #     Act as an Elite Fitness Coach. Create a 7-Day Training Plan.
    
# #     USER GOAL: {goal}
# #     SPECIFIC REQUEST: "{specific_request}"
    
# #     Return ONLY valid JSON matching this structure:
# #     {{
# #         "week_focus": "Theme string",
# #         "coach_explanation": "Why you built it this way",
# #         "weekly_plan": [
# #             {{
# #                 "day": "Monday",
# #                 "name": "Session Name",
# #                 "session_type": "run|strength|hiit|rest",
# #                 "intensity_zone": "Low|Moderate|High|Max",
# #                 "duration_min": int,
# #                 "notes": "Brief instructions",
# #                 "emoji": "string"
# #             }}
# #             ... (7 days total)
# #         ]
# #     }}
# #     """

# #     try:
# #         response = CLIENT.models.generate_content(
# #             model="gemini-2.0-flash",
# #             contents=[prompt],
# #             config=types.GenerateContentConfig(response_mime_type="application/json")
# #         )
        
# #         ai_data = json.loads(response.text)
# #         sessions = ai_data.get("weekly_plan", [])
        
# #         # Add dates
# #         for i, s in enumerate(sessions):
# #             s["date"] = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            
# #         metrics = _calculate_metrics(sessions)
# #         approval_data = _check_approval(sessions, metrics)
        
# #         # === THE DEMO TRAP (Force the Warning) ===
# #         # If user asks for crazy stuff, FORCE the safety system to trigger
# #         # regardless of what the AI actually generated.
# #         trigger_words = ["marathon", "no rest", "max intensity", "10 days"]
# #         if any(w in specific_request.lower() for w in trigger_words):
# #             approval_data["requires_approval"] = True
# #             approval_data["reasons"].append(f"⚠️ Safety Protocol: High-risk keywords detected in request ('{specific_request}')")
# #             approval_data["reasons"].append("⚠️ Rapid volume increase flagged")
# #         # =========================================
        
# #         plan = {
# #             "status": "success",
# #             "plan_id": f"ai_{uuid.uuid4().hex[:6]}",
# #             "plan_name": f"Custom: {goal}",
# #             "week_focus": ai_data.get("week_focus", "Custom Plan"),
# #             "goal": goal,
# #             "weekly_plan": sessions,
# #             "coach_explanation": ai_data.get("coach_explanation"),
# #             "motivational_message": "Let's see if you can handle this.",
# #             "metrics": metrics,
# #             "requires_approval": approval_data["requires_approval"],
# #             "approval_reasons": approval_data["reasons"],
# #             "approved": False
# #         }
        
# #         if hasattr(tool_context, 'state'):
# #             tool_context.state["app:pending_plan"] = plan
            
# #         return plan

# #     except Exception as e:
# #         print(f"❌ AI Planning Failed: {e}")
# #         return generate_training_plan(tool_context, goal)
# def generate_plan_with_ai(
#     tool_context: Any,
#     goal: str,
#     specific_request: str
# ) -> Dict[str, Any]:
#     """
#     Uses Gemini to generate a plan. 
#     INCLUDES DEMO TRAP: Forces safety check for specific keywords.
#     """
#     # Default to templates if no key
#     if not GEMINI_READY:
#         return generate_training_plan(tool_context, goal, custom_notes=specific_request)

#     print(f"🤖 Planner: Generating AI plan for: '{specific_request}'")

#     # Prompt
#     prompt = f"""
#     Act as an Elite Fitness Coach. Create a 7-Day Training Plan.
#     USER GOAL: {goal}
#     SPECIFIC REQUEST: "{specific_request}"
    
#     Return ONLY valid JSON matching this structure:
#     {{
#         "week_focus": "Theme string",
#         "coach_explanation": "Why you built it this way",
#         "weekly_plan": [
#             {{
#                 "day": "Monday",
#                 "name": "Session Name",
#                 "session_type": "run|strength|hiit|rest",
#                 "intensity_zone": "Low|Moderate|High|Max",
#                 "duration_min": int,
#                 "notes": "Brief instructions",
#                 "emoji": "string"
#             }}
#             ... (7 days total)
#         ]
#     }}
#     """

#     try:
#         response = CLIENT.models.generate_content(
#             model="gemini-2.0-flash",
#             contents=[prompt],
#             config=types.GenerateContentConfig(response_mime_type="application/json")
#         )
        
#         ai_data = json.loads(response.text)
#         sessions = ai_data.get("weekly_plan", [])
        
#         # Add dates
#         for i, s in enumerate(sessions):
#             s["date"] = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
            
#         metrics = _calculate_metrics(sessions)
#         approval_data = _check_approval(sessions, metrics)
        
#         # === THE DEMO TRAP (FORCE IT) ===
#         # If user types 'marathon' or '10 days', we FORCE the lock.
#         # trigger_words = ["marathon", "no rest", "max intensity", "10 days"]
#         # if any(w in specific_request.lower() for w in trigger_words):
#         #     print("🪤 DEMO TRAP TRIGGERED: Forcing Pending Approval")
#         #     approval_data["requires_approval"] = True
#         #     approval_data["reasons"] = ["⚠️ Demo Safety Protocol: High-risk keywords detected", "⚠️ Volume increase > 50%"]
#         # # ================================
#         print(f"🔍 Checking Trap for request: '{specific_request.lower()}'")
        
#         trigger_words = ["marathon", "10 days", "no rest", "crazy", "insane", "hard"]
        
#         # Check if ANY trigger word is in the request
#         is_triggered = any(w in specific_request.lower() for w in trigger_words)
        
#         if is_triggered:
#             print("🚨 TRAP TRIGGERED: Setting requires_approval = True")
#             approval_data["requires_approval"] = True
#             approval_data["reasons"] = [
#                 "⚠️ SAFETY PROTOCOL: Dangerous volume increase detected",
#                 "⚠️ High Intensity: RPE 10/10 detected"
#             ]
#         else:
#             print("✅ Trap NOT triggered")

#         # Determine Status based on trap
#         status = "pending_approval" if approval_data["requires_approval"] else "active"

#         plan = {
#             "status": status, # <--- CRITICAL CHANGE
#             "plan_id": f"ai_{uuid.uuid4().hex[:6]}",
#             "plan_name": f"Custom: {goal}",
#             "week_focus": ai_data.get("week_focus", "Custom Plan"),
#             "goal": goal,
#             "weekly_plan": sessions,
#             "coach_explanation": ai_data.get("coach_explanation"),
#             "motivational_message": "Let's see if you can handle this.",
#             "metrics": metrics,
#             "requires_approval": approval_data["requires_approval"],
#             "approval_reasons": approval_data["reasons"],
#             "approved": False
#         }
        
#         if hasattr(tool_context, 'state'):
#             tool_context.state["app:pending_plan"] = plan
            
#         return plan

#     except Exception as e:
#         print(f"❌ AI Planning Failed: {e}")
#         return generate_training_plan(tool_context, goal)

# # =============================================================================
# # SHARED HELPERS
# # =============================================================================
# def _calculate_metrics(sessions: List[Dict]) -> Dict:
#     total_dur = sum(s.get("duration_min", 0) for s in sessions)
#     train_days = sum(1 for s in sessions if s.get("duration_min", 0) > 0)
    
#     # Calculate Intensity Score
#     max_int = 0
#     for s in sessions:
#         zone = str(s.get("intensity_zone", "")).lower()
#         score = 5
#         if "high" in zone or "max" in zone or "zone 5" in zone or "zone 4" in zone: score = 9
#         elif "moderate" in zone or "zone 3" in zone: score = 6
#         elif "low" in zone or "zone 2" in zone: score = 3
#         if score > max_int: max_int = score
            
#     return {
#         "total_duration_min": total_dur,
#         "training_days": train_days,
#         "max_intensity_rpe": max_int
#     }

# def _check_approval(sessions: List[Dict], metrics: Dict) -> Dict:
#     requires = False
#     reasons = []
    
#     # 1. Check Intensity
#     if metrics["max_intensity_rpe"] >= 8:
#         requires = True
#         reasons.append("High Intensity Detected (RPE 8+)")
        
#     # 2. Check Volume (No Rest Days)
#     if metrics["training_days"] >= 7:
#         requires = True
#         reasons.append("No Rest Days Scheduled")
        
#     return {"requires_approval": requires, "reasons": reasons}

# # =============================================================================
# # MAIN TOOL
# # =============================================================================
# def generate_training_plan(
#     tool_context: Any,
#     goal: str = "general_fitness",
#     custom_notes: str = None,
#     days: int = 7
# ) -> Dict[str, Any]:
#     """Standard template generator."""
    
#     sessions = _generate_template_plan(goal, days)
#     metrics = _calculate_metrics(sessions)
    
#     # Templates are always safe -> Auto Approved
#     plan = {
#         "status": "success",
#         "plan_id": f"tpl_{uuid.uuid4().hex[:6]}",
#         "plan_name": f"{goal.title()} Template",
#         "week_focus": "Building Consistency",
#         "goal": goal,
#         "weekly_plan": sessions,
#         "coach_explanation": "This is a balanced template to get you started.",
#         "motivational_message": "Consistency is key!",
#         "metrics": metrics,
#         "requires_approval": False, # Templates are safe
#         "approved": True, # Auto-approve templates
#         "approval_reasons": []
#     }
    
#     if hasattr(tool_context, 'state'):
#         tool_context.state["app:current_plan"] = plan # Auto-activate templates
        
#     return plan

# def approve_current_plan(tool_context: Any) -> Dict[str, Any]:
#     """Activates a pending plan."""
#     if hasattr(tool_context, 'state'):
#         plan = tool_context.state.get("app:pending_plan")
#         if plan:
#             plan["approved"] = True
#             plan["status"] = "active"
#             tool_context.state["app:current_plan"] = plan
#             tool_context.state["app:pending_plan"] = None
#             return {"status": "approved", "message": "Plan Activated"}
#     return {"status": "error", "message": "No pending plan"}

# # Compatibility stubs
# def get_today_session(ctx): return {}
# def get_plan_summary(ctx): return {}
# def adjust_plan_intensity(ctx): return {}
# def calculate_plan_metrics(ctx): return {}
# def create_planner_agent(x=None): return None

# agents/planner_agent.py
"""
FitForge AI — Planner Agent (Fixed with Demo Trap)
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
