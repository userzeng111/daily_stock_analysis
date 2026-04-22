# 问题标题

BackTestSystem 交付前硬化修复包

# 用户原始诉求

只处理 overall review 剩余的 1 个阻塞问题和 2 个重要可用性问题：补齐干净环境下前端独立完成一次回测的最小能力；过滤图表 WAIT/HOLD marker；支持结果页与图表页通过 URL query 恢复历史 run。

# 当前状态

待用户验收：已补齐前端默认策略创建、执行页日期范围输入、结果/图表页 URL 恢复，以及后端/前端双重 marker 过滤；已完成前端定向测试、前端 lint/build、后端 `signal-markers` 定向测试与 `py_compile` 校验。
