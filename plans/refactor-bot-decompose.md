# Refactor: Decompose bot.py into modules with aiogram Routers

## Context

`bot.py` is 776 lines containing all handler logic: helpers, keyboards, processing pipelines, commands, message handlers, callbacks, and entrypoint. The project already has a clean `services/` layer but no handler-level modularity and no use of aiogram Routers.

**Goal**: Split `bot.py` into focused modules using aiogram 3 Routers, so each file has a single responsibility and stays under ~200 lines. The `bot` instance stays in `bot.py`; handlers access it via aiogram's built-in dependency injection (`bot: Bot` kwarg).

## Target structure

```
bot.py                          ~60 lines   entrypoint: bot/dp creation, router assembly, main()
core/
  __init__.py                   empty
  helpers.py                    ~60 lines   _audio_suffix, _escape_md, _run_as_cancellable, _get_audio_from_msg
  keyboards.py                  ~60 lines   keyboard builders + UI label constants
  pipelines.py                  ~220 lines  process_youtube, process_audio, process_text
handlers/
  __init__.py                   empty
  commands.py                   ~180 lines  /start /mode /clear /model /savedoc /stop /ping /limits + mode/cancel callbacks
  messages.py                   ~140 lines  voice, audio, video_note, document, video, text, catch-all
  youtube_callbacks.py          ~60 lines   yt:* callback queries
```

## Routers (3 total)

| Router | File | Handlers |
|--------|------|----------|
| `commands` | `handlers/commands.py` | All `/` commands + `mode:*` and `cancel` callback queries |
| `youtube_callbacks` | `handlers/youtube_callbacks.py` | `yt:*` callback queries |
| `messages` | `handlers/messages.py` | `F.voice`, `F.audio`, `F.video_note`, `F.document`, `F.video`, `F.text`, catch-all |

**Inclusion order in bot.py matters**: commands -> youtube_callbacks -> messages (catch-all must be last).

## Key design decisions

- **`bot` instance access**: Only `process_audio()` needs `bot: Bot` as a parameter (for `bot.get_file()` and `bot.download_file()`). `process_youtube()` and `process_text()` do NOT need `bot` — they use `message.answer()` directly on the message object.
- **Pipelines separate from handlers**: `process_audio` (~120 lines) and `process_youtube` (~100 lines) are too large to inline in handler files. They live in `core/pipelines.py` and are called by handlers.
- **Drop `_` prefix on extracted functions**: Functions that become module-level public API lose the underscore (e.g., `_process_audio` -> `process_audio`, `_escape_md` -> `escape_md`).
- **Per-user settings fit**: Future `/settings` command becomes `handlers/settings.py` with its own Router — no existing files need restructuring.

## Imports per file

| File | Imports |
|------|---------|
| `core/helpers.py` | `asyncio`, `Path`, `types` (aiogram), `active_tasks` (state) |
| `core/keyboards.py` | `InlineKeyboardMarkup`, `InlineKeyboardButton` (aiogram.types) |
| `core/pipelines.py` | `asyncio`, `os`, `re`, `shutil`, `tempfile`, `time`, `uuid`, `datetime`, `Bot`, `BufferedInputFile`, `ParseMode` (aiogram), `core.helpers`, `core.keyboards`, `services.*`, `state`, `config`, `logger` (config) |
| `handlers/commands.py` | `Router`, `Command`, `CommandStart`, `CallbackQuery`, `types`, `gdocs_service`, `state`, `config`, `logger` (config), `core.keyboards` |
| `handlers/messages.py` | `Router`, `F`, `types`, `Bot`, `Path`, `core.helpers`, `core.pipelines`, `state`, `config`, `logger` (config), `wants_diarize` (services.youtube), `YT_URL_RE` (config) |
| `handlers/youtube_callbacks.py` | `Router`, `CallbackQuery`, `time`, `core.keyboards`, `state`, `services.llm`, `config`, `logger` (config) |

## Extraction steps (ordered by dependency — extract leaves first)

### Step 1: `core/helpers.py` + `core/keyboards.py`

Extract pure utilities with zero coupling to handlers.

**`core/helpers.py`** — move from bot.py:
- `_audio_suffix()` (lines 60-77)
- `_escape_md()` (lines 80-84)
- `_run_as_cancellable()` (lines 87-96) — imports `active_tasks` from state
- `_get_audio_from_msg()` (lines 158-174) — uses `_audio_suffix`

