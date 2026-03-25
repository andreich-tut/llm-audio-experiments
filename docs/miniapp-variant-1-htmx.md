# Variant 1: Minimal — HTMX + FastAPI (Single Service)

## Summary

Add a lightweight web layer to the existing bot process. FastAPI serves Jinja2 templates with HTMX for interactivity. No JS build step, no separate deployment. The Mini App runs inside the same Docker container as the bot.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Docker Container                     │
│                                                      │
│  ┌──────────────┐       ┌─────────────────────────┐ │
│  │  aiogram Bot  │       │  FastAPI (uvicorn)      │ │
│  │  (polling)    │       │  /api/settings/*        │ │
│  │               │       │  /app/settings (HTML)   │ │
│  └──────┬───────┘       └──────────┬──────────────┘ │
│         │                          │                 │
│         └──────────┬───────────────┘                 │
│                    │                                  │
│            ┌───────▼───────┐                         │
│            │  SQLite DB    │                          │
│            │  (shared)     │                          │
│            └───────────────┘                         │
└─────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer     | Technology                                     |
|-----------|------------------------------------------------|
| Frontend  | Jinja2 templates + HTMX + Telegram Web App SDK |
| Backend   | FastAPI (mounted in same process or separate)  |
| Auth      | Telegram `initData` HMAC validation            |
| Styling   | Telegram CSS vars (`var(--tg-theme-*)`) + minimal CSS |
| Deploy    | Same Docker container, nginx/caddy for HTTPS   |

## Implementation Plan

### Phase 1: Backend API (REST endpoints)

Add `interfaces/webapp/` directory:

```
interfaces/webapp/
  __init__.py
  app.py            — FastAPI app factory
  auth.py           — Telegram initData HMAC validation
  routes/
    settings.py     — GET/PUT/DELETE /api/settings/{key}
    oauth.py        — GET /api/oauth/url, POST /api/oauth/callback
  templates/
    base.html       — Layout with TG Web App SDK + HTMX
    settings.html   — Main settings page
    partials/
      llm.html      — LLM settings section (HTMX partial)
      yadisk.html   — Yandex.Disk section
      obsidian.html — Obsidian section
  static/
    style.css       — Minimal styles using TG CSS vars
```

**API Endpoints:**

```
GET    /api/settings              → all user settings (masked secrets)
GET    /api/settings/{key}        → single setting value
PUT    /api/settings/{key}        → update setting (body: {value: "..."})
DELETE /api/settings/{key}        → clear setting
DELETE /api/settings/section/{name} → reset section (llm/yadisk/obsidian)
GET    /api/oauth/yandex/url      → generate OAuth URL
POST   /api/oauth/yandex/callback → exchange code for token
DELETE /api/oauth/yandex           → disconnect
GET    /app/settings              → serve HTML page
```

### Phase 2: Telegram initData Auth

```python
# interfaces/webapp/auth.py
import hashlib, hmac, json, time
from urllib.parse import parse_qs

def validate_init_data(init_data: str, bot_token: str, max_age: int = 86400) -> dict:
    """Validate Telegram Mini App initData and return user dict."""
    parsed = dict(parse_qs(init_data, keep_blank_values=True))
    hash_value = parsed.pop("hash", [None])[0]
    if not hash_value:
        raise ValueError("Missing hash")

    # Build check string
    data_check = "\n".join(
        f"{k}={v[0]}" for k, v in sorted(parsed.items())
    )

    # HMAC-SHA256: secret = HMAC("WebAppData", bot_token)
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed, hash_value):
        raise ValueError("Invalid hash")

    # Check auth_date freshness
    auth_date = int(parsed.get("auth_date", [0])[0])
    if time.time() - auth_date > max_age:
        raise ValueError("Data expired")

    return json.loads(parsed["user"][0])
```

### Phase 3: Frontend (Jinja2 + HTMX)

The HTML page uses:
- **Telegram Web App SDK** (`telegram-web-app.js`) for theme, closing, haptic feedback
- **HTMX** for partial page updates without full reload
- **Telegram CSS variables** for native look and feel

```html
<!-- templates/base.html -->
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<script src="https://unpkg.com/htmx.org@2"></script>
<style>
  body {
    font-family: var(--tg-font);
    background: var(--tg-theme-bg-color);
    color: var(--tg-theme-text-color);
  }
  .btn { background: var(--tg-theme-button-color); color: var(--tg-theme-button-text-color); }
  .input { background: var(--tg-theme-secondary-bg-color); }
</style>
```

Key UX patterns:
- Accordion sections for LLM / Yandex.Disk / Obsidian
- Inline edit fields — click value to edit, Enter to save
- Secret fields shown masked, editable with "Change" button
- OAuth button opens Yandex login in external browser, returns via deep link
- `Telegram.WebApp.MainButton` for "Save All" or "Close"
- Haptic feedback on save/error via `Telegram.WebApp.HapticFeedback`

### Phase 4: Integration with Bot

In `bot.py`, mount FastAPI alongside aiogram:

```python
from interfaces.webapp.app import create_webapp

# Option A: Run both in same process
webapp = create_webapp()
# Start uvicorn in background task alongside aiogram polling

# Option B: Separate process (docker-compose)
# webapp runs as separate service sharing the DB volume
```

Register Mini App button via BotFather or send as `MenuButtonWebApp`:

```python
from aiogram.types import MenuButtonWebApp, WebAppInfo

await bot.set_chat_menu_button(
    menu_button=MenuButtonWebApp(
        text="Settings",
        web_app=WebAppInfo(url="https://your-domain.com/app/settings")
    )
)
```

### Phase 5: HTTPS & Deployment

Options for HTTPS (required by Telegram for Mini Apps):

1. **Caddy reverse proxy** (recommended) — auto-TLS, minimal config
2. **Cloudflare Tunnel** — no port opening needed, free
3. **nginx + certbot** — classic approach

```
# Caddyfile example
bot.yourdomain.com {
    reverse_proxy localhost:8080
}
```

## OAuth Flow Change

Current flow uses deep links (`/start oauth_<code>_<state>`). With Mini App:

```
1. User clicks "Login with Yandex" in Mini App
2. Mini App calls GET /api/oauth/yandex/url → returns OAuth URL + state token
3. Mini App opens URL via Telegram.WebApp.openLink() → opens in external browser
4. User authorizes → Yandex redirects to https://your-domain.com/api/oauth/yandex/callback?code=...&state=...
5. Server exchanges code, stores token, renders "Success! You can close this tab." page
6. User returns to Mini App (still open in TG), Mini App polls GET /api/oauth/yandex/status
   or re-fetches settings on visibility change (document.visibilitychange event)
```

**Note:** `openLink()` opens an external browser tab, not an iframe within the Mini App. The callback page cannot close the Mini App or communicate with it directly. The Mini App must detect the user's return (via `visibilitychange`) and re-fetch OAuth status.

## Additional Concerns

### i18n in Mini App
The bot supports ru/en. The Mini App should respect user's language preference:
- Read `Telegram.WebApp.initDataUnsafe.user.language_code` on init
- Or fetch user's saved language from `GET /api/settings`
- Load appropriate strings (can reuse `locales/ru.json` / `en.json` or embed a subset)

### Privileged Keys
The API must enforce the same access control as the bot:
- `obsidian_vault_path` is restricted to users in `ALLOWED_USER_IDS`
- Check in the PUT endpoint, return 403 for unauthorized users

### Cloudflare WARP Compatibility
The current Docker setup uses Cloudflare WARP for outbound traffic. The FastAPI web server needs its own inbound HTTPS exposure (separate from WARP). Ensure the Caddy/nginx reverse proxy is configured independently.

## Pros

- **No JS build step** — just HTML/Jinja2 + HTMX (CDN)
- **Single deployment** — same Docker container, shared DB
- **Python-only** — no Node.js, npm, or frontend toolchain
- **Fast to implement** — reuse existing application layer directly
- **Native feel** — Telegram CSS vars match user's theme
- **Better OAuth UX** — proper redirect instead of deep links

## Cons

- **SSR latency** — each interaction round-trips to server (mitigated by HTMX partials)
- **Limited interactivity** — complex UI patterns harder without JS framework
- **Scaling** — single process serves both bot + web (fine for small user base)
- **HTTPS requirement** — need domain + TLS certificate (new infra)

## Effort Estimate

- Backend API + auth: ~1 day
- Templates + HTMX: ~1 day
- OAuth flow adaptation: ~0.5 day
- HTTPS setup + deployment: ~0.5 day
- **Total: ~3 days**

## When to Choose This Variant

- Small user base (< 100 users)
- Want to ship fast with minimal new tooling
- Team is Python-focused, no frontend expertise
- Settings UI is relatively simple (forms, toggles, OAuth)
