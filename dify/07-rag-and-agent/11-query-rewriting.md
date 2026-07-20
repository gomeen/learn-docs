# 7.2.4 查询改写与 HyDE

> 理解查询改写（Query Rewriting）和 HyDE（Hypothetical Document Embeddings）等查询优化技术。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释为什么需要查询改写
- 描述 HyDE 的核心思想
- 列举常见的查询改写策略（Multi-Query、Step-back、HyDE）
- 看懂 dify 中查询改写的 prompt 模板

## 📚 前置知识

- 混合检索（详见 [Hybrid Search](./09-hybrid-search.md)）
- Prompt 工程（详见 [Prompt 基础](../06-llm-and-ai/08-prompt-basics.md)）
- Function Calling 路由场景（详见 [Function Calling](../06-llm-and-ai/17-function-calling.md)）

## 1. 核心概念

### 1.1 为什么需要查询改写？

用户的查询往往存在以下问题：

| 问题 | 例子 |
|------|------|
| 太口语化 | "那个能聊天的" |
| 太简短 | "dify 是啥？" |
| 缺少关键词 | "怎么做？" |
| 与文档语言不一致 | 用户用英文问，文档是中文 |

查询改写 = 用 LLM 把原始查询**转换成更适合检索的形式**。

### 1.2 常见查询改写策略

1. **Multi-Query**：让 LLM 生成 3-5 个查询变体，分别检索后合并结果
2. **Step-back Prompting**：从具体问题抽象出更通用的问题
3. **HyDE（Hypothetical Document Embeddings）**：让 LLM 生成"假设的答案"，用答案的 Embedding 检索真实文档
4. **Query Decomposition**：复杂问题拆成多个子问题

### 1.3 HyDE 的核心思想

```
用户问题 → LLM 生成假设答案 → Embedding(假设答案) → 检索
```

**为什么有效？** 假设答案虽然内容是假的，但语义空间接近真实文档，向量检索能命中真实答案。

## 2. 代码示例

### 2.1 Multi-Query 检索

```python
from typing import List


class MultiQueryRetriever:
    """生成多个查询变体分别检索"""

    def __init__(self, llm, vector_store, n_queries: int = 3):
        self.llm = llm
        self.vector_store = vector_store
        self.n_queries = n_queries

    def rewrite_query(self, original: str) -> List[str]:
        prompt = f"""基于原问题生成 {self.n_queries} 个不同的搜索查询。
要求：
1. 不同的视角（技术角度、用户角度、文档角度）
2. 不同的关键词
3. 保持原意

原问题：{original}

输出格式（每行一个查询）：
"""
        response = self.llm.invoke(prompt)
        # 解析 LLM 输出
        queries = [q.strip() for q in response.strip().split("\n") if q.strip()]
        return [original] + queries[:self.n_queries]

    def retrieve(self, query: str, top_k: int = 5) -> List[str]:
        queries = self.rewrite_query(query)
        all_docs = []
        for q in queries:
            docs = self.vector_store.search(q, top_k=top_k)
            all_docs.extend(docs)
        # 去重
        return list(dict.fromkeys(all_docs))[:top_k]
```

### 2.2 HyDE 实现

```python
class HyDERetriever:
    """HyDE: 用假设答案的 Embedding 检索"""

    def __init__(self, llm, embedder, vector_store):
        self.llm = llm
        self.embedder = embedder
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 5) -> List[str]:
        # 1. LLM 生成假设答案
        hypothetical_doc = self.llm.invoke(
            f"请基于你的知识回答以下问题，给出 100 字左右的专业回答：\n{query}"
        )
        # 2. 用假设答案做 Embedding
        hyde_embedding = self.embedder.embed(hypothetical_doc)
        # 3. 检索真实文档
        return self.vector_store.search_by_vector(hyde_embedding, top_k=top_k)
```

### 2.3 常见错误：查询改写 Prompt 不清晰

```python
# ❌ 错误：Prompt 太模糊，LLM 不知道改写啥
prompt = f"改写：{query}"

# ✅ 正确：明确指出改写目标和格式
prompt = f"""将以下口语化问题改写为适合文档检索的关键词查询：
要求：
- 删除口语词（那个、这个）
- 补充专业术语
- 保留核心意图

原始查询：{query}
改写后："""
```

## 3. 关键要点总结

- 查询改写把口语化查询转换为检索友好的查询
- Multi-Query：生成多个变体分别检索
- HyDE：用假设答案的 Embedding 检索真实文档
- dify 在多 Dataset 路由和 metadata 过滤中都用到了 LLM 查询改写

---

**文档版本**：v1.0
**最后更新**：2026-07-13
