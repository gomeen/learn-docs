# 7.3.5 dify 的 RAG 实现源码分析

> 深度解读 dify 的 RAG 实现：从前端 API 到后端检索的完整调用链。

## 🎯 学习目标

完成本文档后，你将能够：
- 画出 dify 一次 RAG 检索请求的端到端调用链
- 看懂 `dataset_retrieval.py` 的核心函数
- 理解 dify 如何处理多 Dataset、多模态、引用溯源
- 理解 dify 与 LangChain 的区别

## 📚 前置知识

- 本模块 RAG 系列（详见 [RAG 概览](./01-rag-overview.md)、[检索管道](./13-retrieval-pipeline.md)、[知识库 in dify](./06-knowledge-base-in-dify.md)）
- 向量库在 dify 中的接入（详见 [VDB in dify](../03-database/22-vdb-in-dify.md)）

## 1. 核心概念

### 1.1 dify 的 RAG 调用链

```
HTTP API (POST /v1/chat-messages)
  → 应用层 controller
    → 找到 Application 配置中的 Knowledge Retrieval 节点
      → KnowledgeRetrievalNode.run()
        → DatasetRetrieval.retrieve()
          → RetrievalService.search()
            → VectorStore / KeywordStore (具体后端)
            → RerankRunner.run() (可选)
              → 返回 list[Document]
                → 拼装 Prompt → LLM 调用
                  → 流式返回答案 + 引用信息
```

### 1.2 dify 与 LangChain 的区别

| 维度 | LangChain | dify |
|------|-----------|------|
| 形态 | Python 库 | 完整产品 |
| 用户 | 开发者 | 业务人员 |
| 配置 | 代码 | 图形界面 |
| 扩展 | Python 代码 | DSL + Plugin |

dify 在底层使用了 LangChain 的一些概念（如 Document、TextSplitter），但上层包装了自己的产品形态。

## 2. 代码示例

### 2.1 模拟 dify 的一次检索请求

```python
from dataclasses import dataclass, field
from typing import List


@dataclass
class RetrievalRequest:
    """dify 风格的检索请求"""
    dataset_ids: List[str]
    query: str
    top_k: int = 5
    score_threshold: float = 0.5
    retrieval_mode: str = "semantic_search"  # or "full_text_search", "hybrid_search"
    metadata_filter: dict = field(default_factory=dict)
    rerank_enabled: bool = False
    rerank_model: str = ""


@dataclass
class RetrievalResult:
    content: str
    score: float
    source: str
    metadata: dict


def mock_dify_retrieval(req: RetrievalRequest) -> List[RetrievalResult]:
    """模拟 dify 的检索流程"""
    all_results = []
    for ds_id in req.dataset_ids:
        # 单 Dataset 检索
        if req.retrieval_mode == "semantic_search":
            results = vector_search(ds_id, req.query, req.top_k * 3)
        elif req.retrieval_mode == "full_text_search":
            results = keyword_search(ds_id, req.query, req.top_k * 3)
        else:
            results = hybrid_search(ds_id, req.query, req.top_k * 3)

        # 元数据过滤
        if req.metadata_filter:
            results = [r for r in results if match_filter(r, req.metadata_filter)]
        all_results.extend(results)

    # Rerank
    if req.rerank_enabled:
        all_results = rerank(req.query, all_results, top_k=req.top_k)
    else:
        all_results.sort(key=lambda x: x.score, reverse=True)
        all_results = all_results[:req.top_k]

    return all_results
```

## 3. 关键要点总结

- dify RAG 的统一入口是 `DatasetRetrieval.retrieve()`
- 工作流节点 `KnowledgeRetrievalNode` 调用这个入口
- 三种检索模式 + 可选 Rerank + 可选元数据过滤
- dify 在 LangChain 概念之上做了产品化包装

---

**文档版本**：v1.0
**最后更新**：2026-07-13
