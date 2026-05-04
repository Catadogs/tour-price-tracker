# Biblio-Globus price monitor

Small Docker service for personal monitoring of Biblio-Globus tour prices.

It fetches the configured price page, finds the best offers for departure dates
and night counts, compares 12 vs 13 nights, stores runtime state in SQLite, and
prints price changes to container logs.

## Quick start

Copy `.env.example` to `.env` and adjust values if needed:

```bash
copy .env.example .env
```

Default `.env.example` already contains the current Biblio-Globus URL and
departure range.

```env
BG_MONITOR_URL=https://www.bgoperator.ru/price.shtml?action=price&tid=211&idt=&flt2=100510000863&bfr=1&id_price=121110211810&data=14.09.2026&d2=26.09.2026&f7=12&f7=13&f3=5*&f8=&ho=0&F4=102632942104&ins=0-40000-USD&flt=100410000047&p=0140819900.0140819900
BG_DEPARTURE_FROM=14.09.2026
BG_DEPARTURE_TO=17.09.2026
BG_NIGHTS=12,13
BG_CHECK_INTERVAL_SECONDS=21600
BG_STRONG_DIFF_RUB=20000
BG_STRONG_DIFF_PERCENT=7
BG_DB_PATH=/data/price_monitor.sqlite3
```

Optional room filter:

```env
BG_ROOM_FILTERS=SUPERIOR DELUXE Garden View
```

Run once:

```bash
docker compose run --rm -e BG_RUN_ONCE=1 bg-price-monitor
```

Run continuously:

```bash
docker compose up -d --build
docker logs -f bg-price-monitor
```

Stop:

```bash
docker compose down
```

## Runtime storage

The service stores Telegram settings, latest snapshots, and price history in a
SQLite database at `BG_DB_PATH`. In Docker, `BG_DB_PATH` defaults to
`/data/price_monitor.sqlite3`, which lives in the mounted `bg-price-monitor-data`
volume and survives container restarts.

Old JSON files configured by `BG_SETTINGS_PATH`, `BG_STATE_PATH`, and
`BG_HISTORY_PATH` are migration inputs on first SQLite initialization. After the
database is initialized, SQLite is the runtime storage location.

## Telegram notifications

Create a bot in Telegram:

1. Open `@BotFather`.
2. Send `/newbot`.
3. Copy the bot token.
4. Add it to `.env`.

```env
TELEGRAM_BOT_TOKEN=123456:token
TELEGRAM_CHAT_ID=123456789
```

`TELEGRAM_CHAT_ID` is optional for testing. If it is empty, the bot answers any
chat that writes to it. Press `/start` in the bot and it will show your chat id.
After that, put the id into `.env` and restart the container to restrict access.

```bash
docker compose up -d --build
```

The bot has inline buttons:

- `Check now` - run a manual price check.
- `Settings` - show active search settings.
- `Add hotel/search` - add another Biblio-Globus, Level.Travel, or Travelata URL.
- `Clear extra searches` - remove URLs added from Telegram.
- `Add filter` - add another room/hotel text fragment to monitor.
- `Clear filters` - remove all Telegram-defined filters.
- `Set dates` - change departure range, for example `14.09.2026 17.09.2026`.
- `Set nights` - change nights list, for example `12,13`.
- `Set diff threshold` - change strong difference threshold, for example
  `10000 4.5`.

Settings changed from Telegram are stored in SQLite at `BG_DB_PATH`, so they
survive container restarts.

To add another hotel:

1. Open Biblio-Globus, Level.Travel, or Travelata in a browser and build the needed hotel search.
2. Copy the final URL. For Biblio-Globus use `https://www.bgoperator.ru/price.shtml?...`.
3. Press `Add hotel/search` in Telegram.
4. Send that URL to the bot.
5. Press `Check now`.

Level.Travel and Travelata are shown as reference comparison prices. For exact
comparison, send a concrete hotel/search URL with the needed dates instead of a
homepage URL.

Without Telegram settings the service only writes to Docker logs.

## Backup and restore

The SQLite database at `BG_DB_PATH` (`/data/price_monitor.sqlite3`) is a self-contained
file that stores all settings, price history, and currency observations. Back it up
periodically to avoid data loss.

### Hot backup (container running)

```bash
docker compose cp bg-price-monitor:/data/price_monitor.sqlite3 ./backup-price_monitor.sqlite3
```

### Restore

```bash
docker compose cp ./backup-price_monitor.sqlite3 bg-price-monitor:/data/price_monitor.sqlite3
docker compose restart bg-price-monitor
```

### Alternative: backup with docker compose run (container stopped)

```bash
docker compose run --rm -v $(pwd):/backup bg-price-monitor cp /data/price_monitor.sqlite3 /backup/
```

The SQLite file is portable — you can open it with any SQLite client for inspection.
