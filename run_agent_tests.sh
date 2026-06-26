#!/bin/bash
# AAT Agent Functionality Test Runner
# This script runs basic tests for the AAT agent functionality

echo "🚀 AAT Agent Functionality Test Suite"
echo "========================================"
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"

    echo "🧪 Running: $test_name"
    echo "Command: $test_command"

    if eval "$test_command"; then
        echo -e "${GREEN}✅ PASSED${NC}: $test_name"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAILED${NC}: $test_name"
        ((TESTS_FAILED++))
    fi
    echo ""
}

# Test 1: Check if aat command exists
echo "=== Basic Command Tests ==="
run_test "AAT command availability" "which aat"

# Test 2: Check AAT version
run_test "AAT version check" "aat --version"

# Test 3: Check agent help
run_test "Agent command help" "aat agent --help"

# Test 4: Check if Python imports work
echo ""
echo "=== Python Import Tests ==="
run_test "Agent module imports" "python -c 'from aat.cli.agent_cmd import agent_app; print(\"✅ Agent command module imported\")'"

run_test "Agent config imports" "python -c 'from aat.agent.config import AgentConfig; print(\"✅ AgentConfig imported\")'"

run_test "Simple supervisor imports" "python -c 'from aat.agent.simple_supervisor import SimpleSupervisorAgent; print(\"✅ SimpleSupervisorAgent imported\")'"

# Test 5: Check if config file exists and is valid
echo ""
echo "=== Configuration Tests ==="
run_test "Config file exists" "test -f aat.config.yaml"

run_test "Config file is valid YAML" "python -c 'import yaml; yaml.safe_open(open(\"aat.config.yaml\")); print(\"✅ Config is valid YAML\")'"

# Test 6: Check if example scripts exist
echo ""
echo "=== Example Scripts Tests ==="
run_test "Demo script exists" "test -f examples/agent/demo.py"

run_test "Quickstart script exists" "test -f examples/agent/quickstart.py"

# Test 7: Check if tests exist
echo ""
echo "=== Test Files Tests ==="
run_test "Basic agent test exists" "test -f tests/agent/test_deepagent_basic.py"

run_test "E2E test exists" "test -f examples/agent/test_deepagent_e2e.py"

# Summary
echo ""
echo "========================================"
echo "📊 Test Summary"
echo "========================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo "Total: $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All basic tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Run: python test_agent_basic.py"
    echo "2. Try: aat agent chat"
    echo "3. Test: aat agent analyze https://example.com"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please check the errors above.${NC}"
    exit 1
fi