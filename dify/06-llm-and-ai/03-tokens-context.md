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
- [02-typeddict.md](../01-fundamentals/09-typeddict.md)
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

## 3. 关键要点总结

- token 是 tokenizer 的离散单位，不等同于字符或单词
- 上下文窗口包含提示、历史、工具信息和输出等全部有效上下文
- `max_tokens` 限制输出长度，不能解决输入超出上下文的问题
- 输入与输出价格通常不同，必须分开计算成本
- dify 用 `LLMUsage` 统一记录 token、金额、币种和延迟

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
