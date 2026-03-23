# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Telegram Voice → LLM Bot**: A local Telegram bot that processes voice messages via faster-whisper (STT) and generates responses using Ollama (LLM).

- **Stack**: Python 3.11+, aiogram 3, faster-whisper, Ollama API
- **Architecture**: Async event-driven (asyncio), in-memory conversation state
- **Language**: Russian UI/prompts, but flexible

## Architecture & Key Concepts

### Data Flow
```
User sends voice → bot downloads .ogg file → faster-whisper transcribes (GPU) →
Ollama API processes with conversation context → response sent back to user
```

### Project Structure
```
bot.py              — Entrypoint: Telegram handlers, commands, message routing
config.py           — Env loading, constants, logging, access control
state.py            — In-memory state: conversations, user modes, YT cache
services/
  stt.py            — Whisper model init + transcription (with audio chunking)
  llm.py            — Ollama chat (with history) + one-shot summarization
  youtube.py        — YouTube audio download (yt-dlp), diarization helpers
  gdocs.py          — Google Docs integration (optional)
prompts/
  system.md         — Main chat system prompt
  summary_brief.md  — Brief YouTube summary prompt
  summary_detailed.md — Detailed YouTube summary prompt
  summary_keypoints.md — Keypoints extraction prompt
  note.md           — Obsidian note formatting prompt
tools/
  audio_splitter.py — FFmpeg-based audio chunking (by size or time)
  transcribe_diarize.py — whisperX + pyannote diarization CLI
```

### Key Functions
- `services.stt.transcribe(file_path)` → splits audio into chunks, runs faster-whisper in executor threads
- `services.llm.ask_ollama(user_id, message)` → sends to Ollama with conversation history
- `services.llm.summarize_ollama(text, detail_level)` → one-shot summarization (no history)
- `services.youtube.download_yt_audio(url)` → downloads YouTube audio via yt-dlp
- `state.get_history(user_id)` / `state.add_to_history(...)` → per-user message history
- `config.is_allowed(user_id)` → access control check

### Configuration
All config via `.env` file (template in `.env.example`):
```
BOT_TOKEN=<Telegram bot token>
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b          # Change model here
WHISPER_MODEL=medium           # tiny/small/medium/large-v3
WHISPER_DEVICE=cuda            # cuda or cpu
ALLOWED_USERS=                 # Comma-separated user IDs (empty = all)
SYSTEM_PROMPT=prompts/system.md  # Path to system prompt .md file
```

## Development & Running

### Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: add BOT_TOKEN, adjust OLLAMA_MODEL/WHISPER_MODEL as needed
```

### Prerequisites
- **Ollama**: Running locally on `http://localhost:11434` with a model pulled (e.g., `ollama pull qwen3:8b`)
- **NVIDIA GPU + CUDA**: For faster-whisper GPU acceleration (WHISPER_DEVICE=cuda)
  - Falls back to CPU if not available (set WHISPER_DEVICE=cpu)
- **Telegram Bot Token**: From [@BotFather](https://t.me/BotFather)

### Run Bot
```bash
python bot.py
```
Bot will log startup: `Starting bot... Model: {OLLAMA_MODEL}, Whisper: {WHISPER_MODEL}`

### Debugging
- Check logs in console (basicConfig level=INFO)
- `/ping` command checks Ollama availability and lists models
- Conversation history is in-memory, cleared on restart

## Bot Commands
| Command | Handler | Notes |
|---------|---------|-------|
| `/start` | `cmd_start()` | Shows help & available commands |
| `/clear` | `cmd_clear()` | Clears user's conversation history |
| `/model` | `cmd_model()` | Shows current OLLAMA_MODEL and WHISPER_MODEL |
| `/ping` | `cmd_ping()` | Tests Ollama connection, lists available models |

Voice and text message handlers check `is_allowed()` before processing.

## Common Tasks

### Change LLM Model
Edit `.env`: `OLLAMA_MODEL=llama2` (or any model available in Ollama)

### Change Whisper Model (STT Quality/Speed)
Edit `.env`: `WHISPER_MODEL=large-v3` (better quality, slower) or `tiny` (faster, lower quality)
- GPU VRAM usage: tiny ~1GB, small ~2GB, medium ~5GB, large-v3 ~10GB

### Customize System Prompt
Edit `.env` `SYSTEM_PROMPT=` to change LLM personality/behavior

### Restrict Access
Edit `.env`: `ALLOWED_USERS=123456789,987654321` (comma-separated Telegram user IDs)
- Find your ID: message [@userinfobot](https://t.me/userinfobot) in Telegram

### Run on CPU (no GPU)
Edit `.env`: `WHISPER_DEVICE=cpu`
- slower STT, but works on any hardware

## Code Notes

- **Conversation history**: Trimmed to last MAX_HISTORY (20) pairs to avoid context overflow
- **Message splitting**: Responses >4000 chars split into multiple Telegram messages (char limit per message)
- **Async**: Uses asyncio + aiogram for non-blocking I/O (voice download, Ollama API calls)
- **Error handling**: Exceptions logged and user notified in chat
- **No persistence**: History lost on restart (by design; stored in `conversations` dict only)

## Dependencies
- `aiogram>=3.10` — Telegram bot framework (async)
- `python-dotenv>=1.0` — Load .env config
- `httpx>=0.27` — Async HTTP client for Ollama API
- `faster-whisper>=1.0` — Local GPU-accelerated STT
  - Auto-installs: ctranslate2, tokenizers, onnxruntime (or onnxruntime-gpu)