**`core/keyboards.py`** — move from bot.py:
- `_YT_LEVEL_MAP`, `_YT_LEVEL_LABELS` (lines 103-104)
- `_yt_summary_keyboard()` (lines 107-113)
- `_MODE_LABELS`, `_MODE_DESCRIPTIONS` (lines 119-128)
- `_mode_keyboard()` (lines 131-137)
- `_stop_keyboard()` (lines 140-143)

Update bot.py imports to use `from core.helpers import ...` and `from core.keyboards import ...`.

### Step 2: `core/pipelines.py`

Extract the three processing pipelines.

**Move from bot.py:**
- `_process_youtube()` (lines 177-275) -> `process_youtube(message, url, diarize)` — NO bot param needed
- `_process_audio()` (lines 278-375) -> `process_audio(message, bot, file_id, suffix)` — needs `bot: Bot` param
- `_process_text()` (lines 612-633) -> `process_text(message)` — NO bot param needed

These import from: `core.helpers`, `core.keyboards`, `services.*`, `state`, `config`.

### Step 3: `handlers/commands.py`

Create `router = Router(name="commands")`. Move all command handlers:
- `cmd_start`, `cmd_mode`, `cmd_clear`, `cmd_model`, `cmd_savedoc`, `cmd_stop`, `cmd_ping`, `cmd_limits`
- `handle_mode_callback`, `handle_cancel_callback`

Change `@dp.message(Command(...))` to `@router.message(Command(...))`, same for callback queries.

### Step 4: `handlers/youtube_callbacks.py`

Create `router = Router(name="youtube_callbacks")`. Move:
- `handle_yt_summary_callback`

### Step 5: `handlers/messages.py`

Create `router = Router(name="messages")`. Move all message-type handlers:
- `handle_voice`, `handle_audio`, `handle_video_note`, `handle_document`, `handle_video`, `handle_text`, `handle_unhandled`

**Note**: `handle_text` contains routing logic — it checks for:
1. Reply-to-audio → calls `process_audio()`
2. YouTube URL in text → calls `process_youtube()`
3. Plain text → calls `process_text()`

Each handler that calls `process_audio` passes `bot` from its injected kwarg:
```python
@router.message(F.voice)
async def handle_voice(message: types.Message, bot: Bot):
    if not is_allowed(message.from_user.id):
        return
    await run_as_cancellable(message.from_user.id, process_audio(message, bot, message.voice.file_id, ".ogg"))
```

### Step 6: Slim down `bot.py`

What remains (~60 lines):
- `bot = Bot(...)` and `dp = Dispatcher()`
- `dp.include_routers(commands_router, yt_callbacks_router, messages_router)`
- `async def main()` — register bot commands with Telegram, start polling
- `if __name__ == "__main__": asyncio.run(main())`

## Files to modify/create

| Action | File |
|--------|------|
| Create | `core/__init__.py` |
| Create | `core/helpers.py` |
| Create | `core/keyboards.py` |
| Create | `core/pipelines.py` |
| Create | `handlers/__init__.py` |
| Create | `handlers/commands.py` |
| Create | `handlers/messages.py` |
| Create | `handlers/youtube_callbacks.py` |
| Rewrite | `bot.py` (776 -> ~60 lines) |

No changes to: `config.py`, `state.py`, `services/*`.

## Verification

After each step, run the bot (`python bot.py`) and manually test:
1. **Step 1-2**: Send voice message, text, YouTube URL — all should work (imports changed, logic unchanged)
2. **Step 3**: Test `/start`, `/mode` (press inline buttons), `/clear`, `/model`, `/ping`, `/limits`, `/stop`, `/savedoc`
3. **Step 4**: Send YouTube URL, get transcript, press summary detail buttons (Brief/Detailed/Keypoints)
4. **Step 5-6**: Full regression — voice, audio file, video, text chat, YouTube URL, reply-to-audio, "stop" text command, catch-all for unsupported content

## Progress

- [ ] Step 1: Create `core/helpers.py` and `core/keyboards.py`
- [ ] Step 2: Create `core/pipelines.py`
- [ ] Step 3: Create `handlers/commands.py`
- [ ] Step 4: Create `handlers/youtube_callbacks.py`
- [ ] Step 5: Create `handlers/messages.py`
- [ ] Step 6: Rewrite `bot.py` to use routers
