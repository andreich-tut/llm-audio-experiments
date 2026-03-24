# Yandex OAuth Login & Note URL Features

## Overview

This document describes two new features added to the bot:

1. **Yandex OAuth Login** - Users can authenticate with Yandex.Disk via OAuth 2.0 with automatic redirect back to the bot
2. **Yandex.Disk URL in Notes** - When saving notes via OAuth, the note includes a clickable link to view the file on Yandex.Disk

## Feature 1: Yandex OAuth Login (Simplified Flow)

### Setup Instructions

1. **Create OAuth Application in Yandex**
   - Go to https://oauth.yandex.ru/client/new
   - Create a new OAuth application
   - Set required scopes: `login:info`, `yandexdisk:write`
   - Set redirect URI to: `https://t.me/your_bot_username` (replace with your bot's username)

2. **Configure Bot**
   Add to `.env`:
   ```bash
   YANDEX_OAUTH_CLIENT_ID=your_client_id_here
   YANDEX_OAUTH_CLIENT_SECRET=your_client_secret_here
   ```

3. **Restart the bot**

### User Flow (Automatic Redirect)

1. User sends `/settings` command
2. Clicks "☁️ Yandex.Disk" button
3. Clicks "🔑 Войти через Яндекс" (Login with Yandex) button
4. Opens OAuth URL in browser
5. Authorizes the application with Yandex Passport
6. **Yandex redirects back to the bot automatically** via Telegram deep link
7. Bot processes the OAuth code and saves the token
8. User receives success message with their Yandex login
9. User can go to `/settings` to see their connected account

**No manual URL copying required!** 🎉

### Technical Details

- **Deep Linking**: OAuth redirects to `https://t.me/bot_username?start=oauth_<code>_<state>`
- **Token Storage**: OAuth tokens are stored in `state/user_settings.json` per user
- **Token Structure**:
  ```json
  {
    "access_token": "...",
    "refresh_token": "...",
    "expires_at": "2024-01-01T00:00:00",
    "token_type": "Bearer",
    "login": "username@yandex.ru"
  }
  ```
- **Auto-refresh**: Access tokens are automatically refreshed when expired
- **Security**: State parameter prevents CSRF attacks

## Feature 2: Yandex.Disk URL in Notes

### How It Works

When a user creates a note in "note" mode and is authenticated via OAuth:

1. Note is saved to Yandex.Disk via WebDAV API using OAuth token
2. A Yandex.Disk URL is generated for the saved file
3. The URL is appended to the note content
4. The note is re-saved with the URL included
5. User receives the note file with a clickable link

### Note Format

```markdown
---
date: 2024-01-01
time: 12:00
tags: [voice-note, tag1, tag2]
---

# Note Title

Note content here...

🔗 [View on Yandex.Disk](https://disk.yandex.ru/client/files/...)
```

### User Experience

After the note is sent:
- Caption shows: "📁 Saved to Yandex.Disk: https://disk.yandex.ru/..."
- Note file contains clickable link at the bottom
- User can open the link to view/edit the note directly on Yandex.Disk

## Code Changes

### New Files

- `services/yandex_oauth.py` - OAuth 2.0 flow implementation
  - `get_oauth_url(state)` - Generate authorization URL
  - `exchange_code(code)` - Exchange code for tokens
  - `refresh_access_token(refresh_token)` - Refresh expired tokens
  - `get_user_login(access_token)` - Get Yandex login from token

### Modified Files

1. **`config.py`**
   - Added `YANDEX_OAUTH_CLIENT_ID`, `YANDEX_OAUTH_CLIENT_SECRET`, `YANDEX_OAUTH_REDIRECT_URI`

2. **`state.py`**
   - Added `get_user_setting_json()` / `set_user_setting_json()` for storing OAuth tokens

3. **`handlers/settings.py`**
   - Added OAuth login button to Yandex.Disk keyboard
   - Added OAuth callback handlers
   - Added URL paste message handler
   - Updated display to show OAuth login status

4. **`services/obsidian.py`**
   - Added `_save_webdav_oauth()` function for OAuth authentication
   - Updated `save_note()` to return `(location, disk_url)` tuple
   - Auto-refresh tokens when expired

5. **`core/pipelines.py`**
   - Updated note saving to append Yandex.Disk URL
   - Re-save note with URL included

6. **`locales/ru.json`** / **`locales/en.json`**
   - Added OAuth-related i18n strings
   - Added `vault_saved_with_url` message

7. **`.env.example`**
   - Added OAuth configuration section

## Backward Compatibility

- Existing login/password authentication still works
- OAuth is optional and only available if `YANDEX_OAUTH_CLIENT_ID` is configured
- Local vault saves are unchanged (no URL added)
- OAuth takes priority over login/password if both are configured

## Testing Checklist

- [ ] OAuth login flow works end-to-end
- [ ] Token is stored correctly in `user_settings.json`
- [ ] Token refresh works when expired
- [ ] Note saved to Yandex.Disk via OAuth includes URL
- [ ] Note caption shows Yandex.Disk URL
- [ ] Existing login/password authentication still works
- [ ] Local vault saves work without OAuth
- [ ] OAuth button only shows when `YANDEX_OAUTH_CLIENT_ID` is configured

## Troubleshooting

### OAuth not configured error
- Ensure `YANDEX_OAUTH_CLIENT_ID` is set in `.env`
- Restart the bot after adding credentials

### Invalid state error
- State mismatch can occur if OAuth flow takes too long
- User should restart the flow by clicking "Login with Yandex" again

### Token exchange failed
- Check that OAuth app is properly configured in Yandex
- Verify `YANDEX_OAUTH_CLIENT_SECRET` is correct
- Ensure scopes include `login:info` and `yandexdisk:write`

### Note URL not appearing
- Verify user is authenticated via OAuth (not login/password)
- Check logs for WebDAV save errors
- Ensure `YANDEX_DISK_PATH` is configured correctly
