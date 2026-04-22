# BackTestSystem 独立回测子系统设计

**日期**: 2026-04-22

**目标**: 在 `BackTestSystem/` 内建设一个可单独运行的前后端分离回测子系统，导入 `Data/test_exports/` 历史数据，融合主项目已验证的交易指标与买卖信号逻辑，完成多指标买卖点分析、历史回测、结果看板与 K 线联动分析。

## 1. 设计结论

本轮采用“独立子系统 + 内置策略内核”的方案：

- `BackTestSystem` 独立运行，不以主项目作为运行时依赖
- 主项目仅作为策略和指标实现的参考来源
- 首期在子系统内置一套 `v1` 策略内核，按主项目当前交易理念移植
- 后端采用 `uv + Python + FastAPI`
- 前端采用独立 `React + Vite + TypeScript`
- 视觉方向参考东方财富 fullScreenChart 的高密度行情工作台，同时借鉴 MUI 的秩序感，但首期不强制引入 MUI 组件库

## 2. 目标与边界

### 2.1 目标

- 支持导入本地 CSV 日线历史数据
- 统一标准化不同列结构的数据集
- 计算多种技术指标并生成买卖信号
- 对历史数据执行回测并输出交易结果与统计汇总
- 提供独立 Web 工作台查看导入、配置、执行、结果与图表联动
- 为后续策略扩展、参数调优、独立部署保留清晰边界
- P0 采用“单数据集对应单标的、单策略配置对应单次回测运行”的收敛模型

### 2.2 非目标

- 首期不接入主项目的 LLM 分析、报告生成、消息通知、watchlist 流程
- 首期不直接复用主项目数据库表结构
- 首期不支持做空、融资融券、多账户、多用户体系
- 首期不做分钟级或 tick 级高频回测
- 首期不做复杂撮合模型，只做日线级策略回测
- 首期不做多策略加权组合和多标的批量回测编排

## 3. 参考来源与复用原则

### 3.1 参考来源

首期策略内核参考以下主项目实现：

- [src/stock_analyzer.py](/home/user01/WorkSpace/stockSystem/daily_stock_analysis/src/stock_analyzer.py:171)
- [src/core/backtest_engine.py](/home/user01/WorkSpace/stockSystem/daily_stock_analysis/src/core/backtest_engine.py:50)

### 3.2 复用原则

- 复用的是“算法与规则”，不是“主项目运行时依赖”
- `BackTestSystem` 内建立自己的 `indicators/strategies/backtest_engine` 模块
- 将主项目当前版本的 MA、MACD、RSI、趋势评分、买卖信号和回测评估逻辑移植为子系统 `v1`
- 用测试锁定公式、阈值、字段口径与回测行为
- 不直接依赖主项目的 `config`、数据库、watch 服务、API 层、页面层

### 3.3 首批指标范围

首期落地以下指标与信号：

- 均线系统：`MA5 / MA10 / MA20 / MA60`
- 趋势判断：`trend_status / trend_strength / ma_alignment`
- 乖离率：`bias_ma5 / bias_ma10 / bias_ma20`
- 量能：`volume_ratio_5d / volume_status / volume_trend`
- MACD：`dif / dea / bar / macd_status / macd_signal`
- RSI：`rsi_6 / rsi_12 / rsi_24 / rsi_status / rsi_signal`
- 支撑压力：`support_levels / resistance_levels`
- 综合信号：`buy_signal / signal_score / signal_reasons / risk_factors`

## 4. 总体架构

系统按“数据导入 -> 指标计算 -> 策略生成 -> 回测执行 -> 汇总展示”五段式构建。

```text
CSV 历史数据
  -> 数据标准化与入库
  -> 指标计算
  -> 策略信号生成
  -> 回测执行
  -> 结果汇总与图表序列查询
  -> React 工作台展示
```

### 4.1 后端分层

- `api/`：HTTP 接口、参数校验、响应模型
- `services/`：业务流程编排
- `core/indicators/`：纯指标计算
- `core/strategies/`：纯信号生成与策略规则
- `core/engine/`：纯回测引擎
- `repositories/`：数据访问层
- `infra/`：配置、数据库、文件导入、任务运行基础设施

### 4.2 前端分层

- `app shell`：导航、全局筛选、路由
- `workspaces`：导入、指标配置、回测执行、结果看板、图表详情
- `stores`：跨页面联动状态
- `api client`：统一请求封装
- `chart components`：K 线、指标副图、信号标记与联动信息面板

## 5. 子系统目录设计

