# Async Fix Plan: Eliminate sync `get_user_setting` calls in async context

## Problem
Sync wrappers (`get_user_setting`, `get_user_setting_json`, `set_user_setting`, etc.) are called from async Telegram handlers. When the event loop is running, these can't do `loop.run_until_complete()`, so they either return `default` (losing data) or fire-and-forget via `create_task` (for setters). This produces `RuntimeWarning` at runtime.

## Strategy
Convert all affected sync functions to async, using `*_async` variants from `application/user_settings.py`.

---

## Files & Changes

### 1. `shared/version.py` — ✅ DONE
- **Fix**: Path to `pyproject.toml` was `Path(__file__).parent` (= `shared/`) instead of project root.
- **Change**: `.parent` → `.resolve().parent.parent`

### 2. `.pre-commit-config.yaml` — ✅ DONE
- **Added**: `bot-import-check` hook that runs `python -c "from bot import main"` to catch import-time crashes.

### 3. `application/state.py` — ✅ DONE
- `can_use_shared_credentials()` → `async`, uses `get_user_setting_async`
- `get_mode()` → `async`, uses `get_user_setting_async`
- `set_mode()` → `async`, uses `set_user_setting_async`
- `get_language()` → `async`, uses `get_user_setting_async`
- `set_language()` → `async`, uses `set_user_setting_async`

### 4. `infrastructure/external_api/llm_client.py` — ✅ DONE
- Import changed: `get_user_setting` → `get_user_setting_async`
- `_get_client()` → `async`, uses `get_user_setting_async`
- `_get_model()` → `async`, uses `get_user_setting_async`
- All callers in this file (`ask_ollama`, `summarize_ollama`, `format_note_ollama`) updated with `await`

### 5. `infrastructure/external_api/llm_operations.py` — ✅ DONE
- All `_get_client()`/`_get_model()` calls updated with `await`

### 6. `infrastructure/storage/obsidian.py` — ✅ DONE
- Import changed: `get_user_setting` → `get_user_setting_async`, `get_user_setting_json` → `get_user_setting_json_async`
- `_get_cfg()` → `async`
- `is_obsidian_enabled()` → `async`
- `save_note()` caller of `_get_cfg` updated with `await`
- `_save_webdav_oauth()`: `set_user_setting_json` → `await set_user_setting_json_async`

### 7. `interfaces/telegram/handlers/settings_ui.py` — ✅ DONE
- Import changed: `get_user_setting` → `get_user_setting_async`, `get_user_setting_json` → `get_user_setting_json_async`
- `_val()` → `async`
- `_llm_text()` → `async`
- `_yadisk_text()` → `async`
- `_obsidian_text()` → `async`

### 8. `interfaces/telegram/handlers/settings.py` — ✅ DONE
- Import: Uses `set_user_setting`, `clear_user_settings_section` (already async in state.py)
- All `text_fn(...)` calls now use `await`
- `set_user_setting(...)` and `clear_user_settings_section(...)` now use `await`

### 9. `interfaces/telegram/handlers/settings_oauth.py` — ✅ DONE
- Calls `await _yadisk_text(user_id, locale)` (now async)

### 10. `interfaces/telegram/handlers/commands.py` — ✅ DONE
- Calls `await get_mode()` (now async)
- All `get_locale_from_*` calls now use `await`

### 11. `interfaces/telegram/handlers/diagnostics.py` — ✅ DONE
- Calls `await get_language()` (now async)
- All `get_locale_from_*` calls now use `await`

### 12. `shared/i18n.py` — ✅ DONE
- `get_user_locale()` → `async`, calls `await get_language()`
- All callers updated with `await`

### 13. `shared/utils.py` — ✅ DONE
- `get_locale_from_message()` → `async`, calls `await get_user_locale()`
- `get_locale_from_callback()` → `async`, calls `await get_user_locale()`

### 14. `application/pipelines/audio.py` — ✅ DONE
- Calls `await can_use_shared_credentials()`, `await get_mode()`, `await get_user_setting()`
- `_check_free_tier()`: All async calls updated with `await`
- `await is_obsidian_enabled()` updated

### 15. `application/pipelines/text.py` — ✅ DONE
- `await get_locale_from_message()` updated

### 16. `application/pipelines/youtube.py` — ✅ DONE
- `await get_locale_from_message()` updated

### 17. `interfaces/telegram/handlers/messages.py` — ✅ DONE
- `await get_locale_from_message()` updated in document and text handlers

### 18. `interfaces/telegram/handlers/youtube_callbacks.py` — ✅ DONE
- `await get_locale_from_callback()` updated

### 19. `interfaces/telegram/handlers/oauth_callback.py` — ✅ DONE
- `await get_locale_from_message()` updated

---

## Summary of Changes

### Core async functions in `application/state.py`:
- `can_use_shared_credentials()` - async
- `get_mode()` - async
- `set_mode()` - async
- `get_language()` - async
- `set_language()` - async
- `clear_user_settings_section()` - async
- `set_user_setting()` - async
- `delete_oauth_token()` - async

### Ripple effect - made async:
- `shared/i18n.py:get_user_locale()` - async
- `shared/utils.py:get_locale_from_message()` - async
- `shared/utils.py:get_locale_from_callback()` - async
- `infrastructure/storage/obsidian.py:is_obsidian_enabled()` - async
- `interfaces/telegram/handlers/settings_ui.py:_val()`, `_llm_text()`, `_yadisk_text()`, `_obsidian_text()` - async

### All handler files updated with `await`:
- `interfaces/telegram/handlers/*.py` - All locale and state function calls now use `await`
- `application/pipelines/*.py` - All locale and state function calls now use `await`

---

## Verification

✅ Import test passed: `python -c "from bot import main"` runs without errors

## Next Steps
- Run bot locally
- Test `/mode`, `/settings`, `/lang` commands
- Test voice message processing
- Test YouTube link processing
- Commit & push to deploy
