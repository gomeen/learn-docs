# 7.3.2 上下文窗口管理与截断

> 掌握 RAG 中的上下文窗口管理：截断、压缩、重排，让 LLM 看到最有用的信息。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释为什么需要上下文管理
- 描述主流的上下文压缩方法
- 实现 token 计数和截断逻辑
- 了解 dify 的上下文管理策略

## 📚 前置知识

- Token 与上下文窗口（详见 [Tokens 与上下文](../06-llm-and-ai/03-tokens-context.md)）
- RAG 评测（详见 [RAG Evaluation](./15-rag-evaluation.md)）

## 1. 核心概念

### 1.1 为什么需要上下文管理？

- LLM 有上下文窗口限制（4K-200K tokens）
- 检索到的文档可能很多、很长
- 把所有内容塞给 LLM 会：
  - 超出窗口报错
  - 浪费 token 配额（贵）
  - "中间遗忘"问题（重要信息在中间被忽略）

### 1.2 常见上下文管理策略

| 策略 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| **截断（Truncate）** | 直接砍掉超出部分 | 简单 | 砍掉的可能是关键信息 |
| **Top-K 截断** | 只保留相似度最高的 K 个 | 简单有效 | K 难调 |
| **滑窗** | 分段送入，多轮问答 | 处理长文 | 多轮成本高 |
| **LLM 压缩** | 用 LLM 总结、提取关键信息 | 保留语义 | 成本高、可能丢失信息 |
| **Rerank + 截断** | 先重排再截断 | 综合最优 | 多一步计算 |

### 1.3 Token 计数

精确管理需要按 token 计数：
- OpenAI：`tiktoken` 库
- HuggingFace：`transformers.AutoTokenizer`
- dify：用 GPT2 tokenizer 兜底

## 2. 代码示例

### 2.1 用 tiktoken 计数和截断

```python
import tiktoken


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """精确计算 token 数"""
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def truncate_to_tokens(text: str, max_tokens: int, model: str = "gpt-4") -> str:
    """按 token 截断"""
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return encoding.decode(tokens[:max_tokens])


# 测试
text = "Dify 是一个开源 LLM 平台，" * 100
print(f"原文本 token 数: {count_tokens(text)}")
truncated = truncate_to_tokens(text, max_tokens=50)
print(f"截断后 token 数: {count_tokens(truncated)}")
```

### 2.2 按 token 预算选 Top-K

```python
from typing import List


def select_within_budget(documents: List[dict], query: str, max_tokens: int = 3000) -> List[dict]:
    """在 token 预算内选最相关的文档

    documents: [{"content": str, "score": float}, ...]
    """
    selected = []
    used = 0
    # 为 query 预留一些 token
    query_tokens = count_tokens(query)
    budget = max_tokens - query_tokens

    for doc in sorted(documents, key=lambda x: x["score"], reverse=True):
        doc_tokens = count_tokens(doc["content"])
        if used + doc_tokens > budget:
            continue
        selected.append(doc)
        used += doc_tokens
    return selected
```

### 2.3 用 LLM 压缩上下文

```python
class ContextCompressor:
    """用 LLM 压缩检索结果"""

    PROMPT = """基于以下检索到的文档，提取与问题相关的关键信息，去除冗余。
保留：关键事实、数据、定义
删除：重复内容、不相关段落

问题：{query}

文档：
{documents}

压缩后的关键信息："""

    def __init__(self, llm):
        self.llm = llm

    def compress(self, query: str, documents: List[str]) -> str:
        docs_str = "\n\n".join(documents)
        prompt = self.PROMPT.format(query=query, documents=docs_str)
        return self.llm.invoke(prompt)
```

### 2.4 常见错误：按字符截断而不是 token

```python
# ❌ 错误：按字符截断，中英文混排时误差大
text[:3000]  # 中文字符 1 个可能算多个 token

# ✅ 正确：按 token 截断
truncate_to_tokens(text, max_tokens=1000)
```

## 3. 关键要点总结

- 上下文管理是 RAG 落地必做：截断、压缩、Top-K
- 必须按 token 计数（不是字符）
- 预算分配：query + system + context
- 优先截断 context，保留核心消息

---

**文档版本**：v1.0
**最后更新**：2026-07-13
