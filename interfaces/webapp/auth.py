"""
Telegram Mini App initData HMAC-SHA256 validation.
"""

import hashlib
import hmac
import json
import logging
from urllib.parse import parse_qsl, unquote

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def validate_init_data(init_data: str, bot_token: str) -> dict:
    """
    Validate Telegram WebApp initData and return parsed user dict.
    Raises HTTPException(401) if invalid.
    """
    if not init_data:
        raise HTTPException(status_code=401, detail="Missing X-Telegram-Init-Data header")

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    hash_to_check = parsed.pop("hash", None)
    if not hash_to_check:
        raise HTTPException(status_code=401, detail="Missing hash in initData")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, hash_to_check):
        raise HTTPException(status_code=401, detail="Invalid initData signature")

    user_raw = parsed.get("user", "{}")
    try:
        return json.loads(unquote(user_raw))
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid user field in initData") from exc
