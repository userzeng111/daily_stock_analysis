# BackTestSystem 独立回测子系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `BackTestSystem/` 内落地一个可独立运行的前后端分离回测子系统，完成样例 CSV 导入、多指标信号生成、日线回测、结果看板与 K 线联动分析的 P0 闭环。

**Architecture:** 后端在 `BackTestSystem/` 根目录下使用 `uv + FastAPI + SQLAlchemy + pandas` 建立独立工程，按 `infra / repositories / services / core / api` 分层；前端使用独立 `React + Vite + TypeScript` 工程，按 `pages / components / api / stores / charts` 分层。P0 严格限定为单数据集、单标的、单策略、单 run 视角，先完成从 `BackTestSystem/Data/test_exports/*.csv` 到导入、计算、回测、展示的最小可用链路。

**Tech Stack:** uv, Python 3.12, FastAPI, SQLAlchemy, Pydantic, pandas, numpy, pytest, React 19, Vite 7, TypeScript, Zustand, Recharts, Vitest.

---

## 文件结构

**数据与配置**

- Create: `BackTestSystem/pyproject.toml`
- Create: `BackTestSystem/.env.example`
- Create: `BackTestSystem/README.md`
- Create: `BackTestSystem/data/.gitkeep`

**后端工程**

- Create: `BackTestSystem/backend/src/backtest_system/__init__.py`
- Create: `BackTestSystem/backend/src/backtest_system/main.py`
- Create: `BackTestSystem/backend/src/backtest_system/infra/settings.py`
- Create: `BackTestSystem/backend/src/backtest_system/infra/db.py`
- Create: `BackTestSystem/backend/src/backtest_system/infra/csv_importer.py`
- Create: `BackTestSystem/backend/src/backtest_system/infra/file_store.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/models.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/indicators/moving_average.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/indicators/macd.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/indicators/rsi.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/indicators/volume.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/strategies/trend_following.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/strategies/scoring.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/strategies/signal_rules.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/engine/executor.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/engine/portfolio.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/engine/metrics.py`
- Create: `BackTestSystem/backend/src/backtest_system/repositories/dataset_repo.py`
- Create: `BackTestSystem/backend/src/backtest_system/repositories/bar_repo.py`
- Create: `BackTestSystem/backend/src/backtest_system/repositories/indicator_repo.py`
- Create: `BackTestSystem/backend/src/backtest_system/repositories/strategy_repo.py`
- Create: `BackTestSystem/backend/src/backtest_system/repositories/backtest_repo.py`
- Create: `BackTestSystem/backend/src/backtest_system/repositories/summary_repo.py`
- Create: `BackTestSystem/backend/src/backtest_system/services/import_service.py`
- Create: `BackTestSystem/backend/src/backtest_system/services/indicator_service.py`
- Create: `BackTestSystem/backend/src/backtest_system/services/strategy_service.py`
- Create: `BackTestSystem/backend/src/backtest_system/services/backtest_service.py`
- Create: `BackTestSystem/backend/src/backtest_system/services/summary_service.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/router.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/endpoints/imports.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/endpoints/datasets.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/endpoints/strategies.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/endpoints/backtests.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/endpoints/market_data.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/endpoints/summaries.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/schemas/import_schema.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/schemas/dataset_schema.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/schemas/strategy_schema.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/schemas/backtest_schema.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/schemas/summary_schema.py`

**后端测试**

- Create: `BackTestSystem/tests/backend/test_app_smoke.py`
- Create: `BackTestSystem/tests/backend/test_csv_importer.py`
- Create: `BackTestSystem/tests/backend/test_indicator_engine.py`
- Create: `BackTestSystem/tests/backend/test_signal_rules.py`
- Create: `BackTestSystem/tests/backend/test_backtest_engine.py`
- Create: `BackTestSystem/tests/backend/test_backtest_api.py`
- Create: `BackTestSystem/tests/backend/test_market_data_api.py`

**前端工程**

