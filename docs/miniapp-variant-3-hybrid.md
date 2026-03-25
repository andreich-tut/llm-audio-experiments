# Variant 3: Hybrid — Mini App for Complex Settings, Inline KB for Simple

## Summary

Keep the current inline keyboard UI for quick settings (mode, language) and add a Mini App only for the complex settings that benefit from a web UI (API credentials, OAuth flows, multi-field forms). This is an incremental migration that reduces risk and delivers value immediately.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     Telegram Chat                         │
│                                                           │
│   /mode, /lang  → Inline Keyboard (existing, unchanged)  │
│   /settings     → "Open Settings" WebApp button           │
│                   + fallback inline keyboard for           │
│                     users on old clients                   │
└──────────┬───────────────────────────────┬───────────────┘
           │                               │
     Inline KB path                  Mini App path
     (no changes)                          │
                                           ▼
                              ┌─────────────────────────┐
                              │  FastAPI (same process)  │
                              │  Jinja2 + HTMX or       │
                              │  vanilla JS              │
                              │                          │
                              │  Pages:                  │
                              │  /app/settings — main    │
                              │  /app/oauth/cb — OAuth   │
                              └──────────┬──────────────┘
                                         │
                              ┌──────────▼──────────────┐
                              │     SQLite DB (shared)   │
                              └─────────────────────────┘
```

## What Moves to Mini App vs. What Stays

| Setting / Feature     | Current UI       | Proposed UI         | Why                                          |
|-----------------------|------------------|---------------------|----------------------------------------------|
| Mode (chat/transcribe/note) | Inline KB  | **Stays** inline KB | One-tap toggle, works perfectly              |
| Language (ru/en)      | Inline KB        | **Stays** inline KB | One-tap toggle, works perfectly              |
| LLM API Key          | FSM text input   | **Mini App**        | Secret input in chat is bad UX + security    |
| LLM Base URL         | FSM text input   | **Mini App**        | URL input needs validation + paste support   |
| LLM Model            | FSM text input   | **Mini App**        | Could be a searchable dropdown in future     |
| Yandex.Disk OAuth    | Deep link hack   | **Mini App**        | OAuth redirect works natively in web context |
| Yandex.Disk Path     | FSM text input   | **Mini App**        | Part of Yandex.Disk section                  |
| Obsidian Vault Path  | FSM text input   | **Mini App**        | Part of Obsidian section                     |
| Obsidian Inbox Folder| FSM text input   | **Mini App**        | Part of Obsidian section                     |
| /savedoc toggle      | Command          | **Stays** command   | Simple toggle                                |

## Tech Stack

| Layer     | Technology                                  |
|-----------|---------------------------------------------|
| Frontend  | Vanilla JS + Telegram Web App SDK           |
| Backend   | FastAPI (mounted in bot process)             |
| Auth      | Telegram initData HMAC validation            |
| Templates | Jinja2 (optional, can be pure static HTML)   |
| Styling   | Telegram CSS vars + ~100 lines custom CSS    |
| Deploy    | Same container, caddy/cloudflare for HTTPS   |

## Implementation Plan

### Phase 1: Minimal FastAPI API

Reuse the same API layer from Variant 1, but scope it to only settings that move to Mini App:

```python
# interfaces/webapp/app.py
from fastapi import FastAPI, Depends
from .auth import get_current_user
from .routes import settings, oauth

def create_webapp() -> FastAPI:
    app = FastAPI(title="Bot Settings MiniApp")
    app.include_router(settings.router, prefix="/api")
    app.include_router(oauth.router, prefix="/api/oauth")
    app.mount("/app", StaticFiles(directory="interfaces/webapp/static"), name="static")
    return app
```

### Phase 2: Static HTML Mini App (No Build Step)

Single HTML file with vanilla JS — simplest possible frontend:

```
interfaces/webapp/static/
  index.html          — Settings page (single file)
  style.css           — Minimal styles
