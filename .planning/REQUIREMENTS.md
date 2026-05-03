# Requirements: Personal Tour Price Tracker Bot

**Defined:** 2026-05-03
**Core Value:** The bot must reliably notify the admin when a desirable tour becomes worth acting on before the price changes or disappears.

## v1 Requirements

### Storage

- [x] **STOR-01**: The application stores runtime settings in a local SQLite database file mounted through the Docker data volume.
- [ ] **STOR-02**: The application stores observed tour price history in SQLite with timestamps, provider, hotel/search target, departure date, nights, and price in RUB.
- [ ] **STOR-03**: The application stores latest snapshots in SQLite so price changes can be detected across checks.
- [ ] **STOR-04**: The application can migrate or initialize from an empty database without manual SQL steps.
- [x] **STOR-05**: The application no longer depends on JSON files for settings, snapshots, or price history in normal runtime.

### Telegram

- [ ] **TG-01**: The admin can open an inline keyboard menu from Telegram to view and manage tracking settings.
- [ ] **TG-02**: The admin can add a watched hotel or tour search URL from Telegram.
- [ ] **TG-03**: The admin can manage room/hotel filters from Telegram.
- [ ] **TG-04**: The admin can set departure date range from Telegram.
- [ ] **TG-05**: The admin can set one or more night durations from Telegram.
- [ ] **TG-06**: The admin can set target price in RUB from Telegram.
- [ ] **TG-07**: The admin can set check frequency from Telegram.
- [ ] **TG-08**: Telegram summary messages show current best price, provider/search target, departure date, nights, and key comparisons in a readable format.
- [ ] **TG-09**: Telegram controls reject unauthorized chats when an admin chat id is configured.

### Tracking

- [ ] **TRK-01**: The application periodically fetches tour prices according to the configured check frequency.
- [ ] **TRK-02**: The application supports manual checks from Telegram without corrupting persisted state.
- [ ] **TRK-03**: The application filters parsed offers by configured hotel/search target, date range, nights, and room filters.
- [ ] **TRK-04**: The application identifies the minimum matching tour price for each check.
- [ ] **TRK-05**: The application sends an immediate Telegram alert when the minimum matching price is less than or equal to the configured target price.
- [ ] **TRK-06**: The application records new historical minimums and includes them in notifications.

### Analytics

- [ ] **ANOM-01**: The application compares prices for different night durations on the same departure date.
- [ ] **ANOM-02**: The application detects and highlights cases where a longer duration is cheaper than a shorter duration.
- [ ] **ANOM-03**: The application reports anomaly difference in RUB and percent.
- [ ] **ANOM-04**: The application applies configurable thresholds so minor noise does not trigger strong anomaly alerts.
- [ ] **ANOM-05**: Summary output includes anomaly lines when meaningful duration differences are found.

### Currency

- [ ] **CURR-01**: The application stores daily USD/RUB and EUR/RUB exchange rate observations in SQLite.
- [ ] **CURR-02**: The application can fetch current USD/RUB and EUR/RUB rates from a configured exchange-rate source.
- [ ] **CURR-03**: The application compares intraday exchange-rate movement against configurable alert thresholds.
- [ ] **CURR-04**: The application sends a preemptive Telegram warning when currency movement suggests tour RUB prices may increase after operator recalculation.
- [ ] **CURR-05**: Currency alerts include currency pair, observed change, threshold, and why the warning matters for tour prices.

### Operations

- [x] **OPS-01**: The application runs as a monolithic Python service in one process.
- [x] **OPS-02**: The Docker image starts the bot with a single command and persists SQLite data through a mounted volume.
- [x] **OPS-03**: The project does not require RabbitMQ, Redis, Kafka, Celery, PostgreSQL, MySQL, or separate worker containers.
- [ ] **OPS-04**: The application handles malformed or missing persisted data without crashing the long-running service.
- [ ] **OPS-05**: The application logs check failures, provider parse failures, Telegram delivery failures, and currency fetch failures with actionable messages.

### Quality