- Create: `BackTestSystem/frontend/package.json`
- Create: `BackTestSystem/frontend/tsconfig.json`
- Create: `BackTestSystem/frontend/tsconfig.node.json`
- Create: `BackTestSystem/frontend/vite.config.ts`
- Create: `BackTestSystem/frontend/index.html`
- Create: `BackTestSystem/frontend/src/main.tsx`
- Create: `BackTestSystem/frontend/src/App.tsx`
- Create: `BackTestSystem/frontend/src/app/router.tsx`
- Create: `BackTestSystem/frontend/src/api/client.ts`
- Create: `BackTestSystem/frontend/src/api/imports.ts`
- Create: `BackTestSystem/frontend/src/api/strategies.ts`
- Create: `BackTestSystem/frontend/src/api/backtests.ts`
- Create: `BackTestSystem/frontend/src/api/marketData.ts`
- Create: `BackTestSystem/frontend/src/types/imports.ts`
- Create: `BackTestSystem/frontend/src/types/strategies.ts`
- Create: `BackTestSystem/frontend/src/types/backtests.ts`
- Create: `BackTestSystem/frontend/src/types/marketData.ts`
- Create: `BackTestSystem/frontend/src/stores/backtestStore.ts`
- Create: `BackTestSystem/frontend/src/components/layout/BacktestShell.tsx`
- Create: `BackTestSystem/frontend/src/components/import/ImportWorkspace.tsx`
- Create: `BackTestSystem/frontend/src/components/strategy/StrategyWorkspace.tsx`
- Create: `BackTestSystem/frontend/src/components/run/ExecutionWorkspace.tsx`
- Create: `BackTestSystem/frontend/src/components/results/ResultDashboard.tsx`
- Create: `BackTestSystem/frontend/src/components/charts/ChartWorkspace.tsx`
- Create: `BackTestSystem/frontend/src/pages/ImportPage.tsx`
- Create: `BackTestSystem/frontend/src/pages/StrategyPage.tsx`
- Create: `BackTestSystem/frontend/src/pages/RunPage.tsx`
- Create: `BackTestSystem/frontend/src/pages/ResultsPage.tsx`
- Create: `BackTestSystem/frontend/src/pages/ChartPage.tsx`
- Create: `BackTestSystem/frontend/src/tests/app.smoke.test.tsx`
- Create: `BackTestSystem/frontend/src/tests/results-page.test.tsx`
- Create: `BackTestSystem/frontend/src/tests/chart-page.test.tsx`

**文档与记录**

- Modify: `docs/CHANGELOG.md`
- Modify: `worklog/active/backtest-system/20260422-001-BackTestSystem-子模块回测平台建设.md`

## 执行批次

1. **Batch A:** 后端骨架、配置与导入链路
2. **Batch B:** 指标引擎、策略规则、回测内核
3. **Batch C:** 后端 API 与图表数据契约
4. **Batch D:** 前端工作台、结果页、图表联动
5. **Batch E:** 集成验证、文档与收口

### Task 1: 搭建独立工程骨架

**Files:**
- Create: `BackTestSystem/pyproject.toml`
- Create: `BackTestSystem/.env.example`
- Create: `BackTestSystem/README.md`
- Create: `BackTestSystem/backend/src/backtest_system/__init__.py`
- Create: `BackTestSystem/backend/src/backtest_system/main.py`
- Create: `BackTestSystem/backend/src/backtest_system/infra/settings.py`
- Create: `BackTestSystem/backend/src/backtest_system/infra/db.py`
- Create: `BackTestSystem/tests/backend/test_app_smoke.py`

- [ ] **Step 1: 写后端启动 smoke 测试**

覆盖点：
- `create_app()` 可返回 FastAPI app
- `GET /health` 返回 `200`
- 默认配置指向 `BackTestSystem/data`

- [ ] **Step 2: 运行测试确认 RED**

Run: `cd BackTestSystem && uv run pytest tests/backend/test_app_smoke.py -v`
Expected: FAIL，提示模块或 app 工厂不存在。

- [ ] **Step 3: 写最小实现**

实现内容：
- 在 `pyproject.toml` 定义 `fastapi / uvicorn / sqlalchemy / pydantic / pandas / numpy / pytest / httpx`
- 在 `pyproject.toml` 显式配置 `package-dir = {"": "backend/src"}` 或等效的 `setuptools` 包发现规则，确保 `uv run pytest` 可以直接导入 `backtest_system`
- 在 `.env.example` 定义 `BACKTEST_SYSTEM_DB_URL`、`BACKTEST_SYSTEM_DATA_DIR`
- 在 `settings.py` 实现最小配置加载
- 在 `db.py` 建立 SQLite engine 与 session factory
- 在 `main.py` 提供 `create_app()` 与 `/health`

