# 3.5.1 向量检索基础：余弦相似度 / 向量空间

> 把文本或图片映射到高维向量，用距离度量召回语义相近的内容，并理解近似最近邻的取舍。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 embedding 与向量空间
- 计算余弦相似度、点积和欧氏距离
- 理解 top_k、阈值、归一化和 ANN
- 能看懂 dify 向量创建与检索流程

## 📚 前置知识

- Python 基础与线性代数中的向量
- [3.1.5 SQL 性能优化](../../_common/21-sql/05-sql-performance.md)

## 1. 核心概念

### 1.1 Embedding

Embedding 模型把语义对象映射为固定维度浮点数组。向量维度必须与索引一致；更换模型可能改变维度和空间分布，通常需要重建索引。

### 1.2 相似度

余弦相似度关注夹角：`cos(a,b)=a·b/(||a|| ||b||)`；归一化向量上，点积与余弦排序等价。欧氏距离关注直线距离。不同向量库返回“相似度”或“距离”，阈值方向不能混用。

### 1.3 精确与近似检索

精确搜索比较所有向量，结果准确但 O(Nd)。HNSW、IVF 等 ANN 索引用召回率换速度和内存。`top_k` 决定候选数，`score_threshold` 做最低质量过滤；RAG 常再用 reranker 精排。

## 2. 代码示例

### 2.1 计算余弦相似度并返回 top-k

```python
from math import sqrt


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("vectors must have the same dimension")
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def top_k(query, vectors, k, threshold=0.0):
    scored = [
        (doc_id, cosine_similarity(query, vector))
        for doc_id, vector in vectors.items()
    ]
    ordered = sorted(scored, key=lambda item: item[1], reverse=True)
    return [item for item in ordered if item[1] >= threshold][:k]


vectors = {"a": [0.9, 0.1], "b": [0.0, 1.0]}
print(top_k([1.0, 0.0], vectors, 1))
```

**说明**：示例是精确搜索；生产向量库用 ANN 索引，并要统一“距离转分数”的语义。

## 3. 关键要点总结

- embedding 模型定义向量空间，换模型通常要重建索引
- 余弦、点积和欧氏距离的分数方向不同
- ANN 用少量召回损失换低延迟
- top_k、阈值和 rerank 共同决定质量

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
