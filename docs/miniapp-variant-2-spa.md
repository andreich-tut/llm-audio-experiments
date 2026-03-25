# Variant 2: Modern SPA — React/Solid + FastAPI (Two Services)

![UI Design](tg-app-ui.png)

## Summary

Build a proper single-page application for the Mini App frontend, with a dedicated FastAPI backend. The frontend is a standalone build artifact (static files) served via CDN or static hosting. The backend API is a separate service that shares the database with the bot.

## Architecture

```
┌────────────────────┐     ┌──────────────────────────────┐
│  Telegram Client   │     │     Static Hosting           │
│                    │     │  (Cloudflare Pages / Vercel  │
│  Mini App WebView ─┼────►│   / GitHub Pages / nginx)    │
│                    │     │                              │
│                    │     │  React/Solid SPA bundle      │
└────────┬───────────┘     └──────────────────────────────┘
         │                              │
         │  initData in headers         │ fetch() calls
         │                              ▼
         │              ┌───────────────────────────────┐
         │              │   FastAPI Backend              │
         │              │   /api/v1/settings/*           │
         │              │   /api/v1/oauth/*              │
         │              │   initData HMAC validation     │
         │              └───────────┬───────────────────┘
         │                          │
┌────────▼───────────┐    ┌────────▼──────────┐
│  aiogram Bot       │    │   SQLite DB       │
│  (polling)         │    │   (shared volume) │
└────────────────────┘    └───────────────────┘
```

## Tech Stack

| Layer     | Technology                                          |
|-----------|-----------------------------------------------------|
| Frontend  | React 19 (or SolidJS) + TypeScript + Vite           |
| UI Kit    | @vkruglikov/react-telegram-web-app or Telegram UI   |
| Backend   | FastAPI + Pydantic v2                               |
| Auth      | Telegram `initData` HMAC in middleware               |
| Styling   | Tailwind CSS + Telegram CSS vars                    |
| Deploy    | Static hosting (frontend) + same VPS (API)          |

## Implementation Plan

### Phase 1: FastAPI Backend

```
interfaces/webapp/
  __init__.py
  app.py              — FastAPI app factory with CORS
  auth.py             — initData validation middleware
  dependencies.py     — Depends() for current_user
  routes/
    settings.py       — CRUD endpoints
    oauth.py          — Yandex OAuth endpoints
  schemas.py          — Pydantic request/response models
```

**API Design:**

```
GET    /api/v1/settings              → {settings: {key: value, ...}, oauth: {yandex: {connected, login}}}
PUT    /api/v1/settings/{key}        → {key, value, saved: true}
DELETE /api/v1/settings/{key}        → {key, deleted: true}
POST   /api/v1/settings/reset/{section} → {section, cleared: true}

GET    /api/v1/oauth/yandex/url      → {url: "https://oauth.yandex.ru/..."}
POST   /api/v1/oauth/yandex/exchange → {connected: true, login: "user@yandex.ru"}
DELETE /api/v1/oauth/yandex          → {disconnected: true}
```

**Pydantic Schemas:**

```python
class SettingsResponse(BaseModel):
    settings: dict[str, str | None]  # masked secrets
    oauth: dict[str, OAuthStatus]

class OAuthStatus(BaseModel):
    connected: bool
    login: str | None = None

class SettingUpdate(BaseModel):
    value: str = Field(max_length=500)

class SettingKey(str, Enum):
    llm_api_key = "llm_api_key"
    llm_base_url = "llm_base_url"
    llm_model = "llm_model"
    yadisk_path = "yadisk_path"
    obsidian_vault_path = "obsidian_vault_path"
    obsidian_inbox_folder = "obsidian_inbox_folder"
```

### Phase 2: React Frontend

```
webapp/
  package.json
  vite.config.ts
  tsconfig.json
  src/
    main.tsx
    App.tsx
    api/
      client.ts       — fetch wrapper with initData auth header
      settings.ts     — API functions
    components/
      SettingsPage.tsx — Main page with sections
      Section.tsx      — Collapsible section component
      SettingField.tsx  — Editable field (text, secret, readonly)
      OAuthButton.tsx   — Connect/disconnect Yandex
    hooks/
      useTelegram.ts   — WebApp SDK wrapper (theme, haptics, back button)
      useSettings.ts   — Settings state management (SWR/TanStack Query)
    types.ts
    theme.css          — Telegram CSS vars mapping
```

**Auth in API calls:**

```typescript
// api/client.ts
const tg = window.Telegram.WebApp;

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": tg.initData,  // HMAC-validated server-side
      ...options?.headers,
    },
  });
  if (!res.ok) throw new ApiError(res.status, await res.json());
  return res.json();
}
```

**Component structure:**

```tsx
// App.tsx — simplified
function App() {
  const { settings, update, remove, resetSection } = useSettings();
  const { haptic, showBackButton } = useTelegram();

  return (
    <div className="settings-page">
      <Section title="LLM API" id="llm">
        <SettingField label="API Key" settingKey="llm_api_key" secret onSave={update} />
        <SettingField label="Base URL" settingKey="llm_base_url" onSave={update} />
        <SettingField label="Model" settingKey="llm_model" onSave={update} />
        <ResetButton section="llm" onReset={resetSection} />
      </Section>

      <Section title="Yandex.Disk" id="yadisk">
        <OAuthButton provider="yandex" />
        <SettingField label="Path" settingKey="yadisk_path" onSave={update} />
      </Section>

      <Section title="Obsidian" id="obsidian">
        <SettingField label="Vault Path" settingKey="obsidian_vault_path" onSave={update} />
        <SettingField label="Inbox Folder" settingKey="obsidian_inbox_folder" onSave={update} />
        <ResetButton section="obsidian" onReset={resetSection} />
      </Section>
    </div>
  );
}
```

