# 10.2.5 业务指标：DAU / 转化率 / LLM Token 用量

> 在应用指标之外，业务指标是衡量产品健康度的核心。LLM 应用特别需要关注 Token 用量与成本。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解业务指标与技术指标的区别
- 掌握 DAU、转化率、留存率等核心业务指标
- 能为 LLM 应用设计 Token 用量与成本指标
- 能看懂 dify 中 LLM 用量的计算逻辑

## 📚 前置知识

- 10.2.4 应用指标（`09-app-metrics.md`）
- LLM 基本概念（模型、Token、Prompt）
- 02-domain（用户、租户、应用等模型）

## 1. 核心概念

### 1.1 技术指标 vs 业务指标

| 维度 | 技术指标 | 业务指标 |
|------|----------|----------|
| 受众 | SRE / 工程师 | 产品 / 运营 / 管理层 |
| 衡量 | 服务可用性、性能 | 产品健康度、商业价值 |
| 例子 | QPS、P99 延迟、错误率 | DAU、MAU、GMV、留存 |
| 数据源 | Prometheus / 日志 | 数据库 / 埋点 / BI 系统 |

**关系**：业务指标异常往往先于技术指标暴露问题（如订单下降 → 数据库慢查询）。

### 1.2 互联网核心业务指标

**用户类**：
- **DAU / WAU / MAU**：日/周/月活跃用户数
- **新用户 / 老用户比例**
- **留存率**：D1、D7、D30 留存
- **流失率**

**行为类**：
- **PV / UV**：页面浏览量 / 唯一用户数
- **会话数 / 平均会话时长**
- **功能使用率**

**转化类**：
- **漏斗转化率**：注册 → 激活 → 付费
- **ARPU / ARPPU**：每用户平均收入
- **付费率 / 复购率**

### 1.3 LLM 应用特有指标

| 指标 | 含义 | 价值 |
|------|------|------|
| **总 Token 用量** | prompt_tokens + completion_tokens | 直接关联成本 |
| **平均每次请求的 Token** | 用量 / 请求数 | 衡量 Prompt 优化效果 |
| **流式响应 TTFT** | Time To First Token | 用户感知延迟 |
| **流式响应 TPS** | Tokens Per Second | 模型吞吐能力 |
| **缓存命中率** | 相似问题复用率 | 成本优化的关键 |
| **多模型分布** | 各模型占比 | 成本结构分析 |

### 1.4 LLM 成本分析

```
成本 = prompt_tokens × input_price + completion_tokens × output_price

示例（GPT-4）：
- input:  $0.03 / 1K tokens
- output: $0.06 / 1K tokens
- 一次请求（prompt=1000, output=500）：
  = 1 × $0.03 + 0.5 × $0.06
  = $0.06 / 次
```

## 2. 代码示例

### 2.1 dify 中的 Token 用量统计（核心代码）

**来源**：`api/core/ops/ops_trace_manager.py:683-714`

```python
# 计算工作流的 prompt_tokens 和 completion_tokens
rows = (
    session.execute(
        select(WorkflowNodeExecutionModel.outputs).where(
            WorkflowNodeExecutionModel.tenant_id == tenant_id,
            WorkflowNodeExecutionModel.workflow_run_id == workflow_run_id,
        )
    )
    .scalars()
    .all()
)

total_prompt = 0
total_completion = 0

for raw in rows:
    if not raw:
        continue
    try:
        outputs = JSON_DICT_ADAPTER.validate_json(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        continue
    if not isinstance(outputs, dict):
        continue
    usage = outputs.get("usage")
    if not isinstance(usage, dict):
        continue
    prompt = usage.get("prompt_tokens")
    if isinstance(prompt, (int, float)):
        total_prompt += int(prompt)
    completion = usage.get("completion_tokens")
    if isinstance(completion, (int, float)):
        total_completion += int(completion)

return (total_prompt, total_completion)
```

**说明**：
- dify 在每次工作流执行时，LLM 节点会把 `usage` 写入 `WorkflowNodeExecutionModel.outputs`
- 通过聚合所有节点的 usage，计算整个工作流的 Token 总用量
- **设计亮点**：只 SELECT `outputs` 列，避免加载大 JSON blob

### 2.2 业务指标采集示例

```python
# 假设用 prometheus_client 采集业务指标
from prometheus_client import Counter, Gauge, Histogram

# 1. 用户活跃度（Counter）
active_users = Counter(
    "dify_active_users_total",
    "Total active user sessions",
    ["tenant_id", "app_id"]
)

# 2. 应用请求量（Counter）
app_requests = Counter(
    "dify_app_requests_total",
    "Total requests per app",
    ["tenant_id", "app_id", "status"]
)

# 3. LLM Token 用量（Histogram）
llm_tokens = Histogram(
    "dify_llm_tokens",
    "LLM token usage distribution",
    ["model", "type"],  # type: prompt/completion
    buckets=(100, 500, 1000, 2000, 4000, 8000, 16000)
)

# 4. 流式 TTFT（Histogram）
ttft = Histogram(
    "dify_ttft_seconds",
    "Time to first token (streaming)",
    ["model"],
    buckets=(0.05, 0.1, 0.2, 0.5, 1.0, 2.0)
)

# 使用示例
def handle_llm_request(model, prompt, completion):
    active_users.labels(tenant_id=t, app_id=a).inc()
    llm_tokens.labels(model=model, type="prompt").observe(prompt)
    llm_tokens.labels(model=model, type="completion").observe(completion)
```

### 2.3 业务指标看板查询

```promql
# 1. DAU（通过 Counter 计算）
sum(increase(dify_active_users_total[1d]))

# 2. 各应用 QPS
sum by (app_id) (rate(dify_app_requests_total[5m]))

# 3. 各模型 Token 用量占比
sum by (model) (rate(dify_llm_tokens_sum[1h])) /
sum(rate(dify_llm_tokens_sum[1h]))

# 4. 平均 Prompt 长度（用于优化 Prompt）
rate(dify_llm_tokens_sum{type="prompt"}[1h]) /
rate(dify_llm_tokens_count{type="prompt"}[1h])

# 5. 流式响应 P99 TTFT
histogram_quantile(0.99,
  sum by (model, le) (rate(dify_ttft_seconds_bucket[5m]))
)
```

## 3. 关键要点总结

- 业务指标衡量产品健康度，技术指标衡量服务健康度
- LLM 应用核心指标：Token 用量、TTFT、模型分布
- 成本 = prompt_tokens × input_price + completion_tokens × output_price
- dify 在每次 LLM 节点执行时，把 usage 写入 `outputs` 列
- 多层防御性编程处理 JSON 解析和缺失字段
- 单列 SELECT 优化减少数据库 IO

---

**文档版本**：v1.0
**最后更新**：2026-07-13
