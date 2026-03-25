"""
Settings CRUD API endpoints.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from infrastructure.database.database import Database
from interfaces.webapp.dependencies import get_current_user_id, get_database
from interfaces.webapp.schemas import (
    PRIVILEGED_KEYS,
    SECRET_KEYS,
    SECTION_KEYS,
    OAuthStatus,
    SectionId,
    SettingKey,
    SettingsResponse,
    SettingUpdate,
)
from shared.config import ALLOWED_USER_IDS

router = APIRouter(tags=["settings"])
logger = logging.getLogger(__name__)

KNOWN_KEYS = {k.value for k in SettingKey}


def _mask(key: str, value: str | None) -> str | None:
    """Mask secret values — show first 4 chars + *** if long enough, else ***."""
    if value is None:
        return None
    if key in SECRET_KEYS:
        return value[:4] + "***" if len(value) > 4 else "***"
    return value


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(
    user_id: int = Depends(get_current_user_id),
    db: Database = Depends(get_database),
) -> SettingsResponse:
    all_settings = await db.get_all_settings(user_id)

    # Build response with only known keys, masking secrets
    settings: dict[str, str | None] = {}
    for key in KNOWN_KEYS:
        raw = all_settings.get(key)
        settings[key] = _mask(key, raw)

    # Yandex OAuth status
    yandex_token = await db.get_oauth_token(user_id, "yandex")
    if yandex_token:
        meta = yandex_token.get("token_meta", {}) or {}
        yandex_status = OAuthStatus(connected=True, login=meta.get("login"))
    else:
        yandex_status = OAuthStatus(connected=False)

    return SettingsResponse(settings=settings, oauth={"yandex": yandex_status})


@router.put("/settings/{key}")
async def update_setting(
    key: SettingKey,
    body: SettingUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Database = Depends(get_database),
) -> dict:
    # Privileged keys require admin access
    if key.value in PRIVILEGED_KEYS and ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
        raise HTTPException(status_code=403, detail=f"Setting '{key.value}' requires elevated access")

    encrypt_value = key.value in SECRET_KEYS
    await db.set_setting(user_id, key.value, body.value, encrypt_value=encrypt_value)
    logger.info("Setting updated: user_id=%d key=%s", user_id, key.value)
    return {"key": key.value, "saved": True}


@router.delete("/settings/{key}")
async def delete_setting(
    key: SettingKey,
    user_id: int = Depends(get_current_user_id),
    db: Database = Depends(get_database),
) -> dict:
    await db.delete_setting(user_id, key.value)
    logger.info("Setting deleted: user_id=%d key=%s", user_id, key.value)
    return {"key": key.value, "deleted": True}


@router.post("/settings/reset/{section}")
async def reset_section(
    section: SectionId,
    user_id: int = Depends(get_current_user_id),
    db: Database = Depends(get_database),
) -> dict:
    keys = SECTION_KEYS[section.value]
    deleted = await db.delete_settings_section(user_id, keys)
    logger.info("Section reset: user_id=%d section=%s deleted=%d", user_id, section.value, deleted)
    return {"section": section.value, "cleared": True}
