# Layered Architecture Refactoring Plan

## Overview

Refactor the bot from a simple layered structure to a clean **layered architecture** with clear separation of concerns.

**CRITICAL REQUIREMENT:** Each phase must result in a **fully working application** that can be deployed to production immediately.

---

## Progress Tracking

**IMPORTANT:** Every step must be documented in `REFACTOR_PROGRESS.md`

### Before Starting

```bash
# Create progress tracking file
cp REFACTOR_PROGRESS.md.example REFACTOR_PROGRESS.md
git add REFACTOR_PROGRESS.md
```

### After Each Step

**Update `REFACTOR_PROGRESS.md`:**
```markdown
## [Phase 1] Step 1.2: Move i18n

**Started:** 2024-03-24 10:00
**Completed:** 2024-03-24 10:15
**Status:** ✅ Done

**Changes:**
- Moved `core/i18n.py` → `shared/i18n.py`
- Updated imports in 15 files

**Testing:**
- ✅ `ruff check .` passed
- ✅ Bot starts successfully
- ✅ /start command works (ru/en)
- ✅ Language switching works

**Issues:** None

**Next:** Move keyboards
```

### Before Each Commit

```bash
# Update progress file
vim REFACTOR_PROGRESS.md

# Commit progress with code
git add REFACTOR_PROGRESS.md
git commit -m "refactor: Phase 1 Step 1.2 complete - moved i18n"
```

### Progress File Template

Create `REFACTOR_PROGRESS.md.example`:

```markdown
# Refactoring Progress Tracker

## Phase 1: shared/

**Started:** YYYY-MM-DD HH:MM
**Status:** In Progress / Complete / Skipped

### Step 1.1: Create directory
- [ ] Started
- [ ] Completed
- [ ] Tested
- [ ] Committed

### Step 1.2: Move i18n
- [ ] Started
- [ ] Completed
- [ ] Tested
- [ ] Committed
**Notes:** ...

### Step 1.3: Move keyboards
- [ ] Started
- [ ] Completed
- [ ] Tested
- [ ] Committed
**Notes:** ...

---

## Phase 2: infrastructure/

...
```

### Why Track Progress?

1. **Know exactly where you are** - Don't lose track mid-refactor
2. **Easy to resume** - Pick up where you left off
3. **Document issues** - Remember what problems you solved
4. **Time tracking** - Estimate future refactors better
5. **Team visibility** - Others can see progress

---

## Working Version Guarantee

**After EACH phase:**
- ✅ Bot starts successfully: `python bot.py`
- ✅ All commands work: `/start`, `/mode`, `/settings`, etc.
- ✅ All features functional: voice, YouTube, notes, chat
- ✅ Can deploy to production: `./update.sh`
- ✅ Can rollback safely if issues found
- ✅ Progress documented in `REFACTOR_PROGRESS.md`

**No broken states!** If a phase fails, rollback to previous working version.

---

## Current Problems

### Files Over 150 Lines (Need Splitting)

| Lines | File | Issue | Priority |
|-------|------|-------|----------|
| **540** | `state.py` | Database state + backward compat + sync wrappers | 🔴 Critical |
| **443** | `handlers/settings.py` | Too many handlers, keyboard builders | 🔴 Critical |
| **365** | `handlers/commands.py` | Too many command handlers | 🟡 High |
| **309** | `core/pipelines.py` | Business logic mixed with orchestration | 🔴 Critical |
| **257** | `tools/transcribe_diarize.py` | CLI tool (lower priority) | 🟢 Low |
| **194** | `services/llm.py` | Multiple LLM operations | 🟡 High |
| **186** | `services/yandex_oauth.py` | OAuth flow + token refresh | 🟡 Medium |
| **151** | `core/i18n.py` | i18n logic + locale detection | 🟡 Medium |

---

## Phase 1: Create `shared/` (Low Risk, 2 hours)

### Working State After Phase 1

