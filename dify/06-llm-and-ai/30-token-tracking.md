# 6.1 Token 用量统计与计费

> 理解模型用量的统一结构、流式汇总、精确金额计算，以及 dify 如何持久化一次调用的统计数据。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 prompt、completion 与 total token
- 使用 `Decimal` 根据单价单位精确计算费用
- 解释非流式和流式场景的用量来源
- 看懂 dify 的 `LLMUsage` 以及工具模型调用记录更新流程

## 📚 前置知识

- [Token、上下文窗口与计费](./03-tokens-context.md)
- [dify 的模型适配层](./28-model-runtime.md)
- Python `Decimal`、Pydantic 和数据库事务（详见 [Pydantic 基础](../02-backend/15-pydantic-basics.md)）

## 1. 核心概念

### 1.1 用量统计的三个时点

1. **调用前估算**：用于上下文裁剪、预算检查和配额预留。
2. **调用后结算**：优先使用供应商返回的真实用量。
3. **流式结束汇总**：增量 chunk 通常只携带文本，usage 常在最后一个 chunk 出现。

预估值不能直接当账单真值。不同 tokenizer、工具 Schema、图片输入和服务端特殊 token 都会造成差异。

### 1.2 `LLMUsage` 应包含什么

| 字段组 | 代表字段 | 用途 |
| --- | --- | --- |
| token | `prompt_tokens`、`completion_tokens`、`total_tokens` | 容量与用量 |
| 单价 | `prompt_unit_price`、`completion_unit_price` | 价格配置 |
| 单价单位 | `prompt_price_unit` | 每千或每百万 token |
| 金额 | `prompt_price`、`completion_price`、`total_price` | 结算与展示 |
| 其他 | `currency`、`latency` | 币种和性能观测 |

金额必须用 `Decimal`，并从字符串构造，避免二进制浮点误差。

### 1.3 用量与 SaaS 配额不是一回事

`LLMUsage` 描述一次模型调用的技术用量与价格；`BillingService` 的 quota 描述租户对某项功能的可用额度。前者可以成为后者的计量输入，但不能把模型厂商费用、订阅额度和应用限流混成同一个字段。

## 2. 代码示例

### 2.1 精确计算一次调用费用

```python
# 文件：usage_cost.py
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int
    completion_tokens: int
    prompt_price_per_million: Decimal
    completion_price_per_million: Decimal

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def total_price(self) -> Decimal:
        unit = Decimal("1000000")
        prompt = Decimal(self.prompt_tokens) * self.prompt_price_per_million / unit
        completion = Decimal(self.completion_tokens) * self.completion_price_per_million / unit
        return (prompt + completion).quantize(Decimal("0.000001"))


usage = Usage(12_000, 800, Decimal("3"), Decimal("15"))
print(usage.total_tokens)
print(usage.total_price)
```

**说明**：单价单位进入公式，不能默认所有 Provider 都按同一单位报价。

### 2.2 聚合流式调用的最终用量

```python
# 文件：stream_usage.py
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    text: str
    usage: dict[str, int] | None = None


def consume(chunks: list[Chunk]) -> tuple[str, dict[str, int]]:
    parts: list[str] = []
    final_usage: dict[str, int] | None = None
    for chunk in chunks:
        parts.append(chunk.text)
        if chunk.usage is not None:
            final_usage = chunk.usage

    if final_usage is None:
        final_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    return "".join(parts), final_usage


text, usage = consume([Chunk("你"), Chunk("好", {"prompt_tokens": 8, "completion_tokens": 2, "total_tokens": 10})])
print(text, usage)
```

**说明**：不要把每个 chunk 都当成独立完整用量累加，否则供应商在末尾返回累计 usage 时会重复计费。

## 3. dify 仓库源码解读

### 3.1 统一的 `LLMUsage` 数据模型

**文件位置**：`/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/model_runtime/entities/llm_entities.py`  
**核心代码**（行 43-59）：

```python
class LLMUsage(ModelUsage):
    """
    Model class for llm usage.
    """

    prompt_tokens: int
    prompt_unit_price: Decimal
    prompt_price_unit: Decimal
    prompt_price: Decimal
    completion_tokens: int
    completion_unit_price: Decimal
    completion_price_unit: Decimal
    completion_price: Decimal
    total_tokens: int
    total_price: Decimal
    currency: str
    latency: float
```

**解读**：token、单价、单价单位、金额、币种和延迟被统一封装。所有金额字段使用 `Decimal`，使跨调用聚合不受二进制浮点误差影响。

### 3.2 调用后更新持久化统计

**文件位置**：`/Users/xu/code/github/dify/api/core/tools/utils/model_invocation_utils.py`  
**核心代码**（行 161-173）：

```python
        # update tool model invoke
        tool_model_invoke.model_response = str(response.message.content)
        if response.usage:
            tool_model_invoke.answer_tokens = response.usage.completion_tokens
            tool_model_invoke.answer_unit_price = response.usage.completion_unit_price
            tool_model_invoke.answer_price_unit = response.usage.completion_price_unit
            tool_model_invoke.provider_response_latency = response.usage.latency
            tool_model_invoke.total_price = response.usage.total_price
            tool_model_invoke.currency = response.usage.currency

        db.session.commit()

        return response
```

**解读**：调用完成后，把统一 usage 写回工具调用记录，再提交事务。响应文本、输出 token、价格、延迟和币种由同一次结果更新，便于审计。

## 4. 关键要点总结

- 调用前 token 是估算值，调用后供应商 usage 才是优先结算依据。
- 流式用量可能只在最后一个 chunk 出现，必须理解其是增量还是累计。
- 金额使用 `Decimal`，并显式保留单价单位和币种。
- `LLMUsage` 统一了不同 Provider 的技术用量与价格字段。
- 模型调用统计与租户订阅配额相关，但属于不同领域概念。

## 5. 练习题

### 练习 1：基础（必做）

扩展 `Usage`，分别输出输入费用和输出费用，并验证二者之和等于总费用。

**参考答案**：把两个费用各自实现为 `Decimal` 属性，最后相加并统一量化精度。

### 练习 2：进阶

实现按 Provider、模型和日期聚合的用量报表，输出 token、总价、平均延迟和 P95 延迟。

### 练习 3：挑战（选做）

追踪一次 dify 流式对话的 usage 从最后一个 `LLMResultChunk` 到消息持久化的完整路径，并设计供应商未返回 usage 时的补算与标记策略。

## 6. 参考资料

- `/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/model_runtime/entities/llm_entities.py`
- `/Users/xu/code/github/dify/api/core/tools/utils/model_invocation_utils.py`
- `/Users/xu/code/github/dify/api/services/billing_service.py`
- Python Decimal：https://docs.python.org/3/library/decimal.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