### Phase 3: Telegram Web App SDK Integration

```typescript
// hooks/useTelegram.ts
export function useTelegram() {
  const tg = window.Telegram.WebApp;

  useEffect(() => {
    tg.ready();
    tg.expand();  // full-height Mini App
    tg.BackButton.show();
    tg.BackButton.onClick(() => tg.close());
  }, []);

  return {
    user: tg.initDataUnsafe.user,
    colorScheme: tg.colorScheme,
    haptic: tg.HapticFeedback,
    close: () => tg.close(),
    themeParams: tg.themeParams,
  };
}
```

### Phase 4: OAuth in Mini App

```
1. User taps "Connect Yandex.Disk"
2. Frontend calls GET /api/v1/oauth/yandex/url
3. Receives OAuth URL, opens via Telegram.WebApp.openLink(url) → external browser
4. User authorizes in browser
5. Yandex redirects to https://your-domain.com/api/v1/oauth/yandex/callback?code=...&state=...
6. Server exchanges code, stores token, renders "Success! Close this tab." page
7. User returns to Mini App (still open in TG)
8. Mini App detects return via document.visibilitychange → re-fetches settings
```

**Important:** `openLink()` opens an external browser — the callback page cannot communicate back to the Mini App webview. The SPA must poll or use `visibilitychange` to detect when the user returns and refresh OAuth status.

Alternative: use `Telegram.WebApp.openTelegramLink()` to redirect back to bot deep link (preserves current flow but hybrid approach).

### Phase 5: Build & Deployment

```yaml
# docker-compose.yml
services:
  bot:
    build: .
    volumes:
      - ./data:/app/data

  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    volumes:
      - ./data:/app/data  # shared SQLite
    ports:
      - "8080:8080"

  caddy:
    image: caddy:2
    ports:
      - "443:443"
    volumes:
      - ./webapp/dist:/srv/webapp  # static SPA files
      - ./Caddyfile:/etc/caddy/Caddyfile
```

Or deploy frontend to **Cloudflare Pages** / **Vercel** (free tier, global CDN):

```bash
# Build and deploy
cd webapp && npm run build
npx wrangler pages deploy dist  # Cloudflare Pages
```

### Phase 6: Bot Integration

```python
# In bot.py or commands.py — add Mini App button
from aiogram.types import MenuButtonWebApp, WebAppInfo

await bot.set_chat_menu_button(
    menu_button=MenuButtonWebApp(
        text="Settings",
        web_app=WebAppInfo(url="https://miniapp.yourdomain.com/")
    )
)

# OR: send as inline button in /settings command response
InlineKeyboardButton(
    text="Open Settings",
    web_app=WebAppInfo(url="https://miniapp.yourdomain.com/")
)
```

## Pros

- **Rich UX** — instant UI updates, animations, validation feedback
- **Offline-capable** — SPA can cache settings locally, sync on reconnect
- **Scalable** — frontend on CDN, API horizontally scalable
- **Type-safe** — TypeScript frontend + Pydantic backend
- **Extensible** — easy to add new settings sections, wizards, previews
- **Modern DX** — hot reload, component-based, testable
- **Better OAuth** — proper redirect flow within web context

## Additional Concerns

### CORS
If the SPA is served from a different origin than the API (e.g., `miniapp.yourdomain.com` vs `api.yourdomain.com`), FastAPI needs CORS middleware:
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["https://miniapp.yourdomain.com"], ...)
```
Alternatively, serve both under the same domain via Caddy path routing to avoid CORS entirely.

### i18n
- Read `Telegram.WebApp.initDataUnsafe.user.language_code` on init
- Or fetch saved language from API, load matching string bundle
- Can reuse existing `locales/ru.json` / `en.json` (import as JSON modules in Vite)

### Privileged Keys
API must enforce `obsidian_vault_path` restriction to `ALLOWED_USER_IDS`, same as the bot handler.

### SQLite WAL Mode
Must enable WAL mode for concurrent access from bot + API processes:
```python
# In database init
async with engine.begin() as conn:
    await conn.execute(text("PRAGMA journal_mode=WAL"))
```

## Cons

- **JS toolchain required** — Node.js, npm, Vite build step
- **Two services** — separate frontend + API deployment
- **More complexity** — React, TypeScript, state management
- **SQLite concurrency** — shared DB between bot and API (WAL mode required)
- **HTTPS + domain** — need domain + TLS for both API and Mini App
- **Maintenance overhead** — two codebases (Python + TypeScript)
- **CORS** — cross-origin setup needed if SPA and API on different domains

## Effort Estimate

- FastAPI backend + auth: ~1 day
- React SPA scaffold + components: ~2 days
- Telegram SDK integration + theming: ~0.5 day
- OAuth flow in Mini App: ~0.5 day
- Build pipeline + deployment: ~1 day
- **Total: ~5 days**

## When to Choose This Variant

- Planning to expand Mini App beyond just settings (usage stats, history viewer, etc.)
- Have frontend experience or want polished, app-like UX
- User base is growing, need CDN-served frontend
- Want to add features like model picker with search, API key validation, etc.
