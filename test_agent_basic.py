#!/usr/bin/env python3
"""
Basic AAT Agent functionality test
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all agent modules can be imported"""
    print("🧪 Testing agent imports...")

    try:
        from aat.cli.agent_cmd import agent_app
        print("✅ Agent command module imported successfully")

        from aat.agent.config import AgentConfig, AgentMode
        print("✅ Agent config imported successfully")

        from aat.agent.simple_supervisor import SimpleSupervisorAgent
        print("✅ Simple supervisor imported successfully")

        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_agent_config():
    """Test agent configuration"""
    print("\n🧪 Testing agent configuration...")

    try:
        from aat.agent.config import AgentConfig, AgentMode

        config = AgentConfig(
            ai_model="zhipuai:glm-4.7",
            default_mode=AgentMode.INTERACTIVE,
            max_retry_attempts=3
        )

        print(f"✅ AgentConfig created: {config.ai_model}")
        print(f"   Mode: {config.default_mode}")
        print(f"   Max retries: {config.max_retry_attempts}")

        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_tools():
    """Test that agent tools are available"""
    print("\n🧪 Testing agent tools...")

    try:
        from aat.agent.simple_tools import get_simple_tools

        tools = get_simple_tools()
        print(f"✅ Tools loaded: {len(tools)} tools available")

        for tool in tools[:5]:  # Show first 5 tools
            print(f"   - {tool.name}: {tool.description[:50]}...")

        return True
    except Exception as e:
        print(f"❌ Tools test failed: {e}")
        return False

def main():
    """Run all basic tests"""
    print("🚀 AAT Agent Basic Functionality Test")
    print("=" * 50)

    tests = [
        test_imports,
        test_agent_config,
        test_tools
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)

    print("\n" + "=" * 50)
    print(f"📊 Results: {sum(results)}/{len(results)} tests passed")

    if all(results):
        print("✅ All basic tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())