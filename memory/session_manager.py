"""
FitForge AI — Pure JSON Memory Manager (ADK Compatible)
========================================================
- No SQLite
- ADK State object compatible (no .items() usage)
- Direct Dictionary-to-JSON persistence
"""

import os
import json
from typing import Any, Dict, Optional, List
from datetime import datetime

# =============================================================================
# CONFIGURATION
# =============================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

STATE_FILE = os.path.join(DATA_DIR, "session_state.json")
MEMORY_FILE = os.path.join(DATA_DIR, "long_term_memory.json")

print(f"📂 Storage: {STATE_FILE}")

# =============================================================================
# SIMPLE STATE MANAGER
# =============================================================================
class JsonStateManager:
    """Reads and writes state to a JSON file."""
    
    def __init__(self):
        self.filepath = STATE_FILE
        self.state_cache = self._load()

    def _load(self) -> Dict:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save(self):
        """Write cache to disk."""
        try:
            with open(self.filepath, 'w') as f:
                json.dump(self.state_cache, f, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ Save failed: {e}")

    def get_user_state(self, user_id: str) -> Dict:
        """Get the dictionary for a specific user."""
        if user_id not in self.state_cache:
            self.state_cache[user_id] = {}
        return self.state_cache[user_id]


# Global instance
_STATE_MANAGER = JsonStateManager()


# =============================================================================
# COMPATIBLE CONTEXT (Looks like ADK Context to the Agents)
# =============================================================================
class MockSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.session_id = f"sess_{user_id}"
        self.id = self.session_id  # Some code uses .id


class CompatibleContext:
    def __init__(self, user_id: str, state_dict: Dict):
        self.session = MockSession(user_id)
        self.state = state_dict  # This is a reference to the global cache
        self.memory_service = None


# =============================================================================
# FITFORGE MEMORY MANAGER
# =============================================================================
class FitForgeMemoryManager:
    def __init__(self, use_persistent_sessions: bool = True):
        self.state_manager = _STATE_MANAGER

    async def get_tool_context(self, user_id: str) -> CompatibleContext:
        """Returns a context object where .state is bound to persistent JSON."""
        user_state = self.state_manager.get_user_state(user_id)
        return CompatibleContext(user_id, user_state)

    async def save_context(self, context: Any):
        """Dumps the global state to disk."""
        self.state_manager.save()
        user_id = getattr(getattr(context, 'session', None), 'user_id', 'unknown')
        print(f"💾 State saved for user: {user_id}")


# =============================================================================
# EXPORTS (ADK State Compatible - No .items() usage!)
# =============================================================================
APP_NAME = "fitforge_ai"

# Known keys to check (since ADK State doesn't support .items())
USER_PROFILE_KEYS = [
    "user:name", "user:weight_kg", "user:fitness_goal", 
    "user:experience_level", "user:age", "user:gender",
    "user:activity_level", "user:injuries", "user:equipment"
]


def save_user_profile(tool_context: Any, name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Save user profile data to state."""
    if not hasattr(tool_context, 'state'):
        return {"status": "error", "message": "No state available"}
    
    try:
        if name:
            tool_context.state["user:name"] = name
        
        for k, v in kwargs.items():
            if v is not None:
                tool_context.state[f"user:{k}"] = v
        
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


#
def get_user_profile(tool_context: Any) -> Dict[str, Any]:
    # ADK State doesn't support .items(), check if it's a dict first
    state = tool_context.state
    if hasattr(state, 'items'):
        return {k.replace("user:", ""): v for k,v in state.items() if k.startswith("user:")}
    else:
        # ADK State object - check known keys
        profile = {}
        for key in ["user:name", "user:weight_kg", "user:fitness_goal", "user:experience_level"]:
            try:
                val = state.get(key)
                if val is not None:
                    profile[key.replace("user:", "")] = val
            except:
                pass
        return profile if profile else {"status": "no_data"}

def save_workout_to_state(tool_context: Any, **kwargs) -> Dict[str, Any]:
    """Save workout to state."""
    if not hasattr(tool_context, 'state'):
        return {"status": "error", "message": "No state available"}
    
    try:
        history = tool_context.state.get("user:workout_log") or []
        # Ensure it's a list
        if not isinstance(history, list):
            history = []
        history.append(kwargs)
        tool_context.state["user:workout_log"] = history
        return {"status": "success", "total_workouts": len(history)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_session_workout_history(tool_context: Any) -> Dict[str, Any]:
    """Get workout history from state."""
    if not hasattr(tool_context, 'state'):
        return {"status": "error", "workouts": []}
    
    try:
        workouts = tool_context.state.get("user:workout_log") or []
        return {"status": "success", "workouts": workouts}
    except:
        return {"status": "success", "workouts": []}


def get_latest_analysis(tool_context: Any) -> Dict[str, Any]:
    """Get latest analysis from state."""
    if not hasattr(tool_context, 'state'):
        return {}
    
    try:
        return tool_context.state.get("app:latest_analysis") or {}
    except:
        return {}


def save_analysis_results(tool_context: Any, **kwargs):
    """Save analysis results to state."""
    if hasattr(tool_context, 'state'):
        try:
            tool_context.state["app:latest_analysis"] = kwargs
        except Exception as e:
            print(f"⚠️ Failed to save analysis: {e}")


async def auto_save_to_memory(callback_context):
    """Placeholder for memory auto-save callback."""
    pass


# Dummy tools list for agents
MEMORY_TOOLS = []


# =============================================================================
# EXPORTS
# =============================================================================
__all__ = [
    "FitForgeMemoryManager",
    "JsonStateManager",
    "CompatibleContext",
    "MockSession",
    "APP_NAME",
    "MEMORY_TOOLS",
    "save_user_profile",
    "get_user_profile",
    "save_workout_to_state",
    "get_session_workout_history",
    "get_latest_analysis",
    "save_analysis_results",
    "auto_save_to_memory",
]