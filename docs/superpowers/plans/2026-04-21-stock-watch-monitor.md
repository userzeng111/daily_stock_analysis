# Stock Watch Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a separate continuous watch module that can track stocks, ETFs, and curated themes, detect stage-based buy-point candidates from the latest 30-day history, run LLM feasibility review on candidates, and expose the workflow through new `/api/v1/watch` APIs and a dedicated `/watch` web page without changing existing ask-stock/history/backtest behavior.

**Architecture:** Add a repo-owned watch subsystem with its own tables, repository, services, SSE event bus, and API/router group. Keep runtime control as a single scheduler-registered worker with an internal enabled flag, expand theme targets through a curated local catalog into concrete stock/ETF basket members, and only invoke LLM review for deduplicated candidate events.

**Tech Stack:** FastAPI, SQLAlchemy/SQLite, existing scheduler/task infrastructure, pandas-based technical analysis, existing LLM stack, React + TypeScript + axios + existing UI primitives.

---

## File Structure

**Backend persistence and services**

- Modify: `src/storage.py`
- Create: `src/repositories/watch_repo.py`
- Create: `src/data/watch_theme_catalog.json`
- Create: `src/services/watch_theme_catalog_service.py`
- Create: `src/services/watchlist_service.py`
- Create: `src/services/watch_signal_service.py`
- Create: `src/services/watch_review_service.py`
- Create: `src/services/watch_event_bus.py`
- Create: `src/services/watch_runtime_service.py`
- Modify: `api/deps.py`
- Create: `api/v1/schemas/watch.py`
- Create: `api/v1/endpoints/watch.py`
- Modify: `api/v1/router.py`

**Frontend**

- Create: `apps/dsa-web/src/types/watch.ts`
- Create: `apps/dsa-web/src/api/watch.ts`
- Create: `apps/dsa-web/src/hooks/useWatchStream.ts`
- Create: `apps/dsa-web/src/pages/WatchPage.tsx`
- Modify: `apps/dsa-web/src/App.tsx`
- Modify: `apps/dsa-web/src/components/layout/SidebarNav.tsx`

**Tests**

- Create: `tests/test_watch_repo.py`
- Create: `tests/test_watch_theme_catalog_service.py`
- Create: `tests/test_watch_signal_service.py`
- Create: `tests/test_watch_runtime_service.py`
- Create: `tests/test_watch_api.py`
- Create: `apps/dsa-web/tests/watch-page.test.tsx`

**Docs and config**

- Modify: `.env.example`
- Modify: `docs/full-guide.md`
- Modify: `docs/full-guide_EN.md`
- Modify: `docs/CHANGELOG.md`
- Modify: `worklog/active/monitoring/20260421-001-股票持续监测跟踪功能.md`

**Repo policy note**

- This repo forbids commits without explicit user approval. Ignore the generic “commit every task” pattern while executing this plan unless the user explicitly asks for a commit.

### Task 1: Persistence Foundation and Theme Catalog Baseline

**Files:**
- Modify: `src/storage.py`
- Create: `src/repositories/watch_repo.py`
- Create: `src/data/watch_theme_catalog.json`
- Create: `src/services/watch_theme_catalog_service.py`
- Test: `tests/test_watch_repo.py`
- Test: `tests/test_watch_theme_catalog_service.py`

- [ ] **Step 1: Write failing persistence tests**

Write tests that assert:

- `watch_targets`, `watch_target_members`, `watch_signal_events`, `watch_review_results` can be inserted and queried from a temporary SQLite DB.
- `watch_signal_events.dedupe_key` is unique and duplicate saves update rather than duplicate.
- `watch_review_results` is unique by `signal_event_id + review_round`.

- [ ] **Step 2: Run the new repo tests and verify they fail for missing tables/repository**

Run: `pytest tests/test_watch_repo.py tests/test_watch_theme_catalog_service.py -q`

Expected: failures for missing watch models/repository/service.

- [ ] **Step 3: Implement storage models and repository**

Add SQLAlchemy models to `src/storage.py` and implement a focused `WatchRepository` that supports:

- create/list/update/delete targets
- replace members for one target
- upsert candidate event by `dedupe_key`
- save/get latest review
- paginated list queries for targets and events

- [ ] **Step 4: Add curated theme catalog and loader**

Create `src/data/watch_theme_catalog.json` with a small but real baseline set of themes. Include a few representative entries such as:

