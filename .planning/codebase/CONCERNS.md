# Codebase Concerns

**Analysis Date:** 2026-05-03

## Tech Debt

**Single-file application module:**
- Issue: Most production behavior lives in one 1,231-line file, including config parsing, Biblio-Globus parsing, external price parsing, Telegram polling, Telegram formatting, persistence, and the main loop.
- Files: `price_monitor/monitor.py`
- Impact: Small changes have a high blast radius; parser changes can affect bot control flow, persistence, or scheduling because the module has no clear ownership boundaries.
- Fix approach: Split into focused modules such as `price_monitor/config.py`, `price_monitor/parsers/bgoperator.py`, `price_monitor/parsers/external.py`, `price_monitor/persistence.py`, `price_monitor/telegram.py`, and `price_monitor/service.py`. Keep `price_monitor/monitor.py` as a thin entry point.

**Configuration schema is implicit:**
- Issue: Runtime settings are read from JSON and directly cast in `effective_config()` without a typed schema, version field, or defaulting layer for invalid keys.
- Files: `price_monitor/monitor.py:192`, `price_monitor/monitor.py:206`, `price_monitor/monitor.py:220`, `price_monitor/monitor.py:223`, `price_monitor/monitor.py:225`
- Impact: A malformed `/data/settings.json` value can crash every check or silently change types in `MonitorConfig`.
- Fix approach: Introduce a `RuntimeSettings` dataclass or Pydantic-style validation function. Validate `departure_from`, `departure_to`, `nights`, thresholds, interval bounds, and `target_price_rub` before applying settings.

**Persistence helpers are duplicated and non-atomic:**
- Issue: Settings, snapshot, and history files are read and written through separate helpers with direct `Path.read_text()` and `Path.write_text()` calls.
- Files: `price_monitor/monitor.py:192`, `price_monitor/monitor.py:198`, `price_monitor/monitor.py:397`, `price_monitor/monitor.py:403`, `price_monitor/monitor.py:411`, `price_monitor/monitor.py:417`
- Impact: Partial writes, process interruption, or concurrent writes can leave JSON files corrupted. Corruption crashes subsequent runs because reads do not catch `JSONDecodeError`.
- Fix approach: Centralize JSON persistence behind one helper that writes to a temp file and atomically replaces the target. On read, catch `JSONDecodeError`, log the bad path, and fall back according to file type.

**No project-level Python packaging or tool config:**
- Issue: The project has `price_monitor/requirements.txt` but no `pyproject.toml`, `pytest.ini`, `setup.cfg`, or editable install configuration.
- Files: `price_monitor/requirements.txt`, `tests/test_price_monitor.py`
- Impact: Test and import behavior depends on the caller's current interpreter and working directory. Running `pytest -q` uses a different environment in this workspace and cannot import `price_monitor`.
- Fix approach: Add `pyproject.toml` with package metadata, pytest config, and tool commands. Prefer `python -m pytest` in docs or add a task runner target.

**Generated runtime data is present at project root:**
- Issue: `last_snapshot.json` exists at the repository root while runtime paths point to `/data/last_snapshot.json` in Docker.
- Files: `last_snapshot.json`, `.gitignore`, `price_monitor/monitor.py:77`
- Impact: Local runtime state can drift from Docker volume state and confuse manual verification.
- Fix approach: Keep runtime files under a dedicated ignored local data directory such as `.local-data/`, or remove root snapshots after migration to the Docker volume.

## Known Bugs

**Current test suite fails after `MonitorConfig` fields were added:**
- Symptoms: `python -m pytest -q` runs collection and reports 2 failures. Both failing tests instantiate `MonitorConfig` without `target_price_rub` and `history_path`.
- Files: `price_monitor/monitor.py:44`, `price_monitor/monitor.py:59`, `price_monitor/monitor.py:60`, `tests/test_price_monitor.py:58`, `tests/test_price_monitor.py:88`
- Trigger: Run `python -m pytest -q` from `C:\price_parcer`.
- Workaround: Add `target_price_rub=None` and `history_path=Path("price_history.json")` to test config construction, or give those fields defaults in `MonitorConfig`.

