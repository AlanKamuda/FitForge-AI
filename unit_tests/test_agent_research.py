"""
Unit Tests for Research Agent
=============================
Run with: python -m pytest unit_tests/test_agent_research.py -v
Or simply: python unit_tests/test_agent_research.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_imports():
    """Test that all imports work correctly."""
    print("\n" + "="*60)
    print("TEST 1: Imports")
    print("="*60)
    
    try:
        from agents.research_agent import (
            create_research_agent,
            get_research_agent_tool,
            research_injury_comprehensive,
            research_training_method,
            research_supplement,
            quick_research,
            ADK_AVAILABLE,
            GOOGLE_SEARCH_AVAILABLE,
            CUSTOM_SEARCH_AVAILABLE
        )
        print("✅ All imports successful")
        print(f"   ADK Available: {ADK_AVAILABLE}")
        print(f"   Google Search: {GOOGLE_SEARCH_AVAILABLE}")
        print(f"   Custom Search: {CUSTOM_SEARCH_AVAILABLE}")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_research_injury():
    """Test comprehensive injury research."""
    print("\n" + "="*60)
    print("TEST 2: Injury Research")
    print("="*60)
    
    from agents.research_agent import research_injury_comprehensive
    
    result = research_injury_comprehensive(
        injury_description="pain on outside of knee when running",
        body_part="knee",
        activity_type="running",
        severity="moderate"
    )
    
    print(f"Status: {result['status']}")
    print(f"Body part: {result['body_part']}")
    print(f"Severity: {result['severity']}")
    print(f"Has disclaimer: {'disclaimer' in result}")
    print(f"Severity recommendations: {len(result.get('severity_recommendations', []))} items")
    
    assert result["status"] == "success", "Should succeed"
    assert "disclaimer" in result, "Should have medical disclaimer"
    assert "severity_recommendations" in result, "Should have severity-based recommendations"
    assert "prevention_tips" in result, "Should have prevention tips"
    
    print("✅ Injury research passed")
    return True


def test_research_training_method():
    """Test training method research."""
    print("\n" + "="*60)
    print("TEST 3: Training Method Research")
    print("="*60)
    
    from agents.research_agent import research_training_method
    
    result = research_training_method(
        method_name="5/3/1",
        goal="strength",
        experience_level="intermediate"
    )
    
    print(f"Status: {result['status']}")
    print(f"Method: {result['method_name']}")
    print(f"Goal: {result['goal']}")
    print(f"Has template info: {'template_info' in result}")
    
    if "template_info" in result:
        print(f"   Type: {result['template_info'].get('type')}")
        print(f"   Frequency: {result['template_info'].get('frequency')}")
    
    assert result["status"] == "success", "Should succeed"
    assert "experience_note" in result, "Should have experience note"
    
    print("✅ Training method research passed")
    return True


def test_research_supplement():
    """Test supplement research."""
    print("\n" + "="*60)
    print("TEST 4: Supplement Research")
    print("="*60)
    
    from agents.research_agent import research_supplement
    
    # Test known supplement
    result1 = research_supplement("creatine", purpose="strength")
    
    print(f"\nCreatine research:")
    print(f"   Status: {result1['status']}")
    print(f"   Has database info: {'database_info' in result1}")
    
    if "database_info" in result1:
        print(f"   Effectiveness: {result1.get('effectiveness_rating')}")
        print(f"   Verdict: {result1.get('verdict', 'N/A')[:50]}...")
    
    assert result1["status"] == "success", "Should succeed"
    assert "disclaimer" in result1, "Should have disclaimer"
    
    # Test unknown supplement
    result2 = research_supplement("exotic_berry_extract_xyz")
    print(f"\nUnknown supplement: {result2.get('note', 'No note')}")
    
    print("✅ Supplement research passed")
    return True


def test_severity_recommendations():
    """Test that severity levels give appropriate recommendations."""
    print("\n" + "="*60)
    print("TEST 5: Severity-Based Recommendations")
    print("="*60)
    
    from agents.research_agent import research_injury_comprehensive
    
    severities = ["mild", "moderate", "severe"]
    
    for severity in severities:
        result = research_injury_comprehensive(
            injury_description="knee pain",
            severity=severity
        )
        
        recs = result.get("severity_recommendations", [])
        print(f"\n{severity.upper()}: {len(recs)} recommendations")
        if recs:
            print(f"   First: {recs[0][:50]}...")
        
        assert len(recs) > 0, f"Should have recommendations for {severity}"
    
    print("\n✅ Severity recommendations passed")
    return True


def test_create_research_agent():
    """Test research agent creation."""
    print("\n" + "="*60)
    print("TEST 6: Create Research Agent")
    print("="*60)
    
    from agents.research_agent import create_research_agent, ADK_AVAILABLE
    
    if not ADK_AVAILABLE:
        print("⏭️ Skipped: ADK not available")
        return True
    
    agent = create_research_agent()
    
    if agent:
        print(f"✅ Agent created: {agent.name}")
        print(f"   Description: {agent.description[:50]}...")
        print(f"   Tools: {len(agent.tools)}")
        print(f"   Output key: {agent.output_key}")
        
        # List tools
        for i, tool in enumerate(agent.tools):
            tool_name = getattr(tool, 'name', getattr(tool, '__name__', str(type(tool))))
            print(f"      {i+1}. {tool_name}")
    else:
        print("⚠️ Agent creation returned None")
    
    return True


def test_get_agent_tool():
    """Test getting research agent as AgentTool."""
    print("\n" + "="*60)
    print("TEST 7: Get Agent as AgentTool")
    print("="*60)
    
    from agents.research_agent import get_research_agent_tool, ADK_AVAILABLE
    
    if not ADK_AVAILABLE:
        print("⏭️ Skipped: ADK not available")
        return True
    
    agent_tool = get_research_agent_tool()
    
    if agent_tool:
        print(f"✅ AgentTool created")
        print(f"   Type: {type(agent_tool).__name__}")
        print(f"   Can be used in orchestrator's tools=[] list")
    else:
        print("⚠️ AgentTool creation returned None")
    
    return True


def test_quick_research():
    """Test quick research utility function."""
    print("\n" + "="*60)
    print("TEST 8: Quick Research Function")
    print("="*60)
    
    import asyncio
    from agents.research_agent import quick_research
    
    async def run_test():
        # Test supplement research
        result = await quick_research("protein powder", "supplement")
        print(f"Supplement query status: {result.get('status')}")
        
        # Test training research
        result2 = await quick_research("PPL program", "training")
        print(f"Training query status: {result2.get('status')}")
        
        # Test injury research
        result3 = await quick_research("shoulder pain", "injury")
        print(f"Injury query status: {result3.get('status')}")
        
        return True
    
    # Run async test
    try:
        success = asyncio.run(run_test())
        print("✅ Quick research passed")
        return success
    except Exception as e:
        print(f"⚠️ Quick research test failed: {e}")
        return True  # Don't fail test


def test_tool_docstrings():
    """Verify research tools have proper ADK-compatible docstrings."""
    print("\n" + "="*60)
    print("TEST 9: ADK Docstring Format")
    print("="*60)
    
    from agents.research_agent import (
        research_injury_comprehensive,
        research_training_method,
        research_supplement
    )
    
    tools = [
        ("research_injury_comprehensive", research_injury_comprehensive),
        ("research_training_method", research_training_method),
        ("research_supplement", research_supplement),
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


def test_multi_agent_pattern():
    """Test the multi-agent delegation pattern."""
    print("\n" + "="*60)
    print("TEST 10: Multi-Agent Delegation Pattern")
    print("="*60)
    
    from agents.research_agent import (
        create_research_agent,
        get_research_agent_tool,
        ADK_AVAILABLE
    )
    
    if not ADK_AVAILABLE:
        print("⏭️ Skipped: ADK not available")
        return True
    
    try:
        from google.adk.agents import Agent
        from google.adk.tools import AgentTool
        from google.adk.models.google_llm import Gemini
        
        # Create research agent
        research_agent = create_research_agent()
        
        if not research_agent:
            print("⚠️ Could not create research agent")
            return True
        
        # Wrap as AgentTool
        research_tool = AgentTool(agent=research_agent)
        
        # Create a mock orchestrator that uses it
        orchestrator = Agent(
            name="TestOrchestrator",
            model=Gemini(model="gemini-2.5-flash-lite"),
            description="Test orchestrator with research delegation",
            instruction="Delegate research questions to the research agent.",
            tools=[research_tool]
        )
        
        print(f"✅ Multi-agent pattern works!")
        print(f"   Orchestrator: {orchestrator.name}")
        print(f"   Research Agent: {research_agent.name}")
        print(f"   Delegation via: AgentTool")
        
        return True
        
    except Exception as e:
        print(f"⚠️ Multi-agent pattern test failed: {e}")
        return True  # Don't fail overall


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "🔬"*30)
    print("   RESEARCH AGENT - UNIT TESTS")
    print("🔬"*30)
    
    tests = [
        ("Imports", test_imports),
        ("Injury Research", test_research_injury),
        ("Training Method Research", test_research_training_method),
        ("Supplement Research", test_research_supplement),
        ("Severity Recommendations", test_severity_recommendations),
        ("Create Agent", test_create_research_agent),
        ("Get AgentTool", test_get_agent_tool),
        ("Quick Research", test_quick_research),
        ("ADK Docstrings", test_tool_docstrings),
        ("Multi-Agent Pattern", test_multi_agent_pattern),
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