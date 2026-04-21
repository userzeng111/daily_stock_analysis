# 股票持续监测跟踪功能设计

## 1. 背景与目标

当前系统已经具备：

- 单次问股与首页单股分析；
- 历史分析记录与回测；
- 调度器、后台任务与 SSE 推送；
- 基于均线、MACD、量价的技术分析能力。

缺少的是“持续观察一组目标，并在运行期间主动发现阶段性买点”的闭环能力。新功能需要在不破坏现有问股、历史分析、回测页面的前提下，新增独立的连续跟踪模块。

本次设计目标：

1. 支持用户维护一组连续跟踪目标。
2. 支持三类目标：`stock`、`etf`、`theme`。
3. 系统运行期间按中频轮询持续扫描，默认 30-60 分钟一轮。
4. 基于最近 1 个月历史交易数据，复用现有技术分析逻辑识别阶段性买点候选。
5. 对候选买点再触发 LLM 复核，并结合历史分析/回测上下文给出“可行性判断”。
6. 在 Web 端提供独立的连续跟踪页面，允许启停监测、查看候选事件、查看复核结果。

## 2. 范围与边界

### 2.1 本期纳入

- A 股个股连续跟踪。
- ETF 连续跟踪。
- 主题/板块/概念词跟踪，但主题不会直接作为买点判断对象，而是展开为“代表性股票 + 相关 ETF”篮子。
- 后端周期扫描、候选事件入库、LLM 复核、Web 页面展示。
- 复用现有 `StockTrendAnalyzer`、策略聚合器、`BacktestEngine`、`Scheduler`、任务/SSE 基础设施。

### 2.2 本期明确不做

- 不替换现有首页分析、问股、历史回测逻辑。
- 不做自动卖点监测。
- 不做全市场自动选股，只对用户显式添加的目标生效。
- 不做无限制自由文本主题图谱自动构建。第一版仅支持可解析的主题目录；不在目录内的主题不进入监测篮子。
- 不引入新的外部付费主题数据源作为硬依赖。

## 3. 关键设计决策

### 3.1 单独建设连续跟踪子系统

不在现有 stock-only 分析链路上直接打补丁，而是新增独立的 watch 子系统。这样可以：

- 保留现有分析和回测行为；
- 让持续监测拥有独立的数据模型、运行状态与 UI；
- 避免首页分析、历史列表、回测记录被连续扫描结果污染。

### 3.2 跟踪对象是一等公民

新增统一目标模型 `WatchTarget`，使用 `target_type` 区分：

- `stock`
- `etf`
- `theme`

其中 `theme` 只负责表达用户关注的主题，真正执行技术信号识别的是展开后的具体证券成员。

### 3.3 主题展开采用“本地目录 + 篮子成员”模式

现有数据源缺少稳定的 `theme -> constituent stocks + ETFs` 图谱。为保证第一版可落地，采用本地主题目录作为稳定输入：

- 维护一个 repo 内置的主题目录数据文件，作为第一版唯一真源；
- 每个主题定义若干代表股与相关 ETF；
- 创建或刷新主题目标时，生成成员篮子；
- 未命中目录的主题不进入运行态，并提示用户主题暂不支持。

这比依赖在线临时搜索更稳定，也更利于后续逐步扩容目录。

### 3.4 LLM 只处理候选事件

技术扫描会周期性运行，但 LLM 成本高、响应慢，不应对全部目标每轮都调用。设计为：

- 扫描阶段先做纯规则筛选；
- 只有当具体证券满足阶段性买点候选条件时，才触发 LLM 复核；
- LLM 输入包含 30 日行情快照、技术信号摘要、主题上下文、已有历史分析与回测摘要；
- LLM 输出标准化结论，附置信度、理由、风险点。

### 3.5 回测复用策略

现有回测主要针对已落库的 `AnalysisHistory` 做事后评估，不适合直接判断一个“当前信号”未来是否成立。因此本期采用两层复用：

- 继续复用 `BacktestEngine` 和 `BacktestService` 作为历史表现上下文来源；
- 不尝试让 `BacktestEngine` 直接对当前 watch 候选事件做实时评分；
- 对当前候选事件，由新的复核服务构建“历史分析表现 + 最近 30 日技术快照”的结构化上下文，再交给 LLM 做可行性复核。

也就是说，本期的“LLM 再次回测”是“带历史回测上下文的可行性复核”，而不是对当前事件做伪未来回测。

### 3.6 运行时启停语义