- 算力
- CPO/光模块
- 机器人
- 半导体

Each theme should map to representative stocks and relevant ETFs only. The service should return normalized baskets and reject unknown themes as unsupported.

- [ ] **Step 5: Re-run persistence tests**

Run: `pytest tests/test_watch_repo.py tests/test_watch_theme_catalog_service.py -q`

Expected: PASS.

### Task 2: Watchlist Service and Candidate Signal Detection

**Files:**
- Create: `src/services/watchlist_service.py`
- Create: `src/services/watch_signal_service.py`
- Modify: `src/repositories/watch_repo.py`
- Test: `tests/test_watch_signal_service.py`

- [ ] **Step 1: Write failing service tests**

Write tests that assert:

- stock/ETF targets are normalized into one active member
- theme targets expand into multiple members from the catalog
- unknown themes become `unsupported`
- signal scan over 30-day bars can produce a candidate only when trend/signal conditions are met
- repeated scans for the same day/member reuse the same candidate event via `dedupe_key`

- [ ] **Step 2: Run targeted tests and confirm RED**

Run: `pytest tests/test_watch_signal_service.py -q`

Expected: failures for missing services or candidate logic.

- [ ] **Step 3: Implement WatchlistService**

Implement target creation/update rules:

- detect `stock` vs `etf` using existing code normalization
- resolve `theme` only from the local catalog
- replace member basket on create/refresh
- surface explicit `unsupported` status for unresolved themes

- [ ] **Step 4: Implement WatchSignalService**

Implement a pure service that:

- fetches daily bars via existing stock repository/data-provider path
- limits evaluation to the latest 30-day history
- reuses `StockTrendAnalyzer`
- emits a candidate only when buy-signal, MA support, MACD/volume constraints, and anti-chasing threshold all align

- [ ] **Step 5: Re-run signal tests**

Run: `pytest tests/test_watch_signal_service.py -q`

Expected: PASS.

### Task 3: Runtime Worker, Event Bus, and Review Flow

**Files:**
- Create: `src/services/watch_event_bus.py`
- Create: `src/services/watch_review_service.py`
- Create: `src/services/watch_runtime_service.py`
- Modify: `api/deps.py`
- Test: `tests/test_watch_runtime_service.py`

- [ ] **Step 1: Write failing runtime tests**

Write tests that assert:

- runtime starts without duplicate scheduler registration
- runtime stop flips the enabled flag and prevents scan work
- one cycle scans only active targets
- candidate events publish watch-specific SSE messages
- review failures mark events as `review_failed` without crashing the cycle

- [ ] **Step 2: Run targeted runtime tests and confirm RED**

Run: `pytest tests/test_watch_runtime_service.py -q`

Expected: failures for missing runtime/event bus/review service.

- [ ] **Step 3: Implement WatchEventBus**

Provide a watch-specific pub/sub broadcaster with:

- subscribe/unsubscribe
- `publish(event_type, payload)`
- async queue friendly behavior mirroring current SSE style without coupling to `AnalysisTaskQueue`

- [ ] **Step 4: Implement WatchReviewService**

Implement structured candidate review that:

- loads the candidate event
- fetches historical analysis/backtest summary context only
- builds a compact LLM prompt/input
- parses the review result into `buyable/watch_more/reject`
- stores review rows with `review_round`

- [ ] **Step 5: Implement WatchRuntimeService**

Implement runtime lifecycle with:

- one-time background registration
- in-memory enabled flag
- `start()`, `stop()`, `status()`
- cycle method that scans members, upserts candidates, and dispatches reviews

- [ ] **Step 6: Re-run runtime tests**

Run: `pytest tests/test_watch_runtime_service.py -q`

Expected: PASS.

### Task 4: Watch API Schemas and Endpoints

**Files:**
- Create: `api/v1/schemas/watch.py`
- Create: `api/v1/endpoints/watch.py`
- Modify: `api/v1/router.py`
- Modify: `api/deps.py`
- Test: `tests/test_watch_api.py`

- [ ] **Step 1: Write failing API tests**

Cover:

- create/list/update/delete target
- refresh theme basket
- runtime start/stop/status
- paginated event list with filters
- event detail returning latest review
- stream endpoint basic handshake / payload shape

- [ ] **Step 2: Run the API tests and confirm RED**

