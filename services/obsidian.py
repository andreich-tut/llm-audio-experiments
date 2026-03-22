"""
Obsidian vault integration: save Markdown notes to a local vault folder
or directly to Yandex.Disk via WebDAV.

Priority:
  1. Yandex.Disk WebDAV — if YANDEX_DISK_LOGIN is set
  2. Local filesystem   — if OBSIDIAN_VAULT_PATH is set
"""

import logging
from datetime import datetime
from pathlib import Path

import httpx

from config import (
    OBSIDIAN_INBOX_FOLDER,
    OBSIDIAN_VAULT_PATH,
    YANDEX_DISK_LOGIN,
    YANDEX_DISK_PASSWORD,
    YANDEX_DISK_PATH,
)

logger = logging.getLogger(__name__)

_WEBDAV_BASE = "https://webdav.yandex.ru"


def is_obsidian_enabled() -> bool:
    if YANDEX_DISK_LOGIN:
        return True
    if not OBSIDIAN_VAULT_PATH:
        return False
    vault = Path(OBSIDIAN_VAULT_PATH)
    if not vault.is_dir():
        logger.warning("OBSIDIAN_VAULT_PATH is set but directory does not exist: %s", vault)
        return False
    return True


async def save_note(filename: str, content: str) -> str:
    """Write a Markdown note to the configured destination.

    Returns a human-readable location string.
    Raises on failure.
    """
    if YANDEX_DISK_LOGIN:
        return await _save_webdav(filename, content)
    return _save_local(filename, content)


# ── local ────────────────────────────────────────────────────────────────────

def _save_local(filename: str, content: str) -> str:
    vault = Path(OBSIDIAN_VAULT_PATH)
    folder = vault / OBSIDIAN_INBOX_FOLDER if OBSIDIAN_INBOX_FOLDER else vault
    folder.mkdir(parents=True, exist_ok=True)

    dest = folder / filename
    if dest.exists():
        stem, suffix = dest.stem, dest.suffix
        ts = datetime.now().strftime("%H%M%S")
        dest = folder / f"{stem}-{ts}{suffix}"

    dest.write_text(content, encoding="utf-8")
    logger.info("Obsidian note saved locally: %s", dest)
    return str(dest)


# ── Yandex.Disk WebDAV ───────────────────────────────────────────────────────

async def _save_webdav(filename: str, content: str) -> str:
    auth = (YANDEX_DISK_LOGIN, YANDEX_DISK_PASSWORD)
    folder_parts = [YANDEX_DISK_PATH.strip("/")]
    if OBSIDIAN_INBOX_FOLDER:
        folder_parts.append(OBSIDIAN_INBOX_FOLDER.strip("/"))
    folder_path = "/".join(folder_parts)

    async with httpx.AsyncClient(auth=auth, timeout=30) as client:
        # Ensure each folder level exists (MKCOL is idempotent — 405 = already exists)
        parts = folder_path.split("/")
        for i in range(1, len(parts) + 1):
            partial = "/".join(parts[:i])
            resp = await client.request("MKCOL", f"{_WEBDAV_BASE}/{partial}")
            if resp.status_code not in (201, 405):
                resp.raise_for_status()

        # Check if file exists and add timestamp suffix if so
        file_path = f"{folder_path}/{filename}"
        head = await client.head(f"{_WEBDAV_BASE}/{file_path}")
        if head.status_code == 200:
            stem = filename.rsplit(".", 1)[0]
            suffix = f".{filename.rsplit('.', 1)[1]}" if "." in filename else ""
            ts = datetime.now().strftime("%H%M%S")
            file_path = f"{folder_path}/{stem}-{ts}{suffix}"

        resp = await client.put(
            f"{_WEBDAV_BASE}/{file_path}",
            content=content.encode("utf-8"),
            headers={"Content-Type": "text/markdown; charset=utf-8"},
        )
        resp.raise_for_status()

    location = f"Yandex.Disk:/{file_path}"
    logger.info("Obsidian note saved to %s", location)
    return location
