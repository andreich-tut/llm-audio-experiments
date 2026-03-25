# Yandex.Disk Folder Picker

## Goal

Replace the manual text input for `yadisk_path` with a folder browser modal in the Telegram Mini App. Users tap "Browse", navigate Yandex.Disk folders, and select one — no typing needed.

## Current State

- `yadisk_path` is a plain text `SettingField` in the Yandex.Disk section of `SettingsPage.tsx`
- The value is stored in `user_settings` table (unencrypted), used in `obsidian.py` to construct WebDAV paths
- OAuth token for Yandex is already stored and auto-refreshed
- WebDAV is used for file operations; no REST API calls exist yet

## Approach: Yandex.Disk REST API + Folder Browser Modal

Use the REST API (`https://cloud-api.yandex.net/v1/disk/resources`) to list folders. It returns JSON (simpler than WebDAV PROPFIND XML). Requires `Authorization: OAuth {access_token}` header.

### API Details

```
GET https://cloud-api.yandex.net/v1/disk/resources
  ?path={path}
  &limit=100
  &fields=_embedded.items.name,_embedded.items.path,_embedded.items.type
  &sort=name
```

Filter response to `type == "dir"` items only.

## Implementation Plan

### Step 1: Backend — folder listing endpoint

**File:** `interfaces/webapp/routes/oauth.py`

Add endpoint:

```
GET /api/v1/yandex/folders?path=/
```

- Dependency: `get_current_user_id` (existing auth)
- Load OAuth token from DB via `db.get_oauth_token(user_id, "yandex")`
- If no token or expired — refresh via `yandex_client.refresh_access_token()`, update DB
- Call Yandex REST API with the token
- Return `{ path: string, folders: [{ name: string, path: string }] }`
- On 401 from Yandex — attempt one token refresh, retry; if still fails, return 401

**Token refresh logic:** reuse pattern from `obsidian.py:_refresh_if_needed()` — extract into a shared helper in `yandex_client.py` or call it directly.

### Step 2: Frontend — API client method

**File:** `webapp/src/api/settings.ts`

Add:

```typescript
listYandexFolders: (path: string) =>
  api<{ path: string; folders: { name: string; path: string }[] }>(
    `/api/v1/yandex/folders?path=${encodeURIComponent(path)}`
  )
```

### Step 3: Frontend — FolderPicker component

**File:** `webapp/src/components/FolderPicker.tsx` (new)

UI behavior:
1. "Browse" button next to the yadisk_path field (shown only when Yandex is connected)
2. On tap — opens a modal/overlay:
   - Header: breadcrumb path (e.g., `/ > ObsidianVault > Inbox`) — tappable segments to navigate back
   - Body: list of folders at current path, tap to navigate deeper
   - Footer: "Select this folder" button — saves current path to `yadisk_path`
   - Loading spinner while fetching
   - Empty state: "No subfolders" message
3. On select — calls `onSave('yadisk_path', selectedPath)`, closes modal

Component props:
```typescript
interface FolderPickerProps {
  currentPath: string | null
  onSelect: (path: string) => void
}
```

### Step 4: Frontend — integrate into SettingsPage

**File:** `webapp/src/components/SettingsPage.tsx`

In the Yandex.Disk section, replace or augment the `yadisk_path` SettingField:
- If Yandex is connected: show `FolderPicker` + current path display + reset
- If not connected: hide the field (or show it disabled)

### Step 5: Styling

**File:** `webapp/src/theme.css`

Add styles for:
- `.folder-picker-modal` — full-screen overlay using Telegram theme vars
- `.folder-list` — scrollable list of folder items
- `.folder-item` — tappable row with folder icon and name
- `.breadcrumb` — horizontal path segments
- Consistent with existing `.field-*` and `.btn-*` classes

## File Changes Summary

| File | Change |
|------|--------|
| `interfaces/webapp/routes/oauth.py` | Add `GET /api/v1/yandex/folders` endpoint |
| `infrastructure/external_api/yandex_client.py` | Add `list_folders()` function (REST API call) |
| `webapp/src/api/settings.ts` | Add `listYandexFolders()` method |
| `webapp/src/components/FolderPicker.tsx` | New component — modal folder browser |
| `webapp/src/components/SettingsPage.tsx` | Wire FolderPicker into Yandex.Disk section |
| `webapp/src/theme.css` | Add folder picker styles |

## Scope Boundaries

- Folder listing only (no file listing, no file operations)
- No folder creation from the picker (user creates folders via Yandex.Disk app)
- No drag-and-drop or multi-select
- REST API only (not WebDAV PROPFIND)
- OAuth scope `cloud_api:disk.app_folder` may limit visibility — if needed, update scope to `cloud_api:disk.read` (requires re-auth for existing users)

## Open Questions

- **OAuth scope:** Current scope is `cloud_api:disk.app_folder` — this may only show the app folder, not the full disk. Need to verify. If limited, we'd need to add `cloud_api:disk.read` scope and existing users would need to re-authorize.