Run: `pytest tests/test_watch_api.py -q`

Expected: failures for missing schemas/endpoints/dependencies.

- [ ] **Step 3: Implement watch schemas and endpoints**

Follow the existing endpoint style:

- query params use `page`/`limit`
- 404/400/500 payloads follow current error format
- inject shared services through `api/deps.py`
- register `/api/v1/watch` in `api/v1/router.py`

- [ ] **Step 4: Re-run API tests**

Run: `pytest tests/test_watch_api.py -q`

Expected: PASS.

### Task 5: Web Watch Page, API Client, and SSE Hook

**Files:**
- Create: `apps/dsa-web/src/types/watch.ts`
- Create: `apps/dsa-web/src/api/watch.ts`
- Create: `apps/dsa-web/src/hooks/useWatchStream.ts`
- Create: `apps/dsa-web/src/pages/WatchPage.tsx`
- Modify: `apps/dsa-web/src/App.tsx`
- Modify: `apps/dsa-web/src/components/layout/SidebarNav.tsx`
- Test: `apps/dsa-web/tests/watch-page.test.tsx`

- [ ] **Step 1: Write failing frontend tests**

Cover:

- sidebar contains the new “跟踪” nav entry
- `/watch` route renders the page under `Shell`
- page can load target/event lists from mocked API
- runtime start/stop button triggers API calls
- SSE updates can append or refresh candidate event state

- [ ] **Step 2: Run the frontend test and confirm RED**

Run: `cd apps/dsa-web && npm test -- watch-page`

Expected: failure for missing route/page/api client.

- [ ] **Step 3: Implement watch client/types/hook**

Follow existing patterns from `backtestApi` and page-level state:

- `watch.ts` types mirror backend schemas
- `watchApi` uses axios with snake_case request params and camelCase conversion
- `useWatchStream` owns EventSource lifecycle and watch event parsing

- [ ] **Step 4: Implement WatchPage and navigation**

Add:

- route in `App.tsx`
- one nav item in `SidebarNav.tsx`
- page sections for runtime status, target list, event list, detail panel

- [ ] **Step 5: Re-run frontend test**

Run: `cd apps/dsa-web && npm test -- watch-page`

Expected: PASS.

### Task 6: Config, Docs, Changelog, and Final Verification

**Files:**
- Modify: `.env.example`
- Modify: `docs/full-guide.md`
- Modify: `docs/full-guide_EN.md`
- Modify: `docs/CHANGELOG.md`
- Modify: `worklog/active/monitoring/20260421-001-股票持续监测跟踪功能.md`

- [ ] **Step 1: Add config documentation**

Document:

- `WATCHLIST_ENABLED`
- `WATCHLIST_SCAN_INTERVAL_MINUTES`
- `WATCHLIST_HISTORY_LOOKBACK_DAYS`
- `WATCHLIST_SIGNAL_COOLDOWN_MINUTES`
- `WATCHLIST_MAX_REVIEW_PER_CYCLE`

- [ ] **Step 2: Update user-facing docs**

Add concise usage instructions for:

- creating stock/ETF/theme targets
- starting/stopping runtime
- reading candidate review results
- first-version limitation that themes come from built-in catalog

- [ ] **Step 3: Update changelog and worklog status**

Append flat `[Unreleased]` entries in `docs/CHANGELOG.md` and update the monitoring worklog current status.

- [ ] **Step 4: Run backend verification**

Run:

`python -m py_compile src/storage.py src/repositories/watch_repo.py src/services/watch_theme_catalog_service.py src/services/watchlist_service.py src/services/watch_signal_service.py src/services/watch_review_service.py src/services/watch_event_bus.py src/services/watch_runtime_service.py api/deps.py api/v1/schemas/watch.py api/v1/endpoints/watch.py api/v1/router.py`

`pytest tests/test_watch_repo.py tests/test_watch_theme_catalog_service.py tests/test_watch_signal_service.py tests/test_watch_runtime_service.py tests/test_watch_api.py -q`

- [ ] **Step 5: Run frontend verification**

Run:

`cd apps/dsa-web && npm run lint`

`cd apps/dsa-web && npm run build`

`cd apps/dsa-web && npm test -- watch-page`

- [ ] **Step 6: Record verification gaps if anything cannot run**

Before closing the task, capture exactly which commands passed, which were not run, and what risks remain.
