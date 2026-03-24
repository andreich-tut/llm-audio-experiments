# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Telegram Voice/Audio Bot**: A Telegram bot that processes voice messages, audio files, and YouTube links via Whisper STT and generates responses using any OpenAI-compatible LLM API (default: OpenRouter).

- **Stack**: Python 3.11+, aiogram 3, faster-whisper (local) or Groq (cloud) for STT, OpenAI SDK for LLM
- **Architecture**: Async event-driven (asyncio), in-memory conversation state, Docker deployment with Cloudflare WARP
- **Language**: Bilingual UI (Russian/English), per-user language setting

## Architecture & Key Concepts

### Data Flow
```
User sends voice/audio → bot downloads file → Whisper transcribes (local GPU or Groq cloud) →
  Mode: chat       → LLM processes with conversation context → response sent back
  Mode: transcribe → raw transcript sent back
  Mode: note       → LLM formats as Obsidian note → .md file sent back
```

### Project Structure
```
bot.py              — Entrypoint: creates Bot/Dispatcher, registers routers, starts polling
config.py           — Env loading, constants, logging (rotating file + console), access control
state.py            — In-memory state: conversations, user modes/languages, active tasks, caches
version.py          — Reads __version__ from pyproject.toml
core/
  helpers.py        — Utilities: audio_suffix, escape_md, run_as_cancellable, get_audio_from_msg
  i18n.py           — Internationalization: t(), get_user_locale(), detect_language_from_telegram()
  keyboards.py      — Inline keyboard builders (mode, language, YouTube summary, stop)
  pipelines.py      — Main processing: process_audio(), process_youtube(), process_text()
handlers/
  commands.py       — All /command handlers + inline callback query handlers (mode, lang, cancel)
  messages.py       — Message type handlers: voice, audio, video_note, document, video, text
  youtube_callbacks.py — YouTube summary detail-level inline button handlers
services/
  stt.py            — Whisper transcription: local (faster-whisper) or cloud (Groq API)
  llm.py            — LLM chat (OpenAI SDK): ask_ollama(), summarize_ollama(), format_note_ollama()
  limits.py         — Rate limit checking: OpenRouter key info + cached Groq headers
  obsidian.py       — Obsidian note saving: local vault or Yandex.Disk WebDAV
  youtube.py        — YouTube audio download (yt-dlp), optional whisperX diarization
  gdocs.py          — Google Docs integration (optional)
prompts/
  system.md         — Main chat system prompt
  summary_brief.md  — Brief YouTube summary prompt
  summary_detailed.md — Detailed YouTube summary prompt
  summary_keypoints.md — Keypoints extraction prompt
  note.md           — Obsidian note formatting prompt
locales/
  ru.json           — Russian UI strings
  en.json           — English UI strings
tools/
  audio_splitter.py — FFmpeg-based audio chunking (by size or time)
  transcribe_diarize.py — whisperX + pyannote diarization CLI
  transcribe_cli.py — CLI transcription wrapper (uses bot's Whisper)
  diarize_all.py    — Batch diarize test/chunks/ → test/source.txt
  send_chunks.py    — Split audio + send chunks to bot via Telegram API
  split.sh          — Shell helper for audio splitting
plans/              — Design docs (not part of runtime)
```

### Key Functions
- `core.pipelines.process_audio(message)` → orchestrates STT + mode-based processing
- `core.pipelines.process_youtube(message, url)` → downloads YouTube audio, offers summary options
- `core.pipelines.process_text(message)` → sends text to LLM with history
- `services.stt.transcribe(file_path)` → splits audio into chunks, runs Whisper (local or Groq)
- `services.llm.ask_ollama(user_id, message, locale)` → sends to LLM with conversation history
- `services.llm.summarize_ollama(text, detail_level, title, locale)` → one-shot summarization
- `services.llm.format_note_ollama(text, locale)` → formats transcript as Obsidian note (title, tags, body)
- `services.llm.ping_llm()` → tests LLM API connectivity
- `services.limits.check_openrouter()` / `check_groq()` → rate limit info
- `services.obsidian.save_note(filename, content)` → writes to local vault or WebDAV
- `state.get_history(user_id)` / `state.add_to_history(...)` → per-user message history
- `config.is_allowed(user_id)` → access control check
- `core.i18n.t(key, locale)` → localized string lookup

### Configuration
All config via `.env` file (template in `.env.example`):
```
BOT_TOKEN=<Telegram bot token>
ALLOWED_USERS=                    # Comma-separated user IDs (empty = all)

# LLM — any OpenAI-compatible API
LLM_API_KEY=
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=qwen/qwen3-235b-a22b:free

# STT
WHISPER_BACKEND=local             # "local" (faster-whisper) or "groq" (cloud)
WHISPER_MODEL=medium              # For local: tiny/small/medium/large-v3
WHISPER_DEVICE=cuda               # For local: cuda or cpu
GROQ_API_KEY=                     # Required when WHISPER_BACKEND=groq

# System prompt
SYSTEM_PROMPT=prompts/system.md

# Google Docs (optional)
GDOCS_CREDENTIALS_FILE=
GDOCS_DOCUMENT_ID=

# Obsidian (optional)
OBSIDIAN_VAULT_PATH=
OBSIDIAN_INBOX_FOLDER=Inbox
YANDEX_DISK_LOGIN=                # WebDAV — overrides local vault if set
YANDEX_DISK_PASSWORD=
YANDEX_DISK_PATH=ObsidianVault

# YouTube
YT_MAX_DURATION=7200
YT_COOKIES_FILE=

# Internationalization
DEFAULT_LANGUAGE=ru
```

