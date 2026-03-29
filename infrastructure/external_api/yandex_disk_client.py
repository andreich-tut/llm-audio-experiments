"""
Yandex.Disk REST API client.

Async functions for browsing Yandex.Disk folder structure.
Note: Paths sent to Yandex should be prefixed with 'disk:/' if they aren't already.
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Yandex.Disk API base URL
YANDEX_DISK_API_URL = "https://cloud-api.yandex.net/v1/disk"


def _normalize_path(path: str) -> str:
    """
    Normalize path to Yandex.Disk format.

    Yandex.Disk API expects paths to start with 'disk:/' for absolute paths.
    Root path should be 'disk:/' or '/'.

    Args:
        path: The path to normalize

    Returns:
        Normalized path with 'disk:/' prefix
    """
    if not path:
        return "disk:/"

    # Already normalized
    if path.startswith("disk:/"):
        return path

    # Convert Unix-style absolute path to disk:/ format
    if path.startswith("/"):
        return f"disk:{path}"

    # Relative path - treat as relative to root
    return f"disk:/{path}"


async def list_folder(
    path: str = "/",
    access_token: str = "",
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    List contents of a Yandex.Disk folder.

    Args:
        path: Folder path to list (will be normalized to disk:/ format)
        access_token: Yandex OAuth access token
        limit: Maximum number of items to return (default: 100)
        offset: Pagination offset (default: 0)

    Returns:
        List of folder/file items with metadata

    Raises:
        httpx.HTTPError: If API request fails
    """
    normalized_path = _normalize_path(path)

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(
                f"{YANDEX_DISK_API_URL}/resources",
                params={
                    "path": normalized_path,
                    "limit": limit,
                    "offset": offset,
                },
                headers={"Authorization": f"OAuth {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()

            # Return embedded items list
            items = data.get("_embedded", {}).get("items", [])

            # Transform to consistent format
            result = []
            for item in items:
                result.append(
                    {
                        "name": item.get("name", ""),
                        "path": item.get("path", ""),
                        "type": "dir" if item.get("type") == "dir" else "file",
                        "created": item.get("created"),
                        "modified": item.get("modified"),
                    }
                )

            return result

        except httpx.HTTPError as e:
            logger.error("Yandex.Disk list_folder failed: %s", e)
            raise


async def get_resource_info(
    path: str,
    access_token: str,
) -> dict[str, Any]:
    """
    Get information about a specific resource (file or folder).

    Args:
        path: Resource path
        access_token: Yandex OAuth access token

    Returns:
        Resource metadata dictionary

    Raises:
        httpx.HTTPError: If API request fails
    """
    normalized_path = _normalize_path(path)

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(
                f"{YANDEX_DISK_API_URL}/resources",
                params={"path": normalized_path},
                headers={"Authorization": f"OAuth {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()

            return {
                "name": data.get("name", ""),
                "path": data.get("path", ""),
                "type": "dir" if data.get("type") == "dir" else "file",
                "created": data.get("created"),
                "modified": data.get("modified"),
            }

        except httpx.HTTPError as e:
            logger.error("Yandex.Disk get_resource_info failed: %s", e)
            raise


async def build_folder_tree(
    root_path: str = "/",
    access_token: str = "",
    max_depth: int = 1,
    current_depth: int = 0,
) -> dict[str, Any]:
    """
    Build nested folder tree structure.

    Warning: Keep depth shallow (e.g., 1 or 2) to respect Yandex's ~1 req/sec limit.

    Args:
        root_path: Root folder to start from
        access_token: Yandex OAuth access token
        max_depth: Maximum nesting depth (default: 1)
        current_depth: Current recursion depth (internal use)

    Returns:
        Nested folder tree structure

    Raises:
        httpx.HTTPError: If API request fails
    """
    # Get folder info
    folder_info = await get_resource_info(root_path, access_token)

    result = {
        "name": folder_info["name"],
        "path": folder_info["path"],
        "type": "dir",
        "children": [],
    }

    # Stop if we've reached max depth
    if current_depth >= max_depth:
        return result

    # Get folder contents
    try:
        items = await list_folder(root_path, access_token)

        # Recursively build tree for subdirectories only
        for item in items:
            if item["type"] == "dir":
                child_tree = await build_folder_tree(
                    item["path"],
                    access_token,
                    max_depth,
                    current_depth + 1,
                )
                result["children"].append(child_tree)

    except httpx.HTTPError as e:
        # Log but don't fail - return partial tree
        logger.warning("Failed to fetch children for %s: %s", root_path, e)

    return result
