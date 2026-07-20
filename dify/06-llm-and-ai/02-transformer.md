# 1.1.2 Transformer 架构概述

> 从自注意力、因果掩码和自回归生成出发，理解现代大语言模型如何处理与生成文本。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Transformer 相比 RNN/LSTM 更适合大规模训练的原因
- 理解 Query、Key、Value 与缩放点积注意力的计算过程
- 区分 encoder-only、encoder-decoder 与 decoder-only 三种架构
- 说明因果掩码、多头注意力、残差连接和前馈网络的作用
- 能理解 dify 为什么把模型实现隐藏在统一的 LLM 调用接口之后

## 📚 前置知识

- [01-llm-overview.md](./01-llm-overview.md)
- [08-generator.md](../01-fundamentals/16-generator.md)
- 外部基础：矩阵乘法、点积、Softmax 和神经网络前向传播

## 1. 核心概念

### 1.1 自注意力如何混合上下文

Transformer 先把每个 token 映射成向量，再通过三组可学习矩阵产生 Query、Key、Value：

$$
\operatorname{Attention}(Q,K,V)=\operatorname{softmax}\left(\frac{QK^T}{\sqrt{d_k}}+M\right)V
$$

可以把 Q 理解为“当前 token 想找什么”，K 理解为“每个 token 能用什么特征被匹配”，V 则是匹配后真正汇总的信息。矩阵 $M$ 是可选掩码；在 decoder-only 模型中，它通常是因果掩码，使位置 $i$ 不能读取位置 $i$ 之后的答案。

不同于 RNN 按顺序传递隐藏状态，自注意力可以在训练时同时计算整段序列，并让任意两个位置建立直接联系。代价是标准注意力的时间和显存复杂度随序列长度近似按 $O(n^2)$ 增长，因此长上下文并不是“免费”的。

### 1.2 从 Transformer 块到 decoder-only LLM

一个典型 Transformer 块包含：

1. 多头自注意力：并行学习语法、指代、主题等不同关系。
2. 残差连接与归一化：稳定深层网络训练并保留原始信息。
3. 逐位置前馈网络（FFN）：对每个位置进行非线性特征变换。
4. 位置表示：让模型区分相同 token 出现在不同位置的含义。

三种常见架构各有侧重：

| 架构 | 注意力方式 | 典型任务 |
| --- | --- | --- |
| Encoder-only | 双向读取整段输入 | 分类、检索表示 |
| Encoder-Decoder | 编码输入，解码输出 | 翻译、受控生成 |
| Decoder-only | 因果注意力，自回归预测 | 对话、代码生成、Agent |

现代通用 LLM 多采用 decoder-only：模型根据已有 token 的条件概率逐个预测下一个 token。推理阶段通常使用 KV Cache 保存历史层中的 Key/Value，避免每生成一个 token 都完整重算此前序列，但缓存本身会随上下文增长而占用显存。

## 2. 代码示例

### 2.1 用纯 Python 观察因果自注意力

```python
# 文件：causal_attention.py
import math


def softmax(values: list[float]) -> list[float]:
    maximum = max(values)
    exps = [math.exp(value - maximum) for value in values]
    total = sum(exps)
    return [value / total for value in exps]


def causal_attention(vectors: list[list[float]]) -> list[list[float]]:
    outputs: list[list[float]] = []
    scale = math.sqrt(len(vectors[0]))
    for position, query in enumerate(vectors):
        visible = vectors[: position + 1]
        scores = [sum(q * k for q, k in zip(query, key)) / scale for key in visible]
        weights = softmax(scores)
        outputs.append([
            sum(weight * value[dimension] for weight, value in zip(weights, visible))
            for dimension in range(len(query))
        ])
    return outputs


tokens = [[1.0, 0.0], [0.8, 0.2], [0.0, 1.0]]
for index, output in enumerate(causal_attention(tokens)):
    print(index, [round(value, 3) for value in output])
```

**说明**：示例为便于观察，直接令 Q、K、V 等于输入向量。`visible` 只包含当前位置及之前的 token，这就是因果掩码的效果；真实模型还会使用投影矩阵、多头拆分和批量矩阵运算。

## 3. 关键要点总结

- 自注意力使用 Q/K/V 根据相关性聚合整段上下文
- 因果掩码保证 decoder-only 模型只能依据已有 token 预测后续 token
- 多头注意力、FFN、残差连接和归一化共同组成 Transformer 块
- 标准注意力对序列长度是 $O(n^2)$，长上下文会增加计算与显存开销
- dify 不实现 Transformer，而是通过统一模型运行时调用不同供应商的 LLM

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
