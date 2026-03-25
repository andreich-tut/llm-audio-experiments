# Plan: Add Telegram Notifications to Deploy Workflow

## Context
The user wants real-time Telegram notifications when the GitHub Actions deployment pipeline runs, so they can track deploy state without checking GitHub.

## Approach
Use the Telegram Bot API directly via `curl` in the workflow (no third-party actions needed). Add a dedicated notification bot via two new GitHub secrets: `TG_NOTIFY_BOT_TOKEN` and `TG_NOTIFY_CHAT_ID`.

## Changes

### File: `.github/workflows/deploy.yml`

Add 3 notification steps using `curl` to the Telegram `sendMessage` API:

1. **"Notify: Deploy Started"** — at the very beginning of the `deploy` job (before SSH), sends a message with commit info and link to the workflow run.

2. **"Notify: Deploy Success"** — after the SSH deploy step, on success.

3. **"Notify: Deploy Failed"** — after the SSH deploy step, with `if: failure()`, reports which step failed.

Message format (MarkdownV2):
- **Started**: `Deploying <repo>@<short_sha>... ` + commit message + link to run
- **Success**: `Deploy successful` + duration info + link to run
- **Failed**: `Deploy failed` + link to run

### Required GitHub Secrets
The user needs to add these in repo Settings > Secrets:
- `TG_NOTIFY_BOT_TOKEN` — Bot token for the notification bot
- `TG_NOTIFY_CHAT_ID` — Chat ID to send notifications to

## Verification
1. Push a commit to `main` and verify all 3 notification types appear in Telegram
2. To test failure notification: temporarily break the deploy step (e.g., invalid SSH command)
