"""
FitForge AI — Nutrition & Recovery Agent
=========================================
Elite Macro & Recovery Nutrition Coach
"""

import json
import os
import re
import statistics
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

# =============================================================================
# ADK IMPORTS
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
    print("✅ Nutrition Agent: ADK components ready")
except ImportError as e:
    print(f"⚠️ Nutrition Agent: ADK not available: {e}")
    ToolContext = Any

# =============================================================================
# LOCAL IMPORTS
# =============================================================================
NUTRITION_PARSER_READY = False
PARSER_GEMINI_AVAILABLE = False
FOOD_DATABASE = {}

try:
    from tools.nutrition_parser import (
        parse_nutrition_text,
        calculate_daily_nutrition,
        suggest_meal_for_goal,
        parse_with_heuristics,
        NutritionEntry,
        FOOD_DATABASE,
        GEMINI_AVAILABLE as PARSER_GEMINI_AVAILABLE
    )
    NUTRITION_PARSER_READY = True
except ImportError:
    pass

# Memory Manager
MEMORY_MANAGER_AVAILABLE = False
try:
    from memory.session_manager import APP_NAME
    MEMORY_MANAGER_AVAILABLE = True
except ImportError:
    APP_NAME = "fitforge_ai"

# Gemini for advanced features
GEMINI_READY = False
GEMINI_CLIENT = None
try:
    from google import genai
    from google.genai import types as genai_types
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        GEMINI_CLIENT = genai.Client(api_key=api_key)
        GEMINI_READY = True
except ImportError:
    pass

print(f"🥗 Nutrition Agent: Parser={NUTRITION_PARSER_READY}, Gemini={GEMINI_READY}")

# =============================================================================
# CONFIGURATION
# =============================================================================
NUTRITION_CONFIG = {
    "app_name": APP_NAME,
    "default_bodyweight_kg": 75,
    "protein_per_kg_min": 1.6,
    "protein_per_kg_max": 2.2,
    "carb_target_active": 4.0,
    "carb_target_moderate": 3.0,
    "fat_target_percent": 0.25,
    "fiber_target_g": 30,
    "water_per_kg_ml": 35,
}

MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack", "pre_workout", "post_workout"]

RECOVERY_THRESHOLDS = {
    "elite": 90,
    "strong": 75,
    "moderate": 60,
    "needs_work": 0
}

MACRO_CALORIES = {
    "protein": 4,
    "carbs": 4,
    "fat": 9,
    "alcohol": 7
}

