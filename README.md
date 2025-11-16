# Mahdihosseini Telegram Bot

## Overview

This project implements a Telegram bot that onboards users through a private chat, verifies their membership in a target channel, and optionally enforces mobile number collection before exposing the core menu. A role-protected admin console allows privileged operators to manage additional admins, toggle runtime policies, broadcast announcements, and inspect growth metrics. The runtime is backed by SQLite for persistence and uses `python-telegram-bot` v20+ (async `Application`) for the bot transport.

## Feature Matrix

-   **Private-channel gating**
    -   Rejects any interaction outside 1:1 chats.
    -   Enforces channel membership via `get_chat_member`; configurable invite link surfaces inside inline keyboards.
    -   Centralized keyboard builders live in `bot/keyboards.py`.
-   **Progressive user onboarding**
    -   Ensures a `users` row exists for every contact (`database.ensure_user_record`).
    -   Optional mobile requirement (default set via `REQUIRE_PHONE_DEFAULT`, runtime toggle in admin UI). Phone numbers are normalized to the last 10 digits before persistence.
-   **Core menu**
    -   Dynamic webinar catalogue: selecting “وبینار ها” streams every published webinar with its description and an inline registration button.
    -   Static placeholders for case studies, drop learning, and services with localized responses (`bot/menu.py`).
    -   Service submenu (`SERVICE_MENU_KEYBOARD`) and fallback messaging for upcoming sections.
-   **Admin panel (conversation handler in `bot/admin/conversation.py`)**
    -   Stats dashboard: total users, with phone, without phone.
    -   Runtime phone toggle with immediate feedback.
    -   Broadcast workflows targeting all / with phone / without phone cohorts; resilient logging on Telegram delivery failures.
    -   Admin management: add by phone lookup, remove via inline list (excluding temp IDs), list with emoji index, and cancel navigation.
    -   Webinar lifecycle management: create entries (description + registration link), edit either field, or delete webinars through inline menus with per-item actions.
-   **Resilience & DX**
    -   Centralized error handler (`bot/errors.py`) notifies users on unhandled exceptions.
    -   Config loader searches root `.env` and populates channel globals (`bot/config.py`).
    -   Compile-time safe refactor splits responsibilities into small modules with explicit exports.

## Architecture

```
bot/
  __init__.py            # public factory exported to top-level entrypoint
  application.py         # creates Application, seeds bot_data, attaches handlers + errors
  config.py              # .env loader, token + channel configuration, global state setters
  constants.py           # shared string/state constants such as menu labels and FSM states
  keyboards.py           # static Reply/Inline keyboard builders
  guards.py              # async guard rails (chat type, membership, phone enforcement)
  menu.py                # public user handlers, onboarding flow, membership verification
  utils.py               # shared helpers (admin detection, phone parsing, notifications)
  errors.py              # global error dispatcher
  handlers.py            # registers command/message/callback handlers
  admin/
    conversation.py      # ConversationHandler for the admin console
database.py              # SQLite access layer (users + admins)
bot.py                 # thin entrypoint wiring configuration + polling loop
```

Key runtime invariants:

-   Channel identifiers are resolved once at boot (`configure_channel`) and stored module-wide so inline keyboards always embed the correct invite link.
-   `Application.bot_data["require_phone"]` mirrors the phone requirement toggle and is the single source of truth for both onboarding guards and admin UI.
-   Temporary admins (`TEMP_ADMIN_IDS`) bypass database checks; they are filtered during removal and displayed distinctly in admin lists.

## Setup

1. **Install dependencies**

    ```bash
    python -m venv .venv
    .venv\Scripts\activate              # Windows (PowerShell)
    pip install python-telegram-bot==20.*
    ```

    Add any additional project-specific dependencies (e.g., via `requirements.txt`) if present.

2. **Environment variables** (`.env` at project root)

    ```env
    BOT_TOKEN=123456:telegram-bot-token
    CHANNEL_ID=@your_public_channel_or_full_invite_url
    # Optional overrides:
    CHANNEL_INVITE_LINK=https://t.me/joinchat/abcdef       # for numeric CHANNEL_ID
    CHANNEL_CHAT_ID=-1001234567890                         # required when using invite URLs
    REQUIRE_PHONE_DEFAULT=true                             # initial phone requirement
    ```

3. **Database**
    - On first run `database.init_db()` creates/patches `bot.sqlite3` in the project root.
    - Schemas: `users(telegram_id, phone_number, fname, lname, username)`, `admins(telegram_id)` with cascading deletes, and `webinars(id, description, registration_link, created_at)`.

## Running the Bot

```bash
python bot.py
```

The bot starts polling with `allowed_updates=["message", "callback_query"]` and drops pending updates for a clean session.

## Admin Operations

-   **Access**: only Telegram IDs recorded in `TEMP_ADMIN_IDS` or the `admins` table can open the panel (`/panel` command or “🛠️ پنل ادمین” button).
-   **Add admin**: from the admin menu choose _افزودن ادمین ➕_, input the last 10 digits of the user's phone. The user must have previously shared their contact.
-   **Remove admin**: select a user from the inline list; temporary admins are protected from removal.
-   **Broadcast**: pick a cohort, send a plain-text message, receive delivery stats (success/failure counts).
-   **Toggle phone requirement**: switches the onboarding guard in real time without service restarts.
-   **Manage webinars**:
    -   From _مدیریت وبینارها 🎥_ view the catalog; each webinar appears as a physical button.
    -   _➕ افزودن وبینار_ prompts for a description followed by a registration URL.
    -   Selecting an existing webinar exposes inline actions to edit the description, update the link, or remove the entry entirely.

## Development Notes

-   Use `python -m compileall .` to run a quick syntax check across modules (already integrated in the refactor workflow).
-   Handlers are async; any new handler must be declared with `async def` and registered via `bot/handlers.register_handlers`.
-   Keep new functionality modular—prefer extending existing packages (`bot/menu.py`, `bot/admin/`, etc.) instead of expanding `bot.py`.

## Future Enhancements

-   Replace static service responses with dynamic content (e.g., pulling from a CMS).
-   Persist broadcast history (message body, audience size, success rate) for auditability.
-   Integrate structured logging and monitoring (e.g., Sentry) inside `bot/errors.py`.
