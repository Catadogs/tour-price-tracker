# Roadmap: Personal Tour Price Tracker Bot

## Overview

This roadmap turns the existing Dockerized Python price monitor into a durable personal Telegram bot without changing the operating model: one monolithic Python service, one Docker image/container, one SQLite database in the mounted data volume, no brokers, no heavy database, and Telegram as the only v1 interface. The phases follow the requirements path from durable state, to admin control, to actionable price alerts, to duration anomaly insight, and finally to currency-driven early warnings plus operational hardening.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: SQLite State and Single-Container Foundation** - Runtime state moves from JSON to SQLite while the service remains a one-container monolith.
- [ ] **Phase 2: Admin Telegram Control UI and Authorization** - The admin can safely manage tracking settings from Telegram, and unauthorized chats are blocked.
- [ ] **Phase 3: Price Tracking Summaries and Target Alerts** - Scheduled and manual checks produce readable best-price summaries and immediate target-price alerts.
- [ ] **Phase 4: Duration Anomaly Analytics** - Same-date night-duration comparisons highlight longer-cheaper and better-value tour options.
- [ ] **Phase 5: Currency Early Warnings and Operational Hardening** - Currency jumps are monitored daily and operational failures are visible enough to act on.

## Phase Details

### Phase 1: SQLite State and Single-Container Foundation
**Goal**: The bot keeps durable settings, snapshots, and price history in SQLite while still running as one simple Dockerized Python service.
**Depends on**: Nothing (first phase)
**Requirements**: STOR-01, STOR-02, STOR-03, STOR-04, STOR-05, OPS-01, OPS-02, OPS-03, OPS-04, QUAL-01, QUAL-02
**Success Criteria** (what must be TRUE):
  1. Admin can start the existing Docker service with one command and see the bot use a SQLite database file in the mounted data volume.
  2. A fresh or empty data volume initializes the database automatically without manual SQL steps.
  3. Runtime settings, latest snapshots, and tour price history survive service restarts without normal-runtime JSON files.
  4. Missing or malformed persisted state does not crash the long-running service.
  5. The test suite passes, including focused SQLite tests for initialization, settings, snapshots, and price history writes.
**Plans**: 3 plans
Plans:
- [ ] 01-01-PLAN.md - Create SQLite storage schema, one-time JSON migration, persistence operations, and corruption fallback.
- [ ] 01-02-PLAN.md - Wire monitor runtime settings, snapshots, and price history to SQLite.
- [x] 01-03-PLAN.md - Add Docker and documentation wiring for the SQLite database path.

### Phase 2: Admin Telegram Control UI and Authorization
**Goal**: The configured admin can manage watch settings through Telegram controls, while unauthorized chats and unsafe URLs are rejected.
**Depends on**: Phase 1
**Requirements**: TG-01, TG-02, TG-03, TG-04, TG-05, TG-06, TG-07, TG-09, QUAL-05, QUAL-06
**Success Criteria** (what must be TRUE):
  1. Admin can open a Telegram inline keyboard menu and view the current tracking settings.
  2. Admin can add a watched hotel or tour search URL and manage room filters, departure dates, nights, target price, and check frequency from Telegram.
  3. Unauthorized chats are rejected when an admin chat id is configured and cannot change settings.
  4. Lookalike domains and unauthorized URL shapes are rejected before they can be fetched or persisted.
  5. Telegram menu, formatting helpers, and authorization behavior are covered by focused tests.
**Plans**: TBD
**UI hint**: yes

### Phase 3: Price Tracking Summaries and Target Alerts
**Goal**: The bot can run scheduled and manual tour checks, select the best matching offers, and notify the admin when a target price or new historical minimum appears.
**Depends on**: Phase 2
**Requirements**: TG-08, TRK-01, TRK-02, TRK-03, TRK-04, TRK-05, TRK-06
**Success Criteria** (what must be TRUE):
  1. Admin receives scheduled tour checks according to the configured frequency.
  2. Admin can trigger a manual Telegram check without corrupting persisted settings, snapshots, or history.
  3. Summary messages show current best price, provider or search target, departure date, nights, and key comparisons in a readable format.
  4. Parsed offers are filtered by configured target, date range, nights, and room filters before the minimum matching price is selected.
  5. Admin receives an immediate Telegram alert when the minimum matching price is less than or equal to the configured target price, with new historical minimums included.
