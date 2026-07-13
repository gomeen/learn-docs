# 7.2.1 相似度检索：余弦 / 欧氏 / 点积

> 理解向量相似度的三种度量方式，看懂 dify 在不同场景下如何选择。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分余弦相似度、欧氏距离、点积三种度量
- 选择合适的相似度度量
- 看懂 dify 中向量相似度的计算代码
- 理解向量归一化的重要性

## 📚 前置知识

- 线性代数基础（向量点积、范数）
- 07-rag-and-agent/04-embedding-selection.md

## 1. 核心概念

### 1.1 三种相似度度量

设查询向量为 $q$，文档向量为 $d$。

**余弦相似度**（Cosine Similarity）：
$$\text{cosine}(q, d) = \frac{q \cdot d}{\|q\| \|d\|}$$

**欧氏距离**（Euclidean Distance，值越小越相似）：
$$\text{euclidean}(q, d) = \sqrt{\sum_{i=1}^{n}(q_i - d_i)^2}$$

**点积**（Dot Product，未归一化）：
$$\text{dot}(q, d) = \sum_{i=1}^{n} q_i \cdot d_i$$

### 1.2 如何选择？

| 度量 | 适用场景 |
|------|----------|
| **余弦** | 文本 Embedding（业界默认） |
| **欧氏距离** | 图像 Embedding、聚类 |
| **点积** | 已归一化的向量（等价于余弦，但更快） |

### 1.3 归一化的意义

如果向量都已归一化（$\|v\| = 1$），则点积 = 余弦相似度，但点积计算更快。OpenAI 的 Embedding 模型输出就是归一化向量，所以可以直接用点积。

## 2. 代码示例

### 2.1 手写三种相似度

```python
import numpy as np
from typing import Callable


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """余弦相似度：范围 [-1, 1]，越大越相似"""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    """欧氏距离：范围 [0, +∞)，越小越相似"""
    return float(np.linalg.norm(a - b))


def dot_product(a: np.ndarray, b: np.ndarray) -> float:
    """点积：未归一化时范围很大"""
    return float(np.dot(a, b))


# 测试
q = np.array([1.0, 2.0, 3.0])
d1 = np.array([1.1, 2.1, 2.9])  # 相似
d2 = np.array([-1.0, -2.0, -3.0])  # 反向

print(f"d1 余弦: {cosine_similarity(q, d1):.4f}")  # 接近 1
print(f"d2 余弦: {cosine_similarity(q, d2):.4f}")  # 接近 -1
print(f"d1 欧氏: {euclidean_distance(q, d1):.4f}")  # 接近 0
```

### 2.2 批量计算相似度矩阵

```python
import numpy as np


def batch_cosine(query: np.ndarray, vectors: np.ndarray) -> np.ndarray:
    """query: (D,)，vectors: (N, D) -> 返回 (N,) 的相似度数组"""
    # 归一化
    q_norm = query / np.linalg.norm(query)
    v_norms = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    # 矩阵乘法
    return v_norms @ q_norm


# 使用
vectors = np.random.randn(100, 384)
query = np.random.randn(384)
scores = batch_cosine(query, vectors)
top_5 = np.argsort(scores)[::-1][:5]
print(f"Top-5 索引: {top_5}")
print(f"对应分数: {scores[top_5]}")
```

### 2.3 常见错误：未归一化用点积

```python
import numpy as np

a = np.array([1.0, 1.0])
b = np.array([10.0, 10.0])  # 与 a 同方向但模长 10 倍

# ❌ 错误：用点积，b 比 a 分数高很多
print(f"点积: {np.dot(a, b)}")  # 20.0

# ✅ 正确：用余弦相似度，方向相同都是 1.0
from numpy.linalg import norm
print(f"余弦: {np.dot(a, b) / (norm(a) * norm(b))}")  # 1.0
```

## 3. dify 仓库源码解读

### 3.1 向量检索中的相似度计算

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/retrieval/dataset_retrieval.py`
**核心代码**（节选，向量召回部分）：

```python
from typing import Any

import numpy as np


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """dify 内部用的余弦相似度计算"""
    a = np.array(vec_a)
    b = np.array(vec_b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _vector_search(embedding: list[float], segments: list[Any], top_k: int = 10) -> list[Any]:
    """对一组 Segment 做向量检索，按相似度排序"""
    scored = []
    for seg in segments:
        seg_vec = seg.get_embedding()
        score = _cosine_similarity(embedding, seg_vec)
        scored.append((seg, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [seg for seg, _ in scored[:top_k]]
```

**解读**：
- `_cosine_similarity` 处理了零向量的边界情况（避免除零）
- 实际 dify 用 Weaviate/Qdrant 等向量库的 built-in 相似度函数，这段代码是回退方案
- 检索时统一返回按相似度降序的 top-K

### 3.2 重排序中的加权相似度

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/rerank/weight_rerank.py`
**核心代码**（行 60-75）：

```python
query_scores = self._calculate_keyword_score(query, documents)
query_vector_scores = self._calculate_cosine(self.tenant_id, query, documents, self.weights.vector_setting)

rerank_documents = []
for document, query_score, query_vector_score in zip(documents, query_scores, query_vector_scores):
    score = (
        self.weights.vector_setting.vector_weight * query_vector_score
        + self.weights.keyword_setting.keyword_weight * query_score
    )
    if score_threshold and score < score_threshold:
        continue
    if document.metadata is not None:
        document.metadata["score"] = score
        rerank_documents.append(document)
```

**解读**：
- 综合分数 = 向量相似度 × 向量权重 + 关键词分数 × 关键词权重
- 这是 dify 的"权重重排序"实现，可调节两种信号的占比
- 关键设计：用权重参数让用户自定义偏重

## 4. 关键要点总结

- 余弦相似度是文本 Embedding 的事实标准
- 归一化后，点积 = 余弦相似度（计算更快）
- 欧氏距离常用于图像、聚类
- dify 在 Weight Rerank 中组合多种相似度信号

## 5. 练习题

### 练习 1：基础（必做）

随机生成 1000 个 768 维向量，实现一个纯 NumPy 的 top-10 相似度检索，记录耗时。

### 练习 2：进阶

阅读 `weight_rerank.py` 的 `_calculate_cosine` 方法，画出"加权重排序"的完整流程图。

### 练习 3：挑战（选做）

思考题：为什么 BM25（关键词）和向量检索的分数需要归一化到相同区间才能加权？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/rerank/weight_rerank.py`
- `/Users/xu/code/github/dify/api/core/rag/retrieval/dataset_retrieval.py`
- 向量相似度数学：https://en.wikipedia.org/wiki/Cosine_similarity

---

**文档版本**：v1.0
**最后更新**：2026-07-13