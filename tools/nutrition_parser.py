
# tools/nutrition_parser.py
"""
FitForge AI — Nutrition Parser Tool (ADK Compatible)
=====================================================
Parses natural language meal descriptions into structured macro data.
Uses Gemini for intelligent parsing with offline fallback.

ADK Tool Format: Function with docstring + type hints + dict return
"""

import os
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv

# =============================================================================
# CONFIGURATION
# =============================================================================
load_dotenv()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GEMINI_AVAILABLE = False
CLIENT = None

# Initialize Gemini Client
try:
    from google import genai
    from google.genai import types as genai_types
    
    if GOOGLE_API_KEY:
        CLIENT = genai.Client(api_key=GOOGLE_API_KEY)
        GEMINI_AVAILABLE = True
        print("✅ Nutrition Parser: Gemini ready")
    else:
        print("⚠️ Nutrition Parser: No API key found")
except ImportError as e:
    print(f"⚠️ Nutrition Parser: google-genai not installed: {e}")


# =============================================================================
# VALIDATION SCHEMA
# =============================================================================
class NutritionEntry(BaseModel):
    """Pydantic model for validating nutrition data."""
    calories: Optional[int] = Field(None, ge=0, le=10000)
    protein_g: Optional[float] = Field(None, ge=0, le=500)
    carbs_g: Optional[float] = Field(None, ge=0, le=1000)
    fat_g: Optional[float] = Field(None, ge=0, le=500)
    fiber_g: Optional[float] = Field(None, ge=0, le=100)
    sugar_g: Optional[float] = Field(None, ge=0, le=500)
    sodium_mg: Optional[int] = Field(None, ge=0, le=10000)
    ingredients: List[str] = Field(default_factory=list)
    meal_type: Optional[str] = Field(
        None, 
        pattern="^(breakfast|lunch|dinner|snack|pre_workout|post_workout|unknown)$"
    )
    portion_size: Optional[str] = Field(None, description="e.g., '1 cup', '200g'")
    notes: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)


# =============================================================================
# FOOD DATABASE — Offline Fallback
# =============================================================================
FOOD_DATABASE = {
    # Proteins
    "chicken": {"protein": 31, "carbs": 0, "fat": 3.6, "calories": 165, "per": "100g"},
    "chicken breast": {"protein": 31, "carbs": 0, "fat": 3.6, "calories": 165, "per": "100g"},
    "beef": {"protein": 26, "carbs": 0, "fat": 15, "calories": 250, "per": "100g"},
    "steak": {"protein": 26, "carbs": 0, "fat": 15, "calories": 250, "per": "100g"},
    "salmon": {"protein": 25, "carbs": 0, "fat": 13, "calories": 208, "per": "100g"},
    "tuna": {"protein": 29, "carbs": 0, "fat": 1, "calories": 130, "per": "100g"},
    "egg": {"protein": 6, "carbs": 0.6, "fat": 5, "calories": 78, "per": "1 large"},
    "eggs": {"protein": 12, "carbs": 1.2, "fat": 10, "calories": 156, "per": "2 large"},
    "whey": {"protein": 24, "carbs": 3, "fat": 1, "calories": 120, "per": "1 scoop"},
    "protein shake": {"protein": 25, "carbs": 5, "fat": 2, "calories": 130, "per": "1 serving"},
    "greek yogurt": {"protein": 17, "carbs": 6, "fat": 0.7, "calories": 100, "per": "170g"},
    "cottage cheese": {"protein": 14, "carbs": 3, "fat": 1, "calories": 80, "per": "100g"},
    "tofu": {"protein": 8, "carbs": 2, "fat": 4.5, "calories": 76, "per": "100g"},
    
    # Carbs
    "rice": {"protein": 2.7, "carbs": 28, "fat": 0.3, "calories": 130, "per": "100g cooked"},
    "white rice": {"protein": 2.7, "carbs": 28, "fat": 0.3, "calories": 130, "per": "100g"},
    "brown rice": {"protein": 2.6, "carbs": 23, "fat": 0.9, "calories": 112, "per": "100g"},
    "pasta": {"protein": 5, "carbs": 25, "fat": 1, "calories": 131, "per": "100g cooked"},
    "oats": {"protein": 5, "carbs": 27, "fat": 3, "calories": 150, "per": "40g dry"},
    "oatmeal": {"protein": 5, "carbs": 27, "fat": 3, "calories": 150, "per": "1 serving"},
    "bread": {"protein": 4, "carbs": 20, "fat": 1, "calories": 80, "per": "1 slice"},
    "potato": {"protein": 2, "carbs": 17, "fat": 0.1, "calories": 77, "per": "100g"},
    "sweet potato": {"protein": 1.6, "carbs": 20, "fat": 0.1, "calories": 86, "per": "100g"},
    "banana": {"protein": 1.3, "carbs": 27, "fat": 0.4, "calories": 105, "per": "1 medium"},
    "apple": {"protein": 0.3, "carbs": 25, "fat": 0.2, "calories": 95, "per": "1 medium"},
    
    # Fats
    "avocado": {"protein": 2, "carbs": 9, "fat": 15, "calories": 160, "per": "half"},
    "almonds": {"protein": 6, "carbs": 6, "fat": 14, "calories": 164, "per": "28g"},
    "peanut butter": {"protein": 8, "carbs": 6, "fat": 16, "calories": 188, "per": "2 tbsp"},
    "olive oil": {"protein": 0, "carbs": 0, "fat": 14, "calories": 120, "per": "1 tbsp"},
    
    # Vegetables
    "broccoli": {"protein": 2.8, "carbs": 7, "fat": 0.4, "calories": 35, "per": "100g"},
    "spinach": {"protein": 2.9, "carbs": 3.6, "fat": 0.4, "calories": 23, "per": "100g"},
    "salad": {"protein": 1, "carbs": 3, "fat": 0.2, "calories": 15, "per": "100g"},
    
    # Common meals (approximate)
    "sandwich": {"protein": 15, "carbs": 40, "fat": 12, "calories": 350, "per": "1 sandwich"},
    "burger": {"protein": 25, "carbs": 35, "fat": 20, "calories": 450, "per": "1 burger"},
    "pizza": {"protein": 12, "carbs": 36, "fat": 10, "calories": 285, "per": "1 slice"},
    "salad bowl": {"protein": 8, "carbs": 15, "fat": 12, "calories": 200, "per": "1 bowl"},
}