- [ ] **Step 4: 运行测试确认 GREEN**

Run: `cd BackTestSystem && uv sync && uv run pytest tests/backend/test_app_smoke.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add BackTestSystem/pyproject.toml BackTestSystem/.env.example BackTestSystem/README.md BackTestSystem/backend/src/backtest_system/__init__.py BackTestSystem/backend/src/backtest_system/main.py BackTestSystem/backend/src/backtest_system/infra/settings.py BackTestSystem/backend/src/backtest_system/infra/db.py BackTestSystem/tests/backend/test_app_smoke.py
git commit -m "搭建 BackTestSystem 基础工程骨架" -m "- 新建 uv 与 FastAPI 基础结构\n- 增加配置与数据库初始化\n- 补充健康检查 smoke 测试"
```

### Task 2: 完成 CSV 导入与标准化入库

**Files:**
- Create: `BackTestSystem/backend/src/backtest_system/infra/csv_importer.py`
- Create: `BackTestSystem/backend/src/backtest_system/infra/file_store.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/models.py`
- Create: `BackTestSystem/backend/src/backtest_system/repositories/dataset_repo.py`
- Create: `BackTestSystem/backend/src/backtest_system/repositories/bar_repo.py`
- Create: `BackTestSystem/backend/src/backtest_system/services/import_service.py`
- Create: `BackTestSystem/tests/backend/test_csv_importer.py`

- [ ] **Step 1: 写 failing tests**

覆盖点：
- 可导入 `BackTestSystem/Data/test_exports/guizhou_maotai_600519_2024-01-01_to_2026-04-22.csv`
- 可导入 `BackTestSystem/Data/test_exports/sse50_000016_2024-01-01_to_2026-04-22.csv`
- 自动接受 `amount / outstanding_share / turnover` 缺省列
- 生成 `dataset / import_job / market_bar`
- 持久化 `schema_profile_json`

- [ ] **Step 2: 运行测试确认 RED**

Run: `cd BackTestSystem && uv run pytest tests/backend/test_csv_importer.py -v`
Expected: FAIL，提示导入器、模型或仓储不存在。

- [ ] **Step 3: 写最小实现**

实现内容：
- 用 SQLAlchemy 定义 `dataset / import_job / market_bar`
- `csv_importer.py` 负责字段映射、类型转换、排序、缺失列补齐
- `file_store.py` 负责原始路径与标准化文件路径管理
- `import_service.py` 负责单文件导入事务

- [ ] **Step 4: 运行测试确认 GREEN**

Run: `cd BackTestSystem && uv run pytest tests/backend/test_csv_importer.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add BackTestSystem/backend/src/backtest_system/infra/csv_importer.py BackTestSystem/backend/src/backtest_system/infra/file_store.py BackTestSystem/backend/src/backtest_system/core/models.py BackTestSystem/backend/src/backtest_system/repositories/dataset_repo.py BackTestSystem/backend/src/backtest_system/repositories/bar_repo.py BackTestSystem/backend/src/backtest_system/services/import_service.py BackTestSystem/tests/backend/test_csv_importer.py
git commit -m "实现 BackTestSystem CSV 导入链路" -m "- 支持本地路径注册导入\n- 完成日线数据标准化与入库\n- 记录 schema 元数据与导入任务"
```

### Task 3: 实现指标引擎与信号规则

**Files:**
- Create: `BackTestSystem/backend/src/backtest_system/core/indicators/moving_average.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/indicators/macd.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/indicators/rsi.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/indicators/volume.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/strategies/trend_following.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/strategies/scoring.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/strategies/signal_rules.py`
- Create: `BackTestSystem/backend/src/backtest_system/repositories/indicator_repo.py`
- Create: `BackTestSystem/backend/src/backtest_system/services/indicator_service.py`
- Create: `BackTestSystem/backend/src/backtest_system/services/strategy_service.py`
- Create: `BackTestSystem/tests/backend/test_indicator_engine.py`
- Create: `BackTestSystem/tests/backend/test_signal_rules.py`

