# Watch Target Summary & Detail Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing `/watch` module so each target shows a 7-trading-day summary in the list, and clicking a target opens an on-page detail panel with `7日 / 30日` K-line data plus strategy details for stocks, ETFs, and curated themes.

**Architecture:** Add a watch snapshot layer and two focused backend services: one for target-level summaries and one for on-demand detail payloads. Keep the existing runtime/event pipeline intact, refresh only list summaries during background scans, and load detail/K-line data on demand from a dedicated target detail API used by the current `/watch` page.

**Tech Stack:** FastAPI, SQLAlchemy/SQLite, existing watch services/repositories, pandas-based technical analysis, React + TypeScript + axios + existing card/badge UI primitives.

---

## File Structure

**Backend persistence and service layer**

- Modify: `src/storage.py`
- Modify: `src/repositories/watch_repo.py`
- Create: `src/services/watch_summary_service.py`
- Create: `src/services/watch_detail_service.py`
- Modify: `src/services/watchlist_service.py`
- Modify: `src/services/watch_runtime_service.py`
- Modify: `api/deps.py`
- Modify: `api/v1/schemas/watch.py`
- Modify: `api/v1/endpoints/watch.py`

**Tests**

- Create: `tests/test_watch_summary_service.py`
- Create: `tests/test_watch_detail_service.py`
- Modify: `tests/test_watch_runtime_service.py`
- Modify: `tests/test_watch_api.py`

**Frontend**

- Modify: `apps/dsa-web/src/types/watch.ts`
- Modify: `apps/dsa-web/src/api/watch.ts`
- Modify: `apps/dsa-web/src/pages/WatchPage.tsx`
- Modify: `apps/dsa-web/tests/watch-page.test.tsx`

**Docs / worklog**

- Modify: `docs/CHANGELOG.md`
- Modify: `docs/full-guide.md`
- Modify: `docs/full-guide_EN.md`
- Modify: `worklog/active/monitoring/20260421-001-股票持续监测跟踪功能.md`

**Repo policy note**

- This repo forbids commits without explicit user approval. Ignore the generic “commit every task” pattern unless the user explicitly asks for a commit.

## Execution Batches

To keep agent-team execution safe and avoid overlapping write sets, execute in this order:

1. **Batch A (serial):** snapshot persistence + summary generation
   - touches storage/repo/watchlist service and must land first
2. **Batch B (parallel):**
   - **Backend track:** detail service + API extensions
   - **Frontend track:** `/watch` page summary/detail panel using the approved API contract
3. **Batch C (serial):** runtime summary refresh + docs + final verification

`WatchSummaryService` must reuse the existing watch stack’s data-loading/analyzer conventions instead of inventing a second analytics pipeline:

- reuse the same stock-bar loading path style already used by `WatchSignalService`
- reuse existing analyzer output shape from `StockTrendAnalyzer`
- do **not** modify `data_provider/*` or `src/stock_analyzer.py` for this feature unless a later blocker proves it necessary
- keep `WatchSignalService` limited to candidate-event detection only; do not move snapshot persistence or detail assembly responsibilities into it

### Task 1: Snapshot Persistence and Summary Generation

**Files:**
- Modify: `src/storage.py`
- Modify: `src/repositories/watch_repo.py`
- Create: `src/services/watch_summary_service.py`
- Modify: `src/services/watchlist_service.py`
- Test: `tests/test_watch_summary_service.py`
- Test: `tests/test_watch_repo.py`

- [ ] **Step 1: Write the failing snapshot/service tests**

Add tests that prove:

- `watch_target_snapshots` can be saved and reloaded by `target_id + summary_window_days`
- snapshot status supports `pending` / `ready` / `failed`
- `WatchSummaryService.refresh_target_snapshot(target_id)` computes a stock/ETF snapshot from 30 bars while summarizing the latest 7 trading bars
- theme targets aggregate member summaries and choose a representative member
- creating a target triggers immediate summary generation so the next `GET /api/v1/watch/targets` can return a non-empty `summary` without waiting for runtime scans

- [ ] **Step 2: Run the new summary tests and verify they fail**

Run: `.venv/bin/python -m pytest tests/test_watch_summary_service.py tests/test_watch_repo.py -q`

