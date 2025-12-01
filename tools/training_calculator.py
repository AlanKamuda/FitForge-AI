# tools/training_calculator.py
"""
FitForge AI — Training Calculator Tool (ADK Compatible)
========================================================
Provides fitness calculations using two approaches:
  1. Pre-built FunctionTools for common calculations (fast, reliable)
  2. BuiltInCodeExecutor agent for dynamic/custom calculations (flexible)

This showcases ADK's code execution capability for accurate math
instead of relying on LLM estimation.

ADK Features Used:
  - FunctionTool format (Exercise 3)
  - BuiltInCodeExecutor (Exercise 3)
  - LlmAgent with code_executor (Exercise 3)
"""

import math
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum

# =============================================================================
# ADK IMPORTS
# =============================================================================
try:
    from google.adk.agents import LlmAgent
    from google.adk.models.google_llm import Gemini
    from google.adk.code_executors import BuiltInCodeExecutor
    from google.genai import types
    
    ADK_AVAILABLE = True
    print("✅ Training Calculator: ADK components ready")
except ImportError as e:
    ADK_AVAILABLE = False
    print(f"⚠️ Training Calculator: ADK not available: {e}")


# =============================================================================
# CONSTANTS & FORMULAS
# =============================================================================

# MET values for common activities (Metabolic Equivalent of Task)
MET_VALUES = {
    # Running
    "running_easy": 8.0,      # ~10:00/mi pace
    "running_moderate": 10.0,  # ~8:00/mi pace
    "running_hard": 12.0,      # ~6:30/mi pace
    "running_sprint": 15.0,    # intervals/sprints
    
    # Cycling
    "cycling_easy": 4.0,       # <10 mph
    "cycling_moderate": 8.0,   # 12-14 mph
    "cycling_hard": 10.0,      # 14-16 mph
    "cycling_racing": 12.0,    # >16 mph
    
    # Swimming
    "swimming_easy": 6.0,
    "swimming_moderate": 8.0,
    "swimming_hard": 10.0,
    
    # Strength Training
    "strength_light": 3.5,
    "strength_moderate": 5.0,
    "strength_vigorous": 6.0,
    
    # Other
    "walking": 3.5,
    "hiking": 6.0,
    "rowing": 7.0,
    "hiit": 12.0,
    "yoga": 2.5,
    "stretching": 2.0,
}

# Heart Rate Zone Definitions (% of Max HR)
HR_ZONES = {
    "zone1_recovery": (0.50, 0.60),
    "zone2_aerobic": (0.60, 0.70),
    "zone3_tempo": (0.70, 0.80),
    "zone4_threshold": (0.80, 0.90),
    "zone5_vo2max": (0.90, 1.00),
}

# 1RM Formulas
ONE_RM_FORMULAS = {
    "epley": lambda w, r: w * (1 + r / 30),
    "brzycki": lambda w, r: w * (36 / (37 - r)),
    "lander": lambda w, r: (100 * w) / (101.3 - 2.67123 * r),
    "lombardi": lambda w, r: w * (r ** 0.10),
    "oconner": lambda w, r: w * (1 + r / 40),
}


# =============================================================================
# TOOL 1: Calculate One-Rep Max (1RM)
# =============================================================================

