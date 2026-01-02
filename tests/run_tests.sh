#!/bin/bash
# Run STT and TTS service tests against Docker containers
#
# Usage:
#   ./run_tests.sh              # Run all tests
#   ./run_tests.sh stt          # Run only STT tests
#   ./run_tests.sh tts          # Run only TTS tests
#   ./run_tests.sh quick        # Run only quick tests (skip slow)
#
# Prerequisites:
#   - Docker containers must be running: docker compose up -d stt-service tts-service
#   - Python virtual environment with test dependencies installed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Geveze Service Tests ===${NC}"
echo ""

# Check if services are running
check_services() {
    echo -e "${YELLOW}Checking service availability...${NC}"

    STT_URL="${STT_SERVICE_URL:-http://localhost:8000}"
    TTS_URL="${TTS_SERVICE_URL:-http://localhost:8003}"

    # Check STT service
    if curl -s -o /dev/null -w "%{http_code}" "$STT_URL/health" | grep -q "200"; then
        echo -e "  STT service (Speaches): ${GREEN}Running${NC} at $STT_URL"
    else
        echo -e "  STT service (Speaches): ${RED}Not running${NC} at $STT_URL"
        echo -e "  ${YELLOW}Start with: docker compose up -d stt-service${NC}"
        STT_DOWN=1
    fi

    # Check TTS service
    if curl -s -o /dev/null -w "%{http_code}" "$TTS_URL/v1/audio/voices" | grep -q "200"; then
        echo -e "  TTS service (XTTS):     ${GREEN}Running${NC} at $TTS_URL"
    else
        echo -e "  TTS service (XTTS):     ${RED}Not running${NC} at $TTS_URL"
        echo -e "  ${YELLOW}Start with: docker compose up -d tts-service${NC}"
        TTS_DOWN=1
    fi

    echo ""

    if [[ -n "$STT_DOWN" || -n "$TTS_DOWN" ]]; then
        echo -e "${YELLOW}Warning: Some services are not running. Tests may fail.${NC}"
        echo -e "Run: ${GREEN}docker compose up -d stt-service tts-service${NC}"
        echo ""
        read -p "Continue anyway? [y/N] " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Parse arguments
PYTEST_ARGS=""
case "${1:-all}" in
    stt)
        echo "Running STT service tests only..."
        PYTEST_ARGS="-m stt"
        ;;
    tts)
        echo "Running TTS service tests only..."
        PYTEST_ARGS="-m tts"
        ;;
    quick)
        echo "Running quick tests only (skipping slow tests)..."
        PYTEST_ARGS="-m 'not slow'"
        ;;
    all)
        echo "Running all tests..."
        ;;
    *)
        echo "Unknown option: $1"
        echo "Usage: $0 [stt|tts|quick|all]"
        exit 1
        ;;
esac

# Check services
check_services

# Change to project directory
cd "$PROJECT_DIR"

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
echo ""

if [[ -n "$PYTEST_ARGS" ]]; then
    python -m pytest tests/ $PYTEST_ARGS -v
else
    python -m pytest tests/ -v
fi

EXIT_CODE=$?

echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Some tests failed.${NC}"
fi

exit $EXIT_CODE
