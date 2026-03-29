# Yandex.Disk API Client Specification

**Module:** `infrastructure/external_api/yandex_disk_client.py`  
**Test Suite:** `tests/test_yandex_disk_client.py`  
**Coverage:** 100%

---

## Overview

Async client for Yandex.Disk REST API operations. Handles path normalization, folder listing, resource metadata retrieval, and recursive tree building with rate-limit awareness.

---

## Functions

### `_normalize_path(path: str) -> str`

**Purpose:** Convert various path formats to Yandex.Disk API standard format.

#### Input/Output Mapping

| Input | Output | Notes |
|-------|--------|-------|
| `"/"` | `"disk:/"` | Root path |
| `""` | `"disk:/"` | Empty defaults to root |
| `"disk:/Documents"` | `"disk:/Documents"` | Already normalized |
| `"/Documents"` | `"disk:/Documents"` | Unix absolute path |
| `"/ObsidianVault/Inbox"` | `"disk:/ObsidianVault/Inbox"` | Nested path |
| `"Documents"` | `"disk:/Documents"` | Relative path |
| `"folder/subfolder"` | `"disk:/folder/subfolder"` | Relative nested |

#### Test Cases

```python
def test_root_path():
    assert _normalize_path("/") == "disk:/"

def test_empty_path():
    assert _normalize_path("") == "disk:/"

def test_already_normalized():
    assert _normalize_path("disk:/Documents") == "disk:/Documents"

def test_unix_absolute_path():
    assert _normalize_path("/Documents") == "disk:/Documents"

def test_relative_path():
    assert _normalize_path("Documents") == "disk:/Documents"
```

---

### `list_folder(path, access_token, limit, offset) -> list[dict]`

**Purpose:** List contents of a Yandex.Disk folder with pagination.

#### Parameters

| Parameter | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `path` | `str` | `"/"` | Any valid path |
| `access_token` | `str` | Required | Valid OAuth token |
| `limit` | `int` | `100` | 1-1000 |
| `offset` | `int` | `0` | >= 0 |

#### API Request

```
GET https://cloud-api.yandex.net/v1/disk/resources
  ?path=disk:/<path>
  &limit=<limit>
  &offset=<offset>
Authorization: OAuth <access_token>
```

#### Response Format

```json
[
  {
    "name": "Documents",
    "path": "disk:/Documents",
    "type": "dir",
    "created": "2024-01-15T10:30:00Z",
    "modified": "2024-03-20T14:22:00Z"
  },
  {
    "name": "photo.jpg",
    "path": "disk:/photo.jpg",
    "type": "file",
    "created": null,
    "modified": null
  }
]
```

#### Test Cases

| Test | Scenario | Verification |
|------|----------|--------------|
| `test_list_root_folder` | List root contents | Returns 3 items with correct metadata |
| `test_list_subfolder` | List `/Documents` | Path converted to `disk:/Documents` |
| `test_list_folder_with_pagination` | `limit=10, offset=5` | Params passed to API |
| `test_list_folder_empty_response` | Empty folder | Returns `[]` |
| `test_list_folder_http_error` | HTTP 404 | Raises `HTTPStatusError` |
| `test_list_folder_429_rate_limit` | HTTP 429 | Raises `HTTPStatusError` |

---

### `get_resource_info(path, access_token) -> dict`

**Purpose:** Get metadata for a specific file or folder.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `str` | Resource path |
| `access_token` | `str` | Valid OAuth token |

#### API Request

```
GET https://cloud-api.yandex.net/v1/disk/resources?path=<path>
Authorization: OAuth <access_token>
```

#### Response Format

```json
{
  "name": "ObsidianVault",
  "path": "disk:/ObsidianVault",
  "type": "dir",
  "created": "2024-02-01T08:00:00Z",
  "modified": "2024-03-28T16:45:00Z"
}
```

#### Test Cases

| Test | Scenario | Verification |
|------|----------|--------------|
| `test_get_folder_info` | Folder metadata | All fields present |
| `test_get_file_info` | File metadata | `type="file"` |
| `test_get_resource_info_http_error` | HTTP 404 | Raises `HTTPStatusError` |

---

### `build_folder_tree(root_path, access_token, max_depth) -> dict`

**Purpose:** Build nested folder structure with depth limiting.

#### Parameters

| Parameter | Type | Default | Constraints |
|-----------|------|---------|-------------|
| `root_path` | `str` | `"/"` | Any valid path |
| `access_token` | `str` | Required | Valid OAuth token |
| `max_depth` | `int` | `1` | Recommended: 1-2 |
| `current_depth` | `int` | `0` | Internal use |

#### Rate Limiting Warning

**CRITICAL:** Yandex.Disk API limits to ~1 request/second. Each folder level requires multiple API calls:
- 1 call for `get_resource_info` (root)
- 1 call for `list_folder` (contents)
- N calls for `get_resource_info` (each subdirectory)

**Recommendation:** Use `max_depth=1` for responsive UI, lazy-load children via `list_folder`.

#### Response Format

```json
{
  "name": "root",
  "path": "disk:/",
  "type": "dir",
  "children": [
    {
      "name": "Documents",
      "path": "disk:/Documents",
      "type": "dir",
      "children": []
    },
    {
      "name": "ObsidianVault",
      "path": "disk:/ObsidianVault",
      "type": "dir",
      "children": [
        {
          "name": "Inbox",
          "path": "disk:/ObsidianVault/Inbox",
          "type": "dir",
          "children": []
        }
      ]
    }
  ]
}
```

#### Test Cases

| Test | Scenario | Verification |
|------|----------|--------------|
| `test_build_tree_depth_0` | `max_depth=0` | Root only, empty children |
| `test_build_tree_depth_1` | `max_depth=1` | Root + immediate children |
| `test_build_tree_nested_structure` | `max_depth=2` | 3-level nesting |
| `test_build_tree_handles_list_folder_error` | API fails mid-tree | Returns partial tree, no exception |

#### Error Recovery

When `list_folder` fails during tree building:
- Logs warning with path and error
- Returns tree with empty `children` for failed branch
- Continues processing other branches

---

## Error Handling Strategy

| Error Type | Source | Handling |
|------------|--------|----------|
| `httpx.HTTPStatusError` | Yandex API | Propagated to caller |
| HTTP 401 | Token invalid | Propagated (caller handles refresh) |
| HTTP 404 | Path not found | Propagated |
| HTTP 429 | Rate limit | Propagated (caller should retry) |
| HTTP 5xx | Server error | Propagated |

---

## Dependencies

| Module | Purpose |
|--------|---------|
| `httpx` | Async HTTP client |
| `logging` | Error logging |

---

## Mocking Strategy (Tests)

```python
# Mock httpx.AsyncClient context manager
mock_client = AsyncMock()
mock_client.get.return_value = mock_response

with patch("httpx.AsyncClient") as MockClient:
    MockClient.return_value.__aenter__.return_value = mock_client
    # Call function under test
```

---

## Performance Considerations

1. **Connection Pooling:** `httpx.AsyncClient` created per call (not optimal)
   - Future improvement: Use connection pool or session

2. **Rate Limiting:** No built-in throttling
   - Caller responsibility: Implement retry with backoff

3. **Memory:** Full response loaded into memory
   - Acceptable for typical folder sizes (<1000 items)

---

**Version:** 1.0  
**Last Updated:** 2026-03-29