def calculate_one_rep_max(
    weight: float,
    reps: int,
    formula: str = "epley",
    unit: str = "kg"
) -> Dict[str, Any]:
    """
    Calculate estimated one-rep max (1RM) from a lift.
    
    Uses proven formulas to estimate maximum strength from submaximal lifts.
    Most accurate with 1-10 reps; less reliable above 10 reps.
    
    Args:
        weight: Weight lifted in the set
        reps: Number of repetitions completed (1-15 recommended)
        formula: Calculation formula to use:
                - "epley" (default): Most common, good all-around
                - "brzycki": Good for lower rep ranges
                - "lander": Often used in powerlifting
                - "lombardi": Tends to give lower estimates
                - "oconner": Simple formula
                - "average": Average of all formulas
        unit: Weight unit - "kg" or "lb"
    
    Returns:
        Dictionary with 1RM calculation:
        - status: "success" or "error"
        - estimated_1rm: The calculated one-rep max
        - weight_used: Original weight lifted
        - reps_completed: Reps performed
        - formula_used: Which formula was applied
        - training_percentages: Suggested training loads at various %
        - rep_maxes: Estimated maxes for different rep ranges
    
    Example:
        >>> result = calculate_one_rep_max(100, 5, formula="epley", unit="kg")
        >>> print(result["estimated_1rm"])  # ~116.7 kg
    """
    
    # Input validation
    if weight <= 0:
        return {"status": "error", "error_message": "Weight must be positive"}
    
    if reps < 1:
        return {"status": "error", "error_message": "Reps must be at least 1"}
    
    if reps > 15:
        return {
            "status": "warning",
            "warning": "1RM estimates are less accurate above 10 reps",
            "estimated_1rm": None
        }
    
    if reps == 1:
        # Already a 1RM
        estimated_1rm = weight
        formula_used = "actual"
    elif formula == "average":
        # Calculate average of all formulas
        estimates = [f(weight, reps) for f in ONE_RM_FORMULAS.values()]
        estimated_1rm = sum(estimates) / len(estimates)
        formula_used = "average_all"
    else:
        formula_func = ONE_RM_FORMULAS.get(formula.lower())
        if not formula_func:
            return {
                "status": "error",
                "error_message": f"Unknown formula: {formula}. Use: {list(ONE_RM_FORMULAS.keys())}"
            }
        estimated_1rm = formula_func(weight, reps)
        formula_used = formula
    
    estimated_1rm = round(estimated_1rm, 1)
    
    # Calculate training percentages
    training_percentages = {
        "100%": round(estimated_1rm * 1.00, 1),
        "95%": round(estimated_1rm * 0.95, 1),
        "90%": round(estimated_1rm * 0.90, 1),
        "85%": round(estimated_1rm * 0.85, 1),
        "80%": round(estimated_1rm * 0.80, 1),
        "75%": round(estimated_1rm * 0.75, 1),
        "70%": round(estimated_1rm * 0.70, 1),
        "65%": round(estimated_1rm * 0.65, 1),
        "60%": round(estimated_1rm * 0.60, 1),
    }
    
    # Estimate rep maxes (how much for X reps)
    rep_maxes = {}
    for target_reps in [1, 3, 5, 8, 10, 12, 15]:
        if target_reps == 1:
            rep_maxes[f"{target_reps}RM"] = estimated_1rm
        else:
            # Reverse Epley formula
            rep_maxes[f"{target_reps}RM"] = round(estimated_1rm / (1 + target_reps / 30), 1)
    
    return {
        "status": "success",
        "estimated_1rm": estimated_1rm,
        "weight_used": weight,
        "reps_completed": reps,
        "unit": unit,
        "formula_used": formula_used,
        "training_percentages": training_percentages,
        "rep_maxes": rep_maxes,
        "calculated_at": datetime.now().isoformat()
    }


# =============================================================================
# TOOL 2: Calculate Training Stress Score (TSS)
# =============================================================================