- [ ] **Step 1: 写 failing tests**

覆盖点：
- MA5/10/20/60、MACD、RSI、volume ratio 计算口径与主项目 `v1` 一致
- 输出 `trend_status / bias / support_levels / resistance_levels`
- 输出 `buy_signal / signal_score / signal_reasons / risk_factors`

- [ ] **Step 2: 运行测试确认 RED**

Run: `cd BackTestSystem && uv run pytest tests/backend/test_indicator_engine.py tests/backend/test_signal_rules.py -v`
Expected: FAIL，提示指标或信号规则模块不存在。

- [ ] **Step 3: 写最小实现**

实现内容：
- 以主项目 `src/stock_analyzer.py` 为参考移植公式
- 保持子系统内独立实现，不直接 import 主项目运行时代码
- 将指标序列和最终信号分别落为纯函数，便于单测

- [ ] **Step 4: 运行测试确认 GREEN**

Run: `cd BackTestSystem && uv run pytest tests/backend/test_indicator_engine.py tests/backend/test_signal_rules.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add BackTestSystem/backend/src/backtest_system/core/indicators/moving_average.py BackTestSystem/backend/src/backtest_system/core/indicators/macd.py BackTestSystem/backend/src/backtest_system/core/indicators/rsi.py BackTestSystem/backend/src/backtest_system/core/indicators/volume.py BackTestSystem/backend/src/backtest_system/core/strategies/trend_following.py BackTestSystem/backend/src/backtest_system/core/strategies/scoring.py BackTestSystem/backend/src/backtest_system/core/strategies/signal_rules.py BackTestSystem/backend/src/backtest_system/repositories/indicator_repo.py BackTestSystem/backend/src/backtest_system/services/indicator_service.py BackTestSystem/backend/src/backtest_system/services/strategy_service.py BackTestSystem/tests/backend/test_indicator_engine.py BackTestSystem/tests/backend/test_signal_rules.py
git commit -m "移植 BackTestSystem 指标与信号引擎" -m "- 落地 MA MACD RSI 量能指标计算\n- 实现趋势评分与买卖信号规则\n- 通过指标与信号单测锁定口径"
```

### Task 4: 实现回测内核与 summary 统计

**Files:**
- Create: `BackTestSystem/backend/src/backtest_system/core/engine/executor.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/engine/portfolio.py`
- Create: `BackTestSystem/backend/src/backtest_system/core/engine/metrics.py`
- Create: `BackTestSystem/backend/src/backtest_system/repositories/backtest_repo.py`
- Create: `BackTestSystem/backend/src/backtest_system/repositories/summary_repo.py`
- Create: `BackTestSystem/backend/src/backtest_system/services/backtest_service.py`
- Create: `BackTestSystem/backend/src/backtest_system/services/summary_service.py`
- Create: `BackTestSystem/tests/backend/test_backtest_engine.py`

- [ ] **Step 1: 写 failing tests**

覆盖点：
- 收盘生成信号、次日开盘成交
- `BUY/SELL/HOLD/WAIT` 到交易动作映射
- 末日数据强制平仓
- 保存 `gross_return_pct / net_return_pct / max_drawdown_pct`
- 生成单 run `summary`

- [ ] **Step 2: 运行测试确认 RED**

Run: `cd BackTestSystem && uv run pytest tests/backend/test_backtest_engine.py -v`
Expected: FAIL，提示回测引擎或 summary 逻辑不存在。

- [ ] **Step 3: 写最小实现**

实现内容：
- `portfolio.py` 维护单仓位状态
- `executor.py` 顺序推进 bar、生成交易和 signal marker
- `metrics.py` 汇总胜率、收益率、回撤、收益曲线
- `backtest_service.py` 以单 `dataset + strategy_config` 启动一次 run

- [ ] **Step 4: 运行测试确认 GREEN**