```text
BackTestSystem/
  pyproject.toml
  uv.lock
  README.md
  .env.example
  data/
    raw/
    normalized/
    exports/
  backend/
    src/backtest_system/
      __init__.py
      main.py
      api/
        __init__.py
        v1/
          __init__.py
          router.py
          endpoints/
            imports.py
            datasets.py
            strategies.py
            backtests.py
            market_data.py
            summaries.py
          schemas/
            import_schema.py
            dataset_schema.py
            strategy_schema.py
            backtest_schema.py
            summary_schema.py
      services/
        import_service.py
        indicator_service.py
        strategy_service.py
        backtest_service.py
        summary_service.py
      core/
        models.py
        indicators/
          moving_average.py
          macd.py
          rsi.py
          volume.py
        strategies/
          trend_following.py
          scoring.py
          signal_rules.py
        engine/
          executor.py
          portfolio.py
          metrics.py
      repositories/
        dataset_repo.py
        bar_repo.py
        indicator_repo.py
        strategy_repo.py
        backtest_repo.py
        summary_repo.py
      infra/
        db.py
        settings.py
        csv_importer.py
        file_store.py
  frontend/
    package.json
    src/
      app/
      pages/
      components/
      stores/
      api/
      charts/
  tests/
    backend/
    frontend/
```

## 6. 数据模型

### 6.1 核心表

- `dataset`
  - `id`, `name`, `source_type`, `symbol`, `date_from`, `date_to`, `row_count`, `status`, `schema_version`
- `import_job`
  - `id`, `dataset_id`, `source_path`, `schema_profile_json`, `status`, `error_message`, `created_at`, `finished_at`
- `market_bar`
  - `id`, `dataset_id`, `symbol`, `trade_date`, `open`, `high`, `low`, `close`, `volume`, `amount`, `outstanding_share`, `turnover`
- `indicator_snapshot`
  - `id`, `dataset_id`, `symbol`, `trade_date`, `indicator_name`, `indicator_version`, `params_json`, `value_json`
- `strategy_config`
  - `id`, `name`, `version`, `rule_type`, `params_json`, `enabled`
- `backtest_run`
  - `id`, `dataset_id`, `strategy_config_id`, `start_date`, `end_date`, `status`, `config_json`, `started_at`, `finished_at`
- `backtest_signal`
  - `id`, `run_id`, `symbol`, `trade_date`, `signal_type`, `signal_score`, `signal_payload_json`
- `backtest_trade`
  - `id`, `run_id`, `symbol`, `entry_date`, `entry_price`, `exit_date`, `exit_price`, `exit_reason`, `hold_days`, `gross_return_pct`, `net_return_pct`, `max_drawdown_pct`
- `backtest_summary`
  - `id`, `run_id`, `scope`, `ref_key`, `metrics_json`, `computed_at`

### 6.2 数据标准化规则

P0 的导入约束如下：

- 一个 `dataset` 对应一个 CSV 文件和一个标的
- 样例数据默认来源于仓库路径 `BackTestSystem/Data/test_exports/`
- 标准化后的缓存文件保存到子系统内部 `BackTestSystem/data/normalized/`
- P0 的 API 先支持“注册服务端本地路径导入”，浏览器上传文件留到 P1

导入层必须接受以下列差异：

- 最低必需列：`date, open, high, low, close, volume`
- 可选扩展列：`amount, outstanding_share, turnover`
- 日期统一转 `datetime/date`
- 数值字段统一转浮点或整数
- 按 `trade_date` 升序排序
- 去除关键字段为空的行
- 保留原始文件路径与 schema 检测结果，便于追溯

### 6.3 运行粒度

P0 对 `backtest_run` 的定义固定如下：

- 一个 `backtest_run` 只绑定一个 `dataset`
- 一个 `dataset` 只包含一个标的的历史数据
- 一个 `backtest_run` 只绑定一个 `strategy_config`
- 一个 `backtest_run` 对应一个确定的时间窗口和一组成本参数

如需比较多个标的或多个策略，先创建多次独立 run；批量调度留到 P1。

## 7. 回测规则

### 7.1 交易时序

首期采用固定规则：

- 当日收盘后基于当日 bar 计算指标并生成信号
- 若触发买入/卖出动作，则在下一交易日开盘价成交
- 若无下一交易日，则该信号记为未成交
- 若已持仓且再次出现买入信号，则忽略该信号，不重复加仓
- 若空仓时出现卖出信号，则只记录信号，不生成交易

### 7.2 持仓模型

- 首期仅支持 `long / cash`
- 单标的单仓位，不支持同时多笔持仓
- 默认满仓进出，后续再扩展仓位管理
- 一个 run 仅对其绑定标的进行顺序回测

### 7.3 成本模型

- 手续费、滑点通过回测配置传入
- 首期默认支持：
  - `commission_rate`
  - `slippage_rate`
- 首期不拆分印花税、过户费等更细颗粒成本

### 7.4 交易与盈亏口径

P0 统一采用以下指标口径：

- `entry_price`
  - 下一交易日开盘价上浮买入滑点后的价格
