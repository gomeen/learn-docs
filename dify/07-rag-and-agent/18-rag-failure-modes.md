# 7.3.4 RAG 的常见失败模式与对策

> 总结 RAG 系统的典型失败模式，理解每种问题的根因和对策。

## 🎯 学习目标

完成本文档后，你将能够：
- 列举 RAG 系统的 8 种典型失败模式
- 诊断 RAG 失效的根因
- 应用相应的对策
- 理解"上下文中毒"、"上下文分心"等专业概念

## 📚 前置知识

- [RAG 概览](./01-rag-overview.md)
- [RAG Evaluation](./15-rag-evaluation.md)

## 1. 核心概念

### 1.1 RAG 的 8 大失败模式

来自 Anthropic 等团队的实战总结：

| 失败模式 | 现象 | 根因 | 对策 |
|---------|------|------|------|
| **1. Missing Content** | 答案说"我不知道" | 知识库没有相关内容 | 扩大知识库、降低阈值 |
| **2. Missed Top Ranked** | 相关文档在 top-K 之外 | 检索不够准 | 加 Rerank、调整 K |
| **3. Not in Context** | 文档被检索到但没塞进 prompt | context 截断 | 加大 top-K、压缩 |
| **4. Not Extracted** | 在 context 中但 LLM 没注意 | LLM 没读到 | 加 emphasis、改 prompt |
| **5. Wrong Format** | 答案格式错误 | prompt 没规定格式 | 给样例 |
| **6. Incorrect Specificity** | 答案不准确/太泛 | prompt 不够具体 | Few-shot、加约束 |
| **7. Hallucination** | LLM 编造 | 答案超出 context | 让 LLM 只基于 context 回答 |
| **8. Context Poisoning** | LLM 被错误 context 带偏 | 检索到错误文档 | 严格过滤、人工审核 |

### 1.2 进阶失败模式

- **Context Distraction（分心）**：context 太长，LLM 被无关信息干扰
- **Context Confusion（困惑）**：context 中有矛盾信息
- **Context Clash（冲突）**：context 与 LLM 已有知识冲突

## 2. 代码示例

### 2.1 构造测试用例

```python
class RAGFailureTester:
    """用测试用例诊断 RAG 系统的失败模式"""

    def __init__(self, rag_pipeline):
        self.rag = rag_pipeline

    def test_missing_content(self):
        """测试 1：内容缺失"""
        query = "Dify 支持哪些不存在的功能 X？"  # 知识库里没有
        answer = self.rag.ask(query)
        if "我不知道" in answer or "not found" in answer.lower():
            return "PASS"
        return "FAIL: 应该承认不知道，但 LLM 编造了答案"

    def test_not_extracted(self):
        """测试 4：内容在 context 中但 LLM 没注意到"""
        # 在答案中加入 keyword check
        answer = self.rag.ask("Dify 的发布时间？")
        if "2023" not in answer and "2024" not in answer:
            return "FAIL: 答案中没提到 context 中的关键时间"
        return "PASS"
```

### 2.2 用 LLM 评估答案是否基于 context

```python
class FaithfulnessChecker:
    """检查答案是否忠于 context"""

    PROMPT = """判断以下答案是否完全基于 context（无幻觉）。

Context:
{context}

Answer:
{answer}

如果答案中的所有事实都能在 context 中找到，回答 YES。
如果有答案中的事实在 context 中找不到（属于幻觉），回答 NO，并说明哪些是幻觉。
"""

    def check(self, context: str, answer: str, llm) -> tuple[bool, str]:
        prompt = self.PROMPT.format(context=context, answer=answer)
        response = llm.invoke(prompt)
        is_faithful = "YES" in response.upper()
        return is_faithful, response
```

### 2.3 上下文去重 / 冲突检测

```python
def detect_context_conflicts(documents: list[str], llm) -> list[str]:
    """检测 context 中的事实冲突"""
    prompt = f"""以下文档中是否有事实冲突？请列出冲突点。

文档：
{chr(10).join(documents)}

冲突点（每行一个）："""
    response = llm.invoke(prompt)
    return [line.strip() for line in response.split("\n") if line.strip()]
```

### 2.4 常见错误：以为加了 RAG 就够了

```python
# ❌ 错误：认为 RAG = 一切问题都解决
answer = llm.invoke(f"基于 {docs} 回答：{query}")
# 实际上还有：检索质量、prompt 设计、答案格式 ...

# ✅ 正确：多层防护
def robust_rag(query, retriever, reranker, llm, evaluator):
    docs = retriever.search(query, top_k=20)
    top_docs = reranker.rerank(query, docs, top_k=5)
    context = "\n".join(top_docs)
    # 加防护 prompt
    prompt = f"""仅基于以下资料回答。如果资料不足以回答，请说"我不知道"。

资料：{context}

问题：{query}

答案："""
    answer = llm.invoke(prompt)
    # 自检
    if evaluator.check_faithful(answer, context):
        return answer
    return "无法确定答案"
```

## 3. 关键要点总结

- RAG 有 8 大典型失败模式，从"内容缺失"到"上下文中毒"
- 诊断靠测试用例 + 评估指标
- 对策靠多层防护：检索优化 + Rerank + 防护 prompt + 引用溯源
- 让 LLM 在不知道时主动说"不知道"是减少幻觉的关键

---

**文档版本**：v1.0
**最后更新**：2026-07-13