# Simple food database for fallback
SIMPLE_FOODS = {
    "egg": {"protein": 6, "carbs": 0.6, "fat": 5, "calories": 78},
    "eggs": {"protein": 6, "carbs": 0.6, "fat": 5, "calories": 78},
    "chicken": {"protein": 31, "carbs": 0, "fat": 3.6, "calories": 165},
    "chicken breast": {"protein": 31, "carbs": 0, "fat": 3.6, "calories": 165},
    "rice": {"protein": 2.7, "carbs": 28, "fat": 0.3, "calories": 130},
    "bread": {"protein": 4, "carbs": 20, "fat": 1, "calories": 80},
    "toast": {"protein": 4, "carbs": 20, "fat": 1, "calories": 80},
    "avocado": {"protein": 2, "carbs": 9, "fat": 15, "calories": 160},
    "banana": {"protein": 1.3, "carbs": 27, "fat": 0.4, "calories": 105},
    "oats": {"protein": 5, "carbs": 27, "fat": 3, "calories": 150},
    "oatmeal": {"protein": 5, "carbs": 27, "fat": 3, "calories": 150},
    "protein shake": {"protein": 25, "carbs": 5, "fat": 2, "calories": 130},
    "whey": {"protein": 25, "carbs": 5, "fat": 2, "calories": 130},
    "milk": {"protein": 8, "carbs": 12, "fat": 8, "calories": 150},
    "yogurt": {"protein": 10, "carbs": 7, "fat": 0, "calories": 100},
    "greek yogurt": {"protein": 17, "carbs": 6, "fat": 0, "calories": 100},
    "salmon": {"protein": 25, "carbs": 0, "fat": 13, "calories": 208},
    "beef": {"protein": 26, "carbs": 0, "fat": 15, "calories": 250},
    "steak": {"protein": 26, "carbs": 0, "fat": 15, "calories": 250},
    "pasta": {"protein": 7, "carbs": 43, "fat": 1, "calories": 200},
    "potato": {"protein": 2, "carbs": 21, "fat": 0, "calories": 90},
    "sweet potato": {"protein": 2, "carbs": 24, "fat": 0, "calories": 103},
    "broccoli": {"protein": 3, "carbs": 7, "fat": 0, "calories": 35},
    "salad": {"protein": 1, "carbs": 5, "fat": 0, "calories": 25},
    "apple": {"protein": 0.5, "carbs": 25, "fat": 0, "calories": 95},
    "orange": {"protein": 1, "carbs": 15, "fat": 0, "calories": 62},
    "coffee": {"protein": 0, "carbs": 0, "fat": 0, "calories": 2},
    "peanut butter": {"protein": 8, "carbs": 6, "fat": 16, "calories": 190},
    "almonds": {"protein": 6, "carbs": 6, "fat": 14, "calories": 164},
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def calculate_macro_targets(
    weight_kg: float,
    goal: str = "maintenance",
    activity_level: str = "moderate"
) -> Dict[str, Any]:
    """Calculate personalized macro targets."""
    
    # Protein per kg based on goal
    if goal in ["muscle_gain", "strength"]:
        protein_per_kg = 2.0
    elif goal == "fat_loss":
        protein_per_kg = 2.2
    else:
        protein_per_kg = 1.8
    
    protein_g = round(weight_kg * protein_per_kg)
    
    # Calorie targets
    if goal == "muscle_gain":
        calorie_multiplier = 35 if activity_level == "active" else 32
    elif goal == "fat_loss":
        calorie_multiplier = 24 if activity_level == "active" else 22
    else:
        calorie_multiplier = 30 if activity_level == "active" else 28
    
    target_calories = int(weight_kg * calorie_multiplier)
    
    # Fat and carbs
    fat_calories = target_calories * 0.28
    fat_g = round(fat_calories / 9)
    
    protein_calories = protein_g * 4
    carb_calories = target_calories - protein_calories - fat_calories
    carbs_g = round(carb_calories / 4)
    
    return {
        "calories": target_calories,
        "protein_g": protein_g,
        "carbs_g": carbs_g,
        "fat_g": fat_g,
        "fiber_g": NUTRITION_CONFIG["fiber_target_g"],
        "water_ml": int(weight_kg * NUTRITION_CONFIG["water_per_kg_ml"]),
        "based_on": {
            "weight_kg": weight_kg,
            "goal": goal,
            "activity_level": activity_level
        }
    }


def calculate_recovery_score(
    totals: Dict[str, Any],
    targets: Dict[str, Any],
    workout_intensity: str = "moderate"
) -> Dict[str, Any]:
    """Calculate recovery nutrition score."""
    
    protein_target = targets.get("protein_g", 120)
    carb_target = targets.get("carbs_g", 300)
    
    protein_intake = totals.get("total_protein_g", 0) or totals.get("protein_g", 0)
    carb_intake = totals.get("total_carbs_g", 0) or totals.get("carbs_g", 0)
    
    protein_score = min(100, (protein_intake / max(protein_target, 1)) * 100)
    carb_score = min(100, (carb_intake / max(carb_target, 1)) * 100)
    
    if workout_intensity in ["high", "hard", "intense"]:
        overall = (protein_score * 0.5 + carb_score * 0.5)
    else:
        overall = (protein_score * 0.6 + carb_score * 0.4)
    
    overall = round(overall)
    
    if overall >= RECOVERY_THRESHOLDS["elite"]:
        label, emoji = "Elite", "🏆"
    elif overall >= RECOVERY_THRESHOLDS["strong"]:
        label, emoji = "Strong", "💪"
    elif overall >= RECOVERY_THRESHOLDS["moderate"]:
        label, emoji = "Moderate", "👍"
    else:
        label, emoji = "Needs Work", "⚠️"
    
    advice = []
    if protein_score < 80:
        deficit = protein_target - protein_intake
        advice.append(f"Protein gap: {deficit:.0f}g more needed.")
    if carb_score < 70 and workout_intensity in ["high", "hard"]:
        advice.append("Carbs too low for recovery. Add rice, potato, or fruit.")
    if overall >= 90:
        advice.append("Perfect recovery fuel!")
    elif not advice:
        advice.append("Solid nutrition. Keep it consistent.")
    
    return {
        "recovery_score": overall,
        "label": label,
        "emoji": emoji,
        "protein_score": round(protein_score),
        "carb_score": round(carb_score),
        "protein_target_met": protein_intake >= protein_target * 0.9,
        "carb_target_met": carb_intake >= carb_target * 0.8,
        "advice": advice,
        "post_workout_optimal": protein_score >= 80 and carb_score >= 70
    }


def format_macro_summary(totals: Dict[str, Any]) -> str:
    """Format macro totals into readable summary."""
    calories = totals.get("total_calories", totals.get("calories", 0))
    protein = totals.get("total_protein_g", totals.get("protein_g", 0))
    carbs = totals.get("total_carbs_g", totals.get("carbs_g", 0))
    fat = totals.get("total_fat_g", totals.get("fat_g", 0))
    
    return f"🔥 {calories} kcal | 🥩 {protein}g P | 🍚 {carbs}g C | 🥑 {fat}g F"


def _fallback_parse_meal(text: str) -> Dict[str, Any]:
    """Fallback meal parser using simple food database."""
    if not text:
        return {"status": "error", "error_message": "No text provided"}
    
    text_lower = text.lower()
    totals = {"protein": 0, "carbs": 0, "fat": 0, "calories": 0}
    found = []
    
    for food, macros in SIMPLE_FOODS.items():
        if food in text_lower:
            # Try to find quantity
            qty_pattern = rf'(\d+)\s*(?:x\s*)?{re.escape(food)}'
            qty_match = re.search(qty_pattern, text_lower)
            qty = int(qty_match.group(1)) if qty_match else 1
            
            totals["protein"] += macros["protein"] * qty
            totals["carbs"] += macros["carbs"] * qty
            totals["fat"] += macros["fat"] * qty
            totals["calories"] += macros["calories"] * qty
            found.append(f"{qty}x {food}" if qty > 1 else food)
    
    if not found:
        # Estimate generic meal
        return {
            "status": "partial",
            "calories": 400,
            "protein_g": 20,
            "carbs_g": 40,
            "fat_g": 15,
            "ingredients": ["estimated meal"],
            "confidence": 0.2,
            "message": "Could not identify specific foods. Using estimate."
        }
    
    return {
        "status": "success",
        "calories": int(totals["calories"]),
        "protein_g": round(totals["protein"], 1),
        "carbs_g": round(totals["carbs"], 1),
        "fat_g": round(totals["fat"], 1),
        "ingredients": found,
        "confidence": 0.6
    }


def _get_meal_type_from_time() -> str:
    """Get meal type based on current time."""
    hour = datetime.now().hour
    if hour < 10:
        return "breakfast"
    elif hour < 14:
        return "lunch"
    elif hour < 17:
        return "snack"
    else:
        return "dinner"


# =============================================================================
# MAIN TOOL FUNCTIONS
# =============================================================================
def log_meal(
    tool_context: Any,
    meal_description: str,
    meal_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Log a meal by parsing its description.
    
    Args:
        tool_context: Session context
        meal_description: Natural language description (e.g., "2 eggs with toast")
        meal_type: Optional override (breakfast, lunch, dinner, snack, pre_workout, post_workout)
    
    Returns:
        Logged meal data with macros
    """
    if not meal_description:
        return {"status": "error", "error_message": "No meal description provided."}
    
    print(f"🥗 Logging meal: {meal_description[:50]}...")
    
    # Parse the meal
    if NUTRITION_PARSER_READY:
        try:
            parsed = parse_nutrition_text(meal_description)
        except:
            parsed = _fallback_parse_meal(meal_description)
    else:
        parsed = _fallback_parse_meal(meal_description)
    
    if parsed.get("status") == "error":
        return parsed
    
    # Determine meal type
    if meal_type:
        final_meal_type = meal_type.lower()
    elif parsed.get("meal_type") and parsed["meal_type"] != "unknown":
        final_meal_type = parsed["meal_type"]
    else:
        final_meal_type = _get_meal_type_from_time()
    
    # Build meal record
    meal_id = f"meal_{int(datetime.now().timestamp())}"
    
    meal_record = {
        "meal_id": meal_id,
        "meal_type": final_meal_type,
        "description": meal_description[:200],
        "calories": parsed.get("calories", 0),
        "protein_g": parsed.get("protein_g", 0),
        "carbs_g": parsed.get("carbs_g", 0),
        "fat_g": parsed.get("fat_g", 0),
        "fiber_g": parsed.get("fiber_g"),
        "ingredients": parsed.get("ingredients", []),
        "confidence": parsed.get("confidence", 0.5),
        "logged_at": datetime.now().isoformat()
    }
    
    # Get/create today's log
    today_key = datetime.now().strftime("%Y-%m-%d")
    daily_log_key = f"nutrition:{today_key}"
    
    if hasattr(tool_context, 'state'):
        daily_log = tool_context.state.get(daily_log_key, {
            "date": today_key,
            "meals": [],
            "total_calories": 0,
            "total_protein_g": 0,
            "total_carbs_g": 0,
            "total_fat_g": 0
        })
        
        # Add meal
        daily_log["meals"].append(meal_record)
        daily_log["total_calories"] += meal_record["calories"] or 0
        daily_log["total_protein_g"] += meal_record["protein_g"] or 0
        daily_log["total_carbs_g"] += meal_record["carbs_g"] or 0
        daily_log["total_fat_g"] += meal_record["fat_g"] or 0
        
        # Save
        tool_context.state[daily_log_key] = daily_log
        tool_context.state["nutrition:last_meal"] = meal_record
        tool_context.state["nutrition:last_meal_time"] = datetime.now().isoformat()
    else:
        daily_log = {"total_calories": meal_record["calories"], "total_protein_g": meal_record["protein_g"],
                     "total_carbs_g": meal_record["carbs_g"], "total_fat_g": meal_record["fat_g"], "meals": [meal_record]}
    
    # Tips
    tips = []
    if final_meal_type == "post_workout" and (meal_record["protein_g"] or 0) < 20:
        tips.append("💡 Post-workout meals should have 20-40g protein.")
    if final_meal_type == "breakfast" and (meal_record["protein_g"] or 0) < 15:
        tips.append("💡 More protein at breakfast helps control hunger.")
    
    macro_summary = f"🔥 {meal_record['calories']} kcal | 🥩 {meal_record['protein_g']}g P | 🍚 {meal_record['carbs_g']}g C | 🥑 {meal_record['fat_g']}g F"
    
    return {
        "status": "success",
        "meal_id": meal_id,
        "meal_type": final_meal_type,
        "macros": {
            "calories": meal_record["calories"],
            "protein_g": meal_record["protein_g"],
            "carbs_g": meal_record["carbs_g"],
            "fat_g": meal_record["fat_g"]
        },
        "ingredients": meal_record["ingredients"],
        "daily_running_total": {
            "calories": daily_log["total_calories"],
            "protein_g": round(daily_log["total_protein_g"], 1),
            "carbs_g": round(daily_log["total_carbs_g"], 1),
            "fat_g": round(daily_log["total_fat_g"], 1)
        },
        "meals_today": len(daily_log["meals"]),
        "message": f"✅ {final_meal_type.title()} logged! {macro_summary}",
        "tips": tips if tips else None,
        "confidence": meal_record["confidence"]
    }


def get_daily_nutrition_summary(
    tool_context: Any,
    include_recommendations: bool = True
) -> Dict[str, Any]:
    """
    Get summary of today's nutrition intake.
    
    Args:
        tool_context: Session context
        include_recommendations: Whether to include advice
    
    Returns:
        Daily totals, progress, and recommendations
    """
    today_key = datetime.now().strftime("%Y-%m-%d")
    daily_log_key = f"nutrition:{today_key}"
    
    daily_log = None
    if hasattr(tool_context, 'state'):
        daily_log = tool_context.state.get(daily_log_key)
    
    if not daily_log or not daily_log.get("meals"):
        return {
            "status": "no_data",
            "date": today_key,
            "message": "No meals logged today yet.",
            "tips": ["🍳 Log your first meal to start tracking!"]
        }
    
    # Get targets
    weight_kg = 75
    goal = "maintenance"
    activity = "moderate"
    
    if hasattr(tool_context, 'state'):
        weight_kg = tool_context.state.get("user:weight_kg", 75)
        goal = tool_context.state.get("user:fitness_goal", "maintenance")
        activity = tool_context.state.get("user:activity_level", "moderate")
    
    targets = calculate_macro_targets(weight_kg, goal, activity)
    
    totals = {
        "calories": daily_log["total_calories"],
        "protein_g": round(daily_log["total_protein_g"], 1),
        "carbs_g": round(daily_log["total_carbs_g"], 1),
        "fat_g": round(daily_log["total_fat_g"], 1)
    }
    
    # Progress
    progress = {
        "calories": round((totals["calories"] / max(targets["calories"], 1)) * 100),
        "protein": round((totals["protein_g"] / max(targets["protein_g"], 1)) * 100),
        "carbs": round((totals["carbs_g"] / max(targets["carbs_g"], 1)) * 100),
        "fat": round((totals["fat_g"] / max(targets["fat_g"], 1)) * 100)
    }
    
    # Recovery score
    recovery = calculate_recovery_score(totals, targets, "moderate")
    
    # Meal breakdown
    meal_breakdown = [
        {"type": m.get("meal_type", "unknown"), "calories": m.get("calories", 0)}
        for m in daily_log["meals"]
    ]
    
    # Recommendations
    recommendations = []
    if include_recommendations:
        remaining_protein = targets["protein_g"] - totals["protein_g"]
        remaining_calories = targets["calories"] - totals["calories"]
        
        if remaining_protein > 30:
            recommendations.append(f"🥩 Need ~{remaining_protein:.0f}g more protein.")
        if remaining_calories > 500:
            recommendations.append(f"🔥 ~{remaining_calories} kcal remaining.")
        if progress["protein"] >= 100:
            recommendations.append("✅ Protein target hit!")
        if not recommendations:
            recommendations.append("💪 On track! Keep it up.")
    
    return {
        "status": "success",
        "date": today_key,
        "totals": totals,
        "targets": targets,
        "progress": progress,
        "meals_logged": len(daily_log["meals"]),
        "meal_breakdown": meal_breakdown,
        "recovery_score": recovery["recovery_score"],
        "recovery_label": recovery["label"],
        "recovery_emoji": recovery["emoji"],
        "recommendations": recommendations,
        "summary": format_macro_summary(totals),
        "message": f"📊 Today: {format_macro_summary(totals)}"
    }


def get_macro_targets(
    tool_context: Any,
    weight_kg: Optional[float] = None,
    goal: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get personalized daily macro targets.
    
    Args:
        tool_context: Session context
        weight_kg: Body weight (uses profile if not provided)
        goal: Fitness goal override
    
    Returns:
        Calorie and macro targets
    """
    # Get from state or params
    weight = weight_kg
    user_goal = goal
    activity = "moderate"
    
    if hasattr(tool_context, 'state'):
        weight = weight or tool_context.state.get("user:weight_kg", 75)
        user_goal = user_goal or tool_context.state.get("user:fitness_goal", "maintenance")
        activity = tool_context.state.get("user:activity_level", "moderate")
    else:
        weight = weight or 75
        user_goal = user_goal or "maintenance"
    
    targets = calculate_macro_targets(weight, user_goal, activity)
    
    # Calculate ratios
    total_cals = targets["protein_g"] * 4 + targets["carbs_g"] * 4 + targets["fat_g"] * 9
    ratios = {
        "protein_percent": round((targets["protein_g"] * 4 / max(total_cals, 1)) * 100),
        "carbs_percent": round((targets["carbs_g"] * 4 / max(total_cals, 1)) * 100),
        "fat_percent": round((targets["fat_g"] * 9 / max(total_cals, 1)) * 100)
    }
    
    # Save to state
    if hasattr(tool_context, 'state'):
        tool_context.state["user:macro_targets"] = targets
    
    return {
        "status": "success",
        "daily_targets": {
            "calories": targets["calories"],
            "protein_g": targets["protein_g"],
            "carbs_g": targets["carbs_g"],
            "fat_g": targets["fat_g"],
            "fiber_g": targets["fiber_g"]
        },
        "macro_ratios": ratios,
        "hydration": {
            "water_ml": targets["water_ml"],
            "water_liters": round(targets["water_ml"] / 1000, 1)
        },
        "based_on": targets["based_on"],
        "message": f"🎯 Daily: {targets['calories']} kcal, {targets['protein_g']}g protein"
    }


def suggest_next_meal(
    tool_context: Any,
    specific_goal: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get meal suggestions based on current nutrition status.
    
    Args:
        tool_context: Session context
        specific_goal: Focus (high_protein, pre_workout, post_workout, low_calorie)
    
    Returns:
        Meal suggestions with reasoning
    """
    summary = get_daily_nutrition_summary(tool_context, include_recommendations=False)
    
    # Get remaining budget
    if summary.get("status") == "success":
        targets = summary.get("targets", {})
        totals = summary.get("totals", {})
        remaining_cals = targets.get("calories", 2000) - totals.get("calories", 0)
        remaining_protein = targets.get("protein_g", 120) - totals.get("protein_g", 0)
    else:
        remaining_cals = 800
        remaining_protein = 40
    
    # Determine meal type from time
    hour = datetime.now().hour
    if hour < 10:
        suggested_meal = "breakfast"
    elif hour < 14:
        suggested_meal = "lunch"
    elif hour < 17:
        suggested_meal = "snack"
    else:
        suggested_meal = "dinner"
    
    # Suggestions based on needs
    need_protein = remaining_protein > 30
    
    if need_protein or specific_goal == "high_protein":
        suggestions = [
            {"name": "Grilled Chicken & Rice", "cals": 500, "protein": 40, "desc": "Classic high-protein"},
            {"name": "Salmon with Veggies", "cals": 450, "protein": 35, "desc": "Omega-3 rich"},
            {"name": "Greek Yogurt Bowl", "cals": 300, "protein": 25, "desc": "Quick protein boost"},
            {"name": "Protein Shake + Banana", "cals": 250, "protein": 28, "desc": "Fast and easy"},
        ]
    elif specific_goal == "low_calorie" or remaining_cals < 400:
        suggestions = [
            {"name": "Salad with Chicken", "cals": 300, "protein": 25, "desc": "Light but filling"},
            {"name": "Egg White Omelette", "cals": 200, "protein": 20, "desc": "Low calorie, high protein"},
            {"name": "Veggie Stir Fry", "cals": 250, "protein": 8, "desc": "Nutrient dense"},
        ]
    else:
        suggestions = [
            {"name": "Balanced Bowl", "cals": 500, "protein": 30, "desc": "Rice, protein, veggies"},
            {"name": "Pasta with Meat Sauce", "cals": 600, "protein": 25, "desc": "Carb-rich meal"},
            {"name": "Sandwich & Soup", "cals": 450, "protein": 20, "desc": "Comfort food combo"},
        ]
    
    reasoning = []
    if remaining_protein > 30:
        reasoning.append(f"Need ~{remaining_protein:.0f}g more protein today.")
    if remaining_cals > 500:
        reasoning.append(f"~{remaining_cals} kcal remaining.")
    if specific_goal == "post_workout":
        reasoning.append("Post-workout: prioritize protein + carbs.")
    
    return {
        "status": "success",
        "suggested_meal_type": suggested_meal,
        "suggestions": suggestions,
        "reasoning": reasoning if reasoning else ["Based on time of day."],
        "remaining_budget": {
            "calories": max(0, remaining_cals),
            "protein_g": max(0, remaining_protein)
        },
        "message": f"🍽️ Suggested: {suggested_meal.replace('_', ' ').title()}"
    }


def get_recovery_nutrition_score(
    tool_context: Any,
    workout_intensity: str = "moderate"
) -> Dict[str, Any]:
    """
    Calculate recovery nutrition score.
    
    Args:
        tool_context: Session context
        workout_intensity: low, moderate, or high
    
    Returns:
        Recovery score and advice
    """
    summary = get_daily_nutrition_summary(tool_context, include_recommendations=False)
    
    if summary.get("status") != "success":
        return {
            "status": "no_data",
            "message": "No meals logged. Log post-workout meal for recovery analysis.",
            "tip": "Post-workout nutrition is crucial! Aim for protein + carbs within 2 hours."
        }
    
    totals = summary["totals"]
    targets = summary.get("targets", calculate_macro_targets(75, "maintenance"))
    
    recovery = calculate_recovery_score(totals, targets, workout_intensity)
    
    intensity_advice = []
    if workout_intensity == "high":
        if recovery["carb_score"] < 70:
            intensity_advice.append("🍚 Intense training demands more carbs for glycogen.")
        if not recovery["protein_target_met"]:
            intensity_advice.append("🥩 High-intensity work needs extra protein for repair.")
    
    return {
        "status": "success",
        "recovery_score": recovery["recovery_score"],
        "label": recovery["label"],
        "emoji": recovery["emoji"],
        "breakdown": {
            "protein_score": recovery["protein_score"],
            "carb_score": recovery["carb_score"]
        },
        "advice": recovery["advice"] + intensity_advice,
        "workout_intensity": workout_intensity,
        "message": f"{recovery['emoji']} Recovery: {recovery['recovery_score']}/100 ({recovery['label']})"
    }


def log_water_intake(
    tool_context: Any,
    amount_ml: int,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Log water intake.
    
    Args:
        tool_context: Session context
        amount_ml: Amount in milliliters
        notes: Optional notes
    
    Returns:
        Hydration status
    """
    today_key = datetime.now().strftime("%Y-%m-%d")
    water_key = f"hydration:{today_key}"
    
    water_log = {"date": today_key, "total_ml": 0, "entries": []}
    
    if hasattr(tool_context, 'state'):
        water_log = tool_context.state.get(water_key, water_log)
    
    water_log["total_ml"] += amount_ml
    water_log["entries"].append({
        "amount_ml": amount_ml,
        "notes": notes,
        "logged_at": datetime.now().isoformat()
    })
    
    if hasattr(tool_context, 'state'):
        tool_context.state[water_key] = water_log
    
    # Target
    weight_kg = 75
    if hasattr(tool_context, 'state'):
        weight_kg = tool_context.state.get("user:weight_kg", 75)
    
    target_ml = int(weight_kg * NUTRITION_CONFIG["water_per_kg_ml"])
    progress = min(100, round((water_log["total_ml"] / target_ml) * 100))
    remaining = max(0, target_ml - water_log["total_ml"])
    
    if progress >= 100:
        message = "💧 Hydration target hit!"
        emoji = "✅"
    elif progress >= 75:
        message = f"💧 Almost there! {remaining}ml to go."
        emoji = "💧"
    else:
        message = f"🥤 Keep hydrating! {remaining}ml remaining."
        emoji = "🥤"
    
    return {
        "status": "success",
        "logged_ml": amount_ml,
        "daily_total_ml": water_log["total_ml"],
        "daily_target_ml": target_ml,
        "progress_percent": progress,
        "remaining_ml": remaining,
        "emoji": emoji,
        "message": message
    }


def analyze_meal_balance(
    tool_context: Any,
    days: int = 7
) -> Dict[str, Any]:
    """
    Analyze meal patterns over multiple days.
    
    Args:
        tool_context: Session context
        days: Days to analyze
    
    Returns:
        Pattern analysis and improvements
    """
    daily_data = []
    
    if hasattr(tool_context, 'state'):
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            log_key = f"nutrition:{date}"
            log = tool_context.state.get(log_key)
            
            if log and log.get("meals"):
                daily_data.append({
                    "date": date,
                    "calories": log["total_calories"],
                    "protein_g": log["total_protein_g"],
                    "meal_count": len(log["meals"])
                })
    
    if len(daily_data) < 2:
        return {
            "status": "insufficient_data",
            "days_with_data": len(daily_data),
            "message": "Need more data. Log meals consistently for analysis."
        }
    
    # Averages
    avg_calories = sum(d["calories"] for d in daily_data) / len(daily_data)
    avg_protein = sum(d["protein_g"] for d in daily_data) / len(daily_data)
    avg_meals = sum(d["meal_count"] for d in daily_data) / len(daily_data)
    
    # Consistency
    if len(daily_data) >= 3:
        cal_stdev = statistics.stdev([d["calories"] for d in daily_data])
        consistency_score = max(0, 100 - (cal_stdev / max(avg_calories, 1)) * 100)
    else:
        consistency_score = 50
    
    patterns = []
    if avg_meals < 3:
        patterns.append("⚠️ Fewer than 3 meals/day average")
    else:
        patterns.append("✅ Good meal frequency")
    
    if avg_protein < 100:
        patterns.append("⚠️ Protein may be low")
    elif avg_protein > 150:
        patterns.append("💪 Strong protein intake")
    
    improvements = []
    if consistency_score < 60:
        improvements.append("Try for more consistent daily intake")
    if avg_protein < 120:
        improvements.append("Add protein to each meal")
    if not improvements:
        improvements.append("Great consistency!")
    
    return {
        "status": "success",
        "days_analyzed": len(daily_data),
        "average_daily": {
            "calories": int(avg_calories),
            "protein_g": round(avg_protein, 1),
            "meals_per_day": round(avg_meals, 1)
        },
        "consistency_score": round(consistency_score),
        "patterns": patterns,
        "improvements": improvements,
        "message": f"📊 {len(daily_data)}-day avg: {int(avg_calories)} kcal, {round(avg_protein)}g protein"
    }


# =============================================================================
# ADK AGENT FACTORY
# =============================================================================
def create_nutrition_agent(use_memory_preload: bool = False) -> Optional[Any]:
    """Create ADK LlmAgent for nutrition tracking."""
    if not ADK_AVAILABLE:
        print("⚠️ ADK not available. Cannot create nutrition agent.")
        return None
    
    tools = [
        FunctionTool(func=log_meal),
        FunctionTool(func=get_daily_nutrition_summary),
        FunctionTool(func=get_macro_targets),
        FunctionTool(func=suggest_next_meal),
        FunctionTool(func=get_recovery_nutrition_score),
        FunctionTool(func=log_water_intake),
        FunctionTool(func=analyze_meal_balance),
    ]
    
    if use_memory_preload:
        tools.append(preload_memory)
    else:
        tools.append(load_memory)
    
    agent = LlmAgent(
        name="NutritionCoach",
        model=Gemini(model="gemini-2.5-flash-lite"),
        description="Nutrition and recovery coach for FitForge AI.",
        instruction="""You are FitForge's nutrition coach.

YOUR ROLE:
1. Log meals from natural language descriptions
2. Track daily macros and progress
3. Provide recovery nutrition scoring
4. Suggest meals based on goals and budget
5. Track hydration

PRINCIPLES:
- Protein: 1.6-2.2g per kg for active individuals
- Post-workout: 20-40g protein + carbs within 2 hours
- Hydration: ~35ml per kg bodyweight daily

TOOLS:
- log_meal: Parse and log meals
- get_daily_nutrition_summary: Today's totals
- get_macro_targets: Personalized targets
- suggest_next_meal: Meal suggestions
- get_recovery_nutrition_score: Recovery assessment
- log_water_intake: Track hydration

Be encouraging and practical!""",
        tools=tools,
        output_key="nutrition_response"
    )
    
    print(f"✅ Nutrition Agent created with {len(tools)} tools")
    return agent


# =============================================================================
# EXPORTS
# =============================================================================
__all__ = [
    # Main functions
    "log_meal",
    "get_daily_nutrition_summary",
    "get_macro_targets",
    "suggest_next_meal",
    "get_recovery_nutrition_score",
    "log_water_intake",
    "analyze_meal_balance",
    
    # Helpers
    "calculate_macro_targets",
    "calculate_recovery_score",
    "format_macro_summary",
    
    # Agent
    "create_nutrition_agent",
    
    # Config
    "NUTRITION_CONFIG",
    "MEAL_TYPES",
    
    # Flags
    "ADK_AVAILABLE",
    "NUTRITION_PARSER_READY",
    "GEMINI_READY",
]