```
✅ Bot starts and responds to all commands
✅ i18n works (ru/en languages)
✅ All keyboards render correctly
✅ Config loading unchanged
✅ Can deploy to production
✅ Rollback available if issues found
```

### Steps

**Step 1.1: Create directory**
```bash
mkdir -p shared
git add shared/__init__.py
```

**Step 1.2: Move files one by one (test after each)**

```bash
# Move i18n
cp core/i18n.py shared/i18n.py
# Update imports in ALL files
find . -name "*.py" -exec sed -i 's/from core\.i18n/from shared.i18n/g' {} \;
# TEST: python bot.py, send /start, check language works
git add shared/i18n.py && git commit -m "refactor: move i18n to shared/"

# Move keyboards
cp core/keyboards.py shared/keyboards.py
# Update imports
find . -name "*.py" -exec sed -i 's/from core\.keyboards/from shared.keyboards/g' {} \;
# TEST: python bot.py, send /mode, check keyboard renders
git add shared/keyboards.py && git commit -m "refactor: move keyboards to shared/"

# Move helpers
cp core/helpers.py shared/utils.py
# Update imports
find . -name "*.py" -exec sed -i 's/from core\.helpers/from shared.utils/g' {} \;
# TEST: python bot.py, send voice message
git add shared/utils.py && git commit -m "refactor: move helpers to shared/utils/"

# Move config (keep root copy)
cp config.py shared/config.py
# Add re-export to root config.py
echo "from shared.config import *" >> config.py
# TEST: python bot.py, check all env vars load
git add shared/config.py config.py && git commit -m "refactor: move config to shared/ with re-export"
```

**Step 1.3: Final testing**
```bash
# Run all checks
venv/bin/ruff check .
venv/bin/ruff format .

# Test bot
python bot.py
# In Telegram:
# - Send /start
# - Send /lang (switch ru/en)
# - Send /mode
# - Send voice message

# Deploy
./update.sh
docker logs -f tg-voice
```

### Rollback Plan

```bash
# If issues found at any step:
git stash  # or git reset --hard HEAD~N
# Bot continues working with old structure
```

---

## Phase 2: Create `infrastructure/` (Medium Risk, 4 hours)

### Working State After Phase 2

```
✅ Bot starts and responds to all commands
✅ LLM API calls work (OpenRouter/Groq)
✅ OAuth flow works (Yandex login)
✅ Yandex.Disk saves work
✅ Google Docs saves work
✅ Can deploy to production
✅ Rollback available if issues found
```

### Steps

**Step 2.1: Create directories**
```bash
mkdir -p infrastructure/{database,external_api,storage}
```

**Step 2.2: Move database (lowest risk)**
```bash
# Move db/ folder
mv db infrastructure/database
# Update imports
find . -name "*.py" -exec sed -i 's/from db\./from infrastructure.database./g' {} \;
find . -name "*.py" -exec sed -i 's/import db/from infrastructure import db/g' {} \;
# TEST: python bot.py, check state loads
git add infrastructure/database && git commit -m "refactor: move db to infrastructure/database/"
```

**Step 2.3: Move LLM client**
```bash
# Move and split
cp services/llm.py infrastructure/external_api/llm_client.py
# Update imports
find . -name "*.py" -exec sed -i 's/from services\.llm/from infrastructure.external_api.llm_client/g' {} \;
# TEST: python bot.py, send text message, check LLM responds
git add infrastructure/external_api/llm_client.py && git commit -m "refactor: move llm to infrastructure/external_api/"
```