- `exit_price`
  - 下一交易日开盘价下调卖出滑点后的价格
- `gross_return_pct`
  - `(exit_price - entry_price) / entry_price * 100`
- `net_return_pct`
  - 在毛收益基础上扣除双边手续费后的收益率
- `hold_days`
  - 从 `entry_date` 到 `exit_date` 的交易日数量，含首尾两日
- `max_drawdown_pct`
  - 持仓期间最低 `low` 相对 `entry_price` 的最大回撤百分比
- `exit_reason`
  - `signal_sell | end_of_data`

单笔交易落库时同时保存 `gross_return_pct` 和 `net_return_pct`，summary 层再分别聚合毛收益与净收益。

若数据集结束时仍有未平仓持仓，则执行强制平仓：

- `exit_reason = end_of_data`
- `exit_date` 取数据集最后一个交易日
- `exit_price` 取最后一个交易日 `close` 下调卖出滑点后的价格
- 该笔交易照常参与 `gross_return_pct / net_return_pct / max_drawdown_pct / hold_days` 统计

### 7.5 买卖信号映射

首期按综合信号驱动动作：

- `STRONG_BUY / BUY`：若当前空仓，则生成买入意图
- `SELL / STRONG_SELL`：若当前持仓，则生成卖出意图
- `HOLD / WAIT`：不交易，仅记录观察信号

### 7.6 输出指标

回测至少输出：

- 总交易次数
- 胜率
- 平均毛收益率
- 平均净收益率
- 累计净收益率
- 最大回撤
- 平均持有天数
- 按策略信号的命中率
- 单次 run 的收益曲线

## 8. 后端 API 设计

### 8.1 导入与数据集

- `POST /api/v1/imports/csv`
  - 注册服务端已有 CSV 路径，执行解析与入库
- `GET /api/v1/datasets`
  - 查询已导入数据集
- `GET /api/v1/datasets/{dataset_id}`
  - 查询数据集详情

请求示例：

```json
{
  "source_type": "local_path",
  "file_path": "BackTestSystem/Data/test_exports/guizhou_maotai_600519_2024-01-01_to_2026-04-22.csv",
  "dataset_name": "贵州茅台日线样例"
}
```

响应示例：

```json
{
  "job_id": "imp_001",
  "dataset_id": "ds_001",
  "status": "completed",
  "symbol": "600519",
  "row_count": 540
}
```

### 8.2 策略配置

- `GET /api/v1/strategies`
  - 查询策略模板与实例
- `POST /api/v1/strategies`
  - 创建或保存策略配置

### 8.3 回测执行

- `POST /api/v1/backtests`
  - 提交回测任务
- `GET /api/v1/backtests/{run_id}`
  - 查询运行状态
- `GET /api/v1/backtests/{run_id}/signals`
  - 查询信号明细
- `GET /api/v1/backtests/{run_id}/trades`
  - 查询交易明细
- `GET /api/v1/backtests/{run_id}/summary`
  - 查询汇总统计

P0 的 `POST /api/v1/backtests` 约束如下：

- 一个请求只启动一个 run
- 一个 run 只对应一个 `dataset_id`
- 一个 run 只对应一个 `strategy_config_id`

请求示例：

```json
{
  "dataset_id": "ds_001",
  "strategy_config_id": "stg_001",
  "start_date": "2024-01-01",
  "end_date": "2026-04-22",
  "commission_rate": 0.0003,
  "slippage_rate": 0.0005
}
```

响应示例：

```json
{
  "run_id": "run_001",
  "dataset_id": "ds_001",
  "strategy_config_id": "stg_001",
  "status": "running"
}
```

`GET /api/v1/backtests/{run_id}/signals` 的 P0 返回必须包含：

- `trade_date`
- `signal_type`
- `signal_score`
- `buy_signal`
- `signal_reasons`
- `risk_factors`
- `support_levels`
- `resistance_levels`

前端右侧详情面板通过该接口读取 `support_levels / resistance_levels`，不额外新增独立端点。

### 8.4 图表与联动数据

- `GET /api/v1/market-data/bars`
  - 查询指定标的和时间范围的 OHLCV
- `GET /api/v1/market-data/indicator-series`
  - 查询 MA / MACD / RSI 等序列
- `GET /api/v1/market-data/signal-markers`
  - 查询图表上需要标记的买卖点

P0 查询契约固定如下：

- `bars`
  - 必填：`dataset_id`
  - 可选：`date_from`, `date_to`
- `indicator-series`
  - 必填：`dataset_id`, `indicator_names`
  - 可选：`date_from`, `date_to`
- `signal-markers`
  - 必填：`run_id`
  - 可选：`date_from`, `date_to`

P0 中 `support_levels / resistance_levels` 仅作为结果详情侧边面板展示字段，不作为主图 overlay。

