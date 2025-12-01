"""
FitForge AI — Data Extraction Agent (Aligned with your Image Parser)
====================================================================
- correctly unpacks result['data'] from tools/image_parser.py
- Auto-saves workout on successful image scan
"""

import re
from datetime import datetime
from typing import Dict, Any
import uuid

# Local Tools
try:
    from tools.image_parser import parse_workout_image
    IMAGE_PARSER_READY = True
except ImportError:
    IMAGE_PARSER_READY = False

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def generate_workout_id() -> str:
    timestamp = int(datetime.now().timestamp())
    unique = uuid.uuid4().hex[:6]
    return f"wk_{timestamp}_{unique}"

def detect_workout_type(text: str) -> str:
    if not text: return "general"
    text = text.lower()
    if "run" in text or "jog" in text or "treadmill" in text: return "run"
    if "cycle" in text or "bike" in text: return "cycle"
    if "swim" in text: return "swim"
    if "strength" in text or "lift" in text or "gym" in text: return "strength"
    if "walk" in text or "hike" in text: return "walk"
    return "general"

# =============================================================================
# TOOL: EXTRACT FROM IMAGE (The Fix)
# =============================================================================
def extract_from_image(
    tool_context: Any,
    image_path: str
) -> Dict[str, Any]:
    """
    Extracts data using your tools/image_parser.py and AUTO-SAVES it.
    """
    if not IMAGE_PARSER_READY:
        return {"status": "error", "error_message": "Image parser tool missing"}

    # 1. Run your specific tool
    # Returns: {"status": "success", "data": {"distance_km": 7.06, ...}}
    result = parse_workout_image(image_path)
    
    if result.get("status") != "success":
        return result

    # 2. Unpack the 'data' key (This was the missing link)
    raw_data = result.get("data", {})
    
    # 3. Normalize for the App
    # We map your tool's output keys to the App's expected format
    workout_data = {
        "workout_type": detect_workout_type(raw_data.get("notes", "")),
        "distance_km": raw_data.get("distance_km"),
        "duration_min": raw_data.get("duration_min"),
        "avg_hr": raw_data.get("avg_hr"),
        "elevation_gain_m": raw_data.get("elevation_gain_m"),
        "notes": raw_data.get("notes"),
        "confidence": raw_data.get("confidence", 0.0)
    }

    # 4. Auto-Build & Save Record (Zero-Click Logic)
    # If we found valid numbers, save immediately to the user's log
    if workout_data.get("distance_km") or workout_data.get("duration_min"):
        
        record = build_workout_record(
            tool_context,
            workout_type=workout_data["workout_type"],
            duration_minutes=workout_data["duration_min"],
            distance_km=workout_data["distance_km"],
            intensity="moderate", # Default
            notes=workout_data["notes"]
        )
        
        return {
            "status": "success",
            "message": f"📸 Image Processed & Saved: {record['message']}",
            "extracted_data": workout_data
        }

    return {
        "status": "partial",
        "message": "Image read, but no clear metrics found.",
        "data": workout_data
    }

# =============================================================================
# TOOL: EXTRACT FROM TEXT
# =============================================================================
def extract_from_text(
    tool_context: Any,
    text: str
) -> Dict[str, Any]:
    """Regex extraction for text input."""
    if not text: return {"status": "error", "message": "No text"}

    data = {}
    
    # Distance
    dist = re.search(r"(\d+(\.\d+)?)\s*(k|km|mi)", text, re.I)
    if dist:
        val = float(dist.group(1))
        if "mi" in dist.group(3).lower(): val *= 1.609
        data["distance_km"] = round(val, 2)

    # Duration
    dur_colon = re.search(r"(\d+):(\d+)", text)
    dur_word = re.search(r"(\d+)\s*(min|m)", text, re.I)
    if dur_colon:
        data["duration_min"] = int(dur_colon.group(1)) + int(dur_colon.group(2))/60
    elif dur_word:
        data["duration_min"] = int(dur_word.group(1))

    # Heart Rate
    hr = re.search(r"(hr|heart|bpm)\s*:?\s*(\d+)", text, re.I)
    if hr:
        data["avg_hr"] = int(hr.group(2))

    data["workout_type"] = detect_workout_type(text)
    
    return {
        "status": "success", 
        "data": data,
        "message": f"Found: {data.get('workout_type')} {data.get('distance_km','')}km"
    }



# =============================================================================
# TOOL: BUILD RECORD
# =============================================================================
def build_workout_record(
    tool_context: Any,
    workout_type: str = "general",
    duration_minutes: float = 0,
    distance_km: float = 0,
    intensity: str = "moderate",
    notes: str = ""
) -> Dict[str, Any]:
    """Saves data to the session state."""
    
    record = {
        "id": generate_workout_id(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "workout": {
            "type": workout_type,
            "duration": float(duration_minutes) if duration_minutes else 0,
            "distance_km": float(distance_km) if distance_km else 0,
            "intensity": intensity
        },
        "context": {
            "notes": notes
        }
    }

    if hasattr(tool_context, 'state'):
        log = tool_context.state.get("user:workout_log", [])
        log.append(record)
        tool_context.state["user:workout_log"] = log

    return {
        "status": "success",
        "message": f"{workout_type} ({record['workout']['duration']:.0f} min)",
        "record": record
    }

# =============================================================================
# EXPORTS
# =============================================================================
# Dummy creation function for compatibility
def create_extraction_agent(use_memory_preload=False): return None