**Step 2.4: Move other services**
```bash
# STT
cp services/stt.py infrastructure/external_api/groq_client.py
find . -name "*.py" -exec sed -i 's/from services\.stt/from infrastructure.external_api.groq_client/g' {} \;
git add infrastructure/external_api/groq_client.py && git commit -m "refactor: move stt to infrastructure/external_api/"

# Yandex OAuth
cp services/yandex_oauth.py infrastructure/external_api/yandex_client.py
find . -name "*.py" -exec sed -i 's/from services\.yandex_oauth/from infrastructure.external_api.yandex_client/g' {} \;
git add infrastructure/external_api/yandex_client.py && git commit -m "refactor: move yandex_oauth to infrastructure/"

# Obsidian
cp services/obsidian.py infrastructure/storage/obsidian.py
find . -name "*.py" -exec sed -i 's/from services\.obsidian/from infrastructure.storage.obsidian/g' {} \;
git add infrastructure/storage/obsidian.py && git commit -m "refactor: move obsidian to infrastructure/storage/"

# Google Docs
cp services/gdocs.py infrastructure/storage/gdocs.py
find . -name "*.py" -exec sed -i 's/from services\.gdocs/from infrastructure.storage.gdocs/g' {} \;
git add infrastructure/storage/gdocs.py && git commit -m "refactor: move gdocs to infrastructure/storage/"
```

**Step 2.5: Final testing**
```bash
# Run all checks
venv/bin/ruff check .

# Test bot
python bot.py
# In Telegram:
# - Send text message (LLM)
# - Send voice message (STT + LLM)
# - Test /settings → Yandex.Disk → OAuth login
# - Send note mode, verify Yandex.Disk save

# Deploy
./update.sh
docker logs -f tg-voice
```

### Rollback Plan

```bash
# If LLM calls fail:
git stash
# Bot reverts to Phase 1 state (still working)
```

---

## Phase 3: Create `application/` (Medium Risk, 4 hours)

### Working State After Phase 3

```
✅ Bot starts and responds to all commands
✅ User settings load/save correctly
✅ Conversation history works
✅ OAuth tokens persist correctly
✅ Free tier limits tracked
✅ Can deploy to production
✅ Rollback available if issues found
```

### Steps

**Step 3.1: Create directory**
```bash
mkdir -p application/services
```

**Step 3.2: Move state.py (keep backward compat)**
```bash
# Copy state.py
cp state.py application/state.py

# Add re-export to root state.py
cat >> state.py << 'EOF'

# Backward compatibility: re-export from application layer
from application.state import *  # noqa
EOF

# Update imports in other files
find . -name "*.py" -not -path "./state.py" -exec sed -i 's/^import state$/from application import state/g' {} \;
find . -name "*.py" -not -path "./state.py" -exec sed -i 's/^from state import/from application.state import/g' {} \;

# TEST: python bot.py, check state loads
git add application/state.py state.py && git commit -m "refactor: move state to application/ with re-export"
```

**Step 3.3: Move rate limiter**
```bash
cp services/limits.py application/services/rate_limiter.py
find . -name "*.py" -exec sed -i 's/from services\.limits/from application.services.rate_limiter/g' {} \;
git add application/services/rate_limiter.py && git commit -m "refactor: move limits to application/services/"
```

**Step 3.4: Final testing**
```bash
# Run all checks
venv/bin/ruff check .

# Test bot
python bot.py
# In Telegram:
# - Send /settings, change LLM model
# - Send multiple messages, check history
# - Test OAuth token persistence
# - Restart bot, verify data persists

# Deploy
./update.sh
docker logs -f tg-voice
```

### Rollback Plan

```bash
# If state management fails:
git stash
# Bot reverts to Phase 2 state (still working)
```

---

## Phase 4: Create `domain/` (High Risk, 8 hours)

### Working State After Phase 4

```
✅ Bot starts and responds to all commands
✅ Voice processing works
✅ YouTube download + summary works
✅ Note formatting works
✅ All business logic functional
✅ Can deploy to production
✅ Rollback available if issues found
```

### Steps

**Step 4.1: Create directories**
```bash
mkdir -p domain/{voice,youtube,notes,chat}
```

