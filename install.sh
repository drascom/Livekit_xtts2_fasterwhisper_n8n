#!/bin/bash

# Geveze - AI Voice Assistant
# Install script for development

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

get_default_env_value() {
    local key="$1"
    local value=""

    if [ -f "$BACKEND_DIR/.env.example" ]; then
        value="$(grep -E "^${key}=" "$BACKEND_DIR/.env.example" | head -n 1 | cut -d= -f2-)"
        value="$(echo "$value" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
    fi

    echo "$value"
}

prompt_env_var() {
    local key="$1"
    local value=""
    local default_value=""

    if [ -f "$BACKEND_DIR/.env" ]; then
        value="$(grep -E "^${key}=" "$BACKEND_DIR/.env" | head -n 1 | cut -d= -f2-)"
    fi

    if [ -n "$value" ]; then
        return
    fi

    default_value="$(get_default_env_value "$key")"
    if [ -n "$default_value" ]; then
        read -r -p "Enter ${key} [${default_value}]: " value
        if [ -z "$value" ]; then
            value="$default_value"
        fi
    else
        read -r -p "Enter ${key}: " value
    fi

    if [ -z "$value" ]; then
        echo -e "${YELLOW}${key} is required. Exiting.${NC}"
        exit 1
    fi

    echo "${key}=${value}" >> "$BACKEND_DIR/.env"
}

# Ensure backend env file exists
if [ ! -f "$BACKEND_DIR/.env" ]; then
    if [ -f "$BACKEND_DIR/.env.example" ]; then
        echo -e "${GREEN}Creating backend/.env from backend/.env.example...${NC}"
        cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    else
        echo -e "${YELLOW}Warning: backend/.env.example not found${NC}"
        echo "Create backend/.env and configure it"
    fi
fi

# Install uv if missing
if ! command -v uv >/dev/null 2>&1; then
    echo -e "${YELLOW}uv is not installed. Installing...${NC}"
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget >/dev/null 2>&1; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        echo -e "${YELLOW}Neither curl nor wget is available. Install uv from https://docs.astral.sh/uv/${NC}"
        exit 1
    fi
    if ! command -v uv >/dev/null 2>&1; then
        echo -e "${YELLOW}uv install did not complete. Restart your shell and try again.${NC}"
        exit 1
    fi
fi

# Backend venv + deps
cd "$BACKEND_DIR"
if [ ! -f "$BACKEND_DIR/.venv/bin/activate" ]; then
    echo -e "${GREEN}Creating virtual environment...${NC}"
    uv venv
fi
echo -e "${GREEN}Installing backend dependencies...${NC}"
uv pip install -r requirements.txt

prompt_env_var "LIVEKIT_URL"
prompt_env_var "LIVEKIT_API_KEY"
prompt_env_var "LIVEKIT_API_SECRET"

# Frontend deps
cd "$FRONTEND_DIR"
echo -e "${GREEN}Installing frontend dependencies...${NC}"
pnpm install

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}   Install Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "${YELLOW}Run ./start.sh to launch the app.${NC}"
echo ""