Run: `cd BackTestSystem && uv run pytest tests/backend/test_backtest_engine.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add BackTestSystem/backend/src/backtest_system/core/engine/executor.py BackTestSystem/backend/src/backtest_system/core/engine/portfolio.py BackTestSystem/backend/src/backtest_system/core/engine/metrics.py BackTestSystem/backend/src/backtest_system/repositories/backtest_repo.py BackTestSystem/backend/src/backtest_system/repositories/summary_repo.py BackTestSystem/backend/src/backtest_system/services/backtest_service.py BackTestSystem/backend/src/backtest_system/services/summary_service.py BackTestSystem/tests/backend/test_backtest_engine.py
git commit -m "实现 BackTestSystem 日线回测内核" -m "- 完成单仓位顺序回测执行器\n- 输出交易收益回撤与收益曲线\n- 补齐强制平仓与 summary 统计"
```

### Task 5: 暴露后端 API 与图表数据契约

**Files:**
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/router.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/endpoints/imports.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/endpoints/datasets.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/endpoints/strategies.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/endpoints/backtests.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/endpoints/market_data.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/endpoints/summaries.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/schemas/import_schema.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/schemas/dataset_schema.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/schemas/strategy_schema.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/schemas/backtest_schema.py`
- Create: `BackTestSystem/backend/src/backtest_system/api/v1/schemas/summary_schema.py`
- Create: `BackTestSystem/tests/backend/test_backtest_api.py`
- Create: `BackTestSystem/tests/backend/test_market_data_api.py`

- [ ] **Step 1: 写 failing tests**

覆盖点：
- `POST /api/v1/imports/csv`
- `GET /api/v1/datasets`
- `GET /api/v1/datasets/{dataset_id}`
- `GET /api/v1/strategies`
- `POST /api/v1/strategies`
- `POST /api/v1/backtests`
- `GET /api/v1/backtests/{run_id}`
- `GET /api/v1/backtests/{run_id}/signals`
- `GET /api/v1/backtests/{run_id}/trades`
- `GET /api/v1/backtests/{run_id}/summary`
- `GET /api/v1/market-data/bars`
- `GET /api/v1/market-data/indicator-series`
- `GET /api/v1/market-data/signal-markers`

- [ ] **Step 2: 运行测试确认 RED**

Run: `cd BackTestSystem && uv run pytest tests/backend/test_backtest_api.py tests/backend/test_market_data_api.py -v`
Expected: FAIL，提示路由、schema 或 endpoint 不存在。

- [ ] **Step 3: 写最小实现**

实现内容：
- 路由只暴露 spec 中 P0 约定的字段
- `datasets/{dataset_id}` 返回单数据集详情与导入状态
- `POST /strategies` 支持保存单策略配置
- `GET /backtests/{run_id}` 返回 run 状态、时间范围与执行配置
- `GET /backtests/{run_id}/trades` 返回交易明细，供结果页展示
- `signals` 接口带出 `support_levels / resistance_levels`
- `indicator-series` 与 `signal-markers` 响应结构对齐 spec 示例

- [ ] **Step 3.1: 对照 spec 做接口覆盖核对**

对照表：
- `POST /api/v1/imports/csv` -> `tests/backend/test_backtest_api.py::test_import_csv`
- `GET /api/v1/datasets` -> `tests/backend/test_backtest_api.py::test_list_datasets`
- `GET /api/v1/datasets/{dataset_id}` -> `tests/backend/test_backtest_api.py::test_get_dataset_detail`
- `GET /api/v1/strategies` -> `tests/backend/test_backtest_api.py::test_list_strategies`
- `POST /api/v1/strategies` -> `tests/backend/test_backtest_api.py::test_create_strategy`
- `POST /api/v1/backtests` -> `tests/backend/test_backtest_api.py::test_create_backtest_run`
- `GET /api/v1/backtests/{run_id}` -> `tests/backend/test_backtest_api.py::test_get_backtest_run`
- `GET /api/v1/backtests/{run_id}/signals` -> `tests/backend/test_backtest_api.py::test_get_backtest_signals`
- `GET /api/v1/backtests/{run_id}/trades` -> `tests/backend/test_backtest_api.py::test_get_backtest_trades`
- `GET /api/v1/backtests/{run_id}/summary` -> `tests/backend/test_backtest_api.py::test_get_backtest_summary`
- `GET /api/v1/market-data/bars` -> `tests/backend/test_market_data_api.py::test_get_bars`
- `GET /api/v1/market-data/indicator-series` -> `tests/backend/test_market_data_api.py::test_get_indicator_series`
- `GET /api/v1/market-data/signal-markers` -> `tests/backend/test_market_data_api.py::test_get_signal_markers`

- [ ] **Step 4: 运行测试确认 GREEN**

Run: `cd BackTestSystem && uv run pytest tests/backend/test_backtest_api.py tests/backend/test_market_data_api.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add BackTestSystem/backend/src/backtest_system/api/v1/router.py BackTestSystem/backend/src/backtest_system/api/v1/endpoints/imports.py BackTestSystem/backend/src/backtest_system/api/v1/endpoints/datasets.py BackTestSystem/backend/src/backtest_system/api/v1/endpoints/strategies.py BackTestSystem/backend/src/backtest_system/api/v1/endpoints/backtests.py BackTestSystem/backend/src/backtest_system/api/v1/endpoints/market_data.py BackTestSystem/backend/src/backtest_system/api/v1/endpoints/summaries.py BackTestSystem/backend/src/backtest_system/api/v1/schemas/import_schema.py BackTestSystem/backend/src/backtest_system/api/v1/schemas/dataset_schema.py BackTestSystem/backend/src/backtest_system/api/v1/schemas/strategy_schema.py BackTestSystem/backend/src/backtest_system/api/v1/schemas/backtest_schema.py BackTestSystem/backend/src/backtest_system/api/v1/schemas/summary_schema.py BackTestSystem/tests/backend/test_backtest_api.py BackTestSystem/tests/backend/test_market_data_api.py
git commit -m "开放 BackTestSystem P0 后端接口" -m "- 暴露导入策略回测与图表接口\n- 固化信号与指标响应契约\n- 补齐 API 测试"
```

### Task 6: 搭建前端工程与应用骨架

**Files:**
- Create: `BackTestSystem/frontend/package.json`
- Create: `BackTestSystem/frontend/tsconfig.json`
- Create: `BackTestSystem/frontend/tsconfig.node.json`
- Create: `BackTestSystem/frontend/vite.config.ts`
- Create: `BackTestSystem/frontend/index.html`
- Create: `BackTestSystem/frontend/src/main.tsx`
- Create: `BackTestSystem/frontend/src/App.tsx`
- Create: `BackTestSystem/frontend/src/app/router.tsx`
- Create: `BackTestSystem/frontend/src/stores/backtestStore.ts`
- Create: `BackTestSystem/frontend/src/components/layout/BacktestShell.tsx`
- Create: `BackTestSystem/frontend/src/tests/app.smoke.test.tsx`

- [ ] **Step 1: 写 failing tests**

覆盖点：
- 应用可渲染 `BacktestShell`
- 路由存在 `导入 / 策略 / 执行 / 结果 / 图表`
- 默认进入导入页

- [ ] **Step 2: 运行测试确认 RED**

Run: `cd BackTestSystem/frontend && npm test -- --run src/tests/app.smoke.test.tsx`
Expected: FAIL，提示前端入口或路由不存在。

- [ ] **Step 3: 写最小实现**

实现内容：
- 建立独立 Vite React 工程
- 建立 `BacktestShell` 与基础路由
- 建立全局 store，先放 `selectedDatasetId / selectedRunId / selectedDate`

- [ ] **Step 4: 运行测试确认 GREEN**

Run: `cd BackTestSystem/frontend && npm install && npm test -- --run src/tests/app.smoke.test.tsx`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add BackTestSystem/frontend/package.json BackTestSystem/frontend/tsconfig.json BackTestSystem/frontend/tsconfig.node.json BackTestSystem/frontend/vite.config.ts BackTestSystem/frontend/index.html BackTestSystem/frontend/src/main.tsx BackTestSystem/frontend/src/App.tsx BackTestSystem/frontend/src/app/router.tsx BackTestSystem/frontend/src/stores/backtestStore.ts BackTestSystem/frontend/src/components/layout/BacktestShell.tsx BackTestSystem/frontend/src/tests/app.smoke.test.tsx
git commit -m "搭建 BackTestSystem 前端应用骨架" -m "- 新建独立 React Vite 工程\n- 建立基础路由与工作台壳层\n- 增加前端 smoke 测试"
```

