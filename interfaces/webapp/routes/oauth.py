"""
Yandex OAuth endpoints for the Mini App.

The flow uses the same Telegram deep-link redirect as the bot:
  1. Frontend calls GET /api/v1/oauth/yandex/url → receives OAuth URL
  2. Frontend opens URL via Telegram.WebApp.openLink() (external browser)
  3. User authorises → Yandex redirects to https://t.me/<bot>?start=oauth_<code>_<state>
  4. Telegram opens bot; existing /start oauth_... handler exchanges code and stores token
  5. User returns to Mini App → visibilitychange event → re-fetch /settings
"""

import logging
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException

from infrastructure.database.database import Database
from infrastructure.external_api.yandex_client import exchange_code, get_oauth_url, get_user_login
from interfaces.webapp.dependencies import get_current_user_id, get_database
from interfaces.webapp.schemas import OAuthExchangeRequest
from shared.config import BOT_TOKEN, YANDEX_OAUTH_CLIENT_ID

router = APIRouter(tags=["oauth"])
logger = logging.getLogger(__name__)

# Bot username is fetched once on first request and cached
_bot_username: str | None = None


async def _get_bot_username() -> str:
    global _bot_username
    if _bot_username:
        return _bot_username
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe")
        resp.raise_for_status()
        data = resp.json()
        _bot_username = data["result"]["username"]
        logger.info("Bot username resolved: @%s", _bot_username)
    return _bot_username


@router.get("/oauth/yandex/url")
async def get_yandex_oauth_url(
    user_id: int = Depends(get_current_user_id),
) -> dict:
    if not YANDEX_OAUTH_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Yandex OAuth is not configured")

    state = uuid.uuid4().hex[:16]
    try:
        bot_username = await _get_bot_username()
    except Exception as e:
        logger.error("Failed to resolve bot username: %s", e)
        raise HTTPException(status_code=503, detail="Could not resolve bot username") from e

    url = get_oauth_url(state, bot_username)
    logger.info("OAuth URL generated for user_id=%d", user_id)
    return {"url": url, "state": state}


@router.post("/oauth/yandex/exchange")
async def exchange_yandex_code(
    body: OAuthExchangeRequest,
    user_id: int = Depends(get_current_user_id),
    db: Database = Depends(get_database),
) -> dict:
    """Exchange authorization code for tokens and store them."""
    try:
        bot_username = await _get_bot_username()
    except Exception as e:
        logger.error("Failed to resolve bot username: %s", e)
        raise HTTPException(status_code=503, detail="Could not resolve bot username") from e

    token = await exchange_code(body.code, bot_username)
    if not token:
        raise HTTPException(status_code=400, detail="Failed to exchange OAuth code")

    login = await get_user_login(token.access_token)
    meta = {"login": login}

    await db.set_oauth_token(
        user_id,
        "yandex",
        access_token=token.access_token,
        refresh_token=token.refresh_token,
        expires_at=token.expires_at,
        meta=meta,
    )
    logger.info("Yandex OAuth connected: user_id=%d login=%s", user_id, login)
    return {"connected": True, "login": login}


@router.delete("/oauth/yandex")
async def disconnect_yandex(
    user_id: int = Depends(get_current_user_id),
    db: Database = Depends(get_database),
) -> dict:
    await db.delete_oauth_token(user_id, "yandex")
    logger.info("Yandex OAuth disconnected: user_id=%d", user_id)
    return {"disconnected": True}