**Plain `pytest` resolves to the wrong environment in this workspace:**
- Symptoms: `pytest -q` fails during collection with `ModuleNotFoundError: No module named 'price_monitor'`, while `python -m pytest -q` imports the package and reaches test assertions.
- Files: `tests/test_price_monitor.py:3`, `price_monitor/__init__.py`, `price_monitor/requirements.txt`
- Trigger: Run `pytest -q` from `C:\price_parcer` with the current shell PATH.
- Workaround: Use `python -m pytest -q` until project packaging pins the test runner environment.

**MarkdownV2 link handling can break Telegram messages:**
- Symptoms: `escape_markdown_v2()` escapes link text but preserves raw link URLs. URLs containing `)` or MarkdownV2 special sequences can produce invalid Telegram payloads.
- Files: `price_monitor/monitor.py:675`, `price_monitor/monitor.py:700`, `price_monitor/monitor.py:706`, `price_monitor/monitor.py:723`
- Trigger: A remote offer or external URL includes characters that need MarkdownV2 escaping inside link destinations.
- Workaround: Escape link URLs according to Telegram MarkdownV2 rules, or use Telegram HTML parse mode with explicit URL escaping.

**Mojibake literals are visible in source and tests:**
- Symptoms: Some Russian strings and emoji-like markers appear as mojibake sequences such as `Р`/`С`/`в` variants in source excerpts and tests.
- Files: `price_monitor/monitor.py:570`, `price_monitor/monitor.py:594`, `price_monitor/monitor.py:617`, `tests/test_price_monitor.py:29`, `tests/test_price_monitor.py:134`
- Trigger: Editing or running the project in environments with mismatched encodings.
- Workaround: Normalize all source files to UTF-8, add an editorconfig or pre-commit check for UTF-8, and replace mojibake literals with correct Unicode strings.

**Malformed persisted JSON crashes startup or checks:**
- Symptoms: Invalid `settings.json`, `last_snapshot.json`, or `price_history.json` raises during `json.loads()` and bubbles into the polling loop or manual check.
- Files: `price_monitor/monitor.py:195`, `price_monitor/monitor.py:400`, `price_monitor/monitor.py:414`, `price_monitor/monitor.py:731`, `price_monitor/monitor.py:1211`
- Trigger: Truncated Docker volume file, manual edit, interrupted write, or disk full during save.
- Workaround: Validate JSON before restart, or delete the corrupted volume file to force an empty state.

## Security Considerations

**Telegram control bot is open when `TELEGRAM_CHAT_ID` is unset:**
- Risk: Any Telegram chat that messages the bot can use controls, add searches, modify filters, change dates, trigger price checks, and view settings when `TELEGRAM_CHAT_ID` is empty.
- Files: `price_monitor/monitor.py:1041`, `price_monitor/monitor.py:1042`, `price_monitor/monitor.py:1043`, `README.md:69`, `README.md:70`, `README.md:71`
- Current mitigation: `TELEGRAM_CHAT_ID` restricts access when set.
- Recommendations: Treat missing `TELEGRAM_CHAT_ID` as disabled write access after initial setup, or require an explicit `TELEGRAM_ALLOW_ANY_CHAT=1` development flag. Log a high-severity warning when unrestricted mode is active.

**User-submitted URLs use substring host allowlisting:**
- Risk: `normalize_search_url()` accepts hosts when an allowed domain is contained anywhere in `netloc`; crafted domains such as `bgoperator.ru.example.test` can pass the check.
- Files: `price_monitor/monitor.py:1180`, `price_monitor/monitor.py:1185`, `price_monitor/monitor.py:1186`, `price_monitor/monitor.py:1187`, `price_monitor/monitor.py:1189`
- Current mitigation: URL scheme is limited to `http` and `https`, and Biblio-Globus URLs must contain `price.shtml` in the path.
- Recommendations: Compare exact hostnames or subdomains only: `host == allowed` or `host.endswith("." + allowed)`. Reject userinfo, ports outside defaults if not needed, IP literals, and redirects to disallowed hosts.