## Development & Running

### Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt          # Cloud-only (Groq STT + OpenRouter LLM)
pip install -r requirements-local.txt    # Adds faster-whisper for local STT
cp .env.example .env
# Edit .env: add BOT_TOKEN, LLM_API_KEY, etc.
```

### Prerequisites
- **LLM API**: Any OpenAI-compatible endpoint (OpenRouter, local vLLM, etc.) with API key
- **STT**: Either Groq API key (`WHISPER_BACKEND=groq`) or local faster-whisper with CUDA GPU (`WHISPER_BACKEND=local`)
- **Telegram Bot Token**: From @BotFather

### Run Locally
```bash
python bot.py
```

### Run with Docker
```bash
./start.sh    # Builds Docker image + runs with Cloudflare WARP
./update.sh   # Rebuilds + prunes old images
```

### CI/CD
- `.github/workflows/pylint.yml` — Runs pylint on every push
- `.github/workflows/deploy.yml` — On push to main (or manual): lint → SSH deploy to VPS

### Linting
- **Ruff** via pre-commit hooks (`.pre-commit-config.yaml`): lint + format, line-length 120
- **Pylint** via `.pylintrc`
- Auto version bump: `.githooks/bump-version.sh` increments patch version in `pyproject.toml` on each commit

### Debugging
- Logs: rotating files in `logs/` directory + console output (level=INFO)
- `/ping` command tests LLM API connectivity
- `/limits` shows OpenRouter + Groq rate limit usage
- Conversation history is in-memory, cleared on restart

## Bot Commands
| Command | Handler | Notes |
|---------|---------|-------|
| `/start` | `cmd_start()` | Shows help, version, and available commands |
| `/mode` | `cmd_mode()` | Inline keyboard to switch: chat / transcribe / note |
| `/stop` | `cmd_stop()` | Cancel active processing task (also: "stop" / "стоп" text) |
| `/clear` | `cmd_clear()` | Clears user's conversation history |
| `/model` | `cmd_model()` | Shows current LLM_MODEL and WHISPER_MODEL |
| `/ping` | `cmd_ping()` | Tests LLM API connection |
| `/limits` | `cmd_limits()` | Shows OpenRouter + Groq free-tier usage |
| `/lang` | `cmd_lang()` | Inline keyboard to switch UI language (ru/en) |
| `/savedoc` | `cmd_savedoc()` | Toggle Google Docs saving (opt-in) |

Voice, audio, and text message handlers check `is_allowed()` before processing.

## Common Tasks

### Change LLM Model
Edit `.env`: `LLM_MODEL=anthropic/claude-3.5-sonnet` (or any model on your API provider)

### Change STT Backend
Edit `.env`: `WHISPER_BACKEND=groq` (cloud, needs `GROQ_API_KEY`) or `WHISPER_BACKEND=local` (needs `requirements-local.txt` + GPU)

### Change Whisper Model (local STT only)
Edit `.env`: `WHISPER_MODEL=large-v3` (better quality, slower) or `tiny` (faster, lower quality)
- GPU VRAM: tiny ~1GB, small ~2GB, medium ~5GB, large-v3 ~10GB

### Customize System Prompt
Edit `SYSTEM_PROMPT=` in `.env` to point to a different `.md` file

### Restrict Access
Edit `.env`: `ALLOWED_USERS=123456789,987654321` (comma-separated Telegram user IDs)

### Change UI Language
Default set via `DEFAULT_LANGUAGE=ru` in `.env`. Users can switch per-session with `/lang`.

## Code Notes

- **Conversation history**: Trimmed to last MAX_HISTORY (20) pairs to avoid context overflow
- **Message splitting**: Responses >4000 chars split into multiple Telegram messages
- **Async**: Uses asyncio + aiogram for non-blocking I/O
- **Cancellation**: Active tasks stored in `state.active_tasks`, cancellable via `/stop`
- **Rate limiting**: LLM calls retry with exponential backoff (5s/15s/30s) on RateLimitError
- **Error handling**: Exceptions logged and user notified in chat
- **No persistence**: All state lost on restart (by design)
- **i18n**: All UI strings in `locales/{ru,en}.json`, accessed via `core.i18n.t(key, locale)`

## Dependencies
- `aiogram>=3.10` — Telegram bot framework (async)
- `python-dotenv>=1.0` — Load .env config
- `httpx>=0.27` — Async HTTP client (Groq STT, limits checking)
- `openai>=1.0` — OpenAI-compatible LLM client
- `yt-dlp>=2024.0` — YouTube audio download
- `google-api-python-client>=2.100` / `google-auth>=2.23` — Google Docs integration
- `pre-commit>=3.0` — Git hooks
- `faster-whisper>=1.0` — Local GPU-accelerated STT (optional, in `requirements-local.txt`)