Expected: FAIL because snapshot model/repo/service behavior is missing.

- [ ] **Step 3: Add snapshot persistence**

Implement `watch_target_snapshots` in `src/storage.py` and repository helpers in `src/repositories/watch_repo.py`:

- upsert snapshot by `target_id + summary_window_days`
- fetch one snapshot
- include summary payload assembly helpers

- [ ] **Step 4: Implement WatchSummaryService**

Implement a focused service that:

- loads the latest 30 trading bars per security
- computes indicator state via existing analyzer inputs
- derives 7-day return/high-low/summary brief
- aggregates theme summaries and picks a representative member

- [ ] **Step 5: Trigger initial summary generation on target creation**

Modify `WatchlistService.create_target()` so target creation immediately attempts `refresh_target_snapshot(target.id)` without failing the main create path.

If the immediate refresh throws, persist a `failed` or `pending` snapshot row rather than relying only on list-response fallback logic.

- [ ] **Step 5a: Verify immediate post-create summary availability**

Run a targeted test that creates one watch target, immediately fetches the target list, and verifies `summary.status` is `ready` or `failed` but not absent.

Run: `.venv/bin/python -m pytest tests/test_watch_summary_service.py -q`

Expected: PASS for the post-create summary availability case.

- [ ] **Step 6: Re-run the snapshot/summary tests**

Run: `.venv/bin/python -m pytest tests/test_watch_summary_service.py tests/test_watch_repo.py -q`

Expected: PASS.

### Task 2: On-Demand Target Detail Service

**Files:**
- Create: `src/services/watch_detail_service.py`
- Modify: `src/repositories/watch_repo.py`
- Test: `tests/test_watch_detail_service.py`

- [ ] **Step 1: Write the failing detail service tests**

Add tests that prove:

- target detail supports `window=7` and `window=30`
- stock/ETF targets return one active member and one K-line series
- theme targets return summary + member options + representative default member
- `latest_review` is bound to the selected active member’s latest event review, not any event under the target

- [ ] **Step 2: Run the detail tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_watch_detail_service.py -q`

Expected: FAIL because the detail service does not exist yet.

- [ ] **Step 3: Implement WatchDetailService**

Return one detail payload per request with:

- `target`
- `summary`
- `member_options`
- `active_member`
- `kline`
- `indicators`
- `strategy_insights`
- `latest_review`

Use current watch repo data and the existing analyzer output shape; do not add unrelated abstractions.

- [ ] **Step 4: Re-run the detail tests**

Run: `.venv/bin/python -m pytest tests/test_watch_detail_service.py -q`

Expected: PASS.

### Task 3: Runtime Summary Refresh

**Files:**
- Modify: `src/services/watch_runtime_service.py`
- Modify: `tests/test_watch_runtime_service.py`

- [ ] **Step 1: Extend runtime tests first**

Add failing coverage that proves:

- each background cycle refreshes target snapshots for active targets
- snapshot refresh failure does not stop candidate scan / review flow
- runtime still preserves the existing single-registration semantics

- [ ] **Step 2: Run runtime tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_watch_runtime_service.py -q`

Expected: FAIL due to missing summary refresh integration.

- [ ] **Step 3: Integrate summary refresh into WatchRuntimeService**

After each active target scan, invoke summary refresh for that target and record failures without crashing the cycle.

- [ ] **Step 4: Re-run runtime tests**

Run: `.venv/bin/python -m pytest tests/test_watch_runtime_service.py -q`

Expected: PASS.

### Task 4: Watch API Extension for Summary and Detail

**Files:**
- Modify: `api/deps.py`
- Modify: `api/v1/schemas/watch.py`
- Modify: `api/v1/endpoints/watch.py`
- Modify: `tests/test_watch_api.py`

- [ ] **Step 1: Extend API tests first**

Add failing coverage that proves:

- `GET /api/v1/watch/targets` includes stable `summary` payloads (`pending` / `ready` / `failed`)
- `GET /api/v1/watch/targets/{id}/detail?window=7`
- `GET /api/v1/watch/targets/{id}/detail?window=30`
- theme detail supports `member_code`

- [ ] **Step 2: Run API tests and verify RED**