# Meal type keywords
MEAL_KEYWORDS = {
    "breakfast": ["morning", "breakfast", "oat", "cereal", "toast", "pancake", "waffle"],
    "lunch": ["lunch", "midday", "noon", "sandwich"],
    "dinner": ["dinner", "evening", "supper", "steak", "pasta"],
    "snack": ["snack", "bite", "munch", "nibble"],
    "pre_workout": ["pre-workout", "pre workout", "before gym", "before training"],
    "post_workout": ["post-workout", "post workout", "after gym", "after training", "shake", "whey", "recovery"],
}


# =============================================================================
# HELPER: Extract quantity from text
# =============================================================================
def extract_quantity(text: str, food: str) -> float:
    """
    Extract quantity multiplier from text.
    Examples: "2 eggs" -> 2.0, "double chicken" -> 2.0, "half avocado" -> 0.5
    """
    text_lower = text.lower()
    
    # Direct number before food
    pattern = rf'(\d+\.?\d*)\s*{re.escape(food)}'
    match = re.search(pattern, text_lower)
    if match:
        return float(match.group(1))
    
    # Word multipliers
    if "double" in text_lower or "2x" in text_lower:
        return 2.0
    if "triple" in text_lower or "3x" in text_lower:
        return 3.0
    if "half" in text_lower or "1/2" in text_lower:
        return 0.5
    if "quarter" in text_lower or "1/4" in text_lower:
        return 0.25
    
    # Generic number at start
    start_num = re.match(r'^(\d+)', text_lower)
    if start_num:
        return float(start_num.group(1))
    
    return 1.0


def detect_meal_type(text: str) -> str:
    """Detect meal type from keywords in text."""
    text_lower = text.lower()
    
    for meal_type, keywords in MEAL_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return meal_type
    
    return "unknown"


