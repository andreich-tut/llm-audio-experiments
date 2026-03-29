# Test Specifications by Domain

This document provides a comprehensive overview of test specifications organized by functional domain for the Telegram Voice/Audio Bot project.

---

## Table of Contents

1. [Yandex.Disk API Client](#yandexdisk-api-client-domain)
2. [Yandex.Disk REST API Routes](#yandexdisk-rest-api-routes-domain)
3. [Authentication & Security](#authentication--security-domain)
4. [Test Coverage Summary](#test-coverage-summary)

---

## Yandex.Disk API Client Domain

**File:** `infrastructure/external_api/yandex_disk_client.py`  
**Test File:** `tests/test_yandex_disk_client.py`

### 1.1 Path Normalization (`_normalize_path`)

**Purpose:** Convert various path formats to Yandex.Disk API standard (`disk:/` prefix).

| Test Case | Input | Expected Output | Rationale |
|-----------|-------|-----------------|-----------|
| `test_root_path` | `/` | `disk:/` | Root path normalization |
| `test_empty_path` | `""` | `disk:/` | Empty string defaults to root |
| `test_already_normalized` | `disk:/Documents` | `disk:/Documents` | No double-prefixing |
| `test_unix_absolute_path` | `/Documents` | `disk:/Documents` | Unix to Yandex format |
| `test_relative_path` | `Documents` | `disk:/Documents` | Relative paths treated as root-relative |

**Security Considerations:**
- Path traversal prevention (`..` sequences) is handled at the API route layer, not in normalization
- Normalization is purely format conversion, not validation

---

### 1.2 Folder Listing (`list_folder`)

**Purpose:** Retrieve contents of a Yandex.Disk folder with pagination support.

#### Functional Tests

| Test Case | Parameters | Expected Behavior |
|-----------|------------|-------------------|
| `test_list_root_folder` | `path="/", limit=100, offset=0` | Returns list of folders/files with metadata |
| `test_list_subfolder` | `path="/Documents"` | Correctly prefixes path to `disk:/Documents` |
| `test_list_folder_with_pagination` | `limit=10, offset=5` | Passes pagination params to API |
| `test_list_folder_empty_response` | Empty folder | Returns empty list `[]` |

#### Error Handling Tests

| Test Case | Simulated Error | Expected Exception |
|-----------|-----------------|-------------------|
| `test_list_folder_http_error` | HTTP 404 | `httpx.HTTPStatusError` raised |
| `test_list_folder_429_rate_limit` | HTTP 429 | `httpx.HTTPStatusError` raised |

**API Contract:**
```python
async def list_folder(
    path: str = "/",
    access_token: str = "",
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]
```

**Response Format:**
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

---

### 1.3 Resource Info (`get_resource_info`)

**Purpose:** Retrieve metadata for a specific file or folder.

#### Functional Tests

| Test Case | Resource Type | Expected Fields |
|-----------|--------------|-----------------|
| `test_get_folder_info` | Directory | `name`, `path`, `type="dir"`, `created`, `modified` |
| `test_get_file_info` | File | `name`, `path`, `type="file"` |

#### Error Handling Tests

| Test Case | Simulated Error | Expected Exception |
|-----------|-----------------|-------------------|
| `test_get_resource_info_http_error` | HTTP 404 | `httpx.HTTPStatusError` raised |

**API Contract:**
```python
async def get_resource_info(
    path: str,
    access_token: str,
) -> dict[str, Any]
```

---

### 1.4 Folder Tree Building (`build_folder_tree`)

**Purpose:** Recursively build nested folder structure with depth limiting.

#### Functional Tests

| Test Case | Depth | Expected Behavior |
|-----------|-------|-------------------|
| `test_build_tree_depth_0` | `max_depth=0` | Returns root node with empty `children` |
| `test_build_tree_depth_1` | `max_depth=1` | Returns root + immediate children (dirs only) |
| `test_build_tree_nested_structure` | `max_depth=2` | Returns 3-level nested structure |

#### Error Recovery Tests

| Test Case | Failure Point | Expected Behavior |
|-----------|--------------|-------------------|
| `test_build_tree_handles_list_folder_error` | `list_folder` fails | Returns partial tree (root only), logs warning |

**Rate Limiting Warning:**
- Default `max_depth=1` to respect Yandex's ~1 req/sec limit
- Each folder level requires additional API calls

**API Contract:**
```python
async def build_folder_tree(
    root_path: str = "/",
    access_token: str = "",
    max_depth: int = 1,
    current_depth: int = 0,
) -> dict[str, Any]
```

---

## Yandex.Disk REST API Routes Domain

**File:** `interfaces/webapp/routes/yadisk_folders.py`  
**Test File:** `tests/test_yadisk_folders_routes.py`

### 2.1 List Folders Endpoint

**Endpoint:** `GET /api/v1/yadisk/folders`

#### Success Scenarios

| Test Case | Query Parameters | Expected Response |
|-----------|-----------------|-------------------|
| `test_list_root_folder_success` | (default) | `200 OK`, list of folders |
| `test_list_folder_with_path` | `path=/Documents` | `200 OK`, filtered list |
| `test_list_folder_with_pagination` | `limit=10&offset=5` | `200 OK`, paginated list |

#### Security Tests

| Test Case | Malicious Input | Expected Response |
|-----------|-----------------|-------------------|
| `test_list_folder_path_traversal_blocked` | `path=../etc` | `400 Bad Request`, "Path must start with '/' or 'disk:/'" |
| `test_list_folder_double_dot_blocked` | `path=/Documents/../etc` | `400 Bad Request`, "Path traversal is not allowed" |

#### Authentication Tests

| Test Case | OAuth State | Expected Response |
|-----------|-------------|-------------------|
| `test_list_folder_no_oauth` | No token | `401 Unauthorized`, "OAuth not connected" |
| `test_list_folders_requires_auth` | No Telegram initData | `422 Unprocessable Entity` |

#### Error Propagation Tests

| Test Case | Upstream Error | Expected Response |
|-----------|---------------|-------------------|
| `test_list_folder_404` | HTTP 404 from Yandex | `404 Not Found`, "Folder not found" |
| `test_list_folder_429_rate_limit` | HTTP 429 from Yandex | `429 Too Many Requests`, "Rate limit exceeded" |
| `test_list_folder_403_invalid_token` | HTTP 401 from Yandex | `403 Forbidden`, "Invalid or expired OAuth token" |
| `test_list_folder_500_server_error` | HTTP 500 from Yandex | `500 Internal Server Error` |

---

### 2.2 Folder Tree Endpoint

**Endpoint:** `GET /api/v1/yadisk/folders/tree`

#### Success Scenarios

| Test Case | Query Parameters | Expected Response |
|-----------|-----------------|-------------------|
| `test_get_tree_success` | (default) | `200 OK`, nested tree structure |
| `test_get_tree_with_custom_root` | `root_path=/ObsidianVault` | `200 OK`, tree from specified root |
| `test_get_tree_with_depth` | `depth=2` | `200 OK`, tree with 2 levels |

#### Validation Tests

| Test Case | Invalid Input | Expected Response |
|-----------|--------------|-------------------|
| `test_get_tree_depth_validation` | `depth=5` | `422 Unprocessable Entity` (exceeds max=3) |
| `test_get_tree_path_traversal_blocked` | `root_path=../etc` | `400 Bad Request` |

#### Authentication Tests

| Test Case | OAuth State | Expected Response |
|-----------|-------------|-------------------|
| `test_get_tree_no_oauth` | No token | `401 Unauthorized` |
| `test_tree_endpoint_requires_auth` | No Telegram initData | `422 Unprocessable Entity` |

#### Error Propagation Tests

| Test Case | Upstream Error | Expected Response |
|-----------|---------------|-------------------|
| `test_get_tree_404` | HTTP 404 | `404 Not Found` |
| `test_get_tree_429_rate_limit` | HTTP 429 | `429 Too Many Requests` |

---

## Authentication & Security Domain

### 3.1 Telegram Mini App Authentication

**Dependency:** `get_current_user_id`  
**Mechanism:** HMAC-SHA256 validation of `X-Telegram-Init-Data` header

**Test Coverage:**
- All endpoints require valid Telegram initData (tested via `test_list_folders_requires_auth`, `test_tree_endpoint_requires_auth`)
- Missing header returns `422 Unprocessable Entity`
- Invalid signature returns `401 Unauthorized` (handled by dependency)

---

### 3.2 OAuth Token Management

**Dependency:** `_get_yandex_token` (internal to routes)  
**Mechanism:** Retrieve OAuth token from database, auto-refresh if expired

**Test Coverage:**
| Scenario | Test Case | Expected Behavior |
|----------|-----------|-------------------|
| Token not connected | `test_list_folder_no_oauth` | `401 Unauthorized` |
| Token expired | `test_list_folder_403_invalid_token` | `403 Forbidden` (upstream 401) |
| Token valid | All success tests | Access token passed to API |

---

### 3.3 Path Traversal Prevention

**Validation Rules:**
1. Path must start with `/` or `disk:/`
2. Path must not contain `..` sequences

**Test Coverage:**
- `test_list_folder_path_traversal_blocked` - Relative path with `..`
- `test_list_folder_double_dot_blocked` - Absolute path with `..`
- `test_get_tree_path_traversal_blocked` - Tree endpoint validation

---

## Test Coverage Summary

### Coverage by Module

| Module | Statements | Covered | Coverage |
|--------|-----------|---------|----------|
| `yandex_disk_client.py` | 54 | 54 | **100%** |
| `yadisk_folders.py` | 58 | 50 | **86%** |
| `schemas.py` | 41 | 41 | **100%** |
| `app.py` | 28 | 28 | **100%** |

### Test Distribution

| Domain | Test Count | Percentage |
|--------|-----------|------------|
| Yandex.Disk API Client | 18 | 47% |
| REST API Routes | 20 | 53% |
| **Total** | **38** | **100%** |

### Test Types

| Type | Count | Purpose |
|------|-------|---------|
| Success scenarios | 14 | Verify correct behavior |
| Error handling | 12 | Verify graceful failure |
| Security validation | 6 | Verify access control |
| Input validation | 6 | Verify parameter sanitization |

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=infrastructure --cov=interfaces/webapp --cov-report=term-missing

# Run specific test file
pytest tests/test_yandex_disk_client.py -v

# Run specific test class
pytest tests/test_yandex_disk_client.py::TestListFolder -v

# Run specific test case
pytest tests/test_yandex_disk_client.py::TestListFolder::test_list_root_folder -v

# Run via pre-commit (all files)
pre-commit run --all-files --hook-stage manual

# Run via project checks script
bash scripts/run-checks.sh
```

---

## Fixtures Reference

### Available Fixtures (`tests/conftest.py`)

| Fixture | Type | Description |
|---------|------|-------------|
| `mock_oauth_token` | `MagicMock` | Valid OAuth token with 23h expiry |
| `mock_expired_oauth_token` | `MagicMock` | Expired OAuth token |
| `mock_yandex_folder_response` | `dict` | Mock API response for folder listing |
| `mock_yandex_resource_response` | `dict` | Mock API response for resource info |
| `mock_httpx_get` | `MagicMock` | Mocked `httpx.AsyncClient.get` |
| `mock_db_with_oauth` | `AsyncMock` | Database with valid OAuth token |
| `mock_db_without_oauth` | `AsyncMock` | Database without OAuth token |
| `mock_user_data` | `dict` | Mock Telegram user data |

---

## Future Test Specifications

### Not Yet Covered

1. **Token Refresh Flow**
   - Test automatic token refresh when expired
   - Test refresh failure handling

2. **Integration Tests**
   - End-to-end OAuth flow
   - Real Yandex.Disk API calls (staging environment)

3. **Performance Tests**
   - Rate limit handling under load
   - Concurrent request handling

4. **Frontend Integration**
   - Mini App UI folder selection flow
   - SSE OAuth status updates

---

## CI/CD Integration

### Pre-commit Hooks

Tests are integrated into the pre-commit workflow via `.pre-commit-config.yaml`:

```yaml
- id: pytest
  name: Run pytest tests
  entry: bash -c './.venv/bin/python -m pytest tests/ -v --tb=short'
  language: system
  pass_filenames: false
  stages: [pre-commit, manual]
```

### Project Checks Script

The `scripts/run-checks.sh` script runs all checks including tests:

```bash
#!/usr/bin/env bash
pre-commit run --all-files --hook-stage manual
```

This ensures tests run:
- Before every commit (pre-commit hook)
- During CI/CD pipeline
- Manually via `bash scripts/run-checks.sh`

---

**Document Version:** 1.0  
**Last Updated:** 2026-03-29  
**Test Suite Version:** 38 tests
