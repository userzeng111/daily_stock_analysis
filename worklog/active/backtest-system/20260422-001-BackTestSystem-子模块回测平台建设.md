# 问题标题

BackTestSystem 子模块回测平台建设

# 用户原始诉求

基于 `BackTestSystem` 独立建设一个前后端分离的回测子系统，导入 `BackTestSystem/Data/test_exports/` 下的历史数据，融合主项目已有交易指标（如 MACD 等），对历史数据做多指标买卖点回测；后端采用 `uv + Python`，前端采用 React，视觉参考东方财富 fullScreenChart 与 MUI 的信息密度风格，并先把子模块基础依赖和工程骨架搭起来，保持与主项目独立、互不干扰。

# 当前状态

实现完成，待用户验收：BackTestSystem 前后端、样例数据导入、策略配置、回测执行、结果看板与图表联动链路已落地；本轮已复核后端测试 `52 passed`、前端测试 `14 passed`、Python `py_compile` 成功、前端 `npm run build` 成功，并基于样例 CSV 完成两份数据导入与一次贵州茅台回测 smoke，且已补齐默认策略创建、日期范围执行、marker 过滤与 URL 恢复等交付前硬化问题。
