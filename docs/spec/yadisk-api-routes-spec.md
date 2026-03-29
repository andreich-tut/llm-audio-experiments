# Yandex.Disk REST API Routes Specification

**Module:** `interfaces/webapp/routes/yadisk_folders.py`  
**Test Suite:** `tests/test_yadisk_folders_routes.py`  
**Coverage:** 86%

---

## Overview

FastAPI REST endpoints for browsing Yandex.Disk folder structure. Provides authentication, input validation, error handling, and response formatting.

---

## Endpoints

### `GET /api/v1/yadisk/folders`

**Purpose:** List contents of a Yandex.Disk folder (lazy-loading optimized).

#### Request

```http
GET /api/v1/yadisk/folders?path=/Documents&limit=10&offset=0
X-Telegram-Init-Data: <Telegram WebApp initData>
```

#### Query Parameters

| Parameter | Type | Default | Validation | Description |
|-----------|------|---------|------------|-------------|
| `path` | `str` | `"/"` | Must start with `/` or `disk:/` | Folder path to list |
| `limit` | `int` | `100` | 1-1000 | Maximum items to return |
| `offset` | `int` | `0` | >= 0 | Pagination offset |

#### Headers

| Header | Required | Description |
|--------|----------|-------------|
| `X-Telegram-Init-Data` | Yes | Telegram WebApp authentication |

#### Success Response (200 OK)

```json
[
  {
    "name": "Documents",
    "path": "disk:/Documents",
    "type": "dir",
    "created": "2024-01-15T10:30:00Z",
    "modified": "2024-03-20T14:22:00Z"
  }
]
```

#### Error Responses

