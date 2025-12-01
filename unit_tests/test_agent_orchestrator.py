import pytest
from agents.orchestrator import (
    detect_intent,
    UserIntent,
    route_request,
    process_workout_input
)

def test_detect_intent_greeting():
    intent, conf = detect_intent("Hello coach")
    assert intent == UserIntent.GREETING

def test_detect_intent_workout():
    intent, conf = detect_intent("I ran 5k today")
    assert intent == UserIntent.LOG_WORKOUT

def test_detect_intent_injury():
    intent, conf = detect_intent("My knee hurts when I run")
    assert intent == UserIntent.INJURY_QUESTION

def test_route_request_workout(tool_context):
    # Test routing logic
    response = route_request("I ran 5k", tool_context)
    assert response["action"] == "trigger_extraction"
    assert response["intent"] == "log_workout"