**Step 4.2: Move pipelines (core business logic)**
```bash
# Copy and split
cp core/pipelines.py domain/voice/pipeline.py

# Update imports
find . -name "*.py" -exec sed -i 's/from core\.pipelines/from domain.voice.pipeline/g' {} \;

# TEST: python bot.py, send voice message
git add domain/voice/pipeline.py && git commit -m "refactor: move pipelines to domain/voice/"
```

**Step 4.3: Move YouTube**
```bash
# Copy and split
cp services/youtube.py domain/youtube/downloader.py

# Update imports
find . -name "*.py" -exec sed -i 's/from services\.youtube/from domain.youtube.downloader/g' {} \;

# TEST: python bot.py, send YouTube link
git add domain/youtube/downloader.py && git commit -m "refactor: move youtube to domain/"
```

**Step 4.4: Final testing**
```bash
# Run all checks
venv/bin/ruff check .

# Test bot
python bot.py
# In Telegram:
# - Send voice message (full flow)
# - Send YouTube link (download + summary)
# - Test note mode (formatting)
# - Test all modes (chat/transcribe/note)

# Deploy
./update.sh
docker logs -f tg-voice
```

### Rollback Plan

```bash
# If business logic fails:
git stash
# Bot reverts to Phase 3 state (still working)
```

---

## Phase 5: Create `interfaces/` (High Risk, 6 hours)

### Working State After Phase 5

```
✅ Bot starts and responds to all commands
✅ All handlers work (commands, messages, settings)
✅ All callbacks work (YouTube, mode, lang)
✅ /settings menu navigation works
✅ Clean separation from business logic
✅ Can deploy to production
✅ Rollback available if issues found
```

### Steps

**Step 5.1: Create directories**
```bash
mkdir -p interfaces/telegram/handlers/{commands,settings}
```

**Step 5.2: Move bot.py**
```bash
cp bot.py interfaces/telegram/bot.py

# Update imports in new bot.py
# (handlers will import from new locations)

# Keep root bot.py as re-export
cat >> bot.py << 'EOF'

# Backward compatibility: re-export from interfaces layer
from interfaces.telegram.bot import *  # noqa
EOF

# TEST: python bot.py
git add interfaces/telegram/bot.py bot.py && git commit -m "refactor: move bot to interfaces/ with re-export"
```

**Step 5.3: Move handlers**
```bash
# Commands
cp handlers/commands.py interfaces/telegram/handlers/commands.py
find . -path "./handlers/*" -prune -o -name "*.py" -exec sed -i 's/from handlers\.commands/from interfaces.telegram.handlers.commands/g' {} \;
git add interfaces/telegram/handlers/commands.py && git commit -m "refactor: move commands to interfaces/"

# Messages
cp handlers/messages.py interfaces/telegram/handlers/messages.py
find . -path "./handlers/*" -prune -o -name "*.py" -exec sed -i 's/from handlers\.messages/from interfaces.telegram.handlers.messages/g' {} \;
git add interfaces/telegram/handlers/messages.py && git commit -m "refactor: move messages to interfaces/"

# Settings
cp handlers/settings.py interfaces/telegram/handlers/settings.py
find . -path "./handlers/*" -prune -o -name "*.py" -exec sed -i 's/from handlers\.settings/from interfaces.telegram.handlers.settings/g' {} \;
git add interfaces/telegram/handlers/settings.py && git commit -m "refactor: move settings to interfaces/"

# YouTube callbacks
cp handlers/youtube_callbacks.py interfaces/telegram/handlers/youtube.py
find . -path "./handlers/*" -prune -o -name "*.py" -exec sed -i 's/from handlers\.youtube_callbacks/from interfaces.telegram.handlers.youtube/g' {} \;
git add interfaces/telegram/handlers/youtube.py && git commit -m "refactor: move youtube_callbacks to interfaces/"
```

