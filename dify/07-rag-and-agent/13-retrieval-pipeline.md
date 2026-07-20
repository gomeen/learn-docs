# 7.2.6 dify 的检索管道（Retrieval Pipeline）

> 整体理解 dify 的检索管道：从用户查询到返回 top-K 文档的完整链路。

## 🎯 学习目标

完成本文档后，你将能够：
- 画出一个完整 dify 检索请求的流程
- 理解数据集路由（Dataset Router）的概念
- 看懂 `dataset_retrieval.py` 中的核心函数
- 区分向量检索、关键词检索、全文检索

## 📚 前置知识

- 知识库与检索子步骤（详见 [知识库 in dify](./06-knowledge-base-in-dify.md)、[相似度检索](./08-similarity-search.md)、[Hybrid Search](./09-hybrid-search.md)、[Rerank](./10-rerank.md)、[元数据过滤](./12-metadata-filter.md)）

## 1. 核心概念

### 1.1 dify 检索管道的层次结构

```
Application（应用）
  └── Knowledge Retrieval Node（工作流节点）
        └── DatasetRetrieval / KnowledgeRetrieval
              ├── Multi-Dataset Router（路由到哪些数据集）
              ├── 检索模式选择（向量 / 全文 / 混合）
              ├── 元数据过滤
              ├── Rerank
              └── 返回 Top-K 文档
```

### 1.2 检索模式

| 模式 | 适用 |
|------|------|
| **向量检索** | 语义查询，高质量模式 |
| **全文检索** | 关键词匹配，经济模式 |
| **混合检索** | 向量 + 关键词，平衡模式 |

### 1.3 完整流程

```
1. 多数据集路由（LLM 选择相关 Dataset）
2. 单 Dataset 内检索：
   a. 元数据过滤（可选）
   b. 向量检索 / 关键词检索 / 混合
   c. Top-K 召回
3. Rerank（可选）
4. 返回最终结果
```

## 2. 代码示例

### 2.1 简化的检索管道

```python
from typing import List
from dataclasses import dataclass


@dataclass
class RetrievedDoc:
    content: str
    score: float
    metadata: dict


class RetrievalPipeline:
    """极简 dify 检索管道"""

    def __init__(self, datasets: dict, reranker=None):
        self.datasets = datasets  # {"dataset_id": VectorStore}
        self.reranker = reranker

    def retrieve(
        self,
        query: str,
        dataset_ids: List[str],
        top_k: int = 5,
        metadata_filter: dict = None,
        mode: str = "vector",
    ) -> List[RetrievedDoc]:
        all_results = []

        # 1. 多数据集检索
        for ds_id in dataset_ids:
            store = self.datasets[ds_id]

            # 2. 元数据过滤（如果有）
            candidates = store
            if metadata_filter:
                candidates = store.filter(metadata_filter)

            # 3. 按模式检索
            if mode == "vector":
                results = store.vector_search(query, top_k=top_k)
            elif mode == "keyword":
                results = store.keyword_search(query, top_k=top_k)
            else:  # hybrid
                results = store.hybrid_search(query, top_k=top_k)

            all_results.extend(results)

        # 4. Rerank（如果有）
        if self.reranker:
            all_results = self.reranker.rerank(query, all_results, top_k=top_k)
        else:
            all_results.sort(key=lambda x: x.score, reverse=True)
            all_results = all_results[:top_k]

        return all_results
```

### 2.2 多数据集路由

```python
class DatasetRouter:
    """根据 query 选择要检索的 datasets"""

    def __init__(self, llm, available_datasets: list):
        self.llm = llm
        self.datasets = available_datasets

    def route(self, query: str) -> list:
        # 构造 prompt，让 LLM 选择 dataset
        ds_descriptions = "\n".join(
            f"- id={d['id']}, name={d['name']}, desc={d['description']}"
            for d in self.datasets
        )
        prompt = f"""基于用户查询，选择最相关的知识库（可多选）。

可用知识库：
{ds_descriptions}

用户查询：{query}

输出格式：返回逗号分隔的 dataset id 列表。"""

        response = self.llm.invoke(prompt)
        # 解析
        selected_ids = [s.strip() for s in response.split(",") if s.strip()]
        return selected_ids
```

## 3. 关键要点总结

- dify 检索管道：路由 → 元数据过滤 → 检索 → Rerank
- 三种检索模式：语义 / 全文 / 混合
- 通过统一的 `RetrievalService.search()` 入口屏蔽实现差异
- Rerank 是可选的，但建议生产环境开启

---

**文档版本**：v1.0
**最后更新**：2026-07-13