**Open bot plus URL fetching creates SSRF-like behavior:**
- Risk: When unrestricted Telegram mode is active, an external chat can add a crafted URL and make the container fetch it during manual or scheduled checks.
- Files: `price_monitor/monitor.py:736`, `price_monitor/monitor.py:737`, `price_monitor/monitor.py:959`, `price_monitor/monitor.py:1180`, `price_monitor/monitor.py:1041`
- Current mitigation: Timeout is set in `fetch_html()` and only three provider strings are allowed by substring.
- Recommendations: Fix exact host validation, restrict redirects, and require authorization before accepting any URL. Consider resolving hostnames and blocking private, loopback, link-local, and Docker internal address ranges.

**Telegram API error includes response body in exception:**
- Risk: `telegram_post()` includes Telegram response text in raised exceptions; logs can include sensitive chat or payload details returned by the API.
- Files: `price_monitor/monitor.py:712`, `price_monitor/monitor.py:723`, `price_monitor/monitor.py:724`, `price_monitor/monitor.py:725`, `price_monitor/monitor.py:726`
- Current mitigation: Bot token itself is not logged in this code path.
- Recommendations: Log Telegram method, status code, and a redacted short error description. Do not log full response bodies in production.

**Secret-bearing files exist and are intentionally not inspected:**
- Risk: `.env` is present and can contain Telegram token and chat identifiers. `.env.example` is also present.
- Files: `.env`, `.env.example`, `.gitignore`, `docker-compose.yml`
- Current mitigation: `.gitignore` ignores `.env`; `docker-compose.yml` references environment variables instead of inline secret values.
- Recommendations: Keep `.env` out of commits, avoid placing real secrets in `.env.example`, and add secret scanning before publishing the repository.

## Performance Bottlenecks

**Price history grows without pruning:**
- Problem: `update_price_history()` appends every observed price for every snapshot key, and `save_price_history()` rewrites the whole JSON file on each check.
- Files: `price_monitor/monitor.py:411`, `price_monitor/monitor.py:417`, `price_monitor/monitor.py:422`, `price_monitor/monitor.py:429`, `price_monitor/monitor.py:764`, `price_monitor/monitor.py:775`
- Cause: History is an unbounded in-memory dictionary persisted as one compact JSON blob.
- Improvement path: Add retention by age or count per key, persist line-delimited records, or use SQLite for append-heavy history.

**All target fetches are serial:**
- Problem: `run_check()` fetches each configured search target one at a time.
- Files: `price_monitor/monitor.py:731`, `price_monitor/monitor.py:736`, `price_monitor/monitor.py:737`
- Cause: The service uses synchronous `requests.get()` without concurrency.
- Improvement path: Keep serial behavior for small target counts, but add a bounded worker pool or async client when multiple extra searches are expected.

**Manual checks block scheduled checks:**
- Problem: A manual Telegram check holds the same lock used by the scheduled loop, and the scheduled loop performs all fetches under that lock.
- Files: `price_monitor/monitor.py:799`, `price_monitor/monitor.py:1006`, `price_monitor/monitor.py:1213`
- Cause: One global `threading.Lock` protects the full network and persistence workflow.
- Improvement path: Keep the lock around persistence writes only, or coalesce manual and scheduled checks through a single worker queue.

**HTML parsing scans full documents with broad regexes:**
- Problem: External price parsing scans the entire HTML for `minPrice`, `price`, and localized "from rubles" strings.
- Files: `price_monitor/monitor.py:625`, `price_monitor/monitor.py:628`, `price_monitor/monitor.py:631`
- Cause: The parser does not scope extraction to JSON-LD, known app state payloads, or provider-specific containers.
- Improvement path: Split provider parsers and prefer structured data first. Keep broad regex fallback behind tests that prove it does not pick unrelated prices.

## Fragile Areas

