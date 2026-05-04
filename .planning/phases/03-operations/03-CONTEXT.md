# Phase 3: Operations — Context

**Gathered:** 2026-05-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 adds production-readiness operations infrastructure: container health monitoring, documented disaster-recovery procedures, and an automated CI pipeline. These are operational hardening tasks that close the v2.0 milestone.

All changes are ops-only: no new Python application logic, no new storage features, no Telegram integration changes. The application code itself is complete at 72 passing tests.

</domain>

<decisions>
## Implementation Decisions

### Docker healthcheck (OPER-01)
- **D-01:** Add `HEALTHCHECK` directive to `docker/price-monitor/Dockerfile` — no external dependencies or new Python code.
- **D-02:** Healthcheck interval: 30s, timeout: 10s, retries: 3, start period: 15s.
- **D-03:** Check: verify the SQLite DB file at `$BG_DB_PATH` is accessible via a Python one-liner. This confirms the container is running, Python works, and the data volume is mounted.
- **D-04:** The healthcheck runs `python -c "import sqlite3, os; con = sqlite3.connect(os.environ.get('BG_DB_PATH', '/data/price_monitor.sqlite3')); con.execute('SELECT 1'); con.close()"` — return 0 on success, non-zero on failure.

### Backup and restore docs (OPER-02)
- **D-05:** Add a `## Backup and restore` section to `README.md`.
- **D-06:** Document backup command: `docker compose run --rm -v $(pwd):/backup bg-price-monitor cp /data/price_monitor.sqlite3 /backup/`
- **D-07:** Simpler alternative: `docker compose cp bg-price-monitor:/data/price_monitor.sqlite3 ./backup-price_monitor.sqlite3`
- **D-08:** Document restore: `docker compose cp ./backup-price_monitor.sqlite3 bg-price-monitor:/data/price_monitor.sqlite3` followed by `docker compose restart bg-price-monitor`.
- **D-09:** Note that `docker compose cp` works on running containers for hot backups.

### CI pipeline (OPER-03)
- **D-10:** Create `.github/workflows/ci.yml` — GitHub Actions workflow triggered on push to any branch and on PRs to `main`.
- **D-11:** Job "test": checkout, setup Python 3.11, install deps, run `python -m pytest tests/ -v`.
- **D-12:** Job "build": checkout, build Docker image via `docker compose build`, verify image exists.
- **D-13:** Use `ubuntu-latest` runner with standard GitHub Actions (`actions/checkout@v4`, `actions/setup-python@v5`).

</decisions>

<requirements>
## Requirements Covered

- [ ] **OPER-01**: Docker healthcheck
- [ ] **OPER-02**: Document backup and restore commands for SQLite volume
- [ ] **OPER-03**: CI pipeline for tests and Docker image builds
</requirements>
