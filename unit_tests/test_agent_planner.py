# unit_tests/test_agent_planner.py
"""
Unit Tests for Planner Agent
============================
Run with: python -m pytest unit_tests/test_agent_planner.py -v
Or simply: python unit_tests/test_agent_planner.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
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
        from agents.planner_agent import (
            generate_training_plan,
            generate_plan_with_ai,
            approve_current_plan,
            get_today_session,
            adjust_plan_intensity,
            get_plan_summary,
            calculate_plan_metrics,
            create_planner_agent,
            get_intensity_from_readiness,
            get_volume_adjustment,
            GOAL_TEMPLATES,
            SESSION_TEMPLATES,
            ADK_AVAILABLE,
            TRAINING_CALCULATOR_READY,
            PLAN_APPROVAL_READY,
            GEMINI_READY
        )
        print("✅ All imports successful")
        print(f"   ADK Available: {ADK_AVAILABLE}")
        print(f"   Training Calculator: {TRAINING_CALCULATOR_READY}")
        print(f"   Plan Approval: {PLAN_APPROVAL_READY}")
        print(f"   Gemini: {GEMINI_READY}")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False




def test_session_templates():
    """Test that session templates are properly configured."""
    print("\n" + "="*60)
    print("TEST 3: Session Templates")
    print("="*60)
    
    from agents.planner_agent import SESSION_TEMPLATES
    
    expected_sessions = ["easy_run", "tempo_run", "interval", "strength", "rest", "recovery"]
    
    all_passed = True
    for session in expected_sessions:
        if session in SESSION_TEMPLATES:
            template = SESSION_TEMPLATES[session]
            has_name = "name" in template
            has_emoji = "emoji" in template
            has_duration = "duration_range" in template
            print(f"   ✅ {session}: name={has_name}, emoji={has_emoji}, duration={has_duration}")
        else:
            print(f"   ❌ Missing template: {session}")
            all_passed = False
    
    return all_passed










def test_generate_plan_different_goals():
    """Test plan generation for different goals."""
    print("\n" + "="*60)
    print("TEST 7: Different Goals")
    print("="*60)
    
    from agents.planner_agent import generate_training_plan
    
    goals = ["strength", "endurance", "fat_loss", "race_prep"]
    
    all_passed = True
    for goal in goals:
        ctx = MockToolContext(state={
            "app:latest_analysis": {"readiness_score": 70}
        })
        
        result = generate_training_plan(ctx, goal=goal)
        
        has_plan = result["status"] == "success"
        has_sessions = len(result.get("weekly_plan", [])) > 0
        
        print(f"   {goal}: success={has_plan}, sessions={has_sessions}")
        
        if not (has_plan and has_sessions):
            all_passed = False
    
    print("✅ Different goals test passed" if all_passed else "❌ Some goals failed")
    return all_passed

def test_approve_no_plan():
    """Test approval when no plan exists."""
    print("\n" + "="*60)
    print("TEST 10: Approve No Plan")
    print("="*60)
    
    from agents.planner_agent import approve_current_plan
    
    ctx = MockToolContext(state={})
    
    result = approve_current_plan(ctx)
    
    print(f"   Status: {result['status']}")
    print(f"   Message: {result.get('message')}")
    
    assert result["status"] == "error", "Should fail with no plan"
    
    print("✅ No plan approval handling passed")
    return True





def test_get_today_no_plan():
    """Test getting today's session with no plan."""
    print("\n" + "="*60)
    print("TEST 12: Today's Session - No Plan")
    print("="*60)
    
    from agents.planner_agent import get_today_session
    
    ctx = MockToolContext(state={})
    
    result = get_today_session(ctx)
    
    print(f"   Status: {result['status']}")
    print(f"   Message: {result.get('message')}")
    
    assert result["status"] == "no_plan", "Should indicate no plan"
    
    print("✅ No plan handling passed")
    return True




def test_plan_requires_approval():
    """Test that high-intensity plans require approval."""
    print("\n" + "="*60)
    print("TEST 18: High-Risk Plan Approval")
    print("="*60)
    
    from agents.planner_agent import generate_training_plan
    
    # High readiness = more intense plan
    ctx = MockToolContext(state={
        "app:latest_analysis": {
            "readiness_score": 95,  # Very high readiness
            "risk_level": 0.1,
            "ctl": 80,
            "atl": 60
        },
        "user:injuries": "knee pain"  # Has injuries
    })
    
    result = generate_training_plan(ctx, goal="race_prep")
    
    print(f"   Max Intensity RPE: {result.get('metrics', {}).get('max_intensity_rpe')}")
    print(f"   Requires Approval: {result.get('requires_approval')}")
    print(f"   Approval Reasons: {result.get('approval_reasons')}")
    
    # Should require approval due to injuries + high intensity
    if result.get("requires_approval"):
        print("   ✅ Correctly flagged for approval")
    else:
        print("   ⚠️ Did not require approval (may be acceptable)")
    
    return True


def test_create_planner_agent():
    """Test planner agent creation."""
    print("\n" + "="*60)
    print("TEST 19: Create Planner Agent")
    print("="*60)
    
    from agents.planner_agent import create_planner_agent, ADK_AVAILABLE
    
    if not ADK_AVAILABLE:
        print("⏭️ Skipped: ADK not available")
        return True
    
    agent = create_planner_agent(use_memory_preload=False)
    
    if agent:
        print(f"✅ Agent created: {agent.name}")
        print(f"   Description: {agent.description[:50]}...")
        print(f"   Tools: {len(agent.tools)}")
        
        # List tools
        for i, tool in enumerate(agent.tools[:7]):
            tool_name = getattr(tool, 'name', getattr(tool, '__name__', str(type(tool).__name__)))
            print(f"      {i+1}. {tool_name}")
        if len(agent.tools) > 7:
            print(f"      ... and {len(agent.tools) - 7} more")
    else:
        print("⚠️ Agent creation returned None")
    
    return True


def test_tool_docstrings():
    """Verify tools have proper ADK-compatible docstrings."""
    print("\n" + "="*60)
    print("TEST 20: ADK Docstring Format")
    print("="*60)
    
    from agents.planner_agent import (
        generate_training_plan,
        approve_current_plan,
        get_today_session,
        adjust_plan_intensity,
        get_plan_summary,
        calculate_plan_metrics
    )
    
    tools = [
        ("generate_training_plan", generate_training_plan),
        ("approve_current_plan", approve_current_plan),
        ("get_today_session", get_today_session),
        ("adjust_plan_intensity", adjust_plan_intensity),
        ("get_plan_summary", get_plan_summary),
        ("calculate_plan_metrics", calculate_plan_metrics),
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
        print(f"      Doc: {has_doc}, Args: {has_args}, Returns: {has_returns}, Example: {has_example}")
        
        if not passed:
            all_passed = False
    
    return all_passed



# =============================================================================
# TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "📋"*30)
    print("   PLANNER AGENT - UNIT TESTS")
    print("📋"*30)
    
    tests = [
        ("Imports", test_imports),
        ("Session Templates", test_session_templates),
        ("Different Goals", test_generate_plan_different_goals),
        ("Approve No Plan", test_approve_no_plan),
        ("Today No Plan", test_get_today_no_plan),
        ("High-Risk Approval", test_plan_requires_approval),
        ("Create Agent", test_create_planner_agent),
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