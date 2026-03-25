# Mini App Migration: Variant Comparison

## Side-by-Side Comparison

| Criteria                  | V1: HTMX + FastAPI     | V2: React SPA + API     | V3: Hybrid (incremental) |
|---------------------------|------------------------|-------------------------|--------------------------|
| **Effort**                | ~3 days                | ~5 days                 | ~3 days                  |
| **Frontend toolchain**    | None (Python only)     | Node.js + Vite + TS     | None (vanilla JS)        |
| **Services to deploy**    | 1 (bot + web)          | 2-3 (bot + API + CDN)   | 1 (bot + web)            |
| **UX quality**            | Good (SSR + HTMX)      | Excellent (SPA)         | Good (simple forms)      |
| **Existing KB preserved** | No (full replacement)  | No (full replacement)   | Yes (dual mode)          |
| **Risk level**            | Medium                 | Medium-High             | Low                      |
| **Scalability**           | Low-Medium             | High                    | Low-Medium               |
| **Future extensibility**  | Medium                 | High                    | Low                      |
| **Offline support**       | No                     | Possible (PWA)          | No                       |
| **SQLite concurrency**    | Same process (safe)    | Shared file (WAL mode)  | Same process (safe)      |
| **Team skill required**   | Python                 | Python + TypeScript     | Python + basic JS        |
| **Maintenance burden**    | Low                    | Medium-High             | Lowest                   |

## Common Requirements (All Variants)

All three variants share these mandatory components:

### 1. HTTPS Domain
Telegram Mini Apps require HTTPS. Options:
- **Caddy** (auto-TLS, simplest) — add to existing Docker setup
- **Cloudflare Tunnel** — zero port exposure, free, works behind NAT
- **nginx + certbot** — most common, more config

### 2. Telegram initData Validation
Server-side HMAC-SHA256 validation of `Telegram.WebApp.initData`. This is the auth layer — no sessions, no cookies. Implementation is identical across all variants (~30 lines of Python).

### 3. BotFather Configuration
- Set Mini App URL via BotFather or `bot.set_chat_menu_button()`
- Can also be sent as `WebAppInfo` in inline keyboard buttons

### 4. API Layer
REST endpoints for settings CRUD. The application layer (`application/user_settings.py`, `application/oauth_state.py`) is reused directly — only a thin HTTP adapter is needed.

### 5. OAuth Flow Modernization
All variants improve the current deep-link OAuth hack. The web context allows proper HTTP redirects, which is cleaner and more reliable.

## Decision Matrix

**Choose V1 (HTMX)** if:
- You want a complete Mini App with Python-only stack
- Settings will be the main (only) Mini App feature
- You value simplicity and fast iteration

**Choose V2 (React SPA)** if:
- You plan to expand the Mini App (usage stats, conversation viewer, admin panel)
- You have or want frontend TypeScript experience
- You need polished, app-like interactions (animations, instant feedback)

**Choose V3 (Hybrid)** if:
- You want the lowest risk, most incremental path
- Backward compatibility with old Telegram clients matters
- You want to validate the Mini App concept before committing fully

## Recommendation

**Start with Variant 3 (Hybrid)**, then evolve to Variant 1 or 2 based on needs:

```
Phase 1 (now):     V3 — Ship Mini App for LLM/OAuth/Obsidian settings
                        Keep inline KB for mode/language
                        Validate UX, gather feedback

Phase 2 (if Mini App works well):
  Option A:        V1 — Expand HTMX Mini App, drop inline KB for settings
  Option B:        V2 — Rebuild as React SPA if planning dashboard/admin features

Phase 3 (mature):  Full Mini App with settings + usage stats + conversation history
```

This gives you:
- **Immediate value** with minimal risk (V3)
- **Data-driven decision** on whether to invest in full SPA (V2) or keep it simple (V1)
- **No wasted work** — the FastAPI API layer from V3 is reused in V1 or V2

## Key Technical Decisions to Make Early

1. **Domain**: Do you have a domain for the Mini App HTTPS URL? (e.g., `bot.yourdomain.com`)
2. **HTTPS strategy**: Caddy (simplest), Cloudflare Tunnel (no port opening), or nginx?
3. **Same process or separate?**: Mounting FastAPI in the bot process is simpler but couples them
4. **SQLite WAL mode**: Already enabled? Needed if API runs in a separate process

## Gotchas Discovered During Review

1. **OAuth `openLink()` limitation**: `Telegram.WebApp.openLink()` opens an external browser, not an in-app webview. The OAuth callback page cannot communicate back to the Mini App. Solution: use `document.visibilitychange` event to detect when user returns and re-fetch OAuth status.

2. **Cloudflare WARP**: The bot's Docker container uses WARP for outbound traffic. The FastAPI web server needs independent inbound HTTPS exposure — WARP doesn't help with serving incoming requests.

3. **i18n**: The bot is bilingual (ru/en). The Mini App needs to support both languages too — read from `Telegram.WebApp.initDataUnsafe.user.language_code` or from user's saved preference.

4. **Privileged keys**: `obsidian_vault_path` is restricted to `ALLOWED_USER_IDS` in the bot. The API layer must enforce the same restriction.

5. **CORS** (V2 only): If SPA and API are on different origins, CORS middleware is required. Avoidable by routing both through the same domain via reverse proxy.