### Task 7: 完成导入页、策略页与回测执行页

**Files:**
- Create: `BackTestSystem/frontend/src/api/client.ts`
- Create: `BackTestSystem/frontend/src/api/imports.ts`
- Create: `BackTestSystem/frontend/src/api/strategies.ts`
- Create: `BackTestSystem/frontend/src/api/backtests.ts`
- Create: `BackTestSystem/frontend/src/types/imports.ts`
- Create: `BackTestSystem/frontend/src/types/strategies.ts`
- Create: `BackTestSystem/frontend/src/types/backtests.ts`
- Create: `BackTestSystem/frontend/src/components/import/ImportWorkspace.tsx`
- Create: `BackTestSystem/frontend/src/components/strategy/StrategyWorkspace.tsx`
- Create: `BackTestSystem/frontend/src/components/run/ExecutionWorkspace.tsx`
- Create: `BackTestSystem/frontend/src/pages/ImportPage.tsx`
- Create: `BackTestSystem/frontend/src/pages/StrategyPage.tsx`
- Create: `BackTestSystem/frontend/src/pages/RunPage.tsx`
- Create: `BackTestSystem/frontend/src/tests/results-page.test.tsx`

- [ ] **Step 1: 写 failing tests**

覆盖点：
- 导入页可提交本地路径并展示导入结果
- 策略页可展示模板与参数
- 执行页可选择 `dataset` 并启动 `run`

