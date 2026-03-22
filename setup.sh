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

# ── Done ───────────────────────────────────────────────────────────────────────
step "Setup complete"
echo
echo "OS packages installed. Next steps:"
echo "  1. Set up Python venv and install dependencies:"
echo "       python3 -m venv venv"
echo "       source venv/bin/activate"
echo "       pip install -r requirements.txt"
if $HAS_CUDA; then
    echo "       pip install onnxruntime-gpu"
else
    echo "       pip install onnxruntime"
fi
echo
echo "  2. Edit .env and fill in required values:"
echo "       cp .env.example .env"
echo "       BOT_TOKEN   — from @BotFather on Telegram"
echo "       LLM_API_KEY — from https://openrouter.ai/keys (free tier available)"
if ! $HAS_CUDA; then
    echo
    echo "     No CUDA detected. Choose an STT backend:"
    echo "       WHISPER_BACKEND=groq  + GROQ_API_KEY  (cloud, free tier, recommended)"
    echo "       WHISPER_BACKEND=local + WHISPER_DEVICE=cpu  (local, slow)"
fi
