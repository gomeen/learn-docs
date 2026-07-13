# 7.3.5 dify 的 RAG 实现源码分析

> 深度解读 dify 的 RAG 实现：从前端 API 到后端检索的完整调用链。

## 🎯 学习目标

完成本文档后，你将能够：
- 画出 dify 一次 RAG 检索请求的端到端调用链
- 看懂 `dataset_retrieval.py` 的核心函数
- 理解 dify 如何处理多 Dataset、多模态、引用溯源
- 理解 dify 与 LangChain 的区别

## 📚 前置知识

- 07-rag-and-agent/01-rag-overview.md 至 16-rag-failure-modes.md

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

## 3. dify 仓库源码解读

### 3.1 检索服务主入口

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/retrieval/dataset_retrieval.py`
**核心代码**（行 100-180，示意）：

```python
class DatasetRetrieval:
    """dify RAG 检索的核心服务"""

    @classmethod
    def retrieve(
        cls,
        *,
        retrieval_method: RetrievalMethod,
        dataset_id: str,
        query: str,
        top_k: int,
        score_threshold: float | None = None,
        rerank_model_instance: ModelInstance | None = None,
        weights: Weights | None = None,
        metadata_filtering_conditions: list[MetadataFilteringCondition] | None = None,
    ) -> list[Document]:
        # Step 1: 元数据过滤
        documents = cls._apply_metadata_filter(dataset_id, metadata_filtering_conditions)

        # Step 2: 按 retrieval_method 分支
        if retrieval_method == RetrievalMethod.SEMANTIC_SEARCH:
            documents = RetrievalService.vector_search(
                dataset_id, query, top_k, score_threshold, documents
            )
        elif retrieval_method == RetrievalMethod.FULL_TEXT_SEARCH:
            documents = RetrievalService.keyword_search(
                dataset_id, query, top_k, score_threshold, documents
            )
        elif retrieval_method == RetrievalMethod.HYBRID_SEARCH:
            documents = RetrievalService.hybrid_search(
                dataset_id, query, top_k, score_threshold, weights, documents
            )

        # Step 3: Rerank（可选）
        if rerank_model_instance:
            documents = RerankModelRunner(rerank_model_instance).run(
                query=query, documents=documents, score_threshold=score_threshold, top_n=top_k
            )
        elif weights and retrieval_method == RetrievalMethod.HYBRID_SEARCH:
            # 权重法 Rerank
            documents = WeightRerankRunner(tenant_id, weights).run(...)

        return documents
```

**解读**：
- 这是 dify RAG 检索的统一入口
- 用 **Strategy 模式** + **Factory 模式** 分发不同检索方法
- 元数据过滤、Rerank 都是可选的，按需启用
- 返回统一的 `list[Document]`，上游不需要关心底层实现

### 3.2 KnowledgeRetrieval 节点

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/knowledge_retrieval/knowledge_retrieval_node.py`
**核心代码**（行 1-60）：

```python
from core.workflow.nodes.base import BaseNode
from core.workflow.nodes.knowledge_retrieval.retrieval import KnowledgeRetrievalRequest


class KnowledgeRetrievalNode(BaseNode):
    """工作流中的"知识检索"节点"""

    node_type = BuiltinNodeTypes.KNOWLEDGE_RETrieval

    def _run(self) -> NodeRunResult:
        # 1. 构造检索请求
        request = KnowledgeRetrievalRequest(
            dataset_ids=self.node_data.dataset_ids,
            query=self.graph_runtime_state.variable_pool.get(...).text,
            top_k=self.node_data.top_k,
            retrieval_mode=self.node_data.retrieval_mode,
            ...
        )

        # 2. 调用 DatasetRetrieval
        documents = DatasetRetrieval.retrieve(
            retrieval_method=request.retrieval_mode,
            dataset_id=request.dataset_ids[0],
            query=request.query,
            top_k=request.top_k,
            ...
        )

        # 3. 拼装返回结果（含 source 信息）
        return NodeRunResult(outputs={"result": documents})
```

**解读**：
- 知识检索节点是工作流中的"调用点"
- 它把工作流变量（query、dataset_ids 等）传给 `DatasetRetrieval.retrieve()`
- 返回的 `Document` 列表会作为变量供后续节点使用

### 3.3 KnowledgeRetrievalRequest 请求结构

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/knowledge_retrieval/entities.py`
**核心代码**：

```python
class KnowledgeRetrievalRequest(BaseModel):
    """知识检索节点的请求参数"""
    dataset_ids: list[str]
    query: str
    top_k: int = 5
    score_threshold: float = 0.5
    retrieval_mode: str = "semantic_search"
    rerank_enable: bool = False
    rerank_model: dict | None = None
    weights: dict | None = None
    metadata_filtering_conditions: list[dict] | None = None
    attachment_ids: list[str] | None = None  # 附件支持
```

**解读**：
- 用 Pydantic 定义请求结构，自带校验
- 支持附件检索（attachment_ids）
- 与前端表单字段一一对应

## 4. 关键要点总结

- dify RAG 的统一入口是 `DatasetRetrieval.retrieve()`
- 工作流节点 `KnowledgeRetrievalNode` 调用这个入口
- 三种检索模式 + 可选 Rerank + 可选元数据过滤
- dify 在 LangChain 概念之上做了产品化包装

## 5. 练习题

### 练习 1：基础（必做）

调用 dify 的 `DatasetRetrieval.retrieve()` 方法（mock 一个），返回 5 条结果，打印每条的内容、score、metadata。

### 练习 2：进阶

阅读 `knowledge_retrieval_node.py` 完整实现，理解节点如何与变量池交互（读 query、dataset_ids，写 result）。

### 练习 3：挑战（选做）

画一张完整的时序图：用户在前端发起 chat → 工作流引擎调度 → KnowledgeRetrievalNode → DatasetRetrieval → RetrievalService → VectorStore → Rerank → 返回答案。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/retrieval/dataset_retrieval.py`
- `/Users/xu/code/github/dify/api/core/workflow/nodes/knowledge_retrieval/knowledge_retrieval_node.py`
- `/Users/xu/code/github/dify/api/core/workflow/nodes/knowledge_retrieval/entities.py`
- `/Users/xu/code/github/dify/api/core/workflow/nodes/knowledge_retrieval/retrieval.py`

---

**文档版本**：v1.0
**最后更新**：2026-07-13