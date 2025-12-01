import pytest
import sys
import os
from pathlib import Path

# Add root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class MockSession:
    def __init__(self):
        self.user_id = "test_user"
        self.session_id = "test_session"

class MockToolContext:
    """Mimics the behavior of the new JSON-based context"""
    def __init__(self):
        self.session = MockSession()
        self.state = {
            "user:name": "Test Runner",
            "user:weight_kg": 75,
            "user:fitness_goal": "general_fitness",
            "temp:workout_history": [],
            "user:workout_log": []
        }
        self.memory_service = None

@pytest.fixture
def tool_context():
    return MockToolContext()
