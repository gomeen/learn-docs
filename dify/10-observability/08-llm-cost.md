# 10.5.2 Token 用量与成本分析

> LLM 应用的成本主要来自 Token 用量，掌握用量计算、成本估算、优化策略是 LLM 工程师的必备技能。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 LLM Token 的计费模型
- 掌握 dify 中 Token 用量的计算与存储
- 能为 dify 设计成本监控和优化方案
- 知道常见的成本优化策略

## 📚 前置知识

- 10.5.1 LLM 调用追踪（`07-llm-tracing.md`）
- 10.2.5 业务指标（`04-business-metrics.md`）
- LLM 基本概念（Prompt / Completion / Token）

## 1. 核心概念

### 1.1 Token 的定义

**Token** 是 LLM 处理文本的最小单位。简单理解：
- 英文：1 个 Token ≈ 0.75 个单词（1 个单词 ≈ 1.3 个 Token）
- 中文：1 个汉字 ≈ 1-2 个 Token（不同 tokenizer 有差异）

**示例**：
```
"Hello, world!" → ["Hello", ",", " world", "!"] ≈ 4 tokens
"你好，世界！" → ["你", "好", "，", "世", "界", "！"] ≈ 6 tokens
```

### 1.2 LLM 计费模型

主流模型按 Token 计费：

| 模型 | Input 价格 | Output 价格 |
|------|-----------|-------------|
| GPT-4 | $30 / 1M tokens | $60 / 1M tokens |
| GPT-4 Turbo | $10 / 1M tokens | $30 / 1M tokens |
| GPT-3.5 Turbo | $0.5 / 1M tokens | $1.5 / 1M tokens |
| Claude 3.5 Sonnet | $3 / 1M tokens | $15 / 1M tokens |
| Claude 3 Haiku | $0.25 / 1M tokens | $1.25 / 1M tokens |

**成本公式**：
```
cost = (prompt_tokens / 1000) × input_price + (completion_tokens / 1000) × output_price
```

### 1.3 影响成本的关键因素

1. **Prompt 长度**：系统 Prompt + 用户输入越长，成本越高
2. **模型选择**：大模型比小模型贵 10-100 倍
3. **Output 长度**：Output 通常比 Input 贵 2-3 倍
4. **缓存命中率**：相同/相似问题复用响应
5. **批量调用**：一次调用处理多条请求

### 1.4 成本优化的常见策略

| 策略 | 节省比例 | 实现难度 |
|------|----------|----------|
| **Prompt 压缩** | 30-50% | 低 |
| **使用小模型** | 70-90% | 中 |
| **响应缓存** | 50%+ | 中 |
| **流式响应** | 0% | 低 |
| **批处理** | 20-30% | 高 |
| **Function Calling** | 10-30% | 中 |

## 2. 代码示例

### 2.1 Token 用量统计

```python
# dify 中 Token 用量的存储位置
class WorkflowNodeExecutionModel:
    outputs = Column(JSON)  # 包含完整的 usage 信息
    # outputs = {
    #     "usage": {
    #         "prompt_tokens": 1234,
    #         "completion_tokens": 567,
    #         "total_tokens": 1801,
    #     },
    #     "model": "gpt-4",
    #     "provider": "openai",
    # }
```

### 2.2 计算 LLM 调用成本

```python
# 价格表（美元 / 1M tokens）
PRICING = {
    "gpt-4": {"input": 30, "output": 60},
    "gpt-4-turbo": {"input": 10, "output": 30},
    "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    "claude-3-5-sonnet": {"input": 3, "output": 15},
    "claude-3-haiku": {"input": 0.25, "output": 1.25},
}


def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """计算 LLM 调用的成本（美元）"""
    price = PRICING.get(model, {"input": 0, "output": 0})
    cost = (
        prompt_tokens * price["input"] / 1_000_000
        + completion_tokens * price["output"] / 1_000_000
    )
    return round(cost, 6)


# 示例
print(calculate_cost("gpt-4", 1000, 500))
# = 1000 × 30 / 1e6 + 500 × 60 / 1e6
# = 0.030 + 0.030 = $0.060
```

### 2.3 按租户统计每日成本

```python
from datetime import datetime
from sqlalchemy import select, func
from models.workflow import WorkflowNodeExecutionModel


def daily_cost_by_tenant(date: str) -> dict[str, float]:
    """查询某天各租户的 LLM 成本"""
    costs: dict[str, float] = {}

    with Session(db.engine) as session:
        rows = session.execute(
            select(
                WorkflowNodeExecutionModel.tenant_id,
                WorkflowNodeExecutionModel.outputs,
            ).where(
                func.date(WorkflowNodeExecutionModel.created_at) == date
            )
        ).all()

    for tenant_id, outputs_raw in rows:
        if not outputs_raw:
            continue
        outputs = json.loads(outputs_raw) if isinstance(outputs_raw, str) else outputs_raw
        usage = outputs.get("usage", {})
        model = outputs.get("model", "")

        cost = calculate_cost(
            model,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
        )
        costs[tenant_id] = costs.get(tenant_id, 0) + cost

    return costs
```

### 2.4 常见错误：忽略 output token 价格

```python
# ❌ 错误：用单一价格估算成本
def estimate_cost(model, total_tokens):
    return total_tokens * 0.001  # 1M token $1

# 实际 GPT-4：input $30 + output $60，平均 $45
# 估算偏差 45 倍！

# ✅ 正确：分别计算 input 和 output
def estimate_cost(model, prompt_tokens, completion_tokens):
    return (
        prompt_tokens * INPUT_PRICE[model]
        + completion_tokens * OUTPUT_PRICE[model]
    )
```

## 3. 关键要点总结

- LLM 成本 = prompt_tokens × input_price + completion_tokens × output_price
- output 通常比 input 贵 2-3 倍（GPT-4: $30 vs $60）
- dify 区分 prompt 和 completion token，便于精确计费
- 节点级 trace 包含 `total_price` 和 `currency`
- 成本优化策略：Prompt 压缩、小模型、缓存、批处理
- **多层防御性编程**：每个字段都检查类型和存在性

---

**文档版本**：v1.0
**最后更新**：2026-07-13
