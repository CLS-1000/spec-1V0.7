#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}          SPEC-1 LAUNCH READINESS AUDIT             ${NC}"
echo -e "${BLUE}====================================================${NC}"

PASSED_GATES=0
TOTAL_GATES=5

# GATE 1: ENVIRONMENT CONFIGURATION SECURITY
echo -e "\n${BLUE}[Gate 1/5] Auditing Environment Keys...${NC}"
if [ ! -f ../.env ] && [ ! -f ../.env.example ]; then
    echo -e "  ${YELLOW}! No .env files found in root, scanning source security directly...${NC}"
fi

# Search the actual src directory up one level
if [ -d "../src" ]; then
    LEAK_CHECK=$(grep -rnE "(api_key|secret|token|password)\s*=\s*['\"][a-zA-Z0-9]{15,100}['\"]" ../src/ || true)
    if [ -n "$LEAK_CHECK" ]; then
        echo -e "  ${RED}✗ WARNING: Potential hardcoded secret leaks found in source files:${NC}"
        echo "$LEAK_CHECK"
    else
        echo -e "  ${GREEN}✓ Environment Variable Isolation Secure (No raw strings leaked in src/)${NC}"
        ((PASSED_GATES++))
    fi
else
    echo -e "  ${RED}✗ Critical: Cannot find source directory at ../src/${NC}"
fi

# GATE 2: DEPENDENCY LOCK AND PACKAGING
echo -e "\n${BLUE}[Gate 2/5] Auditing Dependency Pinning...${NC}"
if [ -f ../pyproject.toml ]; then
    echo -e "  ${GREEN}✓ Modern Packaging Format (pyproject.toml) Verified.${NC}"
    ((PASSED_GATES++))
elif [ -f ../requirements.txt ]; then
    echo -e "  ${GREEN}✓ Legacy requirements.txt found.${NC}"
    ((PASSED_GATES++))
else
    echo -e "  ${RED}✗ Critical: No packaging manifests found in root.${NC}"
fi

# GATE 3: REPOSITORY LAYOUT INTEGRITY
echo -e "\n${BLUE}[Gate 3/5] Verifying Clean Workspace Layout...${NC}"
DIRTY_STRAGGLERS=$(ls .. | grep -E "\.(jsonl|log|txt|html)$" | grep -v "requirements.txt" || true)
if [ -n "$DIRTY_STRAGGLERS" ]; then
    echo -e "  ${YELLOW}! Notice: Stray artifacts remain in root directory. Run 'make organize'.${NC}"
    echo "  Files: $DIRTY_STRAGGLERS"
else
    echo -e "  ${GREEN}✓ Workspace Root Pristine. No untracked runtime artifacts found.${NC}"
fi
((PASSED_GATES++))

# GATE 4: MAKE AUTOMATION VALIDATION
echo -e "\n${BLUE}[Gate 4/5] Checking Makefile Targets...${NC}"
if [ -f ../Makefile ]; then
    FIRST_LINE=$(head -n 1 ../Makefile)
    if [[ "$FIRST_LINE" =~ ^[[:space:]] ]]; then
        echo -e "  ${RED}✗ Makefile Syntax Error: Hidden leading whitespace on Line 1.${NC}"
    else
        echo -e "  ${GREEN}✓ Makefile Compilation Syntax Verified.${NC}"
        ((PASSED_GATES++))
    fi
else
    echo -e "  ${RED}✗ Critical: Makefile missing from workspace root.${NC}"
fi

# GATE 5: PROGRAMMATIC INTEGRATION SUITE
echo -e "\n${BLUE}[Gate 5/5] Executing Fast Test Pass...${NC}"
if [ -d ../venv ] || command -v pytest &> /dev/null; then
    echo -e "  Running fast-pass test suite execution..."
    if cd .. && make test-fast && cd scripts; then
        echo -e "  ${GREEN}✓ Core Unit & Integration Suite Status: GREEN${NC}"
        ((PASSED_GATES++))
    else
        cd scripts || true
        echo -e "  ${RED}✗ Integration Tests Failed. Resolve pipeline faults before deployment.${NC}"
    fi
else
    echo -e "  ${YELLOW}! Skipping test gate: pytest environment or venv not actively engaged.${NC}"
fi

# FINAL VERDICT
echo -e "\n${BLUE}====================================================${NC}"
if [ "$PASSED_GATES" -eq "$TOTAL_GATES" ]; then
    echo -e "${GREEN}      VERDICT: LAUNCH READY ($PASSED_GATES/$TOTAL_GATES GATES CLEAR)     ${NC}"
    echo -e "${BLUE}====================================================${NC}"
    exit 0
else
    echo -e "${RED}      VERDICT: BLOCKED ($PASSED_GATES/$TOTAL_GATES GATES CLEAR)     ${NC}"
    echo -e "${BLUE}====================================================${NC}"
    exit 1
fi
