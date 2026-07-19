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
- [3.1.5 SQL 性能优化](./05-sql-performance.md)

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

## 3. dify 仓库源码解读

### 3.1 Dify 的向量写入与删除契约

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/datasource/vdb/vector_base.py`  
**核心代码**（行 21-45）：

```python

    @abstractmethod
    def get_type(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def create(self, texts: list[Document], embeddings: list[list[float]], **kwargs) -> list[str] | None:
        raise NotImplementedError

    @abstractmethod
    def add_texts(self, documents: list[Document], embeddings: list[list[float]], **kwargs) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def text_exists(self, id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete_by_ids(self, ids: list[str]) -> None:
        raise NotImplementedError

    def get_ids_by_metadata_field(self, key: str, value: str):
        raise NotImplementedError

    @abstractmethod
```

**解读**：
- `@abstractmethod` 声明抽象契约（详见 [抽象基类 ABC](../01-fundamentals/19-abc.md)），所有后端必须实现创建、追加、存在检查和删除。
- metadata 字段删除也被纳入统一接口。
- 上层无需知道具体 SDK（dify 适配层详见 [向量库适配层](./28-vdb-in-dify.md)）。

### 3.2 查询文本到向量再检索

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/datasource/vdb/vector_factory.py`  
**核心代码**（行 236-251）：

```python

    def text_exists(self, id: str) -> bool:
        return self._vector_processor.text_exists(id)

    def delete_by_ids(self, ids: list[str]):
        self._vector_processor.delete_by_ids(ids)

    def delete_by_metadata_field(self, key: str, value: str):
        self._vector_processor.delete_by_metadata_field(key, value)

    def search_by_vector(self, query: str, **kwargs: Any) -> list[Document]:
        query_vector = self._embeddings.embed_query(query)
        return self._search_by_vector_traced(query_vector, **kwargs)

    @trace_span()
    def _search_by_vector_traced(self, query_vector: list[float], **kwargs) -> list[Document]:
```

**解读**：
- 文本先通过 embedding 模型变成浮点向量。
- trace_span 包装真正后端检索。
- 上层不依赖具体后端 API。

## 4. 关键要点总结

- embedding 模型定义向量空间，换模型通常要重建索引
- 余弦、点积和欧氏距离的分数方向不同
- ANN 用少量召回损失换低延迟
- top_k、阈值和 rerank 共同决定质量

## 5. 练习题

### 练习 1：基础（必做）

手算两个二维向量的余弦相似度。

### 练习 2：进阶

扩展示例支持欧氏距离并比较排序。

### 练习 3：挑战（选做）

追踪 dify 从查询字符串到后端检索的调用链。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/datasource/vdb/vector_base.py`
- `/Users/xu/code/github/dify/api/core/rag/datasource/vdb/vector_factory.py`
- pgvector 距离：https://github.com/pgvector/pgvector
- HNSW 论文：https://arxiv.org/abs/1603.09320

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
