# 问题标题

BackTestSystem 子模块回测平台建设

# 用户原始诉求

基于 `BackTestSystem` 独立建设一个前后端分离的回测子系统，导入 `BackTestSystem/Data/test_exports/` 下的历史数据，融合主项目已有交易指标（如 MACD 等），对历史数据做多指标买卖点回测；后端采用 `uv + Python`，前端采用 React，视觉参考东方财富 fullScreenChart 与 MUI 的信息密度风格，并先把子模块基础依赖和工程骨架搭起来，保持与主项目独立、互不干扰。

# 当前状态

进行中：已完成主项目指标能力、BackTestSystem 数据样例、现有前端/回测链路的并行勘察，并已产出设计文档 `docs/superpowers/specs/2026-04-22-backtest-system-design.md`；当前正在进行 spec 审阅，待用户确认后进入实现计划。