- [ ] **Step 2: 运行测试确认 RED**

Run: `cd BackTestSystem/frontend && npm test -- --run src/tests/results-page.test.tsx`
Expected: FAIL，提示页面组件或 API client 不存在。

- [ ] **Step 3: 写最小实现**

实现内容：
- `client.ts` 统一处理 `baseURL`
- 导入页只做服务端本地路径注册
- 策略页首期只做模板选择与参数查看
- 执行页提交单 `dataset + strategy_config` run

- [ ] **Step 4: 运行测试确认 GREEN**

Run: `cd BackTestSystem/frontend && npm test -- --run src/tests/results-page.test.tsx`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add BackTestSystem/frontend/src/api/client.ts BackTestSystem/frontend/src/api/imports.ts BackTestSystem/frontend/src/api/strategies.ts BackTestSystem/frontend/src/api/backtests.ts BackTestSystem/frontend/src/types/imports.ts BackTestSystem/frontend/src/types/strategies.ts BackTestSystem/frontend/src/types/backtests.ts BackTestSystem/frontend/src/components/import/ImportWorkspace.tsx BackTestSystem/frontend/src/components/strategy/StrategyWorkspace.tsx BackTestSystem/frontend/src/components/run/ExecutionWorkspace.tsx BackTestSystem/frontend/src/pages/ImportPage.tsx BackTestSystem/frontend/src/pages/StrategyPage.tsx BackTestSystem/frontend/src/pages/RunPage.tsx BackTestSystem/frontend/src/tests/results-page.test.tsx
git commit -m "实现 BackTestSystem 导入与执行工作流" -m "- 接入导入策略与回测启动接口\n- 完成导入页策略页与执行页\n- 锁定单 run 工作流交互"
```

### Task 8: 完成结果看板与 K 线联动页

**Files:**
- Create: `BackTestSystem/frontend/src/api/marketData.ts`
- Create: `BackTestSystem/frontend/src/types/marketData.ts`
- Create: `BackTestSystem/frontend/src/components/results/ResultDashboard.tsx`
- Create: `BackTestSystem/frontend/src/components/charts/ChartWorkspace.tsx`
- Create: `BackTestSystem/frontend/src/pages/ResultsPage.tsx`
- Create: `BackTestSystem/frontend/src/pages/ChartPage.tsx`
- Create: `BackTestSystem/frontend/src/tests/chart-page.test.tsx`

- [ ] **Step 1: 写 failing tests**

覆盖点：
- 结果页展示 `KPI / 收益曲线 / 交易明细 / 信号明细 / 回撤摘要`
- 图表页展示 `K 线 + MA + MACD/RSI`
- 点击信号后可联动定位日期
- 右侧详情可显示 `support_levels / resistance_levels`

- [ ] **Step 2: 运行测试确认 RED**

Run: `cd BackTestSystem/frontend && npm test -- --run src/tests/chart-page.test.tsx`
Expected: FAIL，提示结果页或图表组件不存在。

- [ ] **Step 3: 写最小实现**

实现内容：
- 结果页围绕单 `run` 渲染，不做排名与策略对比
- `ChartWorkspace` 用 `Recharts` 实现主图与副图
- `marketData.ts` 对齐 `bars / indicator-series / signal-markers`

- [ ] **Step 4: 运行测试确认 GREEN**

Run: `cd BackTestSystem/frontend && npm test -- --run src/tests/chart-page.test.tsx`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add BackTestSystem/frontend/src/api/marketData.ts BackTestSystem/frontend/src/types/marketData.ts BackTestSystem/frontend/src/components/results/ResultDashboard.tsx BackTestSystem/frontend/src/components/charts/ChartWorkspace.tsx BackTestSystem/frontend/src/pages/ResultsPage.tsx BackTestSystem/frontend/src/pages/ChartPage.tsx BackTestSystem/frontend/src/tests/chart-page.test.tsx
git commit -m "实现 BackTestSystem 结果看板与图表联动" -m "- 完成单 run 结果页与收益曲线展示\n- 增加 K 线副图与买卖点联动\n- 展示支撑压力与信号详情"
```