def calculate_training_stress(
    duration_minutes: float,
    intensity: str = "moderate",
    activity_type: str = "running_moderate",
    heart_rate_avg: Optional[int] = None,
    heart_rate_max: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calculate Training Stress Score (TSS) and training load metrics.
    
    TSS quantifies training load to help plan recovery and prevent overtraining.
    Higher TSS = more training stress = more recovery needed.
    
    Args:
        duration_minutes: Workout duration in minutes
        intensity: Perceived intensity level:
                  - "easy": Recovery/Zone 1-2
                  - "moderate": Steady state/Zone 2-3
                  - "hard": Tempo/Threshold/Zone 3-4
                  - "very_hard": VO2max intervals/Zone 4-5
        activity_type: Type of activity (see MET_VALUES for options)
        heart_rate_avg: Optional average heart rate (for HR-based TSS)
        heart_rate_max: Optional max heart rate (needed if using HR)
    
    Returns:
        Dictionary with training stress metrics:
        - status: "success" or "error"
        - tss: Training Stress Score (0-300+ scale)
        - tss_interpretation: What the TSS means
        - intensity_factor: Normalized intensity
        - recovery_recommendation: Suggested recovery time
        - weekly_limit_percent: % of typical weekly TSS budget
    
    Example:
        >>> result = calculate_training_stress(60, intensity="hard", activity_type="running_hard")
        >>> print(result["tss"])  # ~75-100
    """
    
    if duration_minutes <= 0:
        return {"status": "error", "error_message": "Duration must be positive"}
    
    # Get MET value for activity
    met = MET_VALUES.get(activity_type, 5.0)  # Default to moderate
    
    # Intensity factors
    intensity_factors = {
        "easy": 0.6,
        "moderate": 0.75,
        "hard": 0.88,
        "very_hard": 1.0,
    }
    
    intensity_factor = intensity_factors.get(intensity.lower(), 0.75)
    
    # Calculate TSS using modified formula
    # TSS = (duration_hours * IF^2 * 100)
    duration_hours = duration_minutes / 60
    
    # Adjust for activity type (endurance vs strength)
    if "strength" in activity_type:
        # Strength training TSS is typically lower
        tss = duration_hours * (intensity_factor ** 2) * 60
    else:
        tss = duration_hours * (intensity_factor ** 2) * 100
    
    # If heart rate data provided, use HR-based calculation
    if heart_rate_avg and heart_rate_max:
        hr_ratio = heart_rate_avg / heart_rate_max
        hr_intensity_factor = hr_ratio * 1.1  # Slight adjustment
        tss = duration_hours * (hr_intensity_factor ** 2) * 100
        intensity_factor = hr_intensity_factor
    
    tss = round(tss, 1)
    
    # Interpret TSS
    if tss < 50:
        interpretation = "Low stress - Easy recovery workout"
        recovery = "Few hours to next day"
    elif tss < 100:
        interpretation = "Moderate stress - Standard training day"
        recovery = "24-36 hours recommended"
    elif tss < 150:
        interpretation = "High stress - Hard training day"
        recovery = "36-48 hours recommended"
    elif tss < 250:
        interpretation = "Very high stress - Key workout or race"
        recovery = "48-72 hours recommended"
    else:
        interpretation = "Extreme stress - Major event"
        recovery = "72+ hours recommended"
    
    # Weekly TSS budget (typical: 300-700 depending on fitness level)
    typical_weekly_tss = 450  # Moderate training load
    weekly_percent = round((tss / typical_weekly_tss) * 100, 1)
    
    return {
        "status": "success",
        "tss": tss,
        "tss_interpretation": interpretation,
        "intensity_factor": round(intensity_factor, 2),
        "duration_minutes": duration_minutes,
        "activity_type": activity_type,
        "met_value": met,
        "recovery_recommendation": recovery,
        "weekly_limit_percent": weekly_percent,
        "calculated_at": datetime.now().isoformat()
    }


# =============================================================================
# TOOL 3: Calculate Calories Burned
# =============================================================================

def calculate_calories_burned(
    weight_kg: float,
    duration_minutes: float,
    activity_type: str = "running_moderate",
    intensity: Optional[str] = None
) -> Dict[str, Any]:
    """
    Calculate estimated calories burned during exercise.
    
    Uses MET (Metabolic Equivalent of Task) values for accurate estimation.
    Formula: Calories = MET × weight(kg) × duration(hours)
    
    Args:
        weight_kg: Body weight in kilograms
        duration_minutes: Exercise duration in minutes
        activity_type: Type of activity. Options:
                      Running: running_easy, running_moderate, running_hard, running_sprint
                      Cycling: cycling_easy, cycling_moderate, cycling_hard, cycling_racing
                      Swimming: swimming_easy, swimming_moderate, swimming_hard
                      Strength: strength_light, strength_moderate, strength_vigorous
                      Other: walking, hiking, rowing, hiit, yoga, stretching
        intensity: Optional override for intensity (easy/moderate/hard)
    
    Returns:
        Dictionary with calorie calculation:
        - status: "success" or "error"
        - calories_burned: Estimated calories
        - met_value: MET value used
        - calories_per_minute: Burn rate
        - equivalent_food: Fun food equivalents
    
    Example:
        >>> result = calculate_calories_burned(75, 45, "running_moderate")
        >>> print(result["calories_burned"])  # ~562 kcal
    """
    
    if weight_kg <= 0:
        return {"status": "error", "error_message": "Weight must be positive"}
    
    if duration_minutes <= 0:
        return {"status": "error", "error_message": "Duration must be positive"}
    
    # Get MET value
    if intensity and activity_type.split("_")[0] in ["running", "cycling", "swimming", "strength"]:
        # Override with intensity-specific MET
        base_activity = activity_type.split("_")[0]
        activity_key = f"{base_activity}_{intensity}"
        met = MET_VALUES.get(activity_key, MET_VALUES.get(activity_type, 5.0))
    else:
        met = MET_VALUES.get(activity_type, 5.0)
    
    # Calculate calories: MET × weight(kg) × duration(hours)
    duration_hours = duration_minutes / 60
    calories = met * weight_kg * duration_hours
    calories = round(calories, 0)
    
    calories_per_minute = round(calories / duration_minutes, 1)
    
    # Fun food equivalents
    food_equivalents = {
        "bananas": round(calories / 105, 1),
        "slices_of_pizza": round(calories / 285, 1),
        "cookies": round(calories / 150, 1),
        "beers": round(calories / 150, 1),
        "chocolate_bars": round(calories / 230, 1),
    }
    
    return {
        "status": "success",
        "calories_burned": int(calories),
        "met_value": met,
        "activity_type": activity_type,
        "duration_minutes": duration_minutes,
        "weight_kg": weight_kg,
        "calories_per_minute": calories_per_minute,
        "equivalent_food": food_equivalents,
        "calculated_at": datetime.now().isoformat()
    }


# =============================================================================
# TOOL 4: Calculate Heart Rate Zones
# =============================================================================

def calculate_heart_rate_zones(
    age: Optional[int] = None,
    max_heart_rate: Optional[int] = None,
    resting_heart_rate: Optional[int] = None,
    method: str = "percentage"
) -> Dict[str, Any]:
    """
    Calculate personalized heart rate training zones.
    
    Provides zones for targeted training at different intensities.
    Can use simple percentage method or Karvonen formula (heart rate reserve).
    
    Args:
        age: Age in years (used to estimate max HR if not provided)
        max_heart_rate: Known maximum heart rate (if available)
        resting_heart_rate: Resting heart rate (for Karvonen method)
        method: Calculation method:
               - "percentage": Simple % of max HR
               - "karvonen": Uses heart rate reserve (more accurate)
    
    Returns:
        Dictionary with heart rate zones:
        - status: "success" or "error"
        - max_hr: Maximum heart rate (estimated or provided)
        - zones: Dict with zone names and HR ranges
        - zone_descriptions: What each zone is for
        - method_used: Which calculation method
    
    Example:
        >>> result = calculate_heart_rate_zones(age=30, resting_heart_rate=60, method="karvonen")
        >>> print(result["zones"]["zone2_aerobic"])  # {"min": 126, "max": 145}
    """
    
    # Determine max HR
    if max_heart_rate:
        max_hr = max_heart_rate
    elif age:
        # Common formula: 220 - age (Tanaka formula is 208 - 0.7*age)
        max_hr = 220 - age
    else:
        return {
            "status": "error",
            "error_message": "Provide either age or max_heart_rate"
        }
    
    if max_hr < 100 or max_hr > 220:
        return {
            "status": "error",
            "error_message": f"Max HR {max_hr} seems invalid (expected 100-220)"
        }
    
    zones = {}
    zone_descriptions = {
        "zone1_recovery": "Active recovery, very easy effort. Good for recovery days.",
        "zone2_aerobic": "Aerobic base building. Conversational pace, fat burning.",
        "zone3_tempo": "Tempo/moderate effort. Comfortably hard, improves efficiency.",
        "zone4_threshold": "Lactate threshold. Hard effort, improves speed.",
        "zone5_vo2max": "VO2max/anaerobic. Maximum effort, short intervals.",
    }
    
    if method.lower() == "karvonen" and resting_heart_rate:
        # Karvonen formula: THR = ((MHR - RHR) × %Intensity) + RHR
        hrr = max_hr - resting_heart_rate  # Heart Rate Reserve
        
        for zone_name, (low_pct, high_pct) in HR_ZONES.items():
            zone_low = round(hrr * low_pct + resting_heart_rate)
            zone_high = round(hrr * high_pct + resting_heart_rate)
            zones[zone_name] = {"min": zone_low, "max": zone_high}
        
        method_used = "karvonen"
    else:
        # Simple percentage method
        for zone_name, (low_pct, high_pct) in HR_ZONES.items():
            zone_low = round(max_hr * low_pct)
            zone_high = round(max_hr * high_pct)
            zones[zone_name] = {"min": zone_low, "max": zone_high}
        
        method_used = "percentage"
    
    return {
        "status": "success",
        "max_hr": max_hr,
        "resting_hr": resting_heart_rate,
        "zones": zones,
        "zone_descriptions": zone_descriptions,
        "method_used": method_used,
        "calculated_at": datetime.now().isoformat()
    }


# =============================================================================
# TOOL 5: Convert Pace
# =============================================================================

def convert_pace(
    pace_value: float,
    from_unit: str,
    to_unit: str
) -> Dict[str, Any]:
    """
    Convert between different pace and speed units.
    
    Supports running/cycling pace conversions between min/km, min/mi,
    km/h, mph, and m/s.
    
    Args:
        pace_value: The pace or speed value to convert
        from_unit: Source unit:
                  - "min_per_km": Minutes per kilometer (e.g., 5.5 for 5:30/km)
                  - "min_per_mi": Minutes per mile
                  - "km_per_h" or "kph": Kilometers per hour
                  - "mi_per_h" or "mph": Miles per hour
                  - "m_per_s" or "mps": Meters per second
        to_unit: Target unit (same options as from_unit)
    
    Returns:
        Dictionary with conversion result:
        - status: "success" or "error"
        - original_value: Input value
        - converted_value: Result in target unit
        - formatted: Human-readable format (e.g., "5:30 /km")
        - all_conversions: Value in all supported units
    
    Example:
        >>> result = convert_pace(5.5, "min_per_km", "min_per_mi")
        >>> print(result["formatted"])  # "8:51 /mi"
    """
    
    if pace_value <= 0:
        return {"status": "error", "error_message": "Pace must be positive"}
    
    # Normalize unit names
    unit_aliases = {
        "kph": "km_per_h",
        "mph": "mi_per_h",
        "mps": "m_per_s",
    }
    from_unit = unit_aliases.get(from_unit.lower(), from_unit.lower())
    to_unit = unit_aliases.get(to_unit.lower(), to_unit.lower())
    
    # First convert everything to m/s (base unit)
    if from_unit == "min_per_km":
        m_per_s = 1000 / (pace_value * 60)
    elif from_unit == "min_per_mi":
        m_per_s = 1609.34 / (pace_value * 60)
    elif from_unit == "km_per_h":
        m_per_s = pace_value * 1000 / 3600
    elif from_unit == "mi_per_h":
        m_per_s = pace_value * 1609.34 / 3600
    elif from_unit == "m_per_s":
        m_per_s = pace_value
    else:
        return {"status": "error", "error_message": f"Unknown unit: {from_unit}"}
    
    # Convert from m/s to target unit
    if to_unit == "min_per_km":
        result = 1000 / (m_per_s * 60)
    elif to_unit == "min_per_mi":
        result = 1609.34 / (m_per_s * 60)
    elif to_unit == "km_per_h":
        result = m_per_s * 3600 / 1000
    elif to_unit == "mi_per_h":
        result = m_per_s * 3600 / 1609.34
    elif to_unit == "m_per_s":
        result = m_per_s
    else:
        return {"status": "error", "error_message": f"Unknown unit: {to_unit}"}
    
    # Format nicely for pace units
    def format_pace(value, unit):
        if "min_per" in unit:
            minutes = int(value)
            seconds = int((value - minutes) * 60)
            suffix = "/km" if "km" in unit else "/mi"
            return f"{minutes}:{seconds:02d} {suffix}"
        elif "km_per_h" in unit:
            return f"{value:.1f} km/h"
        elif "mi_per_h" in unit:
            return f"{value:.1f} mph"
        else:
            return f"{value:.2f} m/s"
    
    # Calculate all conversions
    all_conversions = {
        "min_per_km": round(1000 / (m_per_s * 60), 2),
        "min_per_mi": round(1609.34 / (m_per_s * 60), 2),
        "km_per_h": round(m_per_s * 3600 / 1000, 2),
        "mi_per_h": round(m_per_s * 3600 / 1609.34, 2),
        "m_per_s": round(m_per_s, 2),
    }
    
    return {
        "status": "success",
        "original_value": pace_value,
        "original_unit": from_unit,
        "converted_value": round(result, 2),
        "target_unit": to_unit,
        "formatted": format_pace(result, to_unit),
        "all_conversions": all_conversions,
        "calculated_at": datetime.now().isoformat()
    }


# =============================================================================
# TOOL 6: Calculate Body Metrics (BMI, TDEE, etc.)
# =============================================================================

def calculate_body_metrics(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str = "moderate"
) -> Dict[str, Any]:
    """
    Calculate body composition and energy expenditure metrics.
    
    Provides BMI, BMR (Basal Metabolic Rate), TDEE (Total Daily Energy Expenditure),
    and weight goals.
    
    Args:
        weight_kg: Current body weight in kilograms
        height_cm: Height in centimeters
        age: Age in years
        gender: "male" or "female"
        activity_level: Daily activity level:
                       - "sedentary": Little or no exercise
                       - "light": Light exercise 1-3 days/week
                       - "moderate": Moderate exercise 3-5 days/week
                       - "active": Hard exercise 6-7 days/week
                       - "very_active": Very hard exercise, physical job
    
    Returns:
        Dictionary with body metrics:
        - status: "success" or "error"
        - bmi: Body Mass Index
        - bmi_category: Underweight/Normal/Overweight/Obese
        - bmr: Basal Metabolic Rate (calories at rest)
        - tdee: Total Daily Energy Expenditure
        - calorie_targets: For loss/maintain/gain
        - macro_suggestions: Protein/carb/fat grams
    
    Example:
        >>> result = calculate_body_metrics(75, 175, 30, "male", "moderate")
        >>> print(result["tdee"])  # ~2500 kcal
    """
    
    if weight_kg <= 0 or height_cm <= 0 or age <= 0:
        return {"status": "error", "error_message": "Weight, height, and age must be positive"}
    
    if gender.lower() not in ["male", "female"]:
        return {"status": "error", "error_message": "Gender must be 'male' or 'female'"}
    
    # Calculate BMI
    height_m = height_cm / 100
    bmi = round(weight_kg / (height_m ** 2), 1)
    
    # BMI category
    if bmi < 18.5:
        bmi_category = "Underweight"
    elif bmi < 25:
        bmi_category = "Normal"
    elif bmi < 30:
        bmi_category = "Overweight"
    else:
        bmi_category = "Obese"
    
    # Calculate BMR using Mifflin-St Jeor equation
    if gender.lower() == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    
    bmr = round(bmr)
    
    # Activity multipliers
    activity_multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }
    
    multiplier = activity_multipliers.get(activity_level.lower(), 1.55)
    tdee = round(bmr * multiplier)
    
    # Calorie targets
    calorie_targets = {
        "aggressive_loss": tdee - 750,  # ~1.5 lb/week
        "moderate_loss": tdee - 500,    # ~1 lb/week
        "mild_loss": tdee - 250,        # ~0.5 lb/week
        "maintenance": tdee,
        "mild_gain": tdee + 250,        # ~0.5 lb/week
        "moderate_gain": tdee + 500,    # ~1 lb/week
    }
    
    # Macro suggestions (for maintenance)
    # Protein: 1.6-2.2g/kg for athletes, Carbs: 45-55%, Fat: 25-35%
    protein_g = round(weight_kg * 1.8)  # Moderate protein for active person
    fat_g = round((tdee * 0.30) / 9)    # 30% from fat
    carb_g = round((tdee - protein_g * 4 - fat_g * 9) / 4)  # Rest from carbs
    
    macro_suggestions = {
        "protein_g": protein_g,
        "carbs_g": carb_g,
        "fat_g": fat_g,
        "protein_calories": protein_g * 4,
        "carb_calories": carb_g * 4,
        "fat_calories": fat_g * 9,
    }
    
    # Healthy weight range (BMI 18.5-25)
    healthy_weight_min = round(18.5 * (height_m ** 2), 1)
    healthy_weight_max = round(24.9 * (height_m ** 2), 1)
    
    return {
        "status": "success",
        "bmi": bmi,
        "bmi_category": bmi_category,
        "bmr": bmr,
        "tdee": tdee,
        "activity_level": activity_level,
        "calorie_targets": calorie_targets,
        "macro_suggestions": macro_suggestions,
        "healthy_weight_range": {
            "min_kg": healthy_weight_min,
            "max_kg": healthy_weight_max,
        },
        "calculated_at": datetime.now().isoformat()
    }


# =============================================================================
# TOOL 7: Calculate Training Volume
# =============================================================================

def calculate_training_volume(
    sets: int,
    reps: int,
    weight: float,
    exercises: int = 1,
    unit: str = "kg"
) -> Dict[str, Any]:
    """
    Calculate training volume and related strength metrics.
    
    Volume is a key driver of muscle growth. This calculates total volume
    and provides recommendations for progressive overload.
    
    Args:
        sets: Number of sets per exercise
        reps: Number of reps per set
        weight: Weight used
        exercises: Number of exercises (for total session volume)
        unit: Weight unit - "kg" or "lb"
    
    Returns:
        Dictionary with volume metrics:
        - status: "success" or "error"
        - volume_per_exercise: Sets × Reps × Weight
        - total_volume: Volume across all exercises
        - total_reps: Total repetitions
        - volume_category: Low/Moderate/High
        - progression_suggestions: How to increase volume
    
    Example:
        >>> result = calculate_training_volume(4, 8, 80, exercises=5)
        >>> print(result["total_volume"])  # 12,800 kg
    """
    
    if sets <= 0 or reps <= 0 or weight <= 0:
        return {"status": "error", "error_message": "Sets, reps, and weight must be positive"}
    
    # Calculate volumes
    volume_per_set = reps * weight
    volume_per_exercise = sets * reps * weight
    total_reps_per_exercise = sets * reps
    
    total_volume = volume_per_exercise * exercises
    total_reps = total_reps_per_exercise * exercises
    total_sets = sets * exercises
    
    # Volume category (based on total volume for session)
    if total_volume < 5000:
        volume_category = "Low"
        volume_note = "Good for deload or recovery week"
    elif total_volume < 15000:
        volume_category = "Moderate"
        volume_note = "Standard training volume"
    elif total_volume < 30000:
        volume_category = "High"
        volume_note = "High volume - ensure adequate recovery"
    else:
        volume_category = "Very High"
        volume_note = "Very high volume - typically for advanced lifters"
    
    # Progressive overload suggestions
    progression_suggestions = [
        {
            "method": "Add weight",
            "example": f"Increase to {round(weight * 1.025, 1)} {unit} (+2.5%)",
            "new_volume": round(sets * reps * weight * 1.025 * exercises)
        },
        {
            "method": "Add reps",
            "example": f"Do {reps + 1} reps instead of {reps}",
            "new_volume": round(sets * (reps + 1) * weight * exercises)
        },
        {
            "method": "Add set",
            "example": f"Do {sets + 1} sets instead of {sets}",
            "new_volume": round((sets + 1) * reps * weight * exercises)
        },
    ]
    
    return {
        "status": "success",
        "volume_per_set": round(volume_per_set, 1),
        "volume_per_exercise": round(volume_per_exercise, 1),
        "total_volume": round(total_volume, 1),
        "total_reps": total_reps,
        "total_sets": total_sets,
        "unit": unit,
        "volume_category": volume_category,
        "volume_note": volume_note,
        "progression_suggestions": progression_suggestions,
        "calculated_at": datetime.now().isoformat()
    }


# # =============================================================================
# # ADK CALCULATOR AGENT (with BuiltInCodeExecutor)
# # =============================================================================

def create_calculator_agent(retry_config: Optional[Any] = None):
    """
    Create an ADK agent with BuiltInCodeExecutor for dynamic calculations.
    
    This agent can generate and execute Python code for ANY fitness calculation,
    not just the pre-built functions. Use this for custom or complex calculations.
    
    Args:
        retry_config: Optional retry configuration for the model
    
    Returns:
        LlmAgent with code execution capability, or None if ADK unavailable
    
    Example:
        >>> agent = create_calculator_agent()
        >>> # Use with Runner to execute custom calculations
    """
    
    if not ADK_AVAILABLE:
        print("❌ ADK not available. Cannot create calculator agent.")
        return None
    
    # Create retry config if not provided
    if retry_config is None:
        retry_config = types.HttpRetryOptions(
            attempts=5,
            exp_base=7,
            initial_delay=1,
            http_status_codes=[429, 500, 503, 504],
        )
    
    calculator_agent = LlmAgent(
        name="FitnessCalculator",
        model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
        instruction="""You are a precise fitness and training calculator.

                        When asked to perform calculations, you MUST:
                        1. Generate Python code to compute the result
                        2. Use the code executor to run the calculation
                        3. Return the exact numerical result

                        You can calculate:
                        - One-rep max (1RM) using Epley, Brzycki, or other formulas
                        - Training Stress Score (TSS) and training load
                        - Calories burned using MET values
                        - Heart rate zones (percentage or Karvonen method)
                        - Pace conversions (min/km, min/mi, km/h, mph)
                        - Body metrics (BMI, BMR, TDEE)
                        - Training volume (sets × reps × weight)
                        - Macronutrient calculations
                        - Any other fitness-related math

                        IMPORTANT: Always use code execution for calculations. Do NOT estimate.

                        Example code for 1RM calculation:
                        ```python
                        weight = 100  # kg
                        reps = 5
                        one_rm_epley = weight * (1 + reps / 30)
                        print(f"Estimated 1RM: {one_rm_epley:.1f} kg")
                        """,
                        code_executor=BuiltInCodeExecutor(), # This is the key ADK feature!
                        )

# text

    return calculator_agent
# =============================================================================
# HELPER: Get All Calculator Tools
# =============================================================================
def get_calculator_tools() -> List:
    """
    Get all calculator functions as a list for use as agent tools.

    text

    Returns:
        List of calculator functions ready to use as FunctionTools
    """
    return [
        calculate_one_rep_max,
        calculate_training_stress,
        calculate_calories_burned,
        calculate_heart_rate_zones,
        convert_pace,
        calculate_body_metrics,
        calculate_training_volume
        ]
# =============================================================================
# EXPORTS
# =============================================================================
all = [
    # Pre-built calculation tools
    "calculate_one_rep_max",
    "calculate_training_stress",
    "calculate_calories_burned",
    "calculate_heart_rate_zones",
    "convert_pace",
    "calculate_body_metrics",
    "calculate_training_volume",

    #text
    # ADK Agent with code executor
    "create_calculator_agent",

    #Helper
    "get_calculator_tools",

    # Constants
    "MET_VALUES",
    "HR_ZONES",
    "ONE_RM_FORMULAS",
    "ADK_AVAILABLE",
]