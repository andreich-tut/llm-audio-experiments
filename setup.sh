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

# ── GPU / CUDA detection ───────────────────────────────────────────────────────
step "Detecting GPU"
HAS_GPU=false
HAS_CUDA=false

if command -v nvidia-smi &>/dev/null && nvidia-smi &>/dev/null 2>&1; then
    HAS_GPU=true
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo "unknown")
    info "NVIDIA GPU found: $GPU_NAME"

    if command -v nvcc &>/dev/null || [ -d /usr/local/cuda ]; then
        HAS_CUDA=true
        info "CUDA already installed"
    else
        warn "CUDA not found. Install it to use local Whisper on GPU."
        echo
        echo "  Recommended: install CUDA 12 via NVIDIA's official repo:"
        echo "    https://developer.nvidia.com/cuda-downloads"
        echo "  Or run: sudo apt-get install -y nvidia-cuda-toolkit"
        echo
        read -r -p "  Install nvidia-cuda-toolkit via apt now? [y/N] " ans
        if [[ "${ans,,}" == "y" ]]; then
            sudo apt-get install -y nvidia-cuda-toolkit
            HAS_CUDA=true
            info "CUDA toolkit installed"
        else
            warn "Skipping CUDA. Set WHISPER_BACKEND=groq or WHISPER_DEVICE=cpu in .env"
        fi
    fi
else
    warn "No NVIDIA GPU detected — local Whisper will run on CPU (slower)"
    warn "Consider setting WHISPER_BACKEND=groq in .env for cloud STT"
fi

# ── Python virtual environment ─────────────────────────────────────────────────
step "Setting up Python virtual environment"
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    python3 -m venv "$SCRIPT_DIR/venv"
    info "venv created at $SCRIPT_DIR/venv"
else
    info "venv already exists, reusing"
fi

# shellcheck disable=SC1091
source "$SCRIPT_DIR/venv/bin/activate"
pip install --upgrade pip -q

# ── Python dependencies ────────────────────────────────────────────────────────
step "Installing Python dependencies"
pip install -r "$SCRIPT_DIR/requirements.txt" -q

if $HAS_CUDA; then
    info "Installing onnxruntime-gpu for CUDA acceleration"
    pip install onnxruntime-gpu -q
else
    info "Installing onnxruntime (CPU)"
    pip install onnxruntime -q
fi

# ── .env setup ─────────────────────────────────────────────────────────────────
step "Configuring .env"
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    # If no GPU/CUDA, switch defaults to CPU/groq
    if ! $HAS_CUDA; then
        sed -i 's/^WHISPER_DEVICE=cuda/WHISPER_DEVICE=cpu/' "$SCRIPT_DIR/.env"
    fi
    info ".env created from .env.example"
else
    warn ".env already exists — not overwritten"
fi

# ── Done ───────────────────────────────────────────────────────────────────────
step "Setup complete"
echo
echo "Next steps:"
echo "  1. Edit .env and fill in required values:"
echo "       BOT_TOKEN   — from @BotFather on Telegram"
echo "       LLM_API_KEY — from https://openrouter.ai/keys (free tier available)"
if ! $HAS_CUDA; then
    echo
    echo "     No CUDA detected. Choose an STT backend:"
    echo "       WHISPER_BACKEND=groq  + GROQ_API_KEY  (cloud, free tier, recommended)"
    echo "       WHISPER_BACKEND=local + WHISPER_DEVICE=cpu  (local, slow)"
fi
echo
echo "  2. Activate the venv and start the bot:"
echo "       source $SCRIPT_DIR/venv/bin/activate"
echo "       python $SCRIPT_DIR/bot.py"