`indicator-series` 响应示例：

```json
{
  "dataset_id": "ds_001",
  "symbol": "600519",
  "series": {
    "MA5": [
      {"date": "2024-01-02", "value": 1685.01},
      {"date": "2024-01-03", "value": 1689.50}
    ],
    "MACD_DIF": [
      {"date": "2024-01-02", "value": 0.0},
      {"date": "2024-01-03", "value": 0.72}
    ],
    "MACD_DEA": [
      {"date": "2024-01-02", "value": 0.0},
      {"date": "2024-01-03", "value": 0.14}
    ],
    "MACD_BAR": [
      {"date": "2024-01-02", "value": 0.0},
      {"date": "2024-01-03", "value": 1.16}
    ],
    "RSI_12": [
      {"date": "2024-01-02", "value": 50.0},
      {"date": "2024-01-03", "value": 56.3}
    ]
  }
}
```

`signal-markers` 响应示例：

```json
{
  "run_id": "run_001",
  "symbol": "600519",
  "markers": [
    {
      "trade_date": "2024-02-06",
      "execution_date": "2024-02-07",
      "price": 1681.03,
      "signal_type": "BUY",
      "signal_score": 78,
      "label": "买入"
    },
    {
      "trade_date": "2024-03-18",
      "execution_date": "2024-03-19",
      "price": 1712.50,
      "signal_type": "SELL",
      "signal_score": 34,
      "label": "卖出"
    }
  ]
}
```

### 8.5 基础接口

- `GET /health`
  - 健康检查

## 9. 前端设计

### 9.1 页面信息架构

- `数据导入页`
  - 文件导入、字段校验、导入历史、预览
- `指标配置页`
  - 策略模板选择、参数查看、基础参数调整
- `回测执行页`
  - 数据集选择、日期范围、回测参数、任务进度
- `结果看板页`
  - KPI、收益曲线、交易明细、信号明细、回撤摘要
- `K 线联动详情页`
  - 主图 K 线、指标副图、买卖点标记、结果定位

### 9.2 组件层次

- `BacktestShell`
- `ImportWorkspace`
- `IndicatorWorkspace`
- `ExecutionWorkspace`
- `ResultDashboard`
- `ChartWorkspace`

### 9.3 样式方向

- 高密度工作台布局
- 图表区作为主视图核心
- 使用深色中性底和清晰层级
- 强调红绿信号色与交易语义
- 首期采用 Tailwind 风格化组件，不强行引入 MUI 组件库

### 9.4 状态管理

- URL query 保存可分享的筛选状态
- 本地 store 保存跨页面联动的瞬时状态
- 结果点击后联动更新 `selectedRunId / selectedSymbol / selectedDate`

## 10. 错误处理与稳定性

- 导入失败必须返回字段级错误
- 非法 CSV 不得污染已入库数据
- 指标计算失败只影响当前数据集，不拖垮整个服务
- 单次回测失败可重试，不影响其他任务
- 图表页缺失指标序列时，前端要展示缺失说明而非空白崩溃

## 11. P0 / P1 拆分

### P0

- `BackTestSystem` 独立后端与前端骨架
- CSV 导入与标准化
- MA / MACD / RSI / 趋势评分 / 综合买卖信号
- 次日开盘成交的日线回测
- 回测结果与 summary API
- 结果看板
- K 线 + MA + MACD/RSI 联动页

### P1

- 更多指标和参数模板
- 浏览器文件上传
- 多策略组合对比
- 多标的批量回测
- 更细的成本模型
- 更强的图表交互
- 任务队列与大批量异步运行

## 12. 验证要求

### 12.1 后端

- CSV 标准化单测
- 指标公式单测
- 信号生成单测
- 回测规则单测
- API schema 单测

### 12.2 前端

- 页面路由 smoke
- 导入流程测试
- 结果筛选和钻取测试
- 图表联动测试

### 12.3 集成

- 使用 `BackTestSystem/Data/test_exports/` 的两份样例数据完成至少一次导入与回测
- 验证贵州茅台与上证 50 两类数据都能被标准化处理
- 验证买点、卖点、交易明细和 summary 能闭环展示

## 13. 风险与约束

- 主项目的信号阈值是当前交易理念，不是行业标准；首期只能作为 `v1` 基线
- 如果同时维护主项目和子系统两套策略实现，后续需要版本管理防止口径漂移
- 当前样例数据只有日线，首期所有交互和回测都必须围绕日线设计
- 若未来要支持高密度专业图表，可能需要评估更专业的图表库，但首期先以可用为主

## 14. 下一步

设计确认后，下一阶段进入实现计划，先搭 `BackTestSystem` 基础依赖与目录骨架，再分后端、策略内核、前端三个工作流并行推进。
