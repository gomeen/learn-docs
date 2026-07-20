# 1.1.4 LLM 生成参数：temperature / top_p / top_k / max_tokens

> 理解常见采样参数如何改变候选 token 的概率分布，并为不同任务选择可控的生成策略。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 temperature 对 logits 和概率分布的影响
- 区分 top_p 的累计概率截断与 top_k 的固定候选数截断
- 理解 max_tokens 是输出上限而非回答长度保证
- 为分类、抽取、创意写作等场景选择参数并设计评测
- 能看懂 dify 如何把模型参数传入统一的 `invoke_llm` 接口

## 📚 前置知识

- [02-transformer.md](./02-transformer.md)
- [03-tokens-context.md](./03-tokens-context.md)
- 外部基础：概率、指数函数、Softmax 与字典操作

## 1. 核心概念

### 1.1 temperature、top_p 与 top_k

模型先为词表中每个候选 token 输出 logit，再经过 Softmax 形成概率。temperature 在 Softmax 前缩放 logits：

$$
p_i=\frac{e^{z_i/T}}{\sum_j e^{z_j/T}}
$$

- 较低的 $T$ 让高概率候选更突出，输出通常更稳定。
- 较高的 $T$ 让分布更平坦，增加多样性，也增加偏题风险。
- temperature 接近 0 时通常接近贪心选择，但服务实现可能有自己的下限和规则。

`top_k` 只保留概率最高的 k 个候选；`top_p`（nucleus sampling）按概率从高到低累加，保留累计概率首次达到 p 的最小候选集合。前者候选数固定，后者会随模型置信度动态变化。

参数不是质量旋钮：提高随机性不会增加知识，降低随机性也不能保证事实正确。不同供应商支持的参数、取值范围和组合规则不同；有些模型完全不开放某些采样参数。因此调用前必须以当前模型的参数声明为准。

### 1.2 max_tokens 与参数选择原则

`max_tokens` 是硬输出上限。模型可能因为自然结束、停止序列、工具调用或安全策略而提前停止；如果撞上上限，JSON、代码或句子都可能被截断。

常见起点如下，但必须通过真实数据集评测：

| 场景 | temperature | top_p / top_k | max_tokens 策略 |
| --- | --- | --- | --- |
| 分类、抽取 | 低 | 少调或使用默认值 | 接近目标格式上限 |
| 问答、摘要 | 低到中 | 通常用默认值 | 留出完整回答空间 |
| 头脑风暴 | 中到高 | 可限制概率尾部 | 按创意数量预算 |
| 代码/JSON | 低 | 避免同时过度截断 | 必须覆盖完整结构 |

一次只改变一个采样维度更容易评估。若同时收紧 temperature、top_p 和 top_k，可能导致候选过少和重复；若同时放宽，则难以判断是哪一项导致质量变化。

## 2. 代码示例

### 2.1 在固定 logits 上比较采样策略

```python
# 文件：sampling_demo.py
import math
import random


def sample_token(
    logits: dict[str, float], temperature: float, top_k: int, top_p: float
) -> str:
    scaled = {token: logit / max(temperature, 1e-6) for token, logit in logits.items()}
    maximum = max(scaled.values())
    weights = {token: math.exp(value - maximum) for token, value in scaled.items()}
    total = sum(weights.values())
    ranked = sorted(((token, weight / total) for token, weight in weights.items()), key=lambda x: -x[1])

    candidates = ranked[:top_k]
    nucleus: list[tuple[str, float]] = []
    cumulative = 0.0
    for token, probability in candidates:
        nucleus.append((token, probability))
        cumulative += probability
        if cumulative >= top_p:
            break

    tokens, probabilities = zip(*nucleus)
    return random.choices(tokens, weights=probabilities, k=1)[0]


logits = {"准确": 3.2, "清晰": 2.7, "有趣": 1.8, "离题": 0.2}
random.seed(7)
print([sample_token(logits, 0.4, 4, 0.9) for _ in range(8)])
print([sample_token(logits, 1.2, 4, 0.9) for _ in range(8)])
```

**说明**：示例顺序是 temperature 缩放、top_k 截断、top_p 截断、随机抽样。真实供应商的处理顺序和边界行为可能不同，因此这只是概念模型，不是任何厂商的精确复刻。

## 3. 关键要点总结

- temperature 改变概率分布的尖锐程度，不会改变模型知识
- top_k 固定候选数量，top_p 动态保留累计概率集合
- max_tokens 是输出上限，过小会截断，过大则增加潜在成本
- 参数支持情况是模型相关的，不能假设每个供应商都接受同一组合
- dify 将参数作为字典传给统一运行时，并在业务层继续解析输出

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