- [ ] **QUAL-01**: Existing tests pass with the current `MonitorConfig` shape.
- [ ] **QUAL-02**: SQLite storage has focused tests for initialization, settings persistence, snapshot persistence, and price history writes.
- [ ] **QUAL-03**: Anomaly detection has focused tests for same-date duration comparisons and threshold handling.
- [ ] **QUAL-04**: Currency monitoring has focused tests for rate movement calculations and alert formatting.
- [ ] **QUAL-05**: Telegram formatting and menu helpers have tests for key output and authorization behavior.
- [ ] **QUAL-06**: Provider URL validation rejects lookalike domains and unauthorized URL shapes.

## v2 Requirements

### Providers

- **PROV-01**: Add stored real-world HTML fixtures for Biblio-Globus, Level.Travel, and Travelata.
- **PROV-02**: Split provider-specific parsing into focused modules once the SQLite and alerting migration is stable.
- **PROV-03**: Add per-provider rate limits and retry budgets.

### Analytics

- **ANLY-01**: Add trend charts or compact historical summaries in Telegram.
- **ANLY-02**: Add retention settings for historical prices.
- **ANLY-03**: Add configurable anomaly presets for conservative, balanced, and aggressive alerting.

### Operations

- **OPER-01**: Add a Docker healthcheck or lightweight liveness signal.
- **OPER-02**: Document backup and restore commands for the SQLite volume.
- **OPER-03**: Add CI to run tests and build the Docker image.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Multi-user accounts and role management | The product is explicitly for one admin user. |
| External brokers or worker queues | The architecture must stay monolithic and single-process. |
| PostgreSQL, MySQL, or other heavy databases | SQLite is sufficient and required for local persistence. |
| Separate scheduler or worker container | Background checks must run inside the same application process. |
| Web dashboard | Telegram is the requested v1 presentation layer. |
| Booking and payment workflows | The core value is monitoring and alerting, not purchasing tours. |
| Complex session handling | Single-user Telegram flows only need short pending actions and validation. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| STOR-01 | Phase 1 | Complete |
| STOR-02 | Phase 1 | Pending |
| STOR-03 | Phase 1 | Pending |
| STOR-04 | Phase 1 | Pending |
| STOR-05 | Phase 1 | Complete |
| OPS-01 | Phase 1 | Complete |
| OPS-02 | Phase 1 | Complete |
| OPS-03 | Phase 1 | Complete |
| OPS-04 | Phase 1 | Pending |
| QUAL-01 | Phase 1 | Pending |
| QUAL-02 | Phase 1 | Pending |
| TG-01 | Phase 2 | Pending |
| TG-02 | Phase 2 | Pending |
| TG-03 | Phase 2 | Pending |
| TG-04 | Phase 2 | Pending |
| TG-05 | Phase 2 | Pending |
| TG-06 | Phase 2 | Pending |
| TG-07 | Phase 2 | Pending |
| TG-08 | Phase 3 | Pending |
| TG-09 | Phase 2 | Pending |
| TRK-01 | Phase 3 | Pending |
| TRK-02 | Phase 3 | Pending |
| TRK-03 | Phase 3 | Pending |
| TRK-04 | Phase 3 | Pending |
| TRK-05 | Phase 3 | Pending |
| TRK-06 | Phase 3 | Pending |
| QUAL-05 | Phase 2 | Pending |
| QUAL-06 | Phase 2 | Pending |
| ANOM-01 | Phase 4 | Pending |
| ANOM-02 | Phase 4 | Pending |
| ANOM-03 | Phase 4 | Pending |
| ANOM-04 | Phase 4 | Pending |
| ANOM-05 | Phase 4 | Pending |
| CURR-01 | Phase 5 | Pending |
| CURR-02 | Phase 5 | Pending |
| CURR-03 | Phase 5 | Pending |
| CURR-04 | Phase 5 | Pending |
| CURR-05 | Phase 5 | Pending |
| OPS-05 | Phase 5 | Pending |
| QUAL-03 | Phase 4 | Pending |
| QUAL-04 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 41 total
- Mapped to phases: 41
- Unmapped: 0

---
*Requirements defined: 2026-05-03*
*Last updated: 2026-05-03 after roadmap creation*