Run: `.venv/bin/python -m pytest tests/test_watch_api.py -q`

Expected: FAIL because target detail API and summary serialization are not implemented yet.

- [ ] **Step 3: Implement dependency wiring and endpoint changes**

Add shared dependencies for summary/detail services and update endpoints so:

- list targets returns `summary`
- detail endpoint returns the structured payload from `WatchDetailService`
- create target remains lightweight and frontend refreshes through the list endpoint

- [ ] **Step 4: Re-run API tests**

Run: `.venv/bin/python -m pytest tests/test_watch_api.py -q`

Expected: PASS.

Backend execution note:

- Task 2 and Task 4 are **serial inside the backend track**
- do not dispatch them to separate parallel backend workers because they share API/backend surfaces and would create avoidable merge conflict risk

### Task 5: `/watch` Page Summary Cards and Detail Panel

**Files:**
- Modify: `apps/dsa-web/src/types/watch.ts`
- Modify: `apps/dsa-web/src/api/watch.ts`
- Modify: `apps/dsa-web/src/pages/WatchPage.tsx`
- Modify: `apps/dsa-web/tests/watch-page.test.tsx`

- [ ] **Step 1: Extend the frontend tests first**

Add failing coverage that proves:

- target cards render 7-day summary fields
- clicking a target opens target detail instead of event-only detail
- detail panel supports `7日 / 30日` switching
- theme detail shows member options and updates when a member is selected

- [ ] **Step 2: Run the watch page tests and verify RED**

Run: `cd apps/dsa-web && npm test -- watch-page`

Expected: FAIL because summary/detail panel behavior is incomplete.

This task is safe to run in parallel with Task 4 **after Task 1 is merged**, because its write scope is frontend-only and it targets the stable API contract from the spec:

- `GET /api/v1/watch/targets` returns `summary`
- `GET /api/v1/watch/targets/{id}/detail`

- [ ] **Step 3: Extend types and API client**

Add `summary` on target items and a new `getTargetDetail()` API client that accepts `window` and optional `memberCode`.

- [ ] **Step 4: Implement the page changes**

Update `WatchPage.tsx` so it:

- renders summary on each target card
- uses target-click to open the detail panel
- supports `7日 / 30日`
- shows K-line/indicator/strategy sections
- supports theme member switching with representative default selection

- [ ] **Step 5: Re-run the watch page tests**

Run: `cd apps/dsa-web && npm test -- watch-page`

Expected: PASS.

### Task 6: Docs, Changelog, and Full Verification

**Files:**
- Modify: `docs/CHANGELOG.md`
- Modify: `docs/full-guide.md`
- Modify: `docs/full-guide_EN.md`
- Modify: `worklog/active/monitoring/20260421-001-股票持续监测跟踪功能.md`

- [ ] **Step 1: Update docs for the new watch UX**

Document:

- 7-day summary cards
- on-demand `7日 / 30日` detail panel
- theme representative member behavior

- [ ] **Step 2: Update changelog and worklog**

Append flat `[Unreleased]` entries and update the monitoring worklog current status.

- [ ] **Step 3: Run backend verification**

Run:

`.venv/bin/python -m pytest tests/test_watch_repo.py tests/test_watch_theme_catalog_service.py tests/test_watch_signal_service.py tests/test_watch_runtime_service.py tests/test_watch_api.py tests/test_watch_summary_service.py tests/test_watch_detail_service.py -q`

`.venv/bin/python -m py_compile src/storage.py src/repositories/watch_repo.py src/services/watch_theme_catalog_service.py src/services/watchlist_service.py src/services/watch_signal_service.py src/services/watch_summary_service.py src/services/watch_detail_service.py src/services/watch_event_bus.py src/services/watch_review_service.py src/services/watch_runtime_service.py api/app.py api/deps.py api/v1/schemas/watch.py api/v1/endpoints/watch.py api/v1/router.py src/config.py`

- [ ] **Step 4: Run frontend verification**

Run:

`cd apps/dsa-web && npm test -- watch-page`

`cd apps/dsa-web && npm run lint`

`cd apps/dsa-web && npm run build`

- [ ] **Step 5: Record any gaps**

Before closing, record exactly what passed, what was not run, and any residual risks around chart rendering or theme member UX.