**Biblio-Globus DOM parser depends on exact CSS classes:**
- Files: `price_monitor/monitor.py:136`, `price_monitor/monitor.py:141`, `price_monitor/monitor.py:142`, `price_monitor/monitor.py:143`, `tests/test_price_monitor.py:20`
- Why fragile: `parse_offers()` requires `td.c_ns`, `td.c_pe b.r`, and a booking link with `dt` and `kol` query params. A provider markup change results in empty offers without a provider-specific error.
- Safe modification: Add fixture HTML files from real provider pages and parser tests for missing columns, changed classes, and multiple currencies before changing parsing logic.
- Test coverage: Only compact synthetic HTML is tested in `tests/test_price_monitor.py`; no real-page fixtures or failure-mode tests exist.

**External price parsing is heuristic:**
- Files: `price_monitor/monitor.py:577`, `price_monitor/monitor.py:602`, `price_monitor/monitor.py:625`, `tests/test_price_monitor.py:159`
- Why fragile: `parse_external_price()` chooses the minimum numeric candidate found across broad patterns, which can select unrelated page data.
- Safe modification: Implement provider-specific selectors for `level.travel` and `travelata.ru`, and keep broad regex as a low-confidence fallback displayed separately.
- Test coverage: `tests/test_price_monitor.py` has one microdata-style Level.Travel fixture and no Travelata fixture.

**Runtime settings writes can race with reads:**
- Files: `price_monitor/monitor.py:198`, `price_monitor/monitor.py:207`, `price_monitor/monitor.py:907`, `price_monitor/monitor.py:912`, `price_monitor/monitor.py:949`, `price_monitor/monitor.py:1213`
- Why fragile: Telegram callbacks write settings while scheduled checks can read settings. The shared `check_lock` only protects `run_check()` execution, not every settings write.
- Safe modification: Use a single settings service with a lock and atomic writes. For Telegram handlers, serialize state mutations through the same worker that performs checks.
- Test coverage: No concurrent read/write tests cover `settings.json` behavior.

**Pending Telegram state has no expiry or confirmation:**
- Files: `price_monitor/monitor.py:803`, `price_monitor/monitor.py:861`, `price_monitor/monitor.py:897`, `price_monitor/monitor.py:900`, `price_monitor/monitor.py:917`, `price_monitor/monitor.py:920`, `price_monitor/monitor.py:928`, `price_monitor/monitor.py:934`, `price_monitor/monitor.py:937`
- Why fragile: A user can click a settings action, respond much later, and unintentionally apply a stale pending action.
- Safe modification: Store pending actions with timestamps, expire them after a short timeout, and include cancel behavior.
- Test coverage: No tests cover Telegram conversation state.

**Main loop has limited shutdown and scheduling control:**
- Files: `price_monitor/monitor.py:1205`, `price_monitor/monitor.py:1211`, `price_monitor/monitor.py:1226`, `price_monitor/monitor.py:1227`
- Why fragile: The service sleeps in one long `time.sleep()` call and has no signal-aware graceful shutdown path.
- Safe modification: Replace raw sleep with a `threading.Event` wait and handle SIGTERM/SIGINT so Docker shutdown can stop promptly.
- Test coverage: No tests cover scheduling, adaptive intervals, or shutdown behavior.

## Scaling Limits

**State storage is single-file JSON:**
- Current capacity: Suitable for a small personal monitor with a small number of searches and offers.
- Limit: Large histories and many search targets increase memory use and rewrite time because snapshots and history are loaded and saved as whole files.
- Scaling path: Use SQLite tables for snapshots, history, and settings, with indexed keys for target, departure date, nights, and observed timestamp.

**One process handles polling, bot controls, and checks:**
- Current capacity: One Docker container runs a scheduler loop plus one Telegram polling daemon thread.
- Limit: Long provider fetches delay manual checks and scheduled checks because the workflow is synchronized by one lock.
- Scaling path: Add a queue-based worker model or separate the Telegram control process from the price check worker.

**Provider integrations have no rate controls:**
- Current capacity: Default schedule checks every several hours for a small target set.
- Limit: Adding many searches from Telegram can issue multiple provider requests per check without per-provider pacing.
- Scaling path: Add max target counts, per-provider request delays, retry budgets, and telemetry for fetch duration and failure rates.

## Dependencies at Risk

