# Phase 2: Analytics & Insights — Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 adds visual and analytical intelligence to the bot: trend summaries, weekly price charts, configurable anomaly presets, and automatic price history cleanup. These features build on the price_history SQLite table populated by Phase 1's provider-hardened check loop.

All analytics read from existing SQLite storage — no new data collection needed. The `price_history` table already has `target_name`, `departure_date`, `nights`, `price_rub`, and `observed_at` columns.

</domain>

<decisions>
## Implementation Decisions

### Trend summaries (ANLY-01)
- **D-01:** Add a `/trend` Telegram command that calls existing `compute_trend()` per search target/night combo.
- **D-02:** Trend uses last 6 price points (existing `window=6` default in `compute_trend()`).
- **D-03:** Query price_history from SQLite, group by (target_name, departure_date, nights), compute trend per group.
- **D-04:** Format as compact message: per-target header, then date/nights/trend lines.
- **D-05:** Add "📊 Тренды" button to main keyboard so non-command users can access it.

### Retention (ANLY-02)
- **D-06:** Add `BG_PRICE_HISTORY_RETENTION_DAYS` env var (default 90 days).
- **D-07:** Add `price_history_retention_days` field to `MonitorConfig`.
- **D-08:** Add `prune_price_history(db_path, retention_days)` to `storage.py` — DELETE WHERE observed_at < cutoff.
- **D-09:** Run pruning once per check cycle in `main()` (not every check — use a timestamp tracker).
- **D-10:** Make retention editable from Telegram: add "🗑️ Хранение истории" to settings keyboard → pending action.
- **D-11:** Runtime setting `price_history_retention_days` overrides env var via `effective_config()`.

### Anomaly presets (ANLY-03)
- **D-12:** Define three presets as constants in `monitor.py`:
  - conservative: `strong_diff_rub=30000, strong_diff_percent=10.0`
  - balanced: `strong_diff_rub=20000, strong_diff_percent=7.0` (current default)
  - aggressive: `strong_diff_rub=10000, strong_diff_percent=4.0`
- **D-13:** Store `anomaly_preset` in runtime_settings (values: "conservative", "balanced", "aggressive").
- **D-14:** `effective_config()` reads `anomaly_preset` and replaces `strong_diff_rub`/`strong_diff_percent` accordingly.
- **D-15:** Add "⚠️ Пресет аномалий" button to settings keyboard that cycles through presets.
- **D-16:** Display current preset in `format_settings()`.

### Weekly chart (ANLY-04)
- **D-17:** Create `price_monitor/charts.py` with matplotlib (Agg backend).
- **D-18:** Function `generate_price_chart(db_path, target_name, output_dir) -> Path | None`:
  - Query price_history for target, group by (departure_date, nights).
  - Plot price over time, one line per night duration per departure date.
  - Save PNG to `/data/charts/` (inside container volume).
- **D-19:** Schedule: once per week. Track `last_chart_sent_at` in metadata table.
- **D-20:** Send via `sendPhoto` Telegram API method.
- **D-21:** Add matplotlib to `requirements.txt`.
- **D-22:** Chart sent as part of main loop (after check completes), not as a Telegram command.

### Telegram integration
- **D-23:** All new features use existing `send_message()` / `send_telegram()` infrastructure.
- **D-24:** `main_keyboard()` and `settings_keyboard()` updated with new buttons.
- **D-25:** No new Telegram API methods beyond existing `sendMessage` and new `sendPhoto`.

</decisions>

<requirements>
## Requirements Covered

- [ ] **ANLY-01**: Compact trend summaries in Telegram
- [ ] **ANLY-02**: Retention settings for historical prices
- [ ] **ANLY-03**: Configurable anomaly presets
- [ ] **ANLY-04**: Weekly price change chart (PNG) via matplotlib
</requirements>
