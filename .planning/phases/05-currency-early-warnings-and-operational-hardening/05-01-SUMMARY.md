---
phase: 05-currency-early-warnings-and-operational-hardening
plan: 01
type: summary
completed: 2026-05-03
tests: 58 passed
---

# Phase 05 Plan 01 Summary

## What Was Done

### New Module: `price_monitor/currency.py`
- `fetch_exchange_rates()` — fetches USD/RUB and EUR/RUB from CBR JSON mirror or flat JSON API
- `format_currency_alert()` — formats Telegram alert with pair, direction, RUB/percent change, threshold, and tour-price context
- `run_currency_check()` — orchestrates fetch → store → compare → alert

### Storage: `currency_observations` table
- New SQLite table with `(pair, rate, observed_at)` columns
- `save_currency_observation()` and `load_currency_observations()` functions

### MonitorConfig: 3 new fields
| Field | Default |
|-------|---------|
| `currency_source_url` | `https://www.cbr-xml-daily.ru/daily_json.js` |
| `currency_alert_threshold_pct` | `1.0` |
| `currency_check_hours` | `24` |

### Main loop integration
- Currency check runs every `currency_check_hours` (default 24h)
- Alert sent via Telegram when threshold exceeded
- All failures logged with stack traces

### Example alert:
```
📈 *USD/RUB* вырос на 2.5% за день (+2.45 RUB)
  Было: 97.50 → Стало: 99.95
  ⚠️ Туроператор может пересчитать RUB-цены при следующем обновлении.
  Порог: 1.0%
```

### Tests (7 new in `tests/test_currency.py`)
| Test | What It Verifies |
|------|-----------------|
| `test_fetch_exchange_rates_parses_cbr_style_json` | CBR nested Valute format |
| `test_fetch_exchange_rates_parses_flat_json` | Flat pair-key format |
| `test_format_currency_alert_triggered_on_large_increase` | 📈 on +3 RUB |
| `test_format_currency_alert_triggered_on_large_decrease` | 📉 on -6 RUB |
| `test_format_currency_alert_suppressed_below_threshold` | +0.5 RUB at 1% threshold → None |
| `test_format_currency_alert_returns_none_for_no_previous` | First observation → None |
| `test_currency_observations_round_trip` | SQLite persistence |

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `price_monitor/currency.py` | New module | +140 |
| `price_monitor/storage.py` | currency_observations table + functions | +22 |
| `price_monitor/monitor.py` | 3 config fields + main loop integration | +25 |
| `tests/test_currency.py` | 7 new tests | +130 |
| `docker-compose.yml` | 3 new env vars | +3 |
| `.env.example` | 3 new env vars | +3 |

## Requirements Satisfied

- [x] CURR-01: Daily exchange rate observations in SQLite
- [x] CURR-02: Fetch USD/RUB and EUR/RUB from configurable source
- [x] CURR-03: Compare movement against alert thresholds
- [x] CURR-04: Preemptive Telegram warnings
- [x] CURR-05: Alerts include pair, change, threshold, and why it matters
- [x] OPS-05: Failures logged with actionable messages
- [x] QUAL-04: Focused tests for rate calculations and alert formatting