**Unversioned Python runtime outside Docker:**
- Risk: Docker pins `python:3.11-slim`, but local tests run with whichever `python` and `pytest` are first in PATH.
- Impact: Import behavior and dependency availability differ between local runs and Docker.
- Migration plan: Add `pyproject.toml` with supported Python version, install instructions, and a pinned dev requirements file. Use `python -m pytest` or a task runner command in docs.

**Minimal dependency pinning without update automation:**
- Risk: `requests==2.31.0` and `beautifulsoup4==4.12.3` are pinned in `price_monitor/requirements.txt` with no visible CI, lock refresh process, or vulnerability scanning.
- Impact: Security and compatibility updates depend on manual review.
- Migration plan: Add Dependabot or equivalent for `price_monitor/requirements.txt`, run tests in CI, and document the update cadence.

**No CI pipeline is present:**
- Risk: Test failures and packaging drift are not caught before changes land.
- Impact: Existing test failures can persist unnoticed, and Docker-only behavior is not verified.
- Migration plan: Add a workflow that installs `price_monitor/requirements.txt`, runs `python -m pytest -q`, and builds `docker/price-monitor/Dockerfile`.

## Missing Critical Features

**No health endpoint or liveness signal:**
- Problem: The Docker service only logs status and has no healthcheck in `docker-compose.yml`.
- Blocks: Automated detection of a wedged process, repeated Telegram polling failures, or persistent provider failures.

**No structured observability:**
- Problem: Logging uses plain text and no metrics counters for fetch failures, parse failures, offer counts, Telegram failures, or check duration.
- Blocks: Trend analysis and alerting when provider markup changes or bot delivery fails.

**No explicit backup or recovery flow for Docker volume data:**
- Problem: Runtime settings, snapshots, and history live in the `bg-price-monitor-data` Docker volume without a documented backup/restore command.
- Blocks: Safe migration to a new host and recovery from volume corruption.

**No parser fixture corpus:**
- Problem: Tests do not include stored real-world HTML samples for Biblio-Globus, Level.Travel, or Travelata.
- Blocks: Confident parser changes when provider markup changes.

## Test Coverage Gaps

**Main check workflow is not tested end-to-end:**
- What's not tested: `run_check()` behavior across multiple targets, snapshot diffing, history update, minimum alerts, target alerts, and persistence side effects.
- Files: `price_monitor/monitor.py:731`, `tests/test_price_monitor.py`
- Risk: Alert regressions and persistence breakage can pass the current unit tests.
- Priority: High

**Telegram bot behavior is untested:**
- What's not tested: Authorization, callbacks, pending actions, message splitting, API error handling, and manual check locking.
- Files: `price_monitor/monitor.py:798`, `price_monitor/monitor.py:848`, `price_monitor/monitor.py:875`, `price_monitor/monitor.py:947`, `price_monitor/monitor.py:1004`
- Risk: Bot controls can break or expose write access without test failures.
- Priority: High

**Security validation is under-tested:**
- What's not tested: Rejection of lookalike domains, userinfo URLs, redirects, private IP targets, and invalid schemes.
- Files: `price_monitor/monitor.py:1180`, `tests/test_price_monitor.py:123`, `tests/test_price_monitor.py:128`
- Risk: URL validation changes can introduce SSRF-like fetch behavior.
- Priority: High

**Persistence error paths are untested:**
- What's not tested: Corrupt JSON, missing parent directories, partial writes, and simultaneous settings updates.
- Files: `price_monitor/monitor.py:192`, `price_monitor/monitor.py:198`, `price_monitor/monitor.py:397`, `price_monitor/monitor.py:403`, `price_monitor/monitor.py:411`, `price_monitor/monitor.py:417`
- Risk: A single bad file can take down the service.
- Priority: Medium

**Provider parser coverage is thin:**
- What's not tested: Real Biblio-Globus HTML, Travelata HTML, Level.Travel variants, changed class names, missing prices, and malformed booking links.
- Files: `price_monitor/monitor.py:136`, `price_monitor/monitor.py:557`, `price_monitor/monitor.py:577`, `price_monitor/monitor.py:625`, `tests/test_price_monitor.py`
- Risk: Provider markup changes produce empty or incorrect alerts without detection.
- Priority: Medium

---

*Concerns audit: 2026-05-03*
