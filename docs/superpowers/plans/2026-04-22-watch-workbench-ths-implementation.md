# Watch 工作台与同花顺式行情区实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `/watch` 升级成支持手动刷新、主动扫描和同花顺式基础行情区的连续跟踪工作台。

**Architecture:** 后端新增主动扫描接口并扩展 detail 数据契约；前端把 `/watch` 改造成三栏工作台，采用组件化行情区替换当前简化 SVG K 线。优先完成 P0：主动扫描闭环、detail 自动同步、基础同花顺排版与副图指标切换。

**Tech Stack:** FastAPI, SQLAlchemy, React 19, TypeScript, Recharts, Vitest, pytest。

---

## 文件结构

**后端**

- Modify: `src/services/watch_runtime_service.py`
- Modify: `api/v1/endpoints/watch.py`
- Modify: `api/v1/schemas/watch.py`
- Modify: `src/services/watch_detail_service.py`
- Modify: `src/repositories/watch_repo.py`
- Test: `tests/test_watch_runtime_service.py`
- Test: `tests/test_watch_api.py`
- Test: `tests/test_watch_detail_service.py`

**前端**

- Modify: `apps/dsa-web/src/types/watch.ts`
- Modify: `apps/dsa-web/src/api/watch.ts`
- Modify: `apps/dsa-web/src/pages/WatchPage.tsx`
- Create: `apps/dsa-web/src/components/watch/WatchToolbar.tsx`
- Create: `apps/dsa-web/src/components/watch/WatchTargetList.tsx`
- Create: `apps/dsa-web/src/components/watch/WatchChartPanel.tsx`
- Create: `apps/dsa-web/src/components/watch/WatchSidePanel.tsx`
- Test: `apps/dsa-web/tests/watch-page.test.tsx`

**文档**

- Modify: `docs/CHANGELOG.md`
- Modify: `docs/full-guide.md`
- Modify: `docs/full-guide_EN.md`
- Modify: `worklog/active/monitoring/20260422-001-连续跟踪工作台与同花顺式行情区改造.md`

## 执行批次

1. **Batch A**：后端主动扫描接口与 detail 契约扩展
2. **Batch B**：前端工作台骨架与操作按钮
3. **Batch C**：图表主副图、交互、detail 自动同步
4. **Batch D**：验证与文档

### Task 1: 后端主动扫描闭环

**Files:**
- Modify: `src/services/watch_runtime_service.py`
- Modify: `api/v1/endpoints/watch.py`
- Modify: `api/v1/schemas/watch.py`
- Test: `tests/test_watch_runtime_service.py`
- Test: `tests/test_watch_api.py`

- [ ] 先写 failing tests，覆盖：
  - `POST /api/v1/watch/runtime/scan`
  - `POST /api/v1/watch/targets/{id}/scan`
  - runtime 关闭时仍可扫描
  - 返回处理数、事件数、扫描时间、错误信息
- [ ] 跑后端测试确认 RED
- [ ] 在 runtime service 新增：
  - `run_cycle(force=False)`
  - `run_target_cycle(target_id)`
  - 必要时抽出单目标扫描内部方法
- [ ] 暴露两个新接口并补 schema
- [ ] 复跑测试确认 GREEN

### Task 2: detail 数据契约扩展

**Files:**
- Modify: `src/services/watch_detail_service.py`
- Modify: `api/v1/schemas/watch.py`
- Modify: `api/v1/endpoints/watch.py`
- Test: `tests/test_watch_detail_service.py`
- Test: `tests/test_watch_api.py`

- [ ] 先写 failing tests，覆盖：
  - `timeframe=intraday/day/week/month`
  - `window=30/60/120/250/ytd`
  - detail 返回 `overlays/subIndicators/quoteSnapshot/meta`
- [ ] 跑测试确认 RED
- [ ] 扩展 detail 服务，返回：
  - OHLCV 序列
  - MA5/10/20 序列
  - VOL MA、MACD、RSI 序列
  - 最新行情摘要字段
- [ ] 扩展 API schema 和参数校验
- [ ] 复跑测试确认 GREEN

### Task 3: 前端工作台骨架

**Files:**
- Modify: `apps/dsa-web/src/pages/WatchPage.tsx`
- Create: `apps/dsa-web/src/components/watch/WatchToolbar.tsx`
- Create: `apps/dsa-web/src/components/watch/WatchTargetList.tsx`
- Create: `apps/dsa-web/src/components/watch/WatchSidePanel.tsx`
- Modify: `apps/dsa-web/src/api/watch.ts`
- Modify: `apps/dsa-web/src/types/watch.ts`
- Test: `apps/dsa-web/tests/watch-page.test.tsx`

- [ ] 先写 failing tests，覆盖：
  - 顶部工具条显示 `刷新数据/全量扫描一次/启动停止`
  - 目标卡片或主行情区支持 `仅扫描当前目标`
  - 页面切成三栏工作台
- [ ] 跑前端测试确认 RED
- [ ] 新增工具条、目标列表、右侧面板组件
- [ ] 在目标列表和主行情区都明确放置 `仅扫描当前目标` 入口，避免隐藏在次级交互里
- [ ] 页面状态拆分，保留旧 detail 内容并叠加 loading
- [ ] API 封装补主动扫描方法与扩展 detail 参数
- [ ] 复跑测试确认 GREEN

### Task 4: 同花顺式行情区

**Files:**
- Create: `apps/dsa-web/src/components/watch/WatchChartPanel.tsx`
- Modify: `apps/dsa-web/src/pages/WatchPage.tsx`
- Modify: `apps/dsa-web/src/types/watch.ts`
- Test: `apps/dsa-web/tests/watch-page.test.tsx`

- [ ] 先写 failing tests，覆盖：
  - 周期切换 `分时/日K/周K/月K`
  - 日 K 二级区间切换
  - 副图切换 `VOL/MACD/RSI`
  - tooltip / 信息栏 / 支撑压力显示
- [ ] 跑前端测试确认 RED
- [ ] 用 `recharts` 实现：
  - 主图 K 线 + MA
  - 副图 `VOL/MACD/RSI`
  - 十字光标、tooltip、信息栏、坐标轴
- [ ] 对齐 A 股涨红跌绿配色
- [ ] 复跑测试确认 GREEN

### Task 5: SSE 联动与验证

**Files:**
- Modify: `apps/dsa-web/src/pages/WatchPage.tsx`
- Modify: `apps/dsa-web/src/hooks/useWatchStream.ts`
- Test: `apps/dsa-web/tests/watch-page.test.tsx`
- Modify: `docs/CHANGELOG.md`
- Modify: `docs/full-guide.md`
- Modify: `docs/full-guide_EN.md`
- Modify: `worklog/active/monitoring/20260422-001-连续跟踪工作台与同花顺式行情区改造.md`

- [ ] 补测试：当前 target 收到扫描结果后自动刷新 detail
- [ ] 页面展示扫描状态、连接状态、上次扫描时间、最近错误
- [ ] 跑 `npm test -- watch-page`
- [ ] 跑 `npm run lint && npm run build`
- [ ] 跑 watch 后端 pytest
- [ ] 更新文档与 worklog
