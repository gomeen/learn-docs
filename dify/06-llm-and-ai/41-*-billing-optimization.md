# 小验证：Token 计量 · 缓存 · 路由 · 计费

> 覆盖：
> - [30-token-tracking](./36-token-tracking.md)
> - [31-prompt-caching](./37-prompt-caching.md)
> - [32-model-routing](./38-model-routing.md)
> - [33-rate-limit-quota](./39-rate-limit-quota.md)
> - [34-billing-in-dify](./40-billing-in-dify.md)
>
> 预计：45～75 分钟 · 本地练习或改 dify 仓库

## 背景

成本与配额是 LLM 功能上线的硬约束。验证：定位用量统计与限流，完成一次计量小实验。

## 需求

1. 本地 `usage_meter.py`：记录每次调用的 `model/prompt_tokens/completion_tokens/latency_ms`，汇总成本（单价表写死）。
2. 实现简单路由：`pick_model(task: str, budget: str) -> str`（如 cheap/strong）。
3. 对照 `billing_service` 或 feature/quota 相关代码，`NOTES.md` 写清：计数在何处累加、超额时用户可见错误。
4. （可选）为某计数路径补 debug 日志字段 `trace_id`（若上下文有）。

## 提示

- `api/services/billing_service.py`、feature/quota 相关
- 限流与 Redis 模块呼应

## 验收标准

- [ ] 计量脚本输出汇总表
- [ ] 路由函数有明确规则与测试断言
- [ ] 仓库超额路径说明清楚
- [ ] 不绕过计费做「隐藏免费」改动

## 延伸（选做）

设计 prompt cache 命中率指标如何上报到业务监控。
