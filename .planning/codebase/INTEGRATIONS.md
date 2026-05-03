# External Integrations

**Analysis Date:** 2026-05-03

## APIs & External Services

**Tour Search Pages:**
- Biblio-Globus - Primary price source for structured tour offers.
  - SDK/Client: `requests` in `fetch_html()` inside `price_monitor/monitor.py`.
  - Auth: none detected.
  - Configuration: `BG_MONITOR_URL` in `MonitorConfig.from_env()` inside `price_monitor/monitor.py`.
  - URL validation: `normalize_search_url()` allows `bgoperator.ru` URLs only when the path contains `price.shtml`.
- Level.Travel - Optional comparison price source added through Telegram runtime settings.
  - SDK/Client: `requests` in `fetch_html()` and HTML parsing in `parse_external_price()` inside `price_monitor/monitor.py`.
  - Auth: none detected.
  - Configuration: Stored as runtime search target data in `/data/settings.json` through `save_runtime_settings()` in `price_monitor/monitor.py`.
  - URL validation: `normalize_search_url()` allows hosts containing `level.travel`.
- Travelata - Optional comparison price source added through Telegram runtime settings.
  - SDK/Client: `requests` in `fetch_html()` and HTML parsing in `parse_external_price()` inside `price_monitor/monitor.py`.
  - Auth: none detected.
  - Configuration: Stored as runtime search target data in `/data/settings.json` through `save_runtime_settings()` in `price_monitor/monitor.py`.
  - URL validation: `normalize_search_url()` allows hosts containing `travelata.ru`.

**Messaging:**
- Telegram Bot API - Sends notifications and provides an inline-button control interface.
  - SDK/Client: Direct HTTPS calls with `requests.post()` in `telegram_post()` inside `price_monitor/monitor.py`.
  - Auth: `TELEGRAM_BOT_TOKEN`.
  - Chat restriction: `TELEGRAM_CHAT_ID` in `MonitorConfig.from_env()` inside `price_monitor/monitor.py`.
  - Methods used: `sendMessage`, `getUpdates`, and `answerCallbackQuery` through `telegram_post()` and `TelegramControlBot.api()` in `price_monitor/monitor.py`.

## Data Storage

**Databases:**
- Not detected.
  - Connection: Not applicable.
  - Client: Not applicable.

**File Storage:**
- Local JSON files on the container filesystem, persisted by Docker named volume `bg-price-monitor-data` in `docker-compose.yml`.
- Snapshot storage: `BG_STATE_PATH`, defaulting to `/data/last_snapshot.json`, read and written by `load_snapshot()` and `save_snapshot()` in `price_monitor/monitor.py`.
- Runtime settings storage: `BG_SETTINGS_PATH`, defaulting to `/data/settings.json`, read and written by `load_runtime_settings()` and `save_runtime_settings()` in `price_monitor/monitor.py`.
- Price history storage: `BG_HISTORY_PATH`, defaulting to `/data/price_history.json`, read and written by `load_price_history()` and `save_price_history()` in `price_monitor/monitor.py`.
- Root file `last_snapshot.json` exists and is ignored by `.gitignore`; use the Docker volume path for runtime state.

**Caching:**
- No cache service detected.
- Local JSON snapshot/history files in `price_monitor/monitor.py` provide persistence and change detection, not a general-purpose cache.

## Authentication & Identity

**Auth Provider:**
- Telegram Bot API token authentication.
  - Implementation: `TELEGRAM_BOT_TOKEN` is passed into Telegram API URLs by `telegram_post()` in `price_monitor/monitor.py`.
  - Authorization: optional allowlist using `TELEGRAM_CHAT_ID` in `TelegramControlBot.is_authorized()` inside `price_monitor/monitor.py`.
- No user account system, OAuth provider, session storage, or password authentication detected.

## Monitoring & Observability

**Error Tracking:**
- None detected.

**Logs:**
- Standard Python logging to stdout configured in `configure_logging()` inside `price_monitor/monitor.py`.
- Docker operational workflow in `README.md` uses `docker logs -f bg-price-monitor`.
- Exceptions during price checks and Telegram polling are logged with `logging.exception()` in `main()` and `TelegramControlBot.poll_forever()` inside `price_monitor/monitor.py`.

## CI/CD & Deployment

**Hosting:**
- Local or self-managed Docker Compose deployment through `docker-compose.yml`.
- Service image name is `bg-price-monitor:latest` and container name is `bg-price-monitor` in `docker-compose.yml`.
- Container restart policy is `unless-stopped` in `docker-compose.yml`.

**CI Pipeline:**
- None detected. No GitHub Actions, GitLab CI, or other CI config files found in the project root.

## Environment Configuration

**Required env vars:**
- `BG_MONITOR_URL` - Optional; defaults to a built-in Biblio-Globus URL in `price_monitor/monitor.py`.
- `BG_DEPARTURE_FROM` - Optional; default configured in `MonitorConfig.from_env()` in `price_monitor/monitor.py`.
- `BG_DEPARTURE_TO` - Optional; default configured in `MonitorConfig.from_env()` in `price_monitor/monitor.py`.
- `BG_NIGHTS` - Optional; parsed by `parse_nights()` in `price_monitor/monitor.py`.
- `BG_ROOM_FILTERS` or `BG_ROOM_CONTAINS` - Optional room/hotel text filters parsed by `parse_filters()` in `price_monitor/monitor.py`.
- `BG_CHECK_INTERVAL_SECONDS` - Optional polling interval used by `main()` and adjusted by `adaptive_interval()` in `price_monitor/monitor.py`.
- `BG_RUN_ONCE` - Optional one-shot execution flag used by `main()` in `price_monitor/monitor.py`.
- `BG_STATE_PATH` - Optional snapshot path; default `/data/last_snapshot.json`.
- `BG_SETTINGS_PATH` - Optional runtime settings path; default `/data/settings.json`.
- `BG_HISTORY_PATH` - Optional price history path; default `/data/price_history.json`.
- `BG_STRONG_DIFF_RUB` - Optional threshold for 12/13-night difference alerts in `format_strong_diff_line()` in `price_monitor/monitor.py`.
- `BG_STRONG_DIFF_PERCENT` - Optional percentage threshold for 12/13-night difference alerts in `format_strong_diff_line()` in `price_monitor/monitor.py`.
- `BG_TARGET_PRICE` - Optional target-price alert threshold used by `format_target_alerts()` in `price_monitor/monitor.py`.
- `TELEGRAM_BOT_TOKEN` - Required only for Telegram notifications and bot controls.
- `TELEGRAM_CHAT_ID` - Required only to restrict Telegram access or send automatic notifications to a fixed chat.

**Secrets location:**
- `.env` file present - contains environment configuration and may contain Telegram secrets.
- `.env.example` file present - documents expected variables.
- Docker Compose reads variables from the shell or `.env` by interpolation in `docker-compose.yml`.
- No secret manager integration detected.

## Webhooks & Callbacks

**Incoming:**
- None detected.
- Telegram integration uses outbound long polling with `getUpdates` in `TelegramControlBot.poll_forever()` inside `price_monitor/monitor.py`; it does not expose a webhook endpoint.

**Outgoing:**
- HTTP `GET` to the configured tour/search URLs through `fetch_html()` in `price_monitor/monitor.py`.
- HTTP `POST` to `https://api.telegram.org/bot{token}/{method}` through `telegram_post()` in `price_monitor/monitor.py`.
- Telegram messages are split and sent as MarkdownV2 by `send_telegram()` and `TelegramControlBot.send_message()` in `price_monitor/monitor.py`.

---

*Integration audit: 2026-05-03*