现有 `Scheduler` 只支持注册后台任务，不支持动态移除任务。因此连续跟踪运行时采用“单后台 worker + 内部启停状态”的模式：

- watch 后台 worker 只注册一次；
- `start` 只切换 `enabled=true`，不会重复注册后台任务；
- `stop` 只切换 `enabled=false`，后台 worker 保留但空转；
- `status` 返回当前 enabled 状态与最近扫描时间；
- 服务重启后默认恢复为 stopped，由用户重新点击启动。

这能避免重复注册后台任务，也不需要为 `Scheduler` 追加删除 API。

## 4. 领域模型

### 4.1 WatchTarget

表示一个用户维护的持续跟踪目标。

核心字段：

- `id`
- `target_type`: `stock` / `etf` / `theme`
- `symbol`: 对于 stock / etf 为交易代码；对于 theme 为主题 slug
- `display_name`
- `input_text`: 用户原始输入
- `status`: `active` / `paused` / `unsupported`
- `resolution_state`: `resolved` / `needs_mapping` / `failed`
- `scan_interval_minutes`
- `last_scanned_at`
- `last_signal_at`
- `created_at` / `updated_at`

### 4.2 WatchTargetMember

表示一个目标的具体可扫描成员。

用途：

- stock / etf 目标也统一落成员表，便于后续调度统一处理；
- theme 目标通过成员表展开成若干 stock / etf。

核心字段：

- `target_id`
- `member_type`: `stock` / `etf`
- `member_code`
- `member_name`
- `member_role`: `direct` / `theme_stock` / `theme_etf`
- `weight`
- `is_active`

约束规则：

- `target_id + member_code + member_role` 必须唯一；
- 刷新主题篮子时按目标全量替换成员，避免重复累积旧成员。

### 4.3 WatchSignalEvent

表示一次周期扫描发现的候选买点事件。

核心字段：

- `id`
- `target_id`
- `member_code`
- `member_name`
- `event_date`
- `event_status`: `candidate` / `reviewing` / `accepted` / `rejected` / `review_failed` / `expired`
- `signal_kind`: `stage_buy_point`
- `signal_score`
- `signal_snapshot_json`
- `price_snapshot_json`
- `theme_context_json`
- `dedupe_key`
- `retry_count`
- `review_requested_at`
- `created_at`

去重规则：

- `dedupe_key` 必须有唯一约束；
- 第一版按“同一成员、同一交易日、同一信号类型、同一策略版本”去重；
- 重复扫描命中同一个 `dedupe_key` 时只更新事件时间戳与最新快照，不重复插入新事件。

### 4.4 WatchReviewResult

表示候选事件的 LLM 复核结果。

核心字段：

- `id`
- `signal_event_id`
- `decision`: `buyable` / `watch_more` / `reject`
- `confidence`
- `reason_summary`
- `risks_json`
- `backtest_context_json`
- `llm_model`
- `raw_response`
- `review_round`
- `created_at`

约束规则：

- 第一版以 `signal_event_id + review_round` 唯一；
- 默认只有一轮自动复核，后续人工或系统重试才增加 `review_round`；
- 事件详情默认展示最新一轮复核结果。

## 5. 后端架构

### 5.1 存储层

新增四张表：

- `watch_targets`
- `watch_target_members`
- `watch_signal_events`
- `watch_review_results`

落点：

- ORM 模型继续集中在 `src/storage.py`
- Repository 新增到 `src/repositories/watch_repo.py`
- 主题目录基线文件新增为 `src/data/watch_theme_catalog.json`

### 5.2 服务层拆分

新增服务：

- `WatchlistService`
  - 增删改查跟踪目标；
  - 解析 stock / etf / theme 输入；
  - 刷新主题成员篮子。
- `WatchThemeCatalogService`
  - 管理本地主题目录；
  - 按主题 slug 返回代表股与 ETF；
  - 提供主题搜索/匹配。
- `WatchSignalService`
  - 通过现有 `StockRepository` 与 data provider fallback 获取最近 30 个自然日对应的交易数据；
  - 复用 `StockTrendAnalyzer`、策略聚合与量价规则计算候选信号；
  - 生成 `WatchSignalEvent`。
- `WatchReviewService`
  - 为候选事件装配 LLM 输入；
  - 提取最近历史分析与回测摘要；
  - 触发 LLM 复核并保存 `WatchReviewResult`。
- `WatchEventBus`
  - 独立广播 watch 相关 SSE 事件；
  - 不复用 `AnalysisTaskQueue` 内部的任务广播格式。
