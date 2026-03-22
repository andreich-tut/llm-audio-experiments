# Plan: Per-user settings via Telegram bot

## Goal

Let each Telegram user override Yandex Disk, Obsidian vault, and LLM API
credentials directly in the bot via `/settings` command, without touching `.env`.

## Files to change

### 1. `state.py` — add `user_settings` store

```python
user_settings: dict[int, dict] = {}

def get_user_setting(user_id: int, key: str, default=None)
def set_user_setting(user_id: int, key: str, value: str) -> None
def clear_user_setting(user_id: int, key: str) -> None
```

Fallback chain: `user_settings[user_id][key]` → `config.CONSTANT`

---

### 2. `services/obsidian.py` — accept `user_id`

Change signatures:
- `is_obsidian_enabled(user_id: int) -> bool`
- `save_note(filename: str, content: str, user_id: int) -> str`

Resolve config per-user (falling back to global constants if not set):
- `yadisk_login`, `yadisk_password`, `yadisk_path`
- `obsidian_vault_path`, `obsidian_inbox_folder`

---

### 3. `services/llm.py` — dynamic client per user

Replace module-level `_client` with factory:

```python
def _get_client(api_key: str, base_url: str) -> openai.AsyncOpenAI
```

Update `ask_ollama`, `summarize_ollama`, `format_note_ollama` to accept
`user_id: int` and resolve effective `api_key` / `base_url` / `model` from
user settings, falling back to globals.

---

### 4. `bot.py` — `/settings` command + FSM

- Add `MemoryStorage` to `Dispatcher`
- Add `SettingsState` FSM group with state `waiting_for_value`
  (stores which key is being set in FSM data)
- Add `/settings` command handler and inline keyboard callbacks
- Update all calls to `is_obsidian_enabled()`, `save_note()`, `ask_ollama()`,
  `summarize_ollama()`, `format_note_ollama()` to pass `user_id`

---

## UX flow

```
/settings
  ┌──────────────────────────────────────────┐
  │  [LLM API]   [Yandex.Disk]   [Obsidian]  │
  └──────────────────────────────────────────┘

  LLM API submenu:
    API Key:  ••• (set) / not set
    Base URL: https://openrouter.ai/api/v1
    Model:    qwen/qwen3-235b-a22b:free
    [Set API Key]  [Set Base URL]  [Set Model]  [Reset]  [Back]

  Yandex.Disk submenu:
    Login:    user@ya.ru / not set
    Password: ••• (set) / not set
    Path:     ObsidianVault
    [Set Login]  [Set Password]  [Set Path]  [Clear all]  [Back]

  Obsidian (local) submenu:
    Vault Path:    /path/to/vault / not set
    Inbox Folder:  Inbox
    [Set Vault Path]  [Set Inbox Folder]  [Clear]  [Back]
```

Clicking "Set X":
1. Bot replies: "Send the value:"
2. FSM enters `waiting_for_value` (stores target key in data)
3. User sends value → saved to `user_settings` → bot returns to submenu

Clicking "Reset" / "Clear": removes user's override, falls back to global default.
