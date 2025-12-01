import pytest
from agents.extraction_agent import (
    extract_from_text,
    build_workout_record,
    detect_workout_type
)

def test_detect_workout_type():
    assert detect_workout_type("5k run") == "run"
    assert detect_workout_type("Heavy lift") == "strength"
    assert detect_workout_type("Swim laps") == "swim"
    assert detect_workout_type("Bike ride") == "cycle"
    assert detect_workout_type("Unknown thing") == "general"


def test_extract_from_text_words(tool_context):
    # Ensure "cycle" or "bike" is in the text for detection
    text = "Cycling bike 20km for 45 mins"
    result = extract_from_text(tool_context, text)
    
    assert result["status"] == "success"
    data = result["data"]
    assert data["distance_km"] == 20.0
    assert data["duration_min"] == 45.0
    assert data["workout_type"] == "cycle"

def test_extract_from_text_empty(tool_context):
    result = extract_from_text(tool_context, "")
    assert result["status"] == "error"

