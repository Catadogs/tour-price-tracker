---
phase: 04-duration-anomaly-analytics
plan: 01
type: summary
completed: 2026-05-03
tests: 51 passed
---

# Phase 04 Plan 01 Summary

## What Was Done

### New Function: `format_duration_anomalies`

Replaced the hardcoded 12/13-night `format_strong_diff_line` with a generalized duration anomaly detector:

```python
def format_duration_anomalies(best, config) -> str | None
```

- Compares ALL pairs of night durations on each departure date
- Detects when longer duration is cheaper than shorter duration
- Filters by configurable thresholds (`strong_diff_rub`, `strong_diff_percent`)
- Reports RUB difference and percent for each anomaly

### Integration into `format_report`

- Replaced per-date `format_strong_diff_line` calls with a single `format_duration_anomalies` call
- Anomalies appear in a dedicated "⚠️ *Аномалии длительности*" section
- Example output: `⚠️ 14.09.2026: 13н дешевле 12н на 20 000 RUB (8.0%)`

### Tests Added (5 new)

| Test | What It Verifies |
|------|-----------------|
| `test_duration_anomalies_detects_longer_cheaper` | 13н < 12н flagged, 14н > 13н not flagged |
| `test_duration_anomalies_respects_threshold` | Small diff below threshold suppressed |
| `test_duration_anomalies_returns_none_when_no_anomaly` | All longer = more expensive → None |
| `test_duration_anomalies_multiple_dates` | Anomalies detected across multiple dates |
| `test_format_report_includes_anomaly_section` | Report output includes anomaly section |

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `price_monitor/monitor.py` | Added `format_duration_anomalies`, updated `format_report` | +25 |
| `tests/test_price_monitor.py` | Added 5 test functions | +80 |

## Requirements Satisfied

- [x] ANOM-01: Compare prices for different night durations on same date
- [x] ANOM-02: Detect longer-cheaper anomalies
- [x] ANOM-03: Report diff in RUB and percent
- [x] ANOM-04: Configurable thresholds
- [x] ANOM-05: Summary includes anomaly lines
- [x] QUAL-03: Focused tests for duration comparisons and thresholds
