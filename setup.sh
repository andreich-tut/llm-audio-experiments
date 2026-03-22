#!/usr/bin/env bash
# Setup script for tg-voice bot on Ubuntu 24
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
step()  { echo -e "\n${CYAN}==> $*${NC}"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── System packages ────────────────────────────────────────────────────────────
step "Installing system packages"
sudo apt-get update -qq
sudo apt-get install -y \
    python3 python3-venv python3-pip \
    ffmpeg \
    git curl ca-certificates

info "ffprobe: $(ffprobe -version 2>&1 | head -1)"
info "Python:  $(python3 --version)"

# ── Python venv ────────────────────────────────────────────────────────────────
step "Setting up Python virtual environment"
cd "$SCRIPT_DIR"
python3 -m venv venv
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt
info "Dependencies installed into venv/"

# ── Done ───────────────────────────────────────────────────────────────────────
step "Setup complete"
echo
echo "Next steps:"
echo "  1. Activate the venv before running:"
echo "       source venv/bin/activate"
echo
echo "  2. Edit .env and fill in required values:"
echo "       cp .env.example .env"
echo "       BOT_TOKEN   — from @BotFather on Telegram"
echo "       LLM_API_KEY — from https://openrouter.ai/keys (free tier available)"
