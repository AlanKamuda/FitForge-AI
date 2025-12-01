"""
FitForge AI — Image Parser Tool (Fixed)
=======================================
Extracts workout data using Gemini Vision.
"""

import json
import os
import re
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Gemini Setup
# ---------------------------------------------------------------------------
GEMINI_AVAILABLE = False
CLIENT = None

try:
    from google import genai
    from google.genai import types

    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

    if api_key:
        CLIENT = genai.Client(api_key=api_key)
        GEMINI_AVAILABLE = True
    else:
        print("⚠️ Image Parser: GOOGLE_API_KEY not found in .env")

except ImportError:
    print("⚠️ Image Parser: google-genai library not installed")

# ---------------------------------------------------------------------------
# Validation Schema
# ---------------------------------------------------------------------------
class WorkoutFromImage(BaseModel):
    distance_km: Optional[float] = Field(None, description="Distance in km")
    duration_min: Optional[float] = Field(None, description="Total minutes")
    avg_hr: Optional[int] = Field(None, description="Avg Heart Rate")
    elevation_gain_m: Optional[int] = Field(None, description="Elevation in meters")
    notes: Optional[str] = Field(None, description="Summary")
    confidence: float = Field(default=0.0)

# ---------------------------------------------------------------------------
# Internal Helper (Replaces broken OCRCleaner import)
# ---------------------------------------------------------------------------
def _clean_text(text: str) -> str:
    """Simple cleanup to replace the missing OCRCleaner class."""
    if not text: return ""
    # Remove non-ascii garbage but keep numbers and letters
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    return " ".join(text.split())

def _regex_fallback(text: str) -> Dict[str, Any]:
    """Fallback extraction if AI fails."""
    clean = _clean_text(text)
    out: Dict[str, Any] = {}

    # Distance
    dist = re.search(r"(\d+(\.\d+)?)\s*(km|mi)", clean, re.I)
    if dist:
        val = float(dist.group(1))
        if "mi" in dist.group(3).lower(): val *= 1.609
        out["distance_km"] = round(val, 2)

    # Duration
    dur = re.search(r"(\d{1,2}):(\d{2})", clean)
    if dur:
        out["duration_min"] = int(dur.group(1)) + (int(dur.group(2)) / 60)

    # HR
    hr = re.search(r"(\d{2,3})\s*bpm", clean, re.I)
    if hr:
        out["avg_hr"] = int(hr.group(1))

    return out

# ---------------------------------------------------------------------------
# MAIN TOOL FUNCTION
# ---------------------------------------------------------------------------
def parse_workout_image(image_path: str) -> Dict[str, Any]:
    """
    Extracts workout data from image.
    Returns: {"status": "success", "data": {...}}
    """
    if not GEMINI_AVAILABLE or CLIENT is None:
        return {
            "status": "error",
            "error_message": "Gemini SDK not available or Key missing."
        }

    if not os.path.exists(image_path):
        return {
            "status": "error",
            "error_message": f"File not found: {image_path}"
        }

    try:
        import PIL.Image
        img = PIL.Image.open(image_path)
    except Exception as e:
        return {"status": "error", "error_message": f"Image load failed: {e}"}

    # Prompt
    prompt = """
    Analyze this fitness app screenshot.
    Extract the workout metrics into a JSON object.
    
    Rules:
    - Convert duration to TOTAL MINUTES (e.g. 1h 30m = 90.0)
    - Convert distance to KILOMETERS
    - If a field is not visible, use null
    
    Output Schema:
    {
      "distance_km": float or null,
      "duration_min": float or null,
      "avg_hr": int or null,
      "elevation_gain_m": int or null,
      "notes": "Type of workout (Run/Cycle/etc) and brief summary",
      "confidence": float (0.0 to 1.0)
    }
    """

    # 1. Try Vision AI
    try:
        response = CLIENT.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt, img],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        raw_data = json.loads(response.text)
        
        # Validate
        validated = WorkoutFromImage(**raw_data)
        
        return {
            "status": "success",
            "data": validated.dict()
        }

    except Exception as e:
        print(f"⚠️ Vision AI failed: {e}")
        
        # 2. Fallback to simple text reading
        try:
            ocr_resp = CLIENT.models.generate_content(
                model="gemini-2.0-flash",
                contents=["Read all text in this image.", img]
            )
            fallback_data = _regex_fallback(ocr_resp.text)
            
            if fallback_data:
                fallback_data["notes"] = "Extracted via OCR Fallback"
                fallback_data["confidence"] = 0.4
                return {"status": "success", "data": fallback_data}
                
        except Exception as e2:
            print(f"⚠️ Fallback failed: {e2}")

    return {"status": "error", "error_message": "Could not extract data"}