#!/bin/bash

# Geveze - AI Voice Assistant
# Start script for development

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}   Geveze - AI Voice Assistant${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

version_ge() {
    local a="$1"
    local b="$2"
    local IFS=.
    local i
    read -r -a a_parts <<< "$a"
    read -r -a b_parts <<< "$b"
    for i in 0 1 2; do
        local a_num="${a_parts[$i]:-0}"
        local b_num="${b_parts[$i]:-0}"
        if [ "$a_num" -gt "$b_num" ]; then
            return 0
        elif [ "$a_num" -lt "$b_num" ]; then
            return 1
        fi
    done
    return 0
}

check_node_version() {
    local required="20.9.0"
    if ! command -v node >/dev/null 2>&1; then
        echo -e "${YELLOW}Node.js is not installed. Install >= ${required} to run the frontend.${NC}"
        echo "Ubuntu update steps:"
        echo "  1) sudo apt-get remove -y nodejs || true"
        echo "  2) curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"
        echo "  3) sudo apt-get install -y nodejs"
        echo "  4) node -v && npm -v"
        echo "Or use nvm: https://github.com/nvm-sh/nvm"
        exit 1
    fi
    local current
    current="$(node -v | sed 's/^v//')"
    if ! version_ge "$current" "$required"; then
        echo -e "${YELLOW}Node.js ${current} detected. Next.js requires >= ${required}.${NC}"
        echo "Update Node.js and re-run ./start.sh"
        echo "Ubuntu update steps:"
        echo "  1) sudo apt-get remove -y nodejs || true"
        echo "  2) curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"
        echo "  3) sudo apt-get install -y nodejs"
        echo "  4) node -v && npm -v"
        echo "Or use nvm: https://github.com/nvm-sh/nvm"
        exit 1
    fi
}

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

get_env_value() {
    local key="$1"
    local value=""
    if [ -f "$BACKEND_DIR/.env" ]; then
        value="$(grep -E "^${key}=" "$BACKEND_DIR/.env" | head -n 1 | cut -d= -f2-)"
    fi
    echo "$value"
}

require_env_value() {
    local key="$1"
    local value=""
    value="$(get_env_value "$key")"
    if [ -z "$value" ]; then
        echo -e "${YELLOW}Missing ${key} in backend/.env. Update it and re-run ./start.sh${NC}"
        exit 1
    fi
}

reject_placeholder_env_value() {
    local key="$1"
    local placeholder="$2"
    local value=""
    value="$(get_env_value "$key")"
    if [ "$value" = "$placeholder" ]; then
        echo -e "${YELLOW}${key} is still set to the placeholder value in backend/.env.${NC}"
        echo "Update it with real credentials and re-run ./start.sh"
        exit 1
    fi
}

# Start Backend
echo -e "${GREEN}Starting Backend (Agent + API)...${NC}"
cd "$BACKEND_DIR"
if [ ! -f "$BACKEND_DIR/.venv/bin/activate" ]; then
    echo -e "${YELLOW}Backend environment not found. Run ./install.sh first.${NC}"
    exit 1
fi

source .venv/bin/activate

require_env_value "LIVEKIT_URL"
require_env_value "LIVEKIT_API_KEY"
require_env_value "LIVEKIT_API_SECRET"
reject_placeholder_env_value "LIVEKIT_URL" "wss://your-livekit-server"
reject_placeholder_env_value "LIVEKIT_API_KEY" "your-livekit-key"
reject_placeholder_env_value "LIVEKIT_API_SECRET" "your-livekit-secret"

python3 agent.py dev &
BACKEND_PID=$!

# Wait for API to be ready
echo "Waiting for API server..."
sleep 3

# Start Frontend
echo -e "${GREEN}Starting Frontend...${NC}"
cd "$FRONTEND_DIR"
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}Frontend dependencies not found. Run ./install.sh first.${NC}"
    exit 1
fi
check_node_version
pnpm dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}   Services Started!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "  Frontend:  ${BLUE}http://localhost:3000${NC}"
echo -e "  API:       ${BLUE}http://localhost:8889${NC}"
echo -e "  API Docs:  ${BLUE}http://localhost:8889/docs${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for processes
wait