| Status | Code | Condition |
|--------|------|-----------|
| 400 | `Bad Request` | Path traversal attempt (`..` in path) |
| 400 | `Bad Request` | Invalid path format (doesn't start with `/` or `disk:/`) |
| 401 | `Unauthorized` | OAuth token not connected |
| 403 | `Forbidden` | Invalid/expired OAuth token |
| 404 | `Not Found` | Folder path doesn't exist |
| 422 | `Unprocessable Entity` | Missing/invalid Telegram initData |
| 429 | `Too Many Requests` | Yandex API rate limit exceeded |
| 500 | `Internal Server Error` | Yandex API error |

#### Test Cases

| Test | Scenario | Expected |
|------|----------|----------|
| `test_list_root_folder_success` | Default parameters | 200, list of folders |
| `test_list_folder_with_path` | `path=/Documents` | 200, filtered list |
| `test_list_folder_with_pagination` | `limit=10&offset=5` | 200, paginated |
| `test_list_folder_path_traversal_blocked` | `path=../etc` | 400, error message |
| `test_list_folder_double_dot_blocked` | `path=/Docs/../etc` | 400, error message |
| `test_list_folder_no_oauth` | No OAuth token | 401, error message |
| `test_list_folder_404` | Yandex returns 404 | 404, "Folder not found" |
| `test_list_folder_429_rate_limit` | Yandex returns 429 | 429, "Rate limit exceeded" |
| `test_list_folder_403_invalid_token` | Yandex returns 401 | 403, "Invalid or expired" |
| `test_list_folder_500_server_error` | Yandex returns 500 | 500, generic error |
| `test_list_folders_requires_auth` | No initData header | 422, validation error |

---

### `GET /api/v1/yadisk/folders/tree`

**Purpose:** Get nested folder tree structure (shallow depth recommended).

#### Request

```http
GET /api/v1/yadisk/folders/tree?root_path=/ObsidianVault&depth=2
X-Telegram-Init-Data: <Telegram WebApp initData>
```

#### Query Parameters

| Parameter | Type | Default | Validation | Description |
|-----------|------|---------|------------|-------------|
| `root_path` | `str` | `"/"` | Must start with `/` or `disk:/` | Root folder |
| `depth` | `int` | `1` | 1-3 | Maximum nesting depth |

#### Headers

| Header | Required | Description |
|--------|----------|-------------|
| `X-Telegram-Init-Data` | Yes | Telegram WebApp authentication |

#### Success Response (200 OK)

```json
{
  "name": "root",
  "path": "disk:/",
  "children": [
    {
      "name": "Documents",
      "path": "disk:/Documents",
      "type": "dir",
      "children": []
    }
  ]
}
```

#### Error Responses

| Status | Code | Condition |
|--------|------|-----------|
| 400 | `Bad Request` | Path traversal attempt |
| 400 | `Bad Request` | Invalid path format |
| 401 | `Unauthorized` | OAuth token not connected |
| 403 | `Forbidden` | Invalid/expired OAuth token |
| 404 | `Not Found` | Folder path doesn't exist |
| 422 | `Unprocessable Entity` | Invalid parameters (depth > 3) |
| 422 | `Unprocessable Entity` | Missing/invalid Telegram initData |
| 429 | `Too Many Requests` | Yandex API rate limit exceeded |
| 500 | `Internal Server Error` | Yandex API error |

#### Test Cases

| Test | Scenario | Expected |
|------|----------|----------|
| `test_get_tree_success` | Default parameters | 200, nested tree |
| `test_get_tree_with_custom_root` | `root_path=/Vault` | 200, tree from root |
| `test_get_tree_with_depth` | `depth=2` | 200, 2-level tree |
| `test_get_tree_depth_validation` | `depth=5` | 422, validation error |
| `test_get_tree_path_traversal_blocked` | `root_path=../etc` | 400, error message |
| `test_get_tree_no_oauth` | No OAuth token | 401, error message |
| `test_get_tree_404` | Yandex returns 404 | 404, "Folder not found" |
| `test_get_tree_429_rate_limit` | Yandex returns 429 | 429, "Rate limit exceeded" |
| `test_tree_endpoint_requires_auth` | No initData header | 422, validation error |

---

## Security Specifications

### 1. Authentication Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend  │────▶│  FastAPI     │────▶│  Telegram   │
│  (Mini App) │     │  Dependency  │     │  Validation │
└─────────────┘     └──────────────┘     └─────────────┘
     │                    │                      │
     │ X-Telegram-Init-Data                      │
     │───────────────────▶│                      │
     │                    │ validate_init_data() │
     │                    │─────────────────────▶│
     │                    │  user_id or 401      │
     │                    │◀─────────────────────│
     │                    │                      │
     │                    │ get_current_user_id  │
     │                    │─────────────────────▶│
     │ 200/4xx/5xx        │                      │
     │◀───────────────────│                      │
```

**Validation Steps:**
1. Check `X-Telegram-Init-Data` header present
2. Validate HMAC-SHA256 signature with bot token
3. Extract `user_id` from parsed user data
4. Check user in `ALLOWED_USER_IDS` (if configured)

### 2. Path Traversal Prevention

**Rules:**
```python
# Rule 1: Path must start with / or disk:/
if not path.startswith("/") and not path.startswith("disk:/"):
    raise HTTPException(400, "Path must start with '/' or 'disk:/'")

# Rule 2: No .. sequences
if ".." in path:
    raise HTTPException(400, "Path traversal is not allowed")
```

**Test Coverage:**
- `test_list_folder_path_traversal_blocked` - Relative `../etc`
- `test_list_folder_double_dot_blocked` - Absolute `/Docs/../etc`
- `test_get_tree_path_traversal_blocked` - Tree endpoint

### 3. OAuth Token Validation

**Flow:**
```python
async def _get_yandex_token(user_id: int, db: Database) -> str:
    token = await db.get_oauth_token(user_id, "yandex")
    if not token:
        raise HTTPException(401, "OAuth not connected")
    return token.access_token  # Auto-refresh handled by DB layer
```

**Error Mapping:**
| Token State | User Action Required |
|-------------|---------------------|
| Not connected (None) | Re-authenticate via OAuth |
| Expired (auto-refresh fails) | Re-authenticate via OAuth |
| Invalid (401 from Yandex) | Re-authenticate via OAuth |

---

## Dependency Injection

### Dependencies

| Dependency | Source | Purpose |
|------------|--------|---------|
| `get_current_user_id` | `interfaces.webapp.dependencies` | Telegram auth |
| `get_database` | `interfaces.webapp.dependencies` | Database access |

### Test Override Pattern

```python
@pytest.fixture
def client():
    mock_token = MagicMock()
    mock_token.access_token = "test_access_token"
    
    mock_db = AsyncMock()
    mock_db.get_oauth_token = AsyncMock(return_value=mock_token)
    
    with TestClient(app) as test_client:
        test_client.app.dependency_overrides[get_current_user_id] = lambda: 123456789
        test_client.app.dependency_overrides[get_database] = lambda: mock_db
        yield test_client
        test_client.app.dependency_overrides.clear()
```

---

## Error Handling Matrix

| Layer | Error | Caught By | Response |
|-------|-------|-----------|----------|
| Dependency | Missing initData | `validate_init_data()` | 401/422 |
| Dependency | Invalid signature | `validate_init_data()` | 401 |
| Route | No OAuth token | `_get_yandex_token()` | 401 |
| Route | Path traversal | Input validation | 400 |
| Client | HTTP 401 | Route handler | 403 |
| Client | HTTP 404 | Route handler | 404 |
| Client | HTTP 429 | Route handler | 429 |
| Client | HTTP 5xx | Route handler | 500 |

---

## Performance Considerations

### Rate Limiting

**Yandex.Disk API:** ~1 request/second

**Recommendations:**
1. Use `/folders` endpoint for lazy-loading (on-demand)
2. Limit `/folders/tree` depth to 1-2 levels
3. Implement client-side caching
4. Add retry with exponential backoff for 429 errors

### Response Size

| Endpoint | Typical Size | Max Recommended |
|----------|--------------|-----------------|
| `/folders` | 1-10 KB | 1000 items |
| `/folders/tree` | 1-50 KB | depth=2, ~100 folders |

---

## Integration Flow

```
Frontend          FastAPI           Yandex.Disk API
   │                  │                    │
   │ GET /folders     │                    │
   │─────────────────▶│                    │
   │                  │ Get OAuth token    │
   │                  │───────────────────▶│
   │                  │                    │
   │                  │ List folder        │
   │                  │───────────────────▶│
   │                  │ Folder list        │
   │                  │◀───────────────────│
   │ 200 OK           │                    │
   │◀─────────────────│                    │
   │                  │                    │
   │ User expands     │                    │
   │ GET /folders?path=/Docs              │
   │─────────────────▶│                    │
   │                  │ List subfolder     │
   │                  │───────────────────▶│
   │                  │ Subfolder contents │
   │                  │◀───────────────────│
   │ 200 OK           │                    │
   │◀─────────────────│                    │
```

---

## Pydantic Schemas

### Request Parameters (Query)

```python
# Automatically validated by FastAPI
path: str = Query(default="/", description="...")
limit: int = Query(default=100, ge=1, le=1000)
offset: int = Query(default=0, ge=0)
depth: int = Query(default=1, ge=1, le=3)
```

### Response Schemas (`interfaces/webapp/schemas.py`)

```python
class YandexDiskFolder(BaseModel):
    name: str
    path: str
    type: str  # "dir" or "file"
    created: datetime | None = None
    modified: datetime | None = None

class YandexDiskTreeNode(BaseModel):
    name: str
    path: str
    type: str = "dir"
    children: list["YandexDiskTreeNode"] = []

class YandexDiskTree(BaseModel):
    name: str
    path: str
    children: list[YandexDiskTreeNode]
```

---

**Version:** 1.0  
**Last Updated:** 2026-03-29
