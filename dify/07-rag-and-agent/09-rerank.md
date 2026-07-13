# 7.2.3 重排序（Rerank）模型

> 理解 Rerank 模型的作用：把向量检索的 top-K 重新排序，提升精度。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释为什么需要 Rerank
- 描述主流 Rerank 模型（Cross-Encoder、BGE Reranker、Cohere Rerank）
- 看懂 dify 中 RerankRunner 的实现
- 选择 Rerank 模型与权重 Rerank 的取舍

## 📚 前置知识

- 07-rag-and-agent/08-hybrid-search.md
- 06-llm-and-ai 中关于 Embedding 模型

## 1. 核心概念

### 1.1 为什么需要 Rerank？

向量检索是**双塔模型**（Bi-Encoder）：query 和 document 独立编码，最后算相似度。问题：

- query 和 document **没有深度交互**
- 一些关键的相关性信号被压缩到向量中丢失

**Rerank 模型是 Cross-Encoder**：query 和 document 拼在一起过模型，能做深度交互。精度高得多，但速度慢（无法全库搜，只能对 top-K 重排）。

### 1.2 标准 RAG 检索流程

```
向量召回 top-100 → Rerank 重排 → 取 top-5 → LLM 生成
```

### 1.3 主流 Rerank 模型

| 模型 | 类型 | 特点 |
|------|------|------|
| BGE Reranker v2 | 开源 | 中英双语 |
| Cohere Rerank 3 | 商用 API | 效果好 |
| Jina Rerank | 商用 API | 多语言 |
| 权重法 | 无需模型 | dify 自带 BM25+向量加权 |

## 2. 代码示例

### 2.1 用 BGE Reranker

```python
from sentence_transformers import CrossEncoder

# 加载 BGE Reranker
model = CrossEncoder("BAAI/bge-reranker-base")

# 准备 (query, document) 对
query = "什么是 RAG？"
documents = [
    "RAG 是检索增强生成。",
    "今天的天气真好。",
    "向量数据库存储 Embedding。",
]
pairs = [[query, doc] for doc in documents]

# 计算相关分数
scores = model.predict(pairs)
for doc, score in zip(documents, scores):
    print(f"{score:.4f}: {doc}")

# 按分数排序
ranked = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
```

### 2.2 自己实现一个 Rerank 抽象

```python
from abc import ABC, abstractmethod
from typing import List, Tuple


class BaseReranker(ABC):
    @abstractmethod
    def rerank(self, query: str, documents: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
        pass


class CrossEncoderReranker(BaseReranker):
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        from sentence_transformers import CrossEncoder
        self.model = CrossEncoder(model_name)

    def rerank(self, query, documents, top_k=5):
        pairs = [[query, d] for d in documents]
        scores = self.model.predict(pairs)
        ranked = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
```

### 2.3 常见错误：跳过 Rerank

```python
# ❌ 错误：直接用向量检索结果给 LLM
docs = vector_store.search(query, top_k=20)
context = "\n".join(docs[:5])  # top-5 可能不是最相关的

# ✅ 正确：先 Rerank 再给 LLM
docs = vector_store.search(query, top_k=20)  # 粗排
top_5 = reranker.rerank(query, docs, top_k=5)  # 精排
context = "\n".join([d for d, _ in top_5])
```

## 3. dify 仓库源码解读

### 3.1 RerankModelRunner

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/rerank/rerank_model.py`
**核心代码**（行 16-50）：

```python
class RerankModelRunner(BaseRerankRunner):
    def __init__(self, rerank_model_instance: ModelInstance):
        self.rerank_model_instance = rerank_model_instance

    @override
    def run(
        self,
        query: str,
        documents: list[Document],
        score_threshold: float | None = None,
        top_n: int | None = None,
        query_type: QueryType = QueryType.TEXT_QUERY,
    ) -> list[Document]:
        model_manager = ModelManager.for_tenant(
            tenant_id=self.rerank_model_instance.provider_model_bundle.configuration.tenant_id
        )
        is_support_vision = model_manager.check_model_support_vision(
            tenant_id=self.rerank_model_instance.provider_model_bundle.configuration.tenant_id,
            provider=self.rerank_model_instance.provider,
            model=self.rerank_model_instance.model_name,
            model_type=ModelType.RERANK,
        )
        if not is_support_vision:
            if query_type == QueryType.TEXT_QUERY:
                rerank_result, unique_documents = self.fetch_text_rerank(query, documents, score_threshold, top_n)
            else:
                return documents
```

**解读**：
- 通过 `ModelManager` 拿到 Rerank 模型的实例
- 判断是否支持多模态（视觉 Rerank）
- 不同 query_type 分支处理（文本 vs 多模态）
- 这就是 dify 对接任意 Rerank 提供商的统一接口

### 3.2 Rerank 工厂

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/rerank/rerank_factory.py`
**核心代码**（示意）：

```python
from core.rag.rerank.rerank_model import RerankModelRunner
from core.rag.rerank.weight_rerank import WeightRerankRunner


class RerankRunnerFactory:
    """根据用户配置创建不同的 Rerank Runner"""

    @staticmethod
    def create_rerank_runner(rerank_mode: str, tenant_id: str, weights=None, model_instance=None):
        if rerank_mode == "rerank_model":
            return RerankModelRunner(rerank_model_instance=model_instance)
        elif rerank_mode == "weighted_score":
            return WeightRerankRunner(tenant_id=tenant_id, weights=weights)
        else:
            raise ValueError(f"Unknown rerank mode: {rerank_mode}")
```

**解读**：
- 工厂模式：根据 `rerank_mode` 创建不同 Runner
- 支持两种模式：用专门的 Rerank 模型 / 用权重法（BM25+向量）
- 用户在 dify 前端选择 Rerank 模式，后端用工厂创建对应实现

## 4. 关键要点总结

- Rerank 模型是 Cross-Encoder，精度远高于向量检索
- 标准流程：向量粗排（top-100）→ Rerank 精排（top-5）
- 主流 Rerank 模型：BGE Reranker、Cohere Rerank、Jina
- dify 通过 RerankRunner 抽象，支持模型法和权重法两种 Rerank

## 5. 练习题

### 练习 1：基础（必做）

用 `sentence-transformers` 的 `CrossEncoder("BAAI/bge-reranker-base")` 对一组 (query, document) 对打分，观察排序结果。

### 练习 2：进阶

阅读 `rerank_model.py` 的 `fetch_text_rerank` 方法，理解 Rerank 模型如何把 Document 转换为模型输入格式。

### 练习 3：挑战（选做）

对比实验：在 50 条 QA 数据上，比较"纯向量检索"和"向量检索 + Rerank"的 top-5 命中率。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/rerank/rerank_model.py`
- `/Users/xu/code/github/dify/api/core/rag/rerank/rerank_factory.py`
- `/Users/xu/code/github/dify/api/core/rag/rerank/rerank_base.py`
- BGE Reranker：https://huggingface.co/BAAI/bge-reranker-base

---

**文档版本**：v1.0
**最后更新**：2026-07-13