**Step 5.4: Final testing**
```bash
# Run all checks
venv/bin/ruff check .
venv/bin/ruff format .
venv/bin/python -m pylint $(git ls-files '*.py') --rcfile=.pylintrc

# Test bot
python bot.py
# In Telegram (FULL TEST):
# - /start, /mode, /clear, /model, /ping, /limits, /lang, /savedoc, /settings
# - Send voice, audio, text, YouTube links
# - Navigate /settings menu
# - Test OAuth login
# - Test all callbacks

# Deploy
./update.sh
docker logs -f tg-voice
```

### Rollback Plan

```bash
# If handlers fail:
git stash
# Bot reverts to Phase 4 state (still working)
```

---

## Effort Estimation

| Phase | Files | Lines | Time | Risk | Working Version |
|-------|-------|-------|------|------|-----------------|
| **1. shared/** | 4 | ~400 | 2h | Low | ✅ After 2h |
| **2. infrastructure/** | 8 | ~800 | 4h | Medium | ✅ After 4h |
| **3. application/** | 4 | ~600 | 4h | Medium | ✅ After 4h |
| **4. domain/** | 6 | ~600 | 8h | High | ✅ After 8h |
| **5. interfaces/** | 8 | ~1000 | 6h | High | ✅ After 6h |
| **Total** | **30** | **~3400** | **24h** | - | **After EACH phase** |

---

## Rollback Strategy

### Git Strategy

**Before EACH phase:**
```bash
git checkout -b refactor/phase-N-start
```

**After EACH phase:**
```bash
git add -A
git commit -m "refactor: Phase N complete - working version"
git tag refactor/phase-N-complete
```

**If issues found:**
```bash
# Option 1: Stash current changes
git stash
# Bot reverts to previous working state

# Option 2: Reset to tag
git reset --hard refactor/phase-N-1-complete
# Bot reverts to previous working state

# Option 3: Revert specific commit
git revert <commit-hash>
# Bot reverts specific change
```

### Testing After Each Commit

**Automated checks:**
```bash
# Linting
venv/bin/ruff check .
venv/bin/ruff format . --check

# Syntax
python3 -m py_compile bot.py

# Import test
venv/bin/python -c "from bot import bot; print('OK')"
```

**Manual test (2 minutes):**
```bash
# Start bot
python bot.py

# In Telegram:
# 1. Send /start
# 2. Send voice message
# 3. Send text message
# 4. Check response

# If all work → commit, else → rollback
```

---

## Success Criteria

### After Each Phase

- ✅ All imports resolved
- ✅ Ruff check passes
- ✅ Bot starts successfully
- ✅ All features work (manual test)
- ✅ Can deploy to production
- ✅ Rollback tested and works

### After All Phases

- ✅ Clean layered architecture
- ✅ No circular dependencies
- ✅ Domain layer has NO infrastructure imports
- ✅ All files under 150 lines (or justified exception)
- ✅ Documentation updated

---

## Timeline

**Recommended: 5 weeks (one phase per week)**

| Week | Phase | Deployable Version |
|------|-------|---------------------|
| 1 | shared/ | ✅ End of Week 1 |
| 2 | infrastructure/ | ✅ End of Week 2 |
| 3 | application/ | ✅ End of Week 3 |
| 4 | domain/ | ✅ End of Week 4 |
| 5 | interfaces/ | ✅ End of Week 5 |

**Alternative: 1 week sprint (full-time)**

| Day | Phase | Deployable |
|-----|-------|------------|
| Day 1 | Phase 1 | ✅ Evening |
| Day 2 | Phase 2 | ✅ Evening |
| Day 3 | Phase 3 | ✅ Evening |
| Day 4 | Phase 4 | ✅ Evening |
| Day 5 | Phase 5 + testing | ✅ Evening |

---

## Notes

- **Backward compatibility:** Root `config.py`, `state.py`, `bot.py` re-export during transition
- **Documentation:** Update `QWEN.md`, `CLAUDE.md`, `README.md` after Phase 5
- **Docker:** No changes needed (paths internal to image)
- **CI/CD:** Update pylint workflow if file paths change significantly
- **Each phase is independent** - can stop after any phase
