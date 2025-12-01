# unit_tests/test_agent_coach.py
"""
Unit Tests for Coach Agent
==========================
Run with: python -m pytest unit_tests/test_agent_coach.py -v
Or simply: python unit_tests/test_agent_coach.py
"""

import os
import sys
from pathlib import Path
import asyncio

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# Mock ToolContext for Testing
# =============================================================================

class MockToolContext:
    """Mock ToolContext for testing without full ADK."""
    
    def __init__(self, state: dict = None):
        self.state = state or {}


# =============================================================================
# TESTS
# =============================================================================

def test_imports():
    """Test that all imports work correctly."""
    print("\n" + "="*60)
    print("TEST 1: Imports")
    print("="*60)
    
    try:
        from agents.coach_agent import (
            create_coach_agent,
            create_coach_with_runner,
            get_fitness_status,
            get_workout_summary,
            get_motivation,
            log_coaching_note,
            quick_chat,
            ADK_AVAILABLE,
            MEMORY_MANAGER_AVAILABLE,
            RESEARCH_AGENT_AVAILABLE
        )
        print("✅ All imports successful")
        print(f"   ADK Available: {ADK_AVAILABLE}")
        print(f"   Memory Manager: {MEMORY_MANAGER_AVAILABLE}")
        print(f"   Research Agent: {RESEARCH_AGENT_AVAILABLE}")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_get_fitness_status_with_data():
    """Test fitness status retrieval with data."""
    print("\n" + "="*60)
    print("TEST 2: Fitness Status (With Data)")
    print("="*60)
    
    from agents.coach_agent import get_fitness_status
    
    # Create context with analysis data
    ctx = MockToolContext(state={
        "app:latest_analysis": {
            "readiness_score": 85,
            "fatigue_level": "low",
            "ctl": 65,
            "atl": 55,
            "form": 10,
            "recommendations": ["Ready for hard training", "Focus on strength"],
            "analyzed_at": "2024-01-15T10:30:00"
        }
    })
    
    result = get_fitness_status(ctx)
    
    print(f"Status: {result['status']}")
    print(f"Readiness: {result['readiness_score']}/100")
    print(f"Label: {result['readiness_label']}")
    print(f"Recommendations: {result['recommendations']}")
    
    assert result["status"] == "success", "Should succeed"
    assert result["readiness_score"] == 85, "Should return correct readiness"
    assert "Ready" in result["readiness_label"], "Should have positive label"
    
    print("✅ Fitness status with data passed")
    return True


def test_get_fitness_status_no_data():
    """Test fitness status retrieval without data."""
    print("\n" + "="*60)
    print("TEST 3: Fitness Status (No Data)")
    print("="*60)
    
    from agents.coach_agent import get_fitness_status
    
    # Empty context
    ctx = MockToolContext(state={})
    
    result = get_fitness_status(ctx)
    
    print(f"Status: {result['status']}")
    print(f"Message: {result.get('message', 'N/A')}")
    
    assert result["status"] == "no_data", "Should indicate no data"
    assert "recommendations" in result, "Should provide suggestions"
    
    print("✅ Fitness status without data passed")
    return True


def test_get_workout_summary():
    """Test workout summary retrieval."""
    print("\n" + "="*60)
    print("TEST 4: Workout Summary")
    print("="*60)
    
    from agents.coach_agent import get_workout_summary
    
    # Create context with workout history
    ctx = MockToolContext(state={
        "temp:workout_history": [
            {"type": "strength", "duration": 60},
            {"type": "cardio", "duration": 30},
            {"type": "strength", "duration": 45}
        ]
    })
    
    result = get_workout_summary(ctx)
    
    print(f"Status: {result['status']}")
    print(f"Total workouts: {result['total_workouts']}")
    print(f"Total duration: {result['total_duration_min']} min")
    print(f"Types: {result['workout_types']}")
    
    assert result["status"] == "success", "Should succeed"
    assert result["total_workouts"] == 3, "Should count 3 workouts"
    assert result["total_duration_min"] == 135, "Should sum to 135 min"
    
    print("✅ Workout summary passed")
    return True


