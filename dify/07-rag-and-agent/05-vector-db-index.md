# 7.1.5 向量数据库与索引类型

> 理解向量数据库的工作原理、主流索引算法（HNSW/IVF/Flat），以及 dify 支持的向量库。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释向量数据库与传统数据库的核心差异
- 对比 Flat / IVF / HNSW 三种主流索引
- 列举 dify 支持的向量数据库（Weaviate/Qdrant/Milvus/PGVector/...）
- 理解 ANN（近似最近邻）算法的取舍

## 📚 前置知识

- 向量数据库与 pgvector（详见 [向量检索基础](../03-database/19-vector-search.md)、[pgvector](../03-database/20-pgvector.md)、[向量数据库对比](../03-database/21-vector-databases.md)）
- Embedding 选型（详见 [Embedding 选型](./04-embedding-selection.md)）

## 1. 核心概念

### 1.1 向量数据库做什么？

传统数据库擅长精确匹配（`WHERE name = 'Dify'`），但无法高效做"找最相似"的查询。向量数据库专门解决：

```
给定查询向量 q，在百万级向量库中找 top-K 个最相似的向量
```

> 📌 **Sighting**：相似度度量与 ANN 数学基础见 [向量检索基础](../03-database/19-vector-search.md)；Postgres 扩展见 [pgvector](../03-database/20-pgvector.md)；多后端对比见 [向量数据库对比](../03-database/21-vector-databases.md)。

### 1.2 主流索引算法对比

| 索引 | 原理 | 精度 | 速度 | 适用规模 |
|------|------|------|------|---------|
| **Flat**（暴力） | 遍历所有向量 | 100% | 慢 | < 10K |
| **IVF**（倒排文件） | 聚类分桶，只搜相关桶 | ~95% | 快 | 10K-10M |
| **HNSW**（分层导航小世界） | 图结构，多层跳转 | ~98% | 很快 | 10K-100M |
| **PQ**（乘积量化） | 压缩向量，牺牲精度换内存 | ~85% | 快 | 超大规模 |

### 1.3 dify 支持的向量数据库

dify 通过抽象的 `Vector` 接口支持多种后端：
- **Weaviate**（默认推荐）
- **Qdrant**
- **Milvus**
- **PGVector**（用 Postgres 存向量）
- **Chroma**（轻量本地）

## 2. 代码示例

### 2.1 暴力检索 vs 近似检索

```python
import numpy as np
from typing import List, Tuple


class FlatIndex:
    """暴力检索：遍历所有向量算距离"""
    def __init__(self, dim: int):
        self.vectors: List[np.ndarray] = []

    def add(self, vec: np.ndarray) -> None:
        self.vectors.append(vec)

    def search(self, query: np.ndarray, top_k: int = 5) -> List[Tuple[int, float]]:
        distances = []
        for i, vec in enumerate(self.vectors):
            # 余弦相似度
            sim = np.dot(query, vec) / (np.linalg.norm(query) * np.linalg.norm(vec))
            distances.append((i, sim))
        distances.sort(key=lambda x: x[1], reverse=True)
        return distances[:top_k]


# 测试
np.random.seed(42)
idx = FlatIndex(dim=128)
for i in range(1000):
    idx.add(np.random.randn(128))

query = np.random.randn(128)
results = idx.search(query, top_k=3)
print("Top-3 索引:", results)
```

### 2.2 简单的 HNSW 思想模拟

```python
import numpy as np

class SimpleNSW:
    """简化版 NSW（Navigable Small World）"""
    def __init__(self, dim: int, M: int = 16):
        self.dim = dim
        self.M = M  # 每个节点的邻居数
        self.nodes: List[np.ndarray] = []
        self.graph: List[List[int]] = []  # 邻接表

    def add(self, vec: np.ndarray) -> None:
        idx = len(self.nodes)
        self.nodes.append(vec)
        self.graph.append([])

        if idx == 0:
            return

        # 找最近的 M 个邻居
        distances = [(i, np.linalg.norm(vec - v)) for i, v in enumerate(self.nodes[:-1])]
        distances.sort(key=lambda x: x[1])
        neighbors = [i for i, _ in distances[:self.M]]

        # 双向连接
        self.graph[idx] = neighbors
        for n in neighbors:
            self.graph[n].append(idx)

    def search(self, query: np.ndarray, top_k: int = 5, enter_point: int = 0) -> List[int]:
        # 贪心搜索：从 enter_point 出发，每次跳到最近的邻居
        visited = set()
        current = enter_point
        best_dist = np.linalg.norm(query - self.nodes[current])

        while True:
            improved = False
            for n in self.graph[current]:
                if n in visited:
                    continue
                visited.add(n)
                d = np.linalg.norm(query - self.nodes[n])
                if d < best_dist:
                    current = n
                    best_dist = d
                    improved = True
            if not improved:
                break
        return [current]
```

### 2.3 常见错误：维度不匹配

```python
# ❌ 错误：查询向量与库内向量维度不一致
index.add(np.random.randn(512))
results = index.search(np.random.randn(384))  # 距离计算会出错

# ✅ 正确：保证查询与索引维度一致
assert query.shape[0] == index.dim
```

## 3. 关键要点总结

- 向量数据库专门解决"top-K 相似度检索"
- 主流索引：Flat（精确慢）/ IVF（聚类快）/ HNSW（图结构很快）
- dify 通过 Vector 抽象支持 Weaviate、Qdrant、Milvus、PGVector 等多种后端
- 索引类型选择是精度/速度/内存的权衡

---

**文档版本**：v1.0
**最后更新**：2026-07-13