# =============================================================================
# HELPER: Heuristic Fallback Parser
# =============================================================================
def parse_with_heuristics(text: str) -> Dict[str, Any]:
    """
    Offline fallback: Parse nutrition using food database and keyword matching.
    Used when Gemini is unavailable.
    """
    text_lower = text.lower()
    
    totals = {
        "protein": 0.0,
        "carbs": 0.0,
        "fat": 0.0,
        "calories": 0
    }
    found_ingredients = []
    
    # Search for known foods
    for food, macros in FOOD_DATABASE.items():
        if food in text_lower:
            quantity = extract_quantity(text, food)
            
            totals["protein"] += macros["protein"] * quantity
            totals["carbs"] += macros["carbs"] * quantity
            totals["fat"] += macros["fat"] * quantity
            totals["calories"] += int(macros["calories"] * quantity)
            
            found_ingredients.append(f"{food} x{quantity}" if quantity != 1 else food)
    
    # Detect meal type
    meal_type = detect_meal_type(text)
    
    # Build result
    result = {
        "calories": totals["calories"] if totals["calories"] > 0 else None,
        "protein_g": round(totals["protein"], 1) if totals["protein"] > 0 else None,
        "carbs_g": round(totals["carbs"], 1) if totals["carbs"] > 0 else None,
        "fat_g": round(totals["fat"], 1) if totals["fat"] > 0 else None,
        "ingredients": found_ingredients,
        "meal_type": meal_type,
        "notes": f"Parsed from: {text[:100]}",
        "confidence": 0.4 if found_ingredients else 0.1
    }
    
    return result


# =============================================================================
# MAIN ADK TOOL: parse_nutrition_text
# =============================================================================
def parse_nutrition_text(meal_description: str) -> Dict[str, Any]:
    """
    Parse a natural language meal description into structured nutrition data.
    
    Uses AI (Gemini) for intelligent parsing with automatic fallback to
    offline heuristic matching. Handles various input formats including
    simple descriptions, detailed ingredients, and meal photos descriptions.
    
    Args:
        meal_description: Natural language description of food/meal.
                         Examples:
                         - "2 eggs with toast and avocado"
                         - "Grilled chicken breast with rice and broccoli"
                         - "Post-workout protein shake with banana"
                         - "Large pepperoni pizza, 3 slices"
    
    Returns:
        Dictionary with status and nutrition data:
        - status: "success", "partial", or "error"
        - calories: Total calories (kcal)
        - protein_g: Protein in grams
        - carbs_g: Carbohydrates in grams
        - fat_g: Fat in grams
        - fiber_g: Fiber in grams (if detected)
        - ingredients: List of identified food items
        - meal_type: breakfast|lunch|dinner|snack|pre_workout|post_workout|unknown
        - portion_size: Detected portion description
        - notes: Additional parsing notes
        - confidence: Parsing confidence (0.0 to 1.0)
        - parsing_method: "ai" or "heuristic_fallback"
    
    Example:
        >>> result = parse_nutrition_text("Breakfast: 3 eggs, 2 slices of toast, black coffee")
        >>> print(result)
        {
            "status": "success",
            "calories": 350,
            "protein_g": 21,
            "carbs_g": 40,
            "fat_g": 17,
            "meal_type": "breakfast",
            "ingredients": ["eggs", "toast", "coffee"],
            "confidence": 0.9
        }
    """
    
    # -------------------------------------------------------------------------
    # Input Validation
    # -------------------------------------------------------------------------
    if not meal_description:
        return {
            "status": "error",
            "error_message": "No meal description provided"
        }
    
    text = meal_description.strip()
    if len(text) < 2:
        return {
            "status": "error",
            "error_message": "Meal description too short"
        }
    
    if len(text) > 2000:
        text = text[:2000]  # Truncate very long inputs
    
    # -------------------------------------------------------------------------
    # Attempt 1: AI-Powered Parsing (Gemini)
    # -------------------------------------------------------------------------
    if GEMINI_AVAILABLE and CLIENT is not None:
        try:
            prompt = f"""
            You are a nutrition expert and food analyst. Parse this meal description into detailed nutrition data.
            
            MEAL DESCRIPTION: "{text}"
            
            Analyze the meal and return a JSON object with:
            {{
                "calories": int (total kcal, estimate if not specified),
                "protein_g": float (grams of protein),
                "carbs_g": float (grams of carbohydrates),
                "fat_g": float (grams of fat),
                "fiber_g": float (grams of fiber, if relevant),
                "sugar_g": float (grams of sugar, if relevant),
                "ingredients": ["list", "of", "identified", "foods"],
                "meal_type": "breakfast|lunch|dinner|snack|pre_workout|post_workout|unknown",
                "portion_size": "detected portion info or null",
                "notes": "brief analysis notes",
                "confidence": float (0.0-1.0, your confidence in the estimates)
            }}
            
            IMPORTANT GUIDELINES:
            - Use standard portion sizes if not specified (e.g., 1 medium banana, 1 cup rice)
            - For restaurant meals, estimate generously (portions are usually large)
            - For homemade meals, use standard home-cooking portions
            - If multiple items, sum all macros
            - Be realistic about calorie estimates
            - Set confidence lower if you're making rough estimates
            """
            
            response = CLIENT.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2  # Low temperature for consistent estimates
                )
            )
            
            # Parse JSON response
            raw_data = json.loads(response.text)
            
            # Normalize meal_type to lowercase
            if raw_data.get("meal_type"):
                raw_data["meal_type"] = raw_data["meal_type"].lower()
            
            # Validate with Pydantic
            validated = NutritionEntry(**raw_data)
            result = validated.model_dump(exclude_none=True)
            
            # Add metadata
            result["status"] = "success"
            result["parsing_method"] = "ai"
            result["parsed_at"] = datetime.now().isoformat()
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Nutrition JSON parse failed: {e}. Using fallback...")
            
        except ValidationError as e:
            print(f"⚠️ Nutrition validation failed: {e}. Using fallback...")
            
        except Exception as e:
            print(f"⚠️ Nutrition AI failed: {e}. Using fallback...")
    
    # -------------------------------------------------------------------------
    # Attempt 2: Heuristic Fallback (Offline)
    # -------------------------------------------------------------------------
    fallback_result = parse_with_heuristics(text)
    
    if fallback_result.get("ingredients"):
        fallback_result["status"] = "partial"
        fallback_result["parsing_method"] = "heuristic_fallback"
        fallback_result["parsed_at"] = datetime.now().isoformat()
        return fallback_result
    else:
        return {
            "status": "error",
            "error_message": "Could not identify any foods in the description",
            "original_text": text[:200],
            "suggestion": "Try being more specific: '100g chicken breast with 1 cup rice'"
        }


