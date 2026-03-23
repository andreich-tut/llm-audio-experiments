# Plan: Cache Groq rate-limit headers from real transcription responses

## Context

The `/limits` command shows Groq STT section header ("Groq (STT) (активен)") but no actual limit details. This is because `check_groq()` in `services/limits.py` calls `/v1/models` which doesn't return rate-limit headers. The real rate-limit headers (`x-ratelimit-*`) are only returned by actual API calls like `/v1/audio/transcriptions`.

**Goal**: Capture rate-limit headers from real Groq transcription responses and display them in `/limits` — no extra API calls needed.

## Changes

### 1. Add Groq rate-limit cache to `state.py`

Add a module-level dict to store the latest Groq rate-limit headers:

```python
groq_limits: dict[str, str | None] = {}
```

Add a setter function `update_groq_limits(headers)` that extracts and stores the 6 `x-ratelimit-*` headers.

### 2. Capture headers in `services/stt.py` → `_transcribe_groq()`

After the successful API response (line ~67), extract rate-limit headers from `response.headers` and call `state.update_groq_limits(response.headers)`.

### 3. Update `services/limits.py` → `check_groq()`

- Instead of (or in addition to) calling `/v1/models`, return cached headers from `state.groq_limits` if available.
- Fall back to the current `/v1/models` probe if no cached data exists (first run before any transcription).

### 4. Fix the `None` vs `"?"` bug in `format_limits_message()`

Lines 79-84: `groq_data.get("limit_req", "?")` returns `None` (not `"?"`) when the key exists with value `None`. Fix by using `groq_data.get("limit_req") or "?"`.

## Files to modify

1. `state.py` — add `groq_limits` dict + `update_groq_limits()` function
2. `services/stt.py` — capture headers in `_transcribe_groq()`
3. `services/limits.py` — use cached headers + fix None/"?" bug

## Verification

1. Start bot, send a voice message (triggers Groq transcription)
2. Run `/limits` — Groq section should now show request/token limits with remaining counts
3. Run `/limits` before any voice message — should still show header (with fallback or "no data yet" message)