- `WatchRuntimeService`
  - 维护监测运行状态；
  - 在服务初始化时只注册一次后台 worker；
  - 每轮按目标成员批量执行扫描；
  - 发布 SSE 事件供前端刷新。

运行时边界：

- `WatchEventBus` 与 runtime enabled 状态均为进程内状态；
- 第一版按单进程服务部署假设实现；
- 若未来启用多 worker / 多实例，需要再引入跨进程协调与事件广播。

### 5.3 运行时流程

1. 用户创建目标。
2. 对 `stock` / `etf` 直接生成单成员篮子。
3. 对 `theme` 通过主题目录展开为成员篮子。
4. 用户在连续跟踪页面点击“启动监测”。
5. `WatchRuntimeService` 将内部 `enabled` 切换为 true；后台 worker 如果尚未注册则只注册一次。
6. 每轮对所有活跃成员执行最近 30 天数据扫描。
7. 满足候选条件则写入 `WatchSignalEvent`。
8. 对候选事件异步触发 `WatchReviewService`。
9. LLM 复核结果落库并更新事件状态。
10. 前端页面轮询或通过 SSE 拉取更新。

### 5.4 技术信号判定

候选买点的第一版规则基于现有能力组合，遵循“宁缺毋滥”：

- 仅使用最近 30 个交易 bar；若按自然日拉取后交易日不足，则以实际可得 bar 为准；
- 至少要求基础均线与成交量数据完整；
- 复用现有 `StockTrendAnalyzer` 输出中的：
  - `buy_signal`
  - `signal_score`
  - `trend_status`
  - `volume_status`
  - `macd_status`
  - `support_ma5` / `support_ma10`
- 同时引入额外约束：
  - 不追高，价格相对短均线偏离不能过大；
  - 优先缩量回调、回踩支撑、MACD 走强或金叉；
  - ETF 与个股共享框架，但允许不依赖筹码分布等 ETF 不支持字段。

候选阈值以配置常量实现，不在第一版开放为大量可调 UI 项，避免参数爆炸。

### 5.5 LLM 复核输入

LLM 复核的输入结构化为：

- 目标与成员基础信息；
- 最近 30 日 OHLCV 摘要；
- 技术分析信号摘要；
- 若来自主题，则附带主题名、成员角色、相关 ETF / 代表股说明；
- 同证券近期历史分析摘要；
- 该证券已有回测表现摘要；
- 系统要求输出标准化决策与风险说明。

LLM 输出不直接写自由文本到 UI，而是先归一化成结构化结果，再由前端展示简要结论与详情。

### 5.6 事件状态机

`WatchSignalEvent` 状态机：

- `candidate`：规则引擎刚发现候选；
- `reviewing`：已提交 LLM 复核；
- `accepted`：LLM 认为买点可跟进；
- `rejected`：LLM 否定该候选；
- `review_failed`：复核失败，允许后续重试；
- `expired`：超出有效期后不再作为当前候选显示。

状态迁移规则：

- `candidate -> reviewing -> accepted/rejected/review_failed`
- `review_failed -> reviewing` 允许重试
- 任意未终态在超过 cooldown 或交易日切换后可标记为 `expired`

## 6. API 设计

新增路由组：`/api/v1/watch`

### 6.1 目标管理

- `POST /targets`
- `GET /targets?page=1&limit=20&target_type=&status=&query=`
- `GET /targets/{id}`
- `PATCH /targets/{id}`
- `DELETE /targets/{id}`
- `POST /targets/{id}/refresh-basket`

### 6.2 运行控制

- `GET /runtime/status`
- `POST /runtime/start`
- `POST /runtime/stop`

### 6.3 事件与复核

- `GET /events?page=1&limit=20&status=&decision=&target_id=&member_code=`
- `GET /events/{id}`

### 6.4 流式更新

- `GET /stream`

第一版 SSE 只需要支持：

- `watch.runtime.started`
- `watch.runtime.stopped`
- `watch.scan.completed`
- `watch.signal.created`
- `watch.review.updated`

返回约定：

- `GET /events` 返回分页列表，列表项带 `latest_review_summary`
- `GET /events/{id}` 返回完整事件详情与 `latest_review`；第一版不返回完整 review 历史
- 单独 review 列表接口不作为第一版必须能力

SSE 载荷约定：