# =============================================================================
# ADDITIONAL TOOL: Calculate Daily Totals
# =============================================================================
def calculate_daily_nutrition(meals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate total daily nutrition from multiple meals.
    
    Aggregates nutrition data from multiple meals to provide daily totals
    and compares against recommended daily values.
    
    Args:
        meals: List of nutrition dictionaries (from parse_nutrition_text)
    
    Returns:
        Dictionary with daily totals and analysis:
        - status: "success" or "error"
        - total_calories: Sum of all meal calories
        - total_protein_g: Sum of protein
        - total_carbs_g: Sum of carbs
        - total_fat_g: Sum of fat
        - meal_count: Number of meals analyzed
        - macro_breakdown: Percentage breakdown (protein/carbs/fat)
        - recommendations: Suggestions based on totals
    """
    if not meals:
        return {
            "status": "error",
            "error_message": "No meals provided"
        }
    
    totals = {
        "calories": 0,
        "protein_g": 0.0,
        "carbs_g": 0.0,
        "fat_g": 0.0,
        "fiber_g": 0.0
    }
    
    valid_meals = 0
    meal_types = []
    
    for meal in meals:
        if meal.get("status") in ["success", "partial"]:
            totals["calories"] += meal.get("calories", 0) or 0
            totals["protein_g"] += meal.get("protein_g", 0) or 0
            totals["carbs_g"] += meal.get("carbs_g", 0) or 0
            totals["fat_g"] += meal.get("fat_g", 0) or 0
            totals["fiber_g"] += meal.get("fiber_g", 0) or 0
            valid_meals += 1
            
            if meal.get("meal_type"):
                meal_types.append(meal["meal_type"])
    
    if valid_meals == 0:
        return {
            "status": "error",
            "error_message": "No valid meals to calculate"
        }
    
    # Calculate macro percentages
    total_macro_cals = (
        totals["protein_g"] * 4 + 
        totals["carbs_g"] * 4 + 
        totals["fat_g"] * 9
    )
    
    if total_macro_cals > 0:
        macro_breakdown = {
            "protein_percent": round((totals["protein_g"] * 4 / total_macro_cals) * 100, 1),
            "carbs_percent": round((totals["carbs_g"] * 4 / total_macro_cals) * 100, 1),
            "fat_percent": round((totals["fat_g"] * 9 / total_macro_cals) * 100, 1)
        }
    else:
        macro_breakdown = {"protein_percent": 0, "carbs_percent": 0, "fat_percent": 0}
    
    # Generate recommendations
    recommendations = []
    
    if totals["protein_g"] < 100:
        recommendations.append("Consider adding more protein sources")
    if totals["protein_g"] > 200:
        recommendations.append("Protein intake is high - ensure adequate hydration")
    
    if totals["fiber_g"] < 25:
        recommendations.append("Add more fiber-rich foods (vegetables, whole grains)")
    
    if totals["calories"] < 1500:
        recommendations.append("Calorie intake seems low - ensure you're eating enough")
    if totals["calories"] > 3500:
        recommendations.append("High calorie intake - appropriate for heavy training days")
    
    if macro_breakdown["fat_percent"] > 40:
        recommendations.append("Fat intake is high - consider balancing with more carbs/protein")
    
    return {
        "status": "success",
        "total_calories": totals["calories"],
        "total_protein_g": round(totals["protein_g"], 1),
        "total_carbs_g": round(totals["carbs_g"], 1),
        "total_fat_g": round(totals["fat_g"], 1),
        "total_fiber_g": round(totals["fiber_g"], 1),
        "meal_count": valid_meals,
        "meal_types_logged": list(set(meal_types)),
        "macro_breakdown": macro_breakdown,
        "recommendations": recommendations if recommendations else ["Nutrition looks balanced!"],
        "calculated_at": datetime.now().isoformat()
    }


# =============================================================================
# ADDITIONAL TOOL: Suggest Meal for Goals
# =============================================================================
def suggest_meal_for_goal(
    goal: str,
    meal_type: str = "any",
    calories_target: Optional[int] = None,
    protein_min_g: Optional[int] = None
) -> Dict[str, Any]:
    """
    Suggest meal ideas based on fitness goals.
    
    Provides meal suggestions optimized for specific fitness goals
    like muscle building, weight loss, or endurance training.
    
    Args:
        goal: Fitness goal - "muscle_gain", "fat_loss", "maintenance", "endurance"
        meal_type: Type of meal - "breakfast", "lunch", "dinner", "snack", "post_workout", "any"
        calories_target: Optional target calories for the meal
        protein_min_g: Optional minimum protein requirement
    
    Returns:
        Dictionary with meal suggestions:
        - status: "success" or "error"
        - suggestions: List of meal ideas with macros
        - goal_notes: Tips for the specified goal
    """
    
    # Define meal templates by goal
    MEAL_TEMPLATES = {
        "muscle_gain": {
            "breakfast": [
                {"name": "Power Oatmeal", "desc": "Oats with whey protein, banana, and almonds", "cals": 550, "protein": 35},
                {"name": "Egg White Scramble", "desc": "6 egg whites, 2 whole eggs, toast, avocado", "cals": 480, "protein": 38},
            ],
            "lunch": [
                {"name": "Chicken Rice Bowl", "desc": "Grilled chicken breast, brown rice, vegetables", "cals": 650, "protein": 45},
                {"name": "Tuna Pasta", "desc": "Whole wheat pasta with tuna and olive oil", "cals": 600, "protein": 40},
            ],
            "dinner": [
                {"name": "Steak & Potatoes", "desc": "Lean steak with sweet potato and broccoli", "cals": 700, "protein": 50},
                {"name": "Salmon Quinoa", "desc": "Grilled salmon with quinoa and asparagus", "cals": 620, "protein": 45},
            ],
            "post_workout": [
                {"name": "Protein Shake Plus", "desc": "Whey protein, banana, oats, peanut butter", "cals": 450, "protein": 40},
                {"name": "Chicken Wrap", "desc": "Grilled chicken in whole wheat wrap with veggies", "cals": 400, "protein": 35},
            ],
            "snack": [
                {"name": "Greek Yogurt Mix", "desc": "Greek yogurt with honey and granola", "cals": 280, "protein": 20},
                {"name": "Cottage Cheese Bowl", "desc": "Cottage cheese with berries", "cals": 200, "protein": 18},
            ]
        },
        "fat_loss": {
            "breakfast": [
                {"name": "Egg White Veggie Omelette", "desc": "Egg whites with spinach and tomatoes", "cals": 200, "protein": 22},
                {"name": "Protein Smoothie", "desc": "Whey, spinach, berries, almond milk", "cals": 180, "protein": 25},
            ],
            "lunch": [
                {"name": "Grilled Chicken Salad", "desc": "Large salad with grilled chicken, light dressing", "cals": 350, "protein": 35},
                {"name": "Tuna Lettuce Wraps", "desc": "Tuna in lettuce cups with veggies", "cals": 250, "protein": 30},
            ],
            "dinner": [
                {"name": "Baked Fish & Veggies", "desc": "White fish with roasted vegetables", "cals": 320, "protein": 35},
                {"name": "Turkey Stir Fry", "desc": "Lean turkey with mixed vegetables", "cals": 350, "protein": 38},
            ],
            "post_workout": [
                {"name": "Lean Protein Shake", "desc": "Whey isolate with water and ice", "cals": 120, "protein": 25},
            ],
            "snack": [
                {"name": "Veggie Sticks", "desc": "Celery and carrots with hummus", "cals": 100, "protein": 4},
                {"name": "Hard Boiled Eggs", "desc": "2 hard boiled eggs", "cals": 140, "protein": 12},
            ]
        },
        "endurance": {
            "breakfast": [
                {"name": "Carb-Load Oats", "desc": "Large bowl of oats with honey and fruit", "cals": 500, "protein": 15},
                {"name": "Banana Pancakes", "desc": "Whole grain pancakes with banana and maple syrup", "cals": 550, "protein": 12},
            ],
            "lunch": [
                {"name": "Pasta Primavera", "desc": "Whole wheat pasta with vegetables and olive oil", "cals": 600, "protein": 18},
                {"name": "Rice & Chicken", "desc": "Large portion of rice with lean chicken", "cals": 650, "protein": 35},
            ],
            "dinner": [
                {"name": "Carb Refuel Plate", "desc": "Sweet potato, rice, lean protein, vegetables", "cals": 700, "protein": 30},
            ],
            "post_workout": [
                {"name": "Recovery Smoothie", "desc": "Banana, honey, protein, oats", "cals": 400, "protein": 25},
            ],
            "snack": [
                {"name": "Energy Bars", "desc": "Homemade oat and date bars", "cals": 250, "protein": 8},
                {"name": "Fruit & Nut Mix", "desc": "Dried fruit with almonds", "cals": 200, "protein": 6},
            ]
        }
    }
    
    # Default to maintenance (balanced)
    if goal not in MEAL_TEMPLATES:
        goal = "muscle_gain"  # Default template
    
    templates = MEAL_TEMPLATES[goal]
    
    # Get suggestions for meal type
    if meal_type == "any":
        # Combine all meal types
        all_suggestions = []
        for mt, meals in templates.items():
            for meal in meals:
                meal["meal_type"] = mt
                all_suggestions.append(meal)
        suggestions = all_suggestions[:5]  # Top 5
    else:
        suggestions = templates.get(meal_type, templates.get("snack", []))
    
    # Filter by targets if provided
    if calories_target:
        suggestions = [s for s in suggestions if abs(s["cals"] - calories_target) < 200]
    if protein_min_g:
        suggestions = [s for s in suggestions if s["protein"] >= protein_min_g]
    
    # Goal-specific notes
    goal_notes = {
        "muscle_gain": "Focus on protein timing around workouts. Aim for 1.6-2.2g protein per kg bodyweight.",
        "fat_loss": "Maintain protein intake while reducing overall calories. Stay hydrated.",
        "endurance": "Prioritize carbohydrates for energy. Time larger meals 2-3 hours before training.",
        "maintenance": "Balanced macros with variety. Listen to hunger cues."
    }
    
    return {
        "status": "success",
        "goal": goal,
        "meal_type": meal_type,
        "suggestions": suggestions if suggestions else [{"name": "No matches", "desc": "Try adjusting filters"}],
        "goal_notes": goal_notes.get(goal, "Eat balanced meals with adequate protein."),
        "generated_at": datetime.now().isoformat()
    }


# =============================================================================
# EXPORTS
# =============================================================================
__all__ = [
    "parse_nutrition_text",
    "calculate_daily_nutrition",
    "suggest_meal_for_goal",
    "parse_with_heuristics",
    "NutritionEntry",
    "FOOD_DATABASE"
]