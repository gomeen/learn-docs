# 7.3.1 RAG 评估体系：召回率 / 准确率 / 人工评估

> 掌握 RAG 系统的评估方法：从离线指标到在线 A/B 测试。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分召回率（Recall）和准确率（Precision）
- 描述 RAG 特有的评估指标（Context Relevance / Answer Faithfulness）
- 设计一个 RAG 评估数据集
- 了解 dify 的评估能力

## 📚 前置知识

- 机器学习基础（Precision/Recall/F1）
- 07-rag-and-agent/01-rag-overview.md

## 1. 核心概念

### 1.1 检索阶段指标

```
                    检索到的相关    检索到的不相关
实际相关             TP             FN
实际不相关           FP             TN
```

- **召回率（Recall）= TP / (TP + FN)**：相关文档被搜出来的比例
- **准确率（Precision）= TP / (TP + FP)**：搜出来的文档中相关比例
- **F1 = 2 × P × R / (P + R)**：两者的调和平均

### 1.2 RAG 特有指标（RAGAS 框架）

| 指标 | 衡量 | 计算方式 |
|------|------|----------|
| **Context Relevance** | 检索到的 context 是否与 query 相关 | LLM 评判 |
| **Answer Faithfulness** | 答案是否忠于 context（无幻觉） | LLM 评判 |
| **Answer Relevance** | 答案是否回答了 query | LLM 评判 |

### 1.3 评估的三层

1. **离线评估**：用标注数据集跑模型，算指标
2. **在线评估**：生产环境埋点统计（点击率、用户反馈）
3. **人工评估**：专家抽检，最可靠但成本高

## 2. 代码示例

### 2.1 计算 Precision/Recall/F1

```python
def precision_recall_f1(retrieved: set, relevant: set) -> dict:
    """retrieved: 检索到的 doc_id 集合；relevant: 实际相关的 doc_id 集合"""
    tp = len(retrieved & relevant)
    fp = len(retrieved - relevant)
    fn = len(relevant - retrieved)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    return {"precision": precision, "recall": recall, "f1": f1}


# 测试
retrieved = {"doc1", "doc2", "doc3", "doc4"}
relevant = {"doc2", "doc3", "doc5"}
print(precision_recall_f1(retrieved, relevant))
# precision=0.5, recall=0.67, f1=0.57
```

### 2.2 用 LLM 评估 Context Relevance

```python
class RAGEvaluator:
    """用 LLM 评估 RAG 输出的三个指标"""

    def __init__(self, llm):
        self.llm = llm

    def context_relevance(self, query: str, context: str) -> float:
        prompt = f"""评估检索到的 context 与 query 的相关性。
输出 0-1 的分数，1 表示完全相关。

Query: {query}
Context: {context}

分数："""
        score = float(self.llm.invoke(prompt).strip())
        return min(max(score, 0), 1)

    def faithfulness(self, answer: str, context: str) -> float:
        prompt = f"""评估答案是否忠于 context（无幻觉）。
输出 0-1 的分数，1 表示完全忠于。

Context: {context}
Answer: {answer}

分数："""
        score = float(self.llm.invoke(prompt).strip())
        return min(max(score, 0), 1)
```

### 2.3 构造评估数据集

```python
evaluation_set = [
    {
        "query": "Dify 支持哪些 LLM？",
        "relevant_doc_ids": ["doc_dify_llm_support", "doc_provider_list"],
        "reference_answer": "Dify 支持 OpenAI、Anthropic、本地模型等 20+ 提供商。",
    },
    {
        "query": "如何创建工作流？",
        "relevant_doc_ids": ["doc_workflow_create", "doc_dsl_spec"],
        "reference_answer": "在 dify Studio 中点击新建工作流，拖拽节点编排，保存后即可发布。",
    },
]
```

### 2.4 常见错误：只看 Recall 不看 Precision

```python
# ❌ 错误：召回率 100% 但都是垃圾文档
retrieved = all_documents  # 把所有文档都返回
# 此时 recall=1.0，但 precision≈0

# ✅ 正确：综合 P/R/F1，必要时只看 top-K
results = retrieve(query, top_k=10)
print(precision_recall_f1(set(results), relevant))
```

## 3. dify 仓库源码解读

### 3.1 评估相关的目录

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/`
**结构示意**：

```
core/rag/
├── evaluation/      # 评估相关
└── retrieval/       # 检索（被评估的对象）
```

dify 在前端提供"知识库召回测试"功能，让用户输入查询立即看召回结果，这是最简单的"在线人工评估"。

### 3.2 检索质量埋点

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/retrieval/dataset_retrieval.py`（节选）
**核心代码**（行 22-31）：

```python
from core.ops.ops_trace_manager import TraceQueueManager, TraceTask
from core.ops.entities.trace_entity import TraceTaskName

# 检索时打点，trace 包含：query、检索到的 documents、score、耗时
trace_task = TraceTask(
    trace_task_name=TraceTaskName.DATASET_RETRIEVAL,
    ...
)
TraceQueueManager.add_task(trace_task)
```

**解读**：
- 通过 trace 机制记录每次检索的详细信息
- 可用于事后分析哪些 query 检索效果差
- 是"在线评估"的基础设施

## 4. 关键要点总结

- 检索阶段核心指标：Precision / Recall / F1
- RAG 特有指标：Context Relevance / Faithfulness / Answer Relevance
- 评估需要标注数据集（query + relevant docs + 参考答案）
- 三层评估：离线 / 在线 / 人工

## 5. 练习题

### 练习 1：基础（必做）

构造一个 10 条 QA 的评估数据集，对你之前实现的 MiniRAG 计算 Precision@5、Recall@5。

### 练习 2：进阶

实现一个 RAGAS 风格的评估器，用 LLM 评判 Context Relevance。

### 练习 3：挑战（选做）

设计一个 A/B 测试：在生产环境对 10% 的流量用"向量+Rerank"，对比剩余 90% 用"纯向量"的 CTR 差异。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/retrieval/dataset_retrieval.py`
- `/Users/xu/code/github/dify/api/core/ops/`
- RAGAS 论文：https://arxiv.org/abs/2309.15217

---

**文档版本**：v1.0
**最后更新**：2026-07-13