# 6.2 Prompt Caching（提示词缓存）

> 理解供应商侧提示词前缀缓存的原理，并借助 dify 的模型边界设计稳定、可观测的缓存输入。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Prompt Caching、应用响应缓存和模型 Schema 缓存
- 识别适合缓存的稳定提示词前缀
- 设计缓存命中率、成本和延迟观测指标
- 理解 dify 当前模型管理代码中的缓存边界与失效风险

## 📚 前置知识

- [Token、上下文窗口与计费](./03-tokens-context.md)
- [Token 用量统计与计费](./36-token-tracking.md)
- [dify 的模型适配层](./33-model-runtime.md)
- 哈希、TTL 和缓存失效（详见 [哈希算法](../../_common/06-encryption/03-hash.md)、[缓存策略](../../_common/03-cache-patterns/01-strategies.md)）

## 1. 核心概念

### 1.1 三种容易混淆的缓存

| 缓存 | 缓存内容 | 命中后是否调用模型 |
| --- | --- | --- |
| Prompt Caching | 模型供应商已处理的稳定 token 前缀 | 是，只减少前缀处理成本/延迟 |
| 响应缓存 | 相同请求的最终答案 | 否 |
| Schema/凭据缓存 | 模型元数据或解析后的配置 | 是 |

Prompt Caching 通常由模型供应商实现。应用应按供应商协议传递缓存控制或依赖自动前缀缓存，并读取其返回的缓存用量字段。它不保证相同答案，也不应缓存敏感内容而忽略供应商的数据政策。

### 1.2 如何提高命中率

请求从稳定到动态排列：

```text
稳定 system 指令
→ 稳定工具定义
→ 稳定知识/示例
→ 对话历史
→ 当前用户输入、时间和随机值
```

缓存键通常受到模型、提示词字节、工具顺序和缓存断点影响。即使语义相同，空白、顺序或时间戳变化也可能导致未命中。不要为了缓存命中把不同租户的敏感上下文错误共享。

### 1.3 成本与可观测性

至少记录：普通输入 token、缓存写入 token、缓存读取 token、输出 token、首字延迟和总成本。评估时看“节省金额”，不要只看命中请求数；短提示词即使命中，收益也可能小于复杂度成本。

需要特别说明：给定的 dify `LLMUsage` 源码没有通用 `cached_tokens` 字段，仓库中也未发现一个跨 Provider 自动开启 Prompt Caching 的统一实现。因此，缓存能力和 usage 字段主要取决于具体模型插件，不能声称 dify 核心会自动缓存所有 Prompt。

## 2. 代码示例

### 2.1 构造稳定前缀和动态后缀

```python
# 文件：cache_friendly_prompt.py
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PromptParts:
    stable_prefix: str
    dynamic_suffix: str


def build_prompt(question: str, today: date) -> PromptParts:
    stable = (
        "你是企业知识库助手。\n"
        "规则：只根据证据回答；证据不足时明确说明；输出引用编号。\n"
        "输出格式：answer、citations、confidence。"
    )
    dynamic = f"当前日期：{today.isoformat()}\n用户问题：{question}"
    return PromptParts(stable_prefix=stable, dynamic_suffix=dynamic)


parts = build_prompt("退款规则是什么？", date.today())
print(parts.stable_prefix)
print(parts.dynamic_suffix)
```

**说明**：日期和用户问题位于动态尾部，避免每次改变可缓存的系统前缀。

### 2.2 计算缓存收益

```python
# 文件：cache_savings.py
from decimal import Decimal


def input_cost(
    regular_tokens: int,
    cache_write_tokens: int,
    cache_read_tokens: int,
    regular_price: Decimal,
    write_multiplier: Decimal,
    read_multiplier: Decimal,
) -> Decimal:
    unit = Decimal("1000000")
    cost = Decimal(regular_tokens) * regular_price
    cost += Decimal(cache_write_tokens) * regular_price * write_multiplier
    cost += Decimal(cache_read_tokens) * regular_price * read_multiplier
    return (cost / unit).quantize(Decimal("0.000001"))


first = input_cost(1_000, 20_000, 0, Decimal("3"), Decimal("1.25"), Decimal("0.10"))
next_call = input_cost(1_000, 0, 20_000, Decimal("3"), Decimal("1.25"), Decimal("0.10"))
print("first:", first, "next:", next_call)
```

**说明**：倍率仅作为输入参数演示，真实价格和字段必须读取当前供应商文档及响应，不能写死在平台公共逻辑中。

## 3. 关键要点总结

- Prompt Caching 缓存的是供应商处理后的稳定前缀，不等于答案缓存。
- 稳定内容放前面，时间、用户输入和随机内容放后面。
- 缓存键和隔离范围必须包含模型、租户及影响语义的配置。
- 评估普通、写入、读取 token 与真实金额，不能只看命中次数。
- dify 核心存在凭据和 Schema 缓存，但不能把它们误称为 Prompt Caching；具体能力取决于插件。

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
