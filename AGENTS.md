# Agent Instructions

This project uses GSD planning artifacts. Read `CLAUDE.md` for the generated project guide, stack summary, conventions, architecture notes, and workflow enforcement rules.

Key constraints:

- Single-user/admin-only Telegram bot.
- Monolithic Python service; no brokers, Celery, separate workers, or heavy databases.
- SQLite is the durable storage target for settings, snapshots, price history, and currency observations.
- Deployment must stay simple: one Docker image/container and a mounted volume for the database.
- Telegram is the v1 interface; no public web dashboard in current scope.

Before direct implementation work, use the relevant GSD workflow and keep `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, and `.planning/STATE.md` in sync.