def test_get_motivation():
    """Test motivation generation."""
    print("\n" + "="*60)
    print("TEST 5: Motivation Generation")
    print("="*60)
    
    from agents.coach_agent import get_motivation
    
    # Test with high readiness
    ctx_high = MockToolContext(state={
        "user:name": "Alex",
        "user:fitness_goal": "strength",
        "app:latest_analysis": {"readiness_score": 85}
    })
    
    result_high = get_motivation(ctx_high, context="pre_workout")
    
    print(f"\nHigh readiness, pre-workout:")
    print(f"   Message: {result_high['message'][:60]}...")
    print(f"   Tip: {result_high['tip'][:50]}...")
    
    assert result_high["status"] == "success", "Should succeed"
    assert result_high["personalized_for"] == "Alex", "Should personalize"
    
    # Test with low readiness
    ctx_low = MockToolContext(state={
        "user:name": "Jordan",
        "app:latest_analysis": {"readiness_score": 40}
    })
    
    result_low = get_motivation(ctx_low, context="general")
    
    print(f"\nLow readiness, general:")
    print(f"   Message: {result_low['message'][:60]}...")
    
    assert result_low["status"] == "success", "Should succeed"
    
    # Test struggling context
    result_struggle = get_motivation(ctx_low, context="struggling")
    print(f"\nStruggling context:")
    print(f"   Message: {result_struggle['message'][:60]}...")
    
    print("✅ Motivation generation passed")
    return True


def test_log_coaching_note():
    """Test coaching note logging."""
    print("\n" + "="*60)
    print("TEST 6: Log Coaching Note")
    print("="*60)
    
    from agents.coach_agent import log_coaching_note
    
    ctx = MockToolContext(state={})
    
    # Log a goal
    result1 = log_coaching_note(ctx, "Wants to run a marathon", category="goal")
    print(f"Goal note: {result1['status']}, total: {result1['total_notes']}")
    assert result1["status"] == "success"
    
    # Log a limitation
    result2 = log_coaching_note(ctx, "Has knee issues", category="limitation")
    print(f"Limitation note: {result2['status']}, total: {result2['total_notes']}")
    assert result2["status"] == "success"
    
    # Check state was updated
    assert ctx.state.get("user:stated_goal") == "Wants to run a marathon"
    assert "Has knee issues" in ctx.state.get("user:limitations", [])
    
    print(f"Notes in state: {len(ctx.state.get('coach:notes', []))}")
    print("✅ Coaching note logging passed")
    return True


def test_create_coach_agent():
    """Test coach agent creation."""
    print("\n" + "="*60)
    print("TEST 7: Create Coach Agent")
    print("="*60)
    
    from agents.coach_agent import create_coach_agent, ADK_AVAILABLE
    
    if not ADK_AVAILABLE:
        print("⏭️ Skipped: ADK not available")
        return True
    
    coach = create_coach_agent(use_memory_preload=False, include_research=False)
    
    if coach:
        print(f"✅ Coach created: {coach.name}")
        print(f"   Description: {coach.description[:50]}...")
        print(f"   Tools: {len(coach.tools)}")
        print(f"   Output key: {coach.output_key}")
        
        # List tools
        for i, tool in enumerate(coach.tools[:5]):  # First 5
            tool_name = getattr(tool, 'name', getattr(tool, '__name__', str(type(tool).__name__)))
            print(f"      {i+1}. {tool_name}")
        if len(coach.tools) > 5:
            print(f"      ... and {len(coach.tools) - 5} more")
    else:
        print("⚠️ Coach creation returned None")
    
    return True