```

```html
<!-- index.html — key structure -->
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <div id="app">
    <!-- LLM Section -->
    <section class="settings-section" id="llm-section">
      <h2 onclick="toggleSection('llm')">LLM API</h2>
      <div class="section-body">
        <div class="field">
          <label>API Key</label>
          <input type="password" id="llm_api_key" placeholder="sk-...">
          <button onclick="saveSetting('llm_api_key')">Save</button>
        </div>
        <div class="field">
          <label>Base URL</label>
          <input type="url" id="llm_base_url" placeholder="https://openrouter.ai/api/v1">
          <button onclick="saveSetting('llm_base_url')">Save</button>
        </div>
        <div class="field">
          <label>Model</label>
          <input type="text" id="llm_model" placeholder="qwen/qwen3-235b-a22b:free">
          <button onclick="saveSetting('llm_model')">Save</button>
        </div>
        <button class="reset-btn" onclick="resetSection('llm')">Reset to defaults</button>
      </div>
    </section>

    <!-- Yandex.Disk Section -->
    <section class="settings-section" id="yadisk-section">
      <h2 onclick="toggleSection('yadisk')">Yandex.Disk</h2>
      <div class="section-body">
        <div id="oauth-status"></div>
        <button id="oauth-btn" onclick="handleOAuth()">Connect</button>
        <div class="field">
          <label>Path</label>
          <input type="text" id="yadisk_path">
          <button onclick="saveSetting('yadisk_path')">Save</button>
        </div>
      </div>
    </section>

    <!-- Obsidian Section -->
    <section class="settings-section" id="obsidian-section">
      <h2 onclick="toggleSection('obsidian')">Obsidian</h2>
      <div class="section-body">
        <div class="field">
          <label>Vault Path</label>
          <input type="text" id="obsidian_vault_path">
          <button onclick="saveSetting('obsidian_vault_path')">Save</button>
        </div>
        <div class="field">
          <label>Inbox Folder</label>
          <input type="text" id="obsidian_inbox_folder">
          <button onclick="saveSetting('obsidian_inbox_folder')">Save</button>
        </div>
        <button class="reset-btn" onclick="resetSection('obsidian')">Reset</button>
      </div>
    </section>
  </div>

  <script>
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();

    const API = '/api';
    const headers = {
      'Content-Type': 'application/json',
      'X-Telegram-Init-Data': tg.initData
    };

    // Load settings on open
    fetch(`${API}/settings`, { headers })
      .then(r => r.json())
      .then(data => populateFields(data));

    async function saveSetting(key) {
      const input = document.getElementById(key);
      const res = await fetch(`${API}/settings/${key}`, {
        method: 'PUT', headers,
        body: JSON.stringify({ value: input.value })
      });
      if (res.ok) {
        tg.HapticFeedback.notificationOccurred('success');
        tg.showAlert('Saved!');
      }
    }
    // ... more functions
  </script>
</body>
</html>
```

### Phase 3: Update /settings Command (Dual Mode)

```python
# interfaces/telegram/handlers/commands.py — modified /settings
async def cmd_settings(message: Message, state: FSMContext):
    locale = get_user_locale(message.from_user.id)

    # Try to show Mini App button (works on TG 6.9+)
    webapp_btn = InlineKeyboardButton(
        text=t("settings.open_webapp", locale),
        web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/app/")
    )
    # Fallback: existing inline keyboard for older clients
    fallback_kb = _main_kb(locale)

    # Show both options
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [webapp_btn],
        *fallback_kb.inline_keyboard  # existing submenu buttons below
    ])

    await message.answer(t("settings.menu_title", locale), reply_markup=kb)
```

### Phase 4: OAuth in Web Context

The OAuth flow becomes much cleaner:

```
1. User opens Mini App → sees "Connect Yandex.Disk" button
2. Clicks → JS calls GET /api/oauth/yandex/url
3. Opens URL via Telegram.WebApp.openLink(oauthUrl) → external browser
4. User authorizes on Yandex
5. Redirect to https://your-domain.com/api/oauth/yandex/callback
6. Server exchanges code, stores token, renders "Success! Close this tab." page
7. User switches back to Telegram (Mini App is still open)
8. Mini App detects return via document.visibilitychange → re-fetches settings
```

**Note:** `openLink()` opens an external browser, not an iframe. The callback page cannot send data back to the Mini App directly. Use `visibilitychange` event to trigger a settings refresh when the user returns.

### Phase 5: Deprecation Path for Inline KB Settings

```
Month 1: Ship Mini App + keep inline KB (/settings shows both)
Month 2: Track usage — if >80% use Mini App, make it default
Month 3: Remove inline KB settings handlers, keep /mode and /lang as-is
```

## Pros

- **Lowest risk** — existing flows stay intact, Mini App is additive
- **Incremental** — can ship in stages (LLM first, then OAuth, then Obsidian)
- **Fallback** — users on old Telegram clients still have inline KB
- **No build step** — vanilla JS, no Node.js dependency
- **Single deployment** — same container as bot
- **Best of both worlds** — quick toggles via inline KB, complex forms in Mini App
- **No breaking changes** — all existing handlers continue working

## Additional Concerns

### i18n
- Read `Telegram.WebApp.initDataUnsafe.user.language_code` or fetch from API
- Embed a small strings object in JS (subset of `locales/*.json`) — only ~20 keys needed for settings UI

### Privileged Keys
API must check `ALLOWED_USER_IDS` for `obsidian_vault_path` — same restriction as in bot handlers.

### Cloudflare WARP
Current Docker uses WARP for outbound. The FastAPI server needs separate inbound HTTPS exposure (Caddy/Cloudflare Tunnel), independent of WARP.

## Cons

- **Split UX** — settings in two places (Mini App + inline KB) during transition
- **Vanilla JS** — less structured than React; may get messy if scope grows
- **Still needs HTTPS** — domain + TLS required for Mini App URL
- **Limited scope** — intentionally minimal; if you want a dashboard later, need to rethink

## Effort Estimate

- FastAPI API (scoped to settings): ~0.5 day
- Static HTML Mini App: ~1 day
- Auth middleware: ~0.5 day
- OAuth flow adaptation: ~0.5 day
- /settings dual-mode + testing: ~0.5 day
- HTTPS setup: ~0.5 day
- **Total: ~3 days**

## When to Choose This Variant

- Want minimal disruption to existing users
- Need to ship quickly with low risk
- Settings scope is unlikely to grow significantly
- No frontend toolchain/expertise on team
- Want a graceful deprecation path for inline KB
