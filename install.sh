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
        echo "Update Node.js and re-run ./install.sh"
        echo "Ubuntu update steps:"
        echo "  1) sudo apt-get remove -y nodejs || true"
        echo "  2) curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"
        echo "  3) sudo apt-get install -y nodejs"
        echo "  4) node -v && npm -v"
        echo "Or use nvm: https://github.com/nvm-sh/nvm"
        exit 1
    fi
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
    echo -e "${GREEN}Installing backend dependencies...${NC}"
    uv pip install -r requirements.txt
else
    echo -e "${GREEN}Backend virtual environment already exists. Skipping install.${NC}"
fi

prompt_env_var "LIVEKIT_URL"
prompt_env_var "LIVEKIT_API_KEY"
prompt_env_var "LIVEKIT_API_SECRET"

echo ""
echo -e "${YELLOW}Make sure to update backend/.env with real LiveKit values:${NC}"
echo "  LIVEKIT_URL=wss://your-livekit-server"
echo "  LIVEKIT_API_KEY=your-livekit-key"
echo "  LIVEKIT_API_SECRET=your-livekit-secret"

# Frontend deps
cd "$FRONTEND_DIR"
check_node_version
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${GREEN}Installing frontend dependencies...${NC}"
    pnpm install
else
    echo -e "${GREEN}Frontend dependencies already installed. Skipping install.${NC}"
fi

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}   Install Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "${YELLOW}Run ./start.sh to launch the app.${NC}"
echo ""
