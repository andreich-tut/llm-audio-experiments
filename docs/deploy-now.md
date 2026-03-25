# Deploy to VPS

## Prerequisites
- VPS with Docker installed
- Domain pointing to VPS IP (A record)
- Existing `.env` on the VPS

---

## One-time setup

### 1. Local — push changes

```bash
git push
```

### 2. VPS — pull and stop old container

```bash
cd /path/to/bot
git pull
docker stop tg-voice && docker rm tg-voice
```

### 3. VPS — add domain to `.env`

```bash
echo "DOMAIN=yourdomain.com" >> .env
```

### 4. Build the React frontend

**If Node.js is on the VPS:**
```bash
bash docker/build-webapp.sh
```

**If not — build locally and copy:**
```bash
# local
cd webapp && npm install && npm run build && cd ..
rsync -av webapp/dist/ user@yourserver:/path/to/bot/webapp/dist/
```

### 5. Start everything

```bash
bash docker/start.sh
```

Starts three containers: `bot`, `api`, `caddy`.
Caddy auto-provisions TLS once DNS resolves.

### 6. Register Mini App with BotFather

```
/newapp → pick your bot → URL: https://yourdomain.com
```

---

## Subsequent deploys

```bash
git pull
bash docker/update.sh        # after bot or api changes
bash docker/deploy.sh        # after frontend changes (rebuilds webapp too)
```