**Plans**: TBD
**UI hint**: yes

### Phase 4: Duration Anomaly Analytics
**Goal**: The bot identifies same-date duration anomalies so the admin can spot longer or better-value tours that are unexpectedly cheaper.
**Depends on**: Phase 3
**Requirements**: ANOM-01, ANOM-02, ANOM-03, ANOM-04, ANOM-05, QUAL-03
**Success Criteria** (what must be TRUE):
  1. Admin can see same-departure-date comparisons across configured night durations.
  2. Summary output highlights cases where a longer duration is cheaper than a shorter duration.
  3. Anomaly lines show the difference in RUB and percent.
  4. Configurable thresholds suppress minor price noise from strong anomaly alerts.
  5. Anomaly tests cover same-date duration comparisons and threshold handling.
**Plans**: TBD

### Phase 5: Currency Early Warnings and Operational Hardening
**Goal**: The bot warns the admin about significant USD/RUB and EUR/RUB movement before tour operators may recalculate RUB prices, and failures are logged clearly enough to diagnose.
**Depends on**: Phase 4
**Requirements**: CURR-01, CURR-02, CURR-03, CURR-04, CURR-05, OPS-05, QUAL-04
**Success Criteria** (what must be TRUE):
  1. Daily USD/RUB and EUR/RUB observations are stored in SQLite and survive service restarts.
  2. The bot fetches current USD/RUB and EUR/RUB rates from the configured exchange-rate source.
  3. Intraday exchange-rate movement is compared with configurable alert thresholds.
  4. Admin receives a preemptive Telegram warning when currency movement suggests tour RUB prices may increase after operator recalculation.
  5. Currency warnings include pair, observed change, threshold, and why the warning matters; check, parse, Telegram delivery, and currency fetch failures are logged with actionable messages.
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. SQLite State and Single-Container Foundation | 1/3 | In Progress | - |
| 2. Admin Telegram Control UI and Authorization | 0/TBD | Not started | - |
| 3. Price Tracking Summaries and Target Alerts | 0/TBD | Not started | - |
| 4. Duration Anomaly Analytics | 0/TBD | Not started | - |
| 5. Currency Early Warnings and Operational Hardening | 0/TBD | Not started | - |

## Coverage

| Requirement | Phase |
|-------------|-------|
| STOR-01 | Phase 1 |
| STOR-02 | Phase 1 |
| STOR-03 | Phase 1 |
| STOR-04 | Phase 1 |
| STOR-05 | Phase 1 |
| TG-01 | Phase 2 |
| TG-02 | Phase 2 |
| TG-03 | Phase 2 |
| TG-04 | Phase 2 |
| TG-05 | Phase 2 |
| TG-06 | Phase 2 |
| TG-07 | Phase 2 |
| TG-08 | Phase 3 |
| TG-09 | Phase 2 |
| TRK-01 | Phase 3 |
| TRK-02 | Phase 3 |
| TRK-03 | Phase 3 |
| TRK-04 | Phase 3 |
| TRK-05 | Phase 3 |
| TRK-06 | Phase 3 |
| ANOM-01 | Phase 4 |
| ANOM-02 | Phase 4 |
| ANOM-03 | Phase 4 |
| ANOM-04 | Phase 4 |
| ANOM-05 | Phase 4 |
| CURR-01 | Phase 5 |
| CURR-02 | Phase 5 |
| CURR-03 | Phase 5 |
| CURR-04 | Phase 5 |
| CURR-05 | Phase 5 |
| OPS-01 | Phase 1 |
| OPS-02 | Phase 1 |
| OPS-03 | Phase 1 |
| OPS-04 | Phase 1 |
| OPS-05 | Phase 5 |
| QUAL-01 | Phase 1 |
| QUAL-02 | Phase 1 |
| QUAL-03 | Phase 4 |
| QUAL-04 | Phase 5 |
| QUAL-05 | Phase 2 |
| QUAL-06 | Phase 2 |

**Coverage status:** 41/41 v1 requirements mapped, no orphaned requirements, no duplicate phase assignments.