### Task 9: 完成全链路验证与文档收口

**Files:**
- Modify: `BackTestSystem/README.md`
- Modify: `BackTestSystem/.env.example`
- Modify: `docs/CHANGELOG.md`
- Modify: `worklog/active/backtest-system/20260422-001-BackTestSystem-子模块回测平台建设.md`

- [ ] **Step 1: 运行后端测试**

Run: `cd BackTestSystem && uv run pytest tests/backend -v`
Expected: 全部 PASS

- [ ] **Step 2: 运行前端测试**

Run: `cd BackTestSystem/frontend && npm test -- --run`
Expected: 全部 PASS

- [ ] **Step 3: 运行构建验证**

Run: `cd BackTestSystem && uv run python -m py_compile $(find backend/src -name '*.py')`
Expected: 无报错

Run: `cd BackTestSystem/frontend && npm run build`
Expected: build 成功

- [ ] **Step 4: 用样例数据做手工 smoke**

验证点：
- 导入两份样例 CSV 成功
- 至少完成一次贵州茅台回测
- 能查看交易明细、收益曲线、K 线联动

- [ ] **Step 5: 更新文档与记录**

更新内容：
- `BackTestSystem/README.md` 写清运行方式
- `docs/CHANGELOG.md` 在 `[Unreleased]` 追加扁平条目
- `worklog` 当前状态改成“实现完成，待用户验收”或实际状态

- [ ] **Step 6: 提交**

```bash
git add BackTestSystem/README.md BackTestSystem/.env.example docs/CHANGELOG.md worklog/active/backtest-system/20260422-001-BackTestSystem-子模块回测平台建设.md
git commit -m "完成 BackTestSystem P0 验证与文档收口" -m "- 运行前后端测试与构建验证\n- 更新子系统说明与项目变更记录\n- 同步 worklog 当前状态"
```

## 并行执行建议

- `Task 1` 和 `Task 6` 不应并行，前者先确定后端目录与配置约束，后者再按约定接入 API。
- `Task 2` 可在 `Task 1` 完成后独立推进。
- `Task 3` 与 `Task 4` 可以由两个 worker 顺序接力，不建议同时改同一组 `core/` 文件。
- `Task 5` 可在 `Task 4` 接近完成时启动，但只负责 `api/` 与 `schemas/`，不要回改 `engine/`。
- `Task 7` 与 `Task 8` 可并行，但写入范围必须分开：一个只改工作流页和 API client，一个只改结果页与图表组件。

## 验收标准

- `BackTestSystem` 可在不依赖主项目运行时服务的情况下独立启动
- 两份样例 CSV 都能完成导入与标准化
- 子系统内置 `v1` 指标与信号规则可输出 MA/MACD/RSI/趋势评分/买卖信号
- 回测引擎遵循“收盘信号、次日开盘成交、末日强平”规则
- 前端可完成导入、选策略、启动 run、查看结果、查看图表联动
- 文档、`.env.example`、`docs/CHANGELOG.md`、`worklog` 已同步更新
