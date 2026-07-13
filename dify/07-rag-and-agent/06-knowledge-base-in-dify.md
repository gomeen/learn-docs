# 7.1.6 dify 的知识库架构分析

> 整体理解 dify 知识库的设计：Dataset、Document、Segment 三层模型，以及完整的索引流程。

## 🎯 学习目标

完成本文档后，你将能够：
- 描述 dify 知识库的三层数据模型（Dataset / Document / Segment）
- 画出一个文档从上传到可检索的完整流程
- 理解高质量模式与经济模式的差异
- 看懂 dify 的 IndexProcessor 调度

## 📚 前置知识

- 07-rag-and-agent/01-rag-overview.md 至 05-vector-db-index.md

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

## 3. dify 仓库源码解读

### 3.1 IndexProcessor 调度器

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/index_processor/index_processor.py`
**核心代码**（行 24-50）：

```python
class IndexProcessor:
    def format_preview(self, chunk_structure: str, chunks: Any) -> Preview:
        index_processor = IndexProcessorFactory(chunk_structure).init_index_processor()
        preview = index_processor.format_preview(chunks)
        data = Preview(
            chunk_structure=preview["chunk_structure"],
            total_segments=preview["total_segments"],
            preview=[],
            parent_mode=None,
            qa_preview=[],
        )
        if "parent_mode" in preview:
            data.parent_mode = preview["parent_mode"]

        # Different index processors return different preview shapes:
        # - paragraph/parent-child processors: {"preview": [...]}
        # - QA processor: {"qa_preview": [...]}
        for item in preview.get("preview", []):
            if "content" in item and "child_chunks" in item:
                data.preview.append(
                    PreviewItem(content=item["content"], child_chunks=item["child_chunks"], summary=None)
                )
```

**解读**：
- `IndexProcessorFactory` 是工厂模式，根据 `chunk_structure` 创建不同的 IndexProcessor
- 不同 IndexProcessor 返回的预览格式不同：段落/父子返回 `preview`，QA 返回 `qa_preview`
- 这是"适配器模式"的体现：上层统一接口，下层各自实现

### 3.2 数据模型关系

**文件位置**：`/Users/xu/code/github/dify/api/models/dataset.py`（节选）
**核心代码**（数据模型示意）：

```python
class Dataset(db.Model):
    """知识库（顶层）"""
    __tablename__ = "datasets"
    id = ...
    name = ...
    tenant_id = ...
    indexing_technique = ...  # "high_quality" or "economy"


class Document(db.Model):
    """文档（一个文件）"""
    __tablename__ = "documents"
    id = ...
    dataset_id = ...  # 关联到 Dataset
    data_source_type = ...  # 上传文件 / Notion / 网页
    name = ...


class DocumentSegment(db.Model):
    """文档片段（切片后的 chunk）"""
    __tablename__ = "document_segments"
    id = ...
    document_id = ...  # 关联到 Document
    content = ...
    embedding = ...  # 序列化后的向量（PGVector）
```

**解读**：
- 三层通过外键关联：`Dataset 1:N Document 1:N DocumentSegment`
- 高质量模式下，每个 Segment 有 `embedding` 字段（PGVector 中是 vector 类型）
- 经济模式下不写 `embedding`

## 4. 关键要点总结

- dify 知识库采用三层模型：Dataset → Document → Segment
- 两种索引模式：高质量（Embedding + 向量库）vs 经济（关键词）
- IndexProcessor 是调度器，工厂模式创建具体的索引处理器
- 父子模式：父 chunk + 子 chunk，检索子 chunk 但返回父 chunk（更完整的上下文）

## 5. 练习题

### 练习 1：基础（必做）

用 SQL 或伪 SQL 写出"查询某个知识库下所有包含关键词 'Dify' 的 Segment"的查询语句。

### 练习 2：进阶

阅读 `index_processor_factory.py` 和 `processor/paragraph_index_processor.py`，画出 `IndexProcessor` 的类继承关系。

### 练习 3：挑战（选做）

思考题：父子模式（parent-child）的检索为什么能提升效果？有什么代价？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/index_processor/index_processor.py`
- `/Users/xu/code/github/dify/api/core/rag/index_processor/index_processor_factory.py`
- `/Users/xu/code/github/dify/api/models/dataset.py`
- `/Users/xu/code/github/dify/api/core/rag/index_processor/constant/index_type.py`

---

**文档版本**：v1.0
**最后更新**：2026-07-13