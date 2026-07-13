# 7.1.1 RAG 概述：为什么需要检索增强

> 理解 RAG（Retrieval-Augmented Generation）的核心思想、能解决什么问题，以及它在 dify 中的位置。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 RAG 的核心思想：检索 + 生成
- 列举 LLM 原生方案的三大缺陷（幻觉、知识过时、领域知识缺失）
- 画出 RAG 的标准 Pipeline
- 能看懂 dify 中 `core/rag/` 目录的职责划分

## 📚 前置知识

- 06-llm-and-ai 中关于 LLM 调用、Embedding 的基础
- 03-database 中的向量数据库基础概念

## 1. 核心概念

### 1.1 什么是 RAG？

**RAG（Retrieval-Augmented Generation，检索增强生成）** 是一种将"信息检索"与"文本生成"结合的技术。其核心思想是：

> 在让 LLM 回答问题之前，先从一个**外部知识库**中检索相关文档，把检索到的内容作为上下文（context）一起交给 LLM，让 LLM 基于这些"事实"生成答案。

```
┌──────────┐      ┌──────────┐      ┌──────────┐
│ 用户问题 │ ───> │ 检索器    │ ───> │ LLM 生成 │
└──────────┘      └──────────┘      └──────────┘
                       │
                  ┌────┴────┐
                  │ 知识库   │  ← 文档 -> 切片 -> 向量化 -> 存储
                  └─────────┘
```

### 1.2 为什么需要 RAG？

直接用 LLM 回答问题存在三大问题：

| 问题 | 说明 | RAG 如何解决 |
|------|------|---------------|
| **幻觉（Hallucination）** | LLM 会一本正经地胡说八道 | 让 LLM 基于检索到的真实文档回答 |
| **知识过时** | 训练数据有截止日期 | 知识库可以随时更新 |
| **领域知识缺失** | 不了解企业私有数据 | 把私有文档灌入知识库 |

### 1.3 RAG 的标准 Pipeline

```
文档准备阶段（离线）：
  文档加载 → 文本清洗 → 切片 → Embedding → 向量数据库

回答阶段（在线）：
  用户问题 → Query 改写 → 向量化 → 检索 → 重排序 → Top-K 文档 → Prompt 拼装 → LLM 生成
```

## 2. 代码示例

### 2.1 最小可运行的 RAG Demo

```python
from typing import List

# 模拟一个极简的 RAG 系统
class MiniRAG:
    def __init__(self, knowledge_base: List[str]):
        self.knowledge_base = knowledge_base

    def retrieve(self, query: str, top_k: int = 2) -> List[str]:
        """极简检索：用关键词匹配代替向量检索"""
        scored = []
        for doc in self.knowledge_base:
            score = sum(1 for word in query.split() if word in doc)
            scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in scored[:top_k] if score > 0]

    def generate(self, query: str, context: List[str]) -> str:
        """极简生成：把 context 拼到答案里"""
        return f"基于以下资料：\n" + "\n".join(context) + f"\n\n回答：{query} 的相关信息如上。"

    def ask(self, query: str) -> str:
        context = self.retrieve(query)
        return self.generate(query, context)


# 使用
kb = [
    "Dify 是一个开源的 LLM 应用开发平台。",
    "RAG 是检索增强生成，可以解决 LLM 幻觉问题。",
    "向量数据库用于存储 Embedding 向量。",
]
rag = MiniRAG(kb)
print(rag.ask("什么是 RAG？"))
```

### 2.2 常见错误：没有 RAG 的 LLM 调用

```python
# ❌ 错误：让 LLM 凭空回答企业私有问题
def bad_qa(question: str) -> str:
    return llm.invoke(f"请回答：{question}")  # 没有上下文，LLM 只能瞎猜

# ✅ 正确：先检索，再让 LLM 基于事实回答
def good_qa(question: str, retriever, llm) -> str:
    docs = retriever.search(question, top_k=3)
    context = "\n".join(docs)
    prompt = f"基于以下资料回答问题：\n{context}\n\n问题：{question}"
    return llm.invoke(prompt)
```

## 3. dify 仓库源码解读

### 3.1 RAG 模块的目录结构

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/`
**核心代码**（顶层目录结构）：

```
core/rag/
├── cleaner/         # 文本清洗（去除 HTML 标签、特殊字符）
├── datasource/      # 数据源抽象（向量库 / 关键词表）
├── embedding/       # Embedding 调用与缓存
├── extractor/       # 多格式文档加载（PDF/Word/Markdown/...）
├── index_processor/ # 索引构建（高质量/经济两种模式）
├── models/          # Document、TextSegment 等数据结构
├── rerank/          # 重排序（Rerank 模型 + 权重法）
├── retrieval/       # 检索管道（混合检索、metadata 过滤、router）
└── splitter/        # 文本切片（递归、Fixed、QA 切分）
```

**解读**：
- `extractor/` 对应"文档加载"阶段
- `splitter/` 对应"切片"阶段
- `embedding/` 对应"向量化"阶段
- `index_processor/` 对应"索引构建"
- `retrieval/` 对应"在线检索"
- `rerank/` 对应"重排序"

### 3.2 文档实体类

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/models/document.py`
**核心代码**（行 1-25）：

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    """RAG 管道中流转的统一文档对象。

    不管是 PDF 解析、Markdown 解析、检索结果，统一用 Document 承载。
    """
    page_content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # dify 中所有 chunk 都需要 doc_id 用于去重和引用
        if "doc_id" not in self.metadata:
            self.metadata["doc_id"] = self.page_content[:100]
```

**解读**：
- dify 把所有文档（不论来源）都抽象为 `Document` 对象，包含 `page_content`（内容）和 `metadata`（元数据）
- `metadata` 在检索时被用于过滤和评分
- 这是 RAG 管道中"统一数据模型"的标准做法

## 4. 关键要点总结

- RAG = 检索 + 生成：用外部知识弥补 LLM 的不足
- 标准 Pipeline：文档加载 → 切片 → Embedding → 检索 → 重排序 → 生成
- dify 的 `core/rag/` 完整实现了这个 Pipeline 的每一个环节
- `Document` 是 RAG 管道中流转的统一数据结构

## 5. 练习题

### 练习 1：基础（必做）

手写一个 MiniRAG（不依赖任何框架），支持：
1. 添加 5 条文档到知识库
2. 输入查询返回最相关的一条文档

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/core/rag/extractor/extract_processor.py` 的 `ExtractProcessor.load_from_upload_file` 方法，画出从用户上传文件到 `list[Document]` 的调用链。

### 练习 3：挑战（选做）

思考题：RAG 与"长上下文 LLM"（如 Gemini 1M、Claude 200K）相比，各自的适用场景是什么？什么情况下 RAG 不可替代？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/`
- `/Users/xu/code/github/dify/api/core/rag/models/document.py`
- `/Users/xu/code/github/dify/api/core/rag/extractor/extract_processor.py`
- Lewis et al. 2020, "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"

---

**文档版本**：v1.0
**最后更新**：2026-07-13