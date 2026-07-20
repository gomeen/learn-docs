# 小验证：LLM 可观测性与成本

> 覆盖：
> - [06-llm-tracing](./07-llm-tracing.md)
> - [07-llm-cost](./08-llm-cost.md)
> - [08-llm-quality](./09-llm-quality.md)
> - [09-llm-observability-tools](./10-llm-observability-tools.md)
> - [10-llm-obs-in-dify](./11-llm-obs-in-dify.md)
>
> 预计：45～75 分钟 · 本地练习或改 dify 仓库

## 背景

LLM 调用需要 prompt/响应/token/成本维度。验证：实现最小 tracing 记录，并找 dify 用量点。

## 需求

1. 本地 `llm_trace.py`：保存 span 列表（model、tokens、latency、status、截断后的 prompt hash）。
2. 成本汇总：按模型单价计算。
3. 质量：用规则检查输出是否为空、是否过短、是否含禁词列表。
4. 对照仓库 LLM 监控/用量相关实现写 `NOTES.md`。

## 提示

- 不要默认把完整 prompt 明文打到 INFO
- 仓库：feature/billing/workflow trace 等入口

## 验收标准

- [ ] span 记录可导出 JSON
- [ ] 成本汇总正确（手算对照）
- [ ] 质量规则 ≥3 条可测
- [ ] NOTES 有仓库锚点

## 延伸（选做）

设计用户反馈 thumbs 与 span 关联的数据模型。