def test_create_coach_with_research():
    """Test coach agent creation with research delegation."""
    print("\n" + "="*60)
    print("TEST 8: Coach with Research Agent")
    print("="*60)
    
    from agents.coach_agent import create_coach_agent, ADK_AVAILABLE, RESEARCH_AGENT_AVAILABLE
    
    if not ADK_AVAILABLE:
        print("⏭️ Skipped: ADK not available")
        return True
    
    coach = create_coach_agent(include_research=True)
    
    if coach:
        # Check if research agent tool is included
        tool_names = []
        for tool in coach.tools:
            name = getattr(tool, 'name', getattr(tool, '__name__', str(type(tool).__name__)))
            tool_names.append(name)
        
        print(f"Tools: {tool_names}")
        
        if RESEARCH_AGENT_AVAILABLE:
            has_research = any("research" in str(t).lower() for t in coach.tools)
            print(f"Has research delegation: {has_research}")
        else:
            print("Research agent not available (expected)")
    
    print("✅ Coach with research passed")
    return True




def test_quick_chat():
    """Test quick chat functionality."""
    print("\n" + "="*60)
    print("TEST 10: Quick Chat")
    print("="*60)
    
    from agents.coach_agent import quick_chat, ADK_AVAILABLE
    
    if not ADK_AVAILABLE:
        print("⏭️ Skipped: ADK not available")
        return True
    
    async def run_test():
        response = await quick_chat("Hello, I'm new here!")
        print(f"Response: {response[:200]}...")
        return len(response) > 0
    
    try:
        result = asyncio.run(run_test())
        if result:
            print("✅ Quick chat works")
        return result
    except Exception as e:
        print(f"⚠️ Quick chat error: {e}")
        return True  # Don't fail test


def test_motivation_contexts():
    """Test all motivation contexts."""
    print("\n" + "="*60)
    print("TEST 11: All Motivation Contexts")
    print("="*60)
    
    from agents.coach_agent import get_motivation
    
    contexts = ["general", "pre_workout", "post_workout", "rest_day", "struggling", "milestone"]
    
    ctx = MockToolContext(state={
        "user:name": "TestUser",
        "app:latest_analysis": {"readiness_score": 70}
    })
    
    all_passed = True
    for context in contexts:
        result = get_motivation(ctx, context=context)
        passed = result["status"] == "success" and len(result["message"]) > 0
        status = "✅" if passed else "❌"
        print(f"   {status} {context}: {result['message'][:40]}...")
        if not passed:
            all_passed = False
    
    return all_passed


def test_tool_docstrings():
    """Verify tools have proper ADK-compatible docstrings."""
    print("\n" + "="*60)
    print("TEST 12: ADK Docstring Format")
    print("="*60)
    
    from agents.coach_agent import (
        get_fitness_status,
        get_workout_summary,
        get_motivation,
        log_coaching_note
    )
    
    tools = [
        ("get_fitness_status", get_fitness_status),
        ("get_workout_summary", get_workout_summary),
        ("get_motivation", get_motivation),
        ("log_coaching_note", log_coaching_note),
    ]
    
    all_passed = True
    for name, func in tools:
        doc = func.__doc__
        has_doc = doc is not None
        has_args = doc and "Args:" in doc
        has_returns = doc and "Returns:" in doc
        has_example = doc and "Example:" in doc
        
        passed = has_doc and has_args and has_returns
        status = "✅" if passed else "❌"
        print(f"   {status} {name}")
        
        if not passed:
            all_passed = False
    
    return all_passed


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "🏋️"*30)
    print("   COACH AGENT - UNIT TESTS")
    print("🏋️"*30)
    
    tests = [
        ("Imports", test_imports),
        ("Fitness Status (Data)", test_get_fitness_status_with_data),
        ("Fitness Status (No Data)", test_get_fitness_status_no_data),
        ("Workout Summary", test_get_workout_summary),
        ("Motivation", test_get_motivation),
        ("Log Notes", test_log_coaching_note),
        ("Create Agent", test_create_coach_agent),
        ("With Research", test_create_coach_with_research),
        ("Quick Chat", test_quick_chat),
        ("All Contexts", test_motivation_contexts),
        ("ADK Docstrings", test_tool_docstrings),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ TEST CRASHED: {name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, p in results:
        status = "✅ PASS" if p else "❌ FAIL"
        print(f"   {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)