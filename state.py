"""
In-memory state: conversation history, user modes, YouTube transcript cache.
"""

import time

from config import MAX_HISTORY, YT_CACHE_TTL

# Per-user conversation history
conversations: dict[int, list[dict]] = {}

# Per-user mode: "chat" (transcribe + LLM) or "transcribe" (transcribe only)
user_modes: dict[int, str] = {}

# Per-user Google Docs saving toggle (opt-in, default off)
user_gdocs: dict[int, bool] = {}

# YouTube transcript cache for inline button re-summarization
# Key: 8-char hex ID, Value: {"transcript": str, "title": str, "ts": float}
yt_transcripts: dict[str, dict] = {}


def get_history(user_id: int) -> list[dict]:
    if user_id not in conversations:
        conversations[user_id] = []
    return conversations[user_id]


def add_to_history(user_id: int, role: str, content: str):
    history = get_history(user_id)
    history.append({"role": role, "content": content})
    # Trim: keep last MAX_HISTORY message pairs
    if len(history) > MAX_HISTORY * 2:
        conversations[user_id] = history[-(MAX_HISTORY * 2):]


def clear_history(user_id: int):
    conversations[user_id] = []


def get_mode(user_id: int) -> str:
    return user_modes.get(user_id, "chat")


def cleanup_yt_cache():
    """Remove expired entries from yt_transcripts."""
    now = time.time()
    expired = [k for k, v in yt_transcripts.items() if now - v["ts"] > YT_CACHE_TTL]
    for k in expired:
        del yt_transcripts[k]