- 每条消息至少包含 `event_type`、`occurred_at`、`payload`
- `payload` 中必须带事件相关 id，如 `target_id`、`event_id`、`status`
- 前端仅依赖上述稳定字段，避免与内部实现对象直接耦合

## 7. 前端设计

新增独立页面：`/watch`

### 7.1 页面结构

1. 顶部运行状态栏
   - 当前是否运行
   - 上次扫描时间
   - 下次预估扫描时间
   - 启动/停止按钮
2. 跟踪目标列表
   - 新增 stock / etf / theme
   - 查看状态与成员数
   - 手动刷新主题篮子
3. 候选事件列表
   - 按时间倒序
   - 显示证券、来源目标、信号评分、状态
4. 事件详情抽屉
   - 技术信号摘要
   - 最近 30 日关键数据
   - LLM 复核结果

### 7.2 导航接入

- 在侧边栏新增“跟踪”入口；
- 路由注册在 `App.tsx` 的 `Shell` 内，与首页/回测/设置页面并列；
- 不改首页为多模式复用，避免页面职责混乱。

### 7.3 前端数据接入

- 新增 `watchApi` 与 `watch` types 文件；
- JSON 接口继续走现有 axios client；
- `/api/v1/watch/stream` 采用独立 hook 处理 SSE，不复用现有 analysis task stream hook；
- 列表页遵循现有前端分页模式，不一次性加载全部目标和事件。

功能禁用态：

- 当 `WATCHLIST_ENABLED=false` 时，`/watch` 保持可路由；
- 页面显示“功能未启用”的禁用态说明，不隐藏路由；
- 后端 watch API 返回可识别的禁用错误或禁用状态，前端统一展示说明。

## 8. 配置与默认值

新增配置：

- `WATCHLIST_ENABLED=true`
- `WATCHLIST_SCAN_INTERVAL_MINUTES=45`
- `WATCHLIST_HISTORY_LOOKBACK_DAYS=30`
- `WATCHLIST_SIGNAL_COOLDOWN_MINUTES=240`
- `WATCHLIST_MAX_REVIEW_PER_CYCLE=10`

要求：

- 同步更新 `.env.example`
- 同步更新用户文档与 `docs/CHANGELOG.md`

## 9. 错误处理与降级

- 单个目标解析失败，不应中断整个监测任务。
- 单个成员数据拉取失败，记录错误并继续扫描其他成员。
- LLM 复核失败时，事件保留为 `candidate` 或 `review_failed`，供后续重试。
- 主题未命中目录时，目标进入 `unsupported`，页面明确告知。
- 外部行情源失败时继续复用现有 data provider fallback 逻辑。

## 10. 测试策略

### 10.1 后端

- Repository 单元测试：
  - 目标/成员/事件/复核结果 CRUD
- Signal Service 单元测试：
  - 最近 30 日数据判定候选
  - ETF 分支不依赖个股专属字段
- Theme Catalog 单元测试：
  - 主题展开成员正确
  - 未知主题进入 unsupported
- Runtime Service 单元测试：
  - start / stop / status
  - 扫描过程只对 active 目标生效
- API 测试：
  - 目标增删改查
  - 运行状态控制
  - 事件查询

### 10.2 前端

- 页面路由与导航项渲染；
- 目标列表增删改查交互；
- 运行状态按钮与候选事件列表展示；
- 事件详情抽屉渲染复核结果。

## 11. 迁移与兼容性

- 新模块完全追加，不替换现有历史分析和回测页面；
- 新增 API 路由，不修改既有 `/analysis`、`/history`、`/backtest` 契约；
- 现有首页、问股、持仓、回测页面保持原行为；
- 未开启 `WATCHLIST_ENABLED` 时，新模块可隐藏或返回禁用状态。

## 12. 风险与取舍

### 12.1 最大风险

主题到成员篮子的映射质量决定了主题跟踪体验。第一版不追求自动覆盖全部概念词，而是追求稳定、可解释、可维护。

### 12.2 主要取舍

- 取稳定目录，不取脆弱在线图谱；
- 取候选后再 LLM，不取全量轮询都走 LLM；
- 取独立 watch 子系统，不取把首页与历史分析页继续做成巨石页面；
- 取结构化复核上下文，不伪造“当前事件已完成回测”。

## 13. 实施顺序建议

1. 存储模型、Repository、主题目录基线。
2. 目标管理与主题展开服务。
3. 技术信号扫描服务。
4. 运行时调度与事件入库。
5. LLM 复核服务。
6. API 路由与 Schema。
7. Web 页面与联调。
