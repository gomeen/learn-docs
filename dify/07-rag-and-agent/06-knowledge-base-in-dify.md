# 7.1.6 dify 的知识库架构分析

> 整体理解 dify 知识库的设计：Dataset、Document、Segment 三层模型，以及完整的索引流程。

## 🎯 学习目标

完成本文档后，你将能够：
- 描述 dify 知识库的三层数据模型（Dataset / Document / Segment）
- 画出一个文档从上传到可检索的完整流程
- 理解高质量模式与经济模式的差异
- 看懂 dify 的 IndexProcessor 调度

## 📚 前置知识

- RAG 索引链路（详见 [RAG 概览](./01-rag-overview.md)、[文档加载](./02-document-loading.md)、[Chunking](./03-chunking-strategies.md)、[Embedding 选型](./04-embedding-selection.md)、[向量索引](./05-vector-db-index.md)）
- dify 向量库接入（详见 [VDB in dify](../03-database/22-vdb-in-dify.md)）

## 1. 核心概念

### 1.1 三层数据模型

```
Dataset (知识库)
  └── Document (文档，物理文件)
        └── Segment (片段，切片后的 chunk)
              └── Embedding (向量化的片段)
```

| 层级 | 对应类 | 含义 |
|------|--------|------|
| Dataset | `Dataset` | 一个完整的知识库，可包含多个文档 |
| Document | `Document` | 一个上传的文件 |
| Segment | `DocumentSegment` | 切片后的 chunk |
| Embedding | `Embedding` | Segment 的向量表示 |

### 1.2 两种索引模式

| 模式 | 原理 | 成本 | 精度 |
|------|------|------|------|
| **高质量** | Embedding + 向量库 | 高（要调 Embedding API） | 高 |
| **经济** | 倒排索引（关键词） | 低 | 低 |

### 1.3 完整流程

```
上传文件 → ExtractProcessor 解析 → 文本清洗
        → TextSplitter 切片 → Segment 入库
        → IndexProcessor 索引（高质量：Embedding + 向量库 / 经济：关键词）
        → 完成
```

## 2. 代码示例

### 2.1 用伪代码模拟 dify 知识库创建

```python
from dataclasses import dataclass, field
from typing import List
import uuid


@dataclass
class Segment:
    content: str
    doc_id: str
    embedding: List[float] = field(default_factory=list)


@dataclass
class Document:
    name: str
    segments: List[Segment] = field(default_factory=list)


@dataclass
class Dataset:
    name: str
    documents: List[Document] = field(default_factory=list)
    embedding_cache: dict = field(default_factory=dict)

    def add_document(self, doc: Document) -> None:
        self.documents.append(doc)


class KnowledgeBaseService:
    """模拟 dify 的 KnowledgeBaseService"""

    def __init__(self, dataset: Dataset, mode: str = "high_quality"):
        self.dataset = dataset
        self.mode = mode

    def add_text(self, doc_name: str, text: str, splitter, embedder):
        # 1. 切片
        chunks = splitter.split_text(text)
        # 2. Embedding（仅高质量模式）
        doc = Document(name=doc_name)
        for chunk in chunks:
            seg = Segment(content=chunk, doc_id=str(uuid.uuid4()))
            if self.mode == "high_quality":
                seg.embedding = embedder.embed(chunk)
            doc.segments.append(seg)
        self.dataset.add_document(doc)
        return len(chunks)
```

### 2.2 高质量 vs 经济模式对比

```python
class HighQualityIndex:
    """高质量模式：向量检索"""

    def search(self, dataset: Dataset, query: str, embedder, top_k: int = 5):
        q_vec = embedder.embed(query)
        all_segments = [s for doc in dataset.documents for s in doc.segments]
        scored = [(s, self._cosine(q_vec, s.embedding)) for s in all_segments]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    @staticmethod
    def _cosine(a, b):
        import math
        dot = sum(x * y for x, y in zip(a, b))
        return dot / (math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(y*y for y in b)))


class EconomyIndex:
    """经济模式：关键词匹配"""

    def search(self, dataset: Dataset, query: str, top_k: int = 5):
        query_words = set(query.split())
        all_segments = [s for doc in dataset.documents for s in doc.segments]
        scored = []
        for s in all_segments:
            score = len(query_words & set(s.content.split()))
            scored.append((s, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, sc in scored[:top_k] if sc > 0]
```

## 3. 关键要点总结

- dify 知识库采用三层模型：Dataset → Document → Segment
- 两种索引模式：高质量（Embedding + 向量库）vs 经济（关键词）
- IndexProcessor 是调度器，工厂模式创建具体的索引处理器
- 父子模式：父 chunk + 子 chunk，检索子 chunk 但返回父 chunk（更完整的上下文）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
