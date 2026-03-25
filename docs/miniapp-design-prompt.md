# Design Prompt: Telegram Mini App Settings SPA

## Context

Design a **Settings Mini App** for a Telegram bot that processes voice/audio messages. The Mini App opens inside Telegram's WebView and allows users to configure personal API credentials, storage integrations, and LLM preferences. It must feel native to Telegram — matching its color scheme, spacing, and interaction patterns.

## Target Platform

- **Telegram Mini App WebView** (both iOS and Android)
- Full-height mode (`tg.expand()`)
- Adapts to Telegram's light/dark theme via CSS variables (`var(--tg-theme-bg-color)`, `var(--tg-theme-text-color)`, etc.)
- Back button handled by Telegram SDK (`tg.BackButton`)

## Screens & Layout

### 1. Main Settings Screen

A single scrollable page with collapsible sections. Each section groups related settings.

**Sections:**

#### LLM API
- **API Key** — masked input field (shows `••••••last4`), tap to edit, tap to clear
- **Base URL** — text input with placeholder `https://openrouter.ai/api/v1`
- **Model** — text input with placeholder showing current default model
- **Reset to defaults** — subtle destructive button at section bottom

#### Yandex.Disk Integration
- **Connection status** — shows connected user email or "Not connected"
- **Connect / Disconnect** — primary action button
  - Connect: opens OAuth flow in external browser
  - Disconnect: confirmation dialog, then removes token
- **Disk Path** — text input, only visible when connected (e.g., `ObsidianVault`)

#### Obsidian Notes
- **Vault Path** — text input (server-side path, restricted to admin users)
- **Inbox Folder** — text input with placeholder `Inbox`
- **Reset to defaults** — subtle destructive button

### 2. Field Editing (Inline)

Fields edit in-place (no separate screen):
- Tap a field row to enter edit mode
- Shows text input with current value, Save/Cancel buttons
- Secret fields: show full value only while editing, mask on save
- Validation: inline error message below field if API rejects
- Haptic feedback on save success (`tg.HapticFeedback.notificationOccurred('success')`)

### 3. OAuth Flow Overlay

When user taps "Connect Yandex.Disk":
- Show a brief loading/waiting state in the section
- External browser opens for authorization
- When user returns to Mini App, auto-refresh connection status
- Success: show connected email with green checkmark
- Failure: show error with retry option

## Visual Design Requirements

### General
- Use Telegram's native CSS variables for ALL colors — no hardcoded colors
- Font: system font stack (Telegram WebView inherits device fonts)
- Border radius: 12px for cards/sections (matching Telegram's style)
- Spacing: 16px horizontal padding, 12px between sections
- Max width: 100% (mobile-first, no desktop breakpoints needed)

### Color Tokens (map to Telegram CSS vars)
| Element | Light | Dark | CSS Variable |
|---------|-------|------|-------------|
| Page background | — | — | `--tg-theme-secondary-bg-color` |
| Section card bg | — | — | `--tg-theme-bg-color` |
| Primary text | — | — | `--tg-theme-text-color` |
| Secondary text | — | — | `--tg-theme-hint-color` |
| Accent / links | — | — | `--tg-theme-link-color` |
| Button bg | — | — | `--tg-theme-button-color` |
| Button text | — | — | `--tg-theme-button-text-color` |
| Destructive | #FF3B30 | #FF453A | custom (iOS red) |
| Success | #34C759 | #30D158 | custom (iOS green) |
| Input border | — | — | `--tg-theme-hint-color` at 30% opacity |

### Section Card Style
- White/dark card on secondary background (like Telegram's settings groups)
- Section header: bold, 15px, uppercase hint-color text above card
- Items separated by 0.5px divider lines (hint-color at 20% opacity)
- Collapsible: tap header to expand/collapse with smooth animation

### Setting Row Layout
```
┌─────────────────────────────────────────┐
│  Label                        Value ▸   │
│  (hint text if applicable)              │
└─────────────────────────────────────────┘
```
- Label: primary text, left-aligned
- Value: hint-color, right-aligned, truncated with ellipsis
- Secret values: `••••••` with last 4 chars visible
- Chevron or edit icon on the right edge
- Tap entire row to edit

### Edit Mode (Inline Expansion)
```
┌─────────────────────────────────────────┐
│  Label                                  │
│  ┌───────────────────────────────────┐  │
│  │ current value                     │  │
│  └───────────────────────────────────┘  │
│  [Error message if any]                 │
│                         Cancel   Save   │
└─────────────────────────────────────────┘
```

### OAuth Section
```
┌─────────────────────────────────────────┐
│  Yandex.Disk              Connected ●   │
│  user@yandex.ru                         │
│                                         │
│         [ Disconnect ]                  │
└─────────────────────────────────────────┘
```
or
```
┌─────────────────────────────────────────┐
│  Yandex.Disk          Not connected ○   │
│                                         │
│      [ Connect Yandex.Disk ]            │
└─────────────────────────────────────────┘
```

### Buttons
- **Primary** (Save, Connect): `--tg-theme-button-color` bg, `--tg-theme-button-text-color` text, full-width or inline
- **Secondary** (Cancel): transparent bg, `--tg-theme-link-color` text
- **Destructive** (Reset, Disconnect): transparent bg, red text, confirmation popup before action
- Border radius: 10px, height: 44px (touch-friendly)

### Animations & Interactions
- Section collapse/expand: 200ms ease-out height transition
- Field edit mode: 150ms slide-down expansion
- Save success: brief green checkmark flash + haptic
- Loading states: subtle skeleton shimmer on initial load
- Pull-to-refresh: not needed (data rarely changes externally)

## Typography

| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Section header | 13px | 600 | hint-color, uppercase |
| Setting label | 16px | 400 | text-color |
| Setting value | 16px | 400 | hint-color |
| Input text | 16px | 400 | text-color |
| Hint / description | 13px | 400 | hint-color |
| Button | 16px | 600 | button-text-color |
| Error message | 13px | 400 | destructive red |

## Deliverables

Please produce:
1. **Full-page mockup** of the main settings screen (collapsed default state) — both light and dark themes
2. **Expanded section** showing LLM API settings with one field in edit mode
3. **OAuth section** in both connected and disconnected states
4. **Mobile viewport**: 390x844 (iPhone 14 / similar Android) with Telegram WebView chrome at the top

## Reference

- Telegram's native Settings screen for visual hierarchy and spacing
- Telegram iOS app's section card style (grouped UITableView look)
- Telegram Mini App design guidelines: https://core.telegram.org/bots/webapps
