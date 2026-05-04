---
phase: 02-analytics-insights
plan: 01
type: summary
completed: 2026-05-04
tests: 72 passed (64 existing + 8 new)
---

# Phase 02 Plan 01 Summary

## What Was Done

### ANLY-01: Trend summaries (`/trend` command)

- `format_trend_report(db_path)` — reads `price_history` via `storage.load_price_history_grouped()`, computes direction per (target, date, nights), formats compact Markdown.
- `/trend` text command + "📊 Тренды" inline button in both `main_keyboard()` and `settings_keyboard()`.

### ANLY-02: Retention settings and auto-pruning

- `storage.prune_price_history(db_path, retention_days)` — DELETE rows older than cutoff, returns count.
- `MonitorConfig.price_history_retention_days` — env var `BG_PRICE_HISTORY_RETENTION_DAYS` (default 90).
- Telegram setting "🗑️ Хранение истории" → pending action `set_retention`.
- `_prune_if_needed()` — runs pruning max once per 24h in main loop.

### ANLY-03: Anomaly presets

- `ANOMALY_PRESETS` constant: conservative (30k/10%), balanced (20k/7%), aggressive (10k/4%).
- `MonitorConfig.anomaly_preset` — env var `BG_ANOMALY_PRESET` (default "balanced").
- Telegram "⚠️ Пресет аномалий" button cycles through presets, updates `strong_diff_rub`/`strong_diff_percent`.
- `effective_config()` applies preset from runtime settings.
- `format_settings()` shows current preset label + retention days.

### ANLY-04: Weekly price chart

- `price_monitor/charts.py` — `generate_price_chart()` with matplotlib Agg backend. Groups by (target, date, nights), plots lines, saves PNG.
- `send_chart()` — sends PNG via Telegram `sendPhoto` API.
- `_send_chart_if_needed()` — runs once per `chart_interval_hours` (default 168 = 7 days).
- `matplotlib==3.10.9` added to `requirements.txt`.

### Storage additions

- `storage.load_price_history_grouped()` — returns nested dict: target → date → nights → [(ts, price)].
- `storage.prune_price_history()` — deletes old rows with `_WRITE_LOCK`.

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `price_monitor/storage.py` | +2 functions | +46 |
| `price_monitor/monitor.py` | +3 fields, +5 functions, +2 helpers, keyboards | +130 |
| `price_monitor/charts.py` | New module | +80 |
| `price_monitor/requirements.txt` | +matplotlib | +1 |
| `tests/test_price_monitor.py` | +8 tests, +imports, +field updates | +145 |

## Requirements Satisfied

- [x] ANLY-01: Compact trend summaries in Telegram
- [x] ANLY-02: Retention settings with auto-pruning
- [x] ANLY-03: Configurable anomaly presets (3 modes)
- [x] ANLY-04: Weekly price chart (PNG via matplotlib → Telegram sendPhoto)

## Remaining (Phase 3: Operations)

- OPER-01: Docker healthcheck
- OPER-02: Document backup/restore commands
- OPER-03: CI pipeline
