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

# Check if .env exists
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo -e "${YELLOW}Warning: backend/.env not found${NC}"
    echo "Copy backend/.env.example to backend/.env and configure it"
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start Backend
echo -e "${GREEN}Starting Backend (Agent + API)...${NC}"
cd "$BACKEND_DIR"
source .venv/bin/activate
python3 agent.py dev &
BACKEND_PID=$!

# Wait for API to be ready
echo "Waiting for API server..."
sleep 3

# Start Frontend
echo -e "${GREEN}Starting Frontend...${NC}"
cd "$FRONTEND_DIR"
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
