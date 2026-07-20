# 1.1.6 Embedding 模型原理与选型

> 理解文本如何映射到向量空间，并从语义质量、维度、语言、成本和迁移风险选择 Embedding 模型。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Embedding 向量如何表达文本的语义相似性
- 使用余弦相似度比较查询与文档向量
- 区分 Embedding、生成式 LLM 与 Rerank 模型的职责
- 从维度、上下文长度、语言、领域和成本评估模型
- 能看懂 dify 如何区分 `LLM`、`TEXT_EMBEDDING` 和 `RERANK` 模型类型

## 📚 前置知识

- [主流大模型对比](./01-llm-overview.md)
- [Transformer](./02-transformer.md)
- [Tokens 与上下文](./03-tokens-context.md)
- 向量检索与相似度度量（详见 [向量检索基础](../03-database/19-vector-search.md)）

## 1. 核心概念

### 1.1 从文本到语义向量

Embedding 模型把文本 $x$ 映射为固定维向量 $f(x)\in\mathbb{R}^d$。训练目标会让语义相近的文本在向量空间中更接近，让不相关文本更远。检索时先离线计算文档向量，再计算查询向量，通过近似最近邻索引找候选文档。

常用余弦相似度为：

$$
\operatorname{cos}(a,b)=\frac{a\cdot b}{\|a\|\|b\|}
$$

若向量已归一化，余弦相似度就等于点积。Embedding 擅长快速召回，但它把整段文本压缩成一个向量，细粒度条件可能丢失。因此 RAG（详见 [RAG 概览](../07-rag-and-agent/01-rag-overview.md)）常采用“两阶段检索”：Embedding 从大量文档中召回候选，Rerank 模型再同时阅读 query-document 对并精排（详见 [Rerank](../07-rag-and-agent/10-rerank.md)）。

### 1.2 模型选型与生命周期

选型不能只看排行榜，需要匹配实际数据：

| 维度 | 要问的问题 |
| --- | --- |
| 语义质量 | 在自有 query-document 标注集上 Recall@K、MRR 如何？ |
| 语言/领域 | 是否覆盖中文、代码、法律、医疗等真实语料？ |
| 上下文长度 | 文档块是否会被截断？长块是否真的提升召回？ |
| 向量维度 | 存储、索引内存和检索延迟是否可接受？ |
| 成本/吞吐 | 批量建库和在线查询的价格与速率如何？ |
| 可运维性 | 是否支持批处理、私有部署、版本固定与监控？ |

同一索引中的文档向量和查询向量必须来自同一模型、同一版本与同一预处理方案。更换模型后，旧向量与新向量不在同一个坐标空间，通常需要全量重建索引。模型迁移应采用双写、回填、离线评测、灰度切流，而不是只替换模型名称。

## 2. 代码示例

### 2.1 用余弦相似度完成一个最小检索器

```python
# 文件：vector_search.py
import math


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def search(
    query_vector: list[float], documents: dict[str, list[float]], limit: int = 2
) -> list[tuple[str, float]]:
    scored = [
        (document_id, cosine_similarity(query_vector, vector))
        for document_id, vector in documents.items()
    ]
    return sorted(scored, key=lambda item: item[1], reverse=True)[:limit]


document_vectors = {
    "refund": [0.95, 0.05, 0.10],
    "password": [0.05, 0.95, 0.10],
    "invoice": [0.75, 0.10, 0.45],
}
print(search([0.90, 0.08, 0.15], document_vectors))
```

**说明**：向量数值在真实系统中由 Embedding 模型生成。示例只展示检索阶段；大规模场景会使用向量数据库的近似最近邻索引，而不是遍历所有文档。

## 3. 关键要点总结

- Embedding 把文本映射到向量空间，用距离近似语义相关性
- 余弦相似度适合比较方向；归一化向量时可直接使用点积
- Embedding 负责高效召回，Rerank 负责对少量候选做更精细判断
- 选型必须使用自有语料评测，并权衡维度、成本、语言和上下文长度
- 更换 Embedding 模型通常需要重建全部文档向量和索引

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
