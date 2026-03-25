# Mini App Implementation Plan

Based on [miniapp-variant-2-spa.md](miniapp-variant-2-spa.md).

## Status

- [x] FastAPI backend (`interfaces/webapp/`)
- [x] React SPA (`webapp/`)
- [x] Docker setup (`docker/docker-compose.yml`, `docker/Dockerfile.api`)
- [x] Caddy reverse proxy (`Caddyfile`)
- [ ] VPS deployment
- [ ] BotFather Mini App registration

---

## What was built

### Backend — `interfaces/webapp/`

| File | Purpose |
|------|---------|
| `auth.py` | Telegram `initData` HMAC-SHA256 validation |
| `dependencies.py` | `get_current_user_id`, `get_database` Depends() |
| `schemas.py` | Pydantic models, `SECTION_KEYS`, `SECRET_KEYS`, `PRIVILEGED_KEYS` |
| `routes/settings.py` | `GET/PUT/DELETE /api/v1/settings/{key}`, `POST /api/v1/settings/reset/{section}` |
| `routes/oauth.py` | Yandex OAuth URL gen, code exchange, disconnect |
| `app.py` | FastAPI factory with CORS and lifespan `init_db`/`close` |

`app_runner.py` (project root) — uvicorn entrypoint for local dev.

### Frontend — `webapp/`

| File | Purpose |
|------|---------|
| `src/api/client.ts` | `fetch` wrapper injecting `X-Telegram-Init-Data` header |
| `src/api/settings.ts` | Typed API functions |
| `src/hooks/useTelegram.ts` | SDK init: `ready()`, `expand()`, back button |
| `src/hooks/useSettings.ts` | TanStack Query with `update`/`remove`/`resetSection` |
| `src/components/SettingField.tsx` | Inline edit, secret masking, Save/Clear |
| `src/components/Section.tsx` | Card with title and Reset button |
| `src/components/OAuthButton.tsx` | Connect/Disconnect + `visibilitychange` re-fetch |
| `src/components/SettingsPage.tsx` | LLM / Yandex.Disk / Obsidian sections |
| `src/theme.css` | Telegram CSS vars (`--tg-theme-*`) |

### Deployment — `docker/`

| File | Purpose |
|------|---------|
| `Dockerfile.api` | Slim Python image for FastAPI |
| `docker-compose.yml` | `bot` + `api` + `caddy` services |
| `start.sh` | `docker compose up -d --build` |
| `update.sh` | Rebuild + restart + image prune |
| `deploy.sh` | Build webapp + `update.sh` |
| `build-webapp.sh` | `npm install && npm run build` |

`Caddyfile` (project root) — `/api/*` → `api:8080`, all else → SPA with fallback to `index.html`.

---

## Key decisions

- **OAuth flow** reuses the existing Telegram deep-link approach (`https://t.me/<bot>?start=oauth_...`) — no new redirect URI needed in the Yandex app
- **Shared database** — both `bot` and `api` mount `./data` volume (same SQLite file)
- **Bot username** — resolved once at runtime via `GET /bot{token}/getMe` and cached
- **`obsidian_vault_path`** is a privileged key — only writable by `ALLOWED_USER_IDS`
- **Secret masking** — `llm_api_key` is stored encrypted and returned as `****` in GET responses

---

## VPS deployment steps

```bash
# 1. Local — push code
git push

# 2. VPS — pull and remove old standalone container
git pull
docker stop tg-voice && docker rm tg-voice

# 3. VPS — set domain in .env
echo "DOMAIN=yourdomain.com" >> .env

# 4. Build frontend (on VPS if Node installed, else build locally and rsync)
bash docker/build-webapp.sh
# or locally:
#   cd webapp && npm install && npm run build
#   rsync -av webapp/dist/ user@vps:/path/to/bot/webapp/dist/

# 5. Start all services
bash docker/start.sh

# 6. DNS — add A record: yourdomain.com → VPS IP
#    Caddy auto-provisions TLS once DNS resolves

# 7. BotFather — register Mini App
#    /newapp → your bot → URL: https://yourdomain.com
```

### Future updates

```bash
git pull
bash docker/update.sh       # bot or api code changes
bash docker/deploy.sh       # includes frontend rebuild
```

---

## Local development

```bash
# Backend
pip install -r requirements.txt
python app_runner.py          # FastAPI on :8080

# Frontend (proxies /api/* to :8080 via vite.config.ts)
cd webapp && npm install && npm run dev
```
