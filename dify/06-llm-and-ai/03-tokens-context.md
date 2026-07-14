# 1.1.3 Token、上下文窗口与计费

> 理解文本如何变成 token、上下文如何占用容量，以及一次 LLM 请求的成本如何从输入与输出用量计算出来。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分字符、单词与 token，并解释 token 数为何依模型而异
- 计算一次请求的输入 token、输出 token 和总 token
- 理解上下文窗口与最大输出长度之间的容量约束
- 根据输入价与输出价估算调用成本
- 能看懂 dify `LLMUsage` 中 token、价格和延迟字段的含义

## 📚 前置知识

- [01-llm-overview.md](./01-llm-overview.md)
- [02-transformer.md](./02-transformer.md)
- [02-typeddict.md](../01-fundamentals/08-typeddict.md)
- 外部基础：Decimal、小数乘法与基本 API 计费概念

## 1. 核心概念

### 1.1 Token 化与上下文窗口

LLM 不直接读取“字”或“单词”，而是读取 tokenizer 划分出的 token ID。常见 tokenizer 会把高频词、子词、标点、空白或字节序列映射到词表。于是：

- 英文单词可能是一个或多个 token。
- 中文字符不保证“一字一 token”。
- 代码的缩进、符号和长标识符也会消耗 token。
- 同一文本换模型或 tokenizer 后，token 数可能变化。

上下文窗口是模型单次推理可处理的总 token 容量，通常包含系统提示、历史消息、检索资料、工具定义、工具结果和本次生成内容。工程上可用以下不等式检查预算：

$$
T_{system}+T_{history}+T_{tools}+T_{input}+T_{output}\leq T_{context}
$$

`max_tokens` 一般只限制本次最多生成多少 token，它不会扩大上下文窗口。若输入已接近窗口上限，就需要删减、分块、检索、摘要或压缩历史，而不是只调高输出上限。

### 1.2 输入/输出计费与预算

多数 LLM 分开报告并计价：

- `prompt_tokens`：发送给模型的输入 token。
- `completion_tokens`：模型生成的输出 token。
- `total_tokens`：二者之和；不能用它直接乘一个统一单价，除非输入输出价相同。

若价格单位是每 1,000,000 token，成本公式为：

$$
Cost=\frac{T_{in}}{1{,}000{,}000}P_{in}+\frac{T_{out}}{1{,}000{,}000}P_{out}
$$

真实账单还可能包含缓存写入/读取、批处理、推理 token、图片 token、工具费用或供应商舍入规则。因此生产系统应优先保存供应商返回的 usage 与价格字段，离线估算只用于预算和预警。

## 2. 代码示例

### 2.1 估算上下文余量和调用成本

```python
# 文件：token_budget.py
from decimal import Decimal


def estimate_request(
    context_limit: int,
    input_tokens: int,
    requested_output_tokens: int,
    input_price_per_million: Decimal,
    output_price_per_million: Decimal,
) -> dict[str, int | Decimal]:
    available_output = max(context_limit - input_tokens, 0)
    allowed_output = min(requested_output_tokens, available_output)
    input_cost = Decimal(input_tokens) / Decimal(1_000_000) * input_price_per_million
    output_cost = Decimal(allowed_output) / Decimal(1_000_000) * output_price_per_million
    return {
        "allowed_output_tokens": allowed_output,
        "remaining_context_tokens": available_output - allowed_output,
        "estimated_max_cost": input_cost + output_cost,
    }


budget = estimate_request(
    context_limit=128_000,
    input_tokens=92_000,
    requested_output_tokens=48_000,
    input_price_per_million=Decimal("3"),
    output_price_per_million=Decimal("15"),
)
print(budget)
```

**说明**：请求虽然希望输出 48,000 token，但上下文只剩 36,000 token，所以必须限制输出或缩短输入。示例用 `Decimal` 避免浮点数在金额累计时产生不必要误差。

## 3. dify 仓库源码解读

### 3.1 `LLMUsage` 明确拆分输入与输出用量

**文件位置**：`/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/model_runtime/entities/llm_entities.py`  
**核心代码**（行 42-58）：

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

**解读**：
- 第 47-50 行：输入 token、输入单价单位和输入金额独立保存。
- 第 51-54 行：输出也使用独立单价，避免把高价输出错误地按输入价计算。
- 第 55-58 行：总 token、总金额、币种和延迟一起构成一次调用的可观测数据。
- 整体设计意图：把不同供应商返回的 usage 统一为精确、可累计的领域对象。

### 3.2 缺失总 token 时进行兼容计算

**文件位置**：`/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/model_runtime/entities/llm_entities.py`  
**核心代码**（行 88-109）：

```python
        prompt_tokens = metadata.get("prompt_tokens", 0)
        completion_tokens = metadata.get("completion_tokens", 0)
        total_tokens = metadata.get("total_tokens", 0)

        # If total_tokens is not provided but prompt and completion tokens are,
        # calculate total_tokens
        if total_tokens == 0 and (prompt_tokens > 0 or completion_tokens > 0):
            total_tokens = prompt_tokens + completion_tokens

        return cls(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            prompt_unit_price=Decimal(str(metadata.get("prompt_unit_price", 0))),
            completion_unit_price=Decimal(str(metadata.get("completion_unit_price", 0))),
            total_price=Decimal(str(metadata.get("total_price", 0))),
            currency=metadata.get("currency", "USD"),
            prompt_price_unit=Decimal(str(metadata.get("prompt_price_unit", 0))),
            completion_price_unit=Decimal(str(metadata.get("completion_price_unit", 0))),
            prompt_price=Decimal(str(metadata.get("prompt_price", 0))),
            completion_price=Decimal(str(metadata.get("completion_price", 0))),
            latency=metadata.get("latency", 0.0),
        )
```

**解读**：
- 第 88-95 行：供应商未返回 `total_tokens` 时，dify 用输入与输出之和补齐。
- 第 97-109 行：所有金额先转为字符串再构造 `Decimal`，减少二进制浮点误差。
- 整体设计意图：兼容供应商字段差异，同时保持下游计费与统计接口稳定。

## 4. 关键要点总结

- token 是 tokenizer 的离散单位，不等同于字符或单词
- 上下文窗口包含提示、历史、工具信息和输出等全部有效上下文
- `max_tokens` 限制输出长度，不能解决输入超出上下文的问题
- 输入与输出价格通常不同，必须分开计算成本
- dify 用 `LLMUsage` 统一记录 token、金额、币种和延迟

## 5. 练习题

### 练习 1：基础（必做）

某请求输入 80,000 token、输出 4,000 token，输入价为 2 美元/百万 token，输出价为 8 美元/百万 token。计算总成本。

**参考答案**：见 `solutions/03-tokens-context.md`

### 练习 2：进阶

扩展示例，使其分别接收系统提示、历史、检索资料、工具定义和用户输入的 token 数，并在剩余输出不足 1,024 token 时给出压缩建议。

### 练习 3：挑战（选做）

阅读 `LLMUsage.plus`，设计一个多步骤 Agent 的用量聚合器，并说明为什么累计时要同时关注总成本、总延迟以及每一步使用的单价。

## 6. 参考资料

- `/Users/xu/OrbStack/docker/images/langgenius/dify-api:2.0.0-beta.2/app/api/core/model_runtime/entities/llm_entities.py`
- `/Users/xu/code/github/dify/api/services/billing_service.py`
- Hugging Face Tokenizers：https://huggingface.co/docs/tokenizers/
- Anthropic Token Counting：https://platform.claude.com/docs/en/build-with-claude/token-counting

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
