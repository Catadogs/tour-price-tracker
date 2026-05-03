# Technology Stack

**Analysis Date:** 2026-05-03

## Languages

**Primary:**
- Python 3.11 - Production runtime via `docker/price-monitor/Dockerfile` using `python:3.11-slim`; application code lives in `price_monitor/monitor.py`.

**Secondary:**
- Markdown - Project documentation in `README.md`.
- YAML - Docker Compose configuration in `docker-compose.yml`.
- Dockerfile - Container build definition in `docker/price-monitor/Dockerfile`.

## Runtime

**Environment:**
- Dockerized Python service using `python:3.11-slim` from `docker/price-monitor/Dockerfile`.
- Local analysis environment has Python 3.14.4 and pytest 9.0.3 available, but production runtime is the Docker image.
- Application entrypoint is `python -m price_monitor.monitor` from `docker/price-monitor/Dockerfile`.

**Package Manager:**
- pip - Installs dependencies from `price_monitor/requirements.txt`.
- Lockfile: missing. There is no `requirements-lock.txt`, `pyproject.toml`, `poetry.lock`, `Pipfile.lock`, or root-level package manifest.

## Frameworks

**Core:**
- No web framework detected - `price_monitor/monitor.py` is a long-running worker process with a polling loop in `main()`.
- requests 2.31.0 - HTTP client for price pages and Telegram API calls, declared in `price_monitor/requirements.txt`.
- beautifulsoup4 4.12.3 - HTML parsing for Biblio-Globus, Level.Travel, and Travelata pages, declared in `price_monitor/requirements.txt`.
- Python standard library dataclasses - Domain models `Offer`, `MonitorConfig`, `SearchTarget`, and `ExternalPrice` are declared in `price_monitor/monitor.py`.

**Testing:**
- pytest 9.0.3 - Test runner available in the current environment; tests live in `tests/test_price_monitor.py`.
- pytest is not declared in `price_monitor/requirements.txt`; install it separately for local test execution.

**Build/Dev:**
- Docker - Container image built from `docker/price-monitor/Dockerfile`.
- Docker Compose - Service orchestration in `docker-compose.yml`.
- No linting or formatting tool detected in root config files.

## Key Dependencies

**Critical:**
- `requests==2.31.0` - Performs outbound `GET` requests in `fetch_html()` and outbound Telegram `POST` requests in `telegram_post()` inside `price_monitor/monitor.py`.
- `beautifulsoup4==4.12.3` - Parses tour-price HTML in `parse_offers()`, `extract_hotel_name()`, and `extract_external_hotel_name()` inside `price_monitor/monitor.py`.

**Infrastructure:**
- Docker named volume `bg-price-monitor-data` - Persists `/data/last_snapshot.json`, `/data/price_history.json`, and `/data/settings.json` as configured by `docker-compose.yml` and `price_monitor/monitor.py`.
- Python logging module - Writes service logs to stdout through `configure_logging()` in `price_monitor/monitor.py`.
- Python threading module - Runs the Telegram control bot as a daemon thread through `TelegramControlBot.start()` in `price_monitor/monitor.py`.

## Configuration

**Environment:**
- Runtime configuration is loaded from environment variables in `MonitorConfig.from_env()` inside `price_monitor/monitor.py`.
- Docker Compose injects environment variables in `docker-compose.yml`.
- `.env` file present - contains local environment configuration and must not be read or committed with secret values.
- `.env.example` file present - template environment file; do not treat example values as production secrets.
- Supported environment variables in `price_monitor/monitor.py`: `BG_MONITOR_URL`, `BG_DEPARTURE_FROM`, `BG_DEPARTURE_TO`, `BG_NIGHTS`, `BG_ROOM_FILTERS`, `BG_ROOM_CONTAINS`, `BG_CHECK_INTERVAL_SECONDS`, `BG_RUN_ONCE`, `BG_STATE_PATH`, `BG_SETTINGS_PATH`, `BG_STRONG_DIFF_RUB`, `BG_STRONG_DIFF_PERCENT`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `BG_TARGET_PRICE`, and `BG_HISTORY_PATH`.
- Runtime settings can override selected env-derived values through JSON at `BG_SETTINGS_PATH`, defaulting to `/data/settings.json`.

**Build:**
- `docker/price-monitor/Dockerfile` sets `WORKDIR /app`, installs `price_monitor/requirements.txt`, copies `price_monitor/`, sets `PYTHONUNBUFFERED=1`, and runs `python -m price_monitor.monitor`.
- `docker-compose.yml` builds the `bg-price-monitor` service from the repository root with Dockerfile `docker/price-monitor/Dockerfile`.
- `price_monitor/requirements.txt` is the only dependency manifest.
- `.gitignore` excludes `.env`, `.pytest_cache/`, `__pycache__/`, `*.pyc`, and `last_snapshot.json`.

## Platform Requirements

**Development:**
- Python 3.x with pytest installed to run `tests/test_price_monitor.py`.
- pip to install `price_monitor/requirements.txt`.
- Docker and Docker Compose for the documented runtime workflow in `README.md`.
- Network access to `bgoperator.ru`, `level.travel`, `travelata.ru`, and `api.telegram.org` for live monitoring.

**Production:**
- Docker Compose service `bg-price-monitor` in `docker-compose.yml`.
- Persistent Docker named volume `bg-price-monitor-data` mounted at `/data`.
- Environment configuration supplied through `.env` or equivalent deployment environment variables.
- No dedicated production hosting provider, orchestrator, or CI/CD platform detected.

---

*Stack analysis: 2026-05-03*
