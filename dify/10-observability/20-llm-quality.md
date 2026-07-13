# 10.5.3 响应质量评估：人工反馈 / 自动评估

> LLM 应用上线后，如何评估响应质量？人工反馈 + 自动评估是两大核心手段。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 LLM 响应质量的多维度评估
- 掌握人工反馈（thumbs up/down）的实现
- 掌握自动评估（BLEU / 困惑度 / LLM-as-a-Judge）的方法
- 能在 dify 中集成质量评估

## 📚 前置知识

- 10.5.1 LLM 调用追踪（`18-llm-tracing.md`）
- LLM 基本概念
- dify 应用结构（消息、对话、应用）

## 1. 核心概念

### 1.1 LLM 响应质量的维度

| 维度 | 含义 | 衡量方法 |
|------|------|----------|
| **准确性** | 是否回答正确 | 人工评分 / LLM-as-a-Judge |
| **相关性** | 是否切题 | 余弦相似度 / LLM 评分 |
| **流畅性** | 语言是否自然 | 困惑度 |
| **一致性** | 多次调用结果是否一致 | 标准差 |
| **安全性** | 是否包含有害内容 | 内容审核 API |
| **有用性** | 是否解决了用户问题 | 用户反馈 |

### 1.2 人工反馈（Human Feedback）

最简单的质量评估：让用户给 thumbs up/down。

**dify 中的实现**：
```python
class MessageFeedback:
    rating: str  # "like" / "dislike"
    content: str  # 反馈说明（可选）
```

**优势**：
- 真实用户反馈，最有说服力
- 实现简单

**劣势**：
- 反馈率低（通常 < 5%）
- 用户主观性强

### 1.3 自动评估方法

#### 方法 1：LLM-as-a-Judge

用一个 LLM（通常是 GPT-4）评估另一个 LLM 的输出：

```python
def llm_judge(question, answer, criteria):
    prompt = f"""
    评估以下回答的质量：

    问题：{question}
    回答：{answer}
    评估标准：{criteria}

    请给出 1-10 分，并说明理由。
    """
    return gpt4_client.complete(prompt)
```

**优势**：
- 接近人类评分
- 可解释（LLM 给出理由）

**劣势**：
- 成本高（每次评估都要调用 LLM）
- LLM 自身有偏差

#### 方法 2：参考对比（BLEU / ROUGE）

把 LLM 输出与"标准答案"对比，常用于翻译、摘要：

```python
from nltk.translate.bleu_score import sentence_bleu

reference = ["the cat is on the mat"]
candidate = "the cat is on mat"
score = sentence_bleu(reference, candidate.split())
```

**优势**：
- 计算快、成本低
- 有标准的 metric

**劣势**：
- 对开放式回答不适用
- 表面相似 ≠ 语义相似

#### 方法 3：困惑度（Perplexity）

衡量 LLM 对自己输出的"惊讶程度"——越低说明质量越好。

```python
perplexity = model.compute_perplexity(text)
```

**适用**：评估模型在特定数据集上的表现，不适合评估单次输出。

### 1.4 dify 的反馈机制

dify 支持两类反馈：
1. **消息反馈**：用户对单条消息点赞/点踩
2. **工作流反馈**：对整个工作流执行的反馈

反馈会写入数据库，并可作为数据集用于后续微调或评估。

## 2. 代码示例

### 2.1 dify 中的消息反馈（伪代码）

```python
from models.model import MessageFeedback


@app.post("/messages/{message_id}/feedbacks")
def submit_feedback(message_id: str, rating: str, content: str = ""):
    """用户对消息提交反馈"""
    feedback = MessageFeedback(
        message_id=message_id,
        rating=rating,  # "like" / "dislike"
        content=content,
        user_id=current_user.id,
    )
    db.session.add(feedback)
    db.session.commit()
    return {"success": True}
```

### 2.2 LLM-as-a-Judge 评估示例

```python
import openai


def evaluate_response_quality(
    question: str,
    answer: str,
    judge_model: str = "gpt-4",
) -> dict:
    """用 GPT-4 评估回答质量"""

    prompt = f"""你是一个专业的 LLM 评估专家。请评估以下回答的质量。

问题：{question}

回答：{answer}

请从以下维度评分（1-10）：
1. 准确性：回答是否正确
2. 相关性：回答是否切题
3. 流畅性：语言是否自然
4. 完整性：是否回答了所有问题

请用 JSON 格式输出：{{"accuracy": 8, "relevance": 9, "fluency": 9, "completeness": 7, "overall": 8, "reason": "..."}}"""

    response = openai.chat.completions.create(
        model=judge_model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    import json
    return json.loads(response.choices[0].message.content)


# 示例
result = evaluate_response_quality(
    question="Python 的 GIL 是什么？",
    answer="GIL 是全局解释器锁，保证同一时刻只有一个线程执行 Python 字节码。"
)
print(result)
# {"accuracy": 9, "relevance": 10, "fluency": 10, "completeness": 9, ...}
```

### 2.3 内容安全审核

```python
import openai


def content_moderation(text: str) -> dict:
    """用 OpenAI Moderation API 检查内容安全"""
    response = openai.moderations.create(input=text)
    result = response.results[0]

    return {
        "flagged": result.flagged,
        "categories": {
            "hate": result.categories.hate,
            "violence": result.categories.violence,
            "self_harm": result.categories.self_harm,
            "sexual": result.categories.sexual,
        },
        "scores": {
            "hate": result.category_scores.hate,
            "violence": result.category_scores.violence,
        }
    }
```

### 2.4 批量评估 Pipeline

```python
import csv
from typing import Callable


def batch_evaluate(
    test_cases: list[dict],  # [{"question": ..., "expected": ..., "actual": ...}]
    evaluator: Callable,
    output_file: str = "eval_results.csv",
):
    """批量评估 LLM 输出"""
    results = []
    for case in test_cases:
        score = evaluator(case["question"], case["actual"], case.get("expected"))
        results.append({**case, **score})

    # 写入 CSV
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    # 计算平均分
    avg_overall = sum(r["overall"] for r in results) / len(results)
    print(f"平均分：{avg_overall:.2f}")
```

## 3. dify 仓库源码解读

### 3.1 dify 的反馈数据模型（推测）

> dify 的反馈机制主要在数据库层实现，dify 仓库源码中暂未直接看到完整的反馈模型代码，但根据 ORM 模型推测：

```python
# 推测的 dify 反馈模型（api/models/model.py）
class MessageFeedback:
    id: str
    message_id: str
    rating: str  # "like" / "dislike"
    content: str | None
    from_account_id: str | None
    from_end_user_id: str | None
    created_at: datetime
```

### 3.2 dify 中的消息查询（关联反馈）

**文件位置**：`/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
**核心代码**（行 1406-1421）：

```python
message_id: str | None = None
conversation_id = node_data.get("conversation_id")
workflow_execution_id = node_data.get("workflow_execution_id")
if conversation_id and workflow_execution_id and not dumped_parent_trace_context:
    with Session(db.engine) as session:
        msg_id = session.scalar(
            select(Message.id).where(
                Message.conversation_id == conversation_id,
                Message.workflow_run_id == workflow_execution_id,
            )
        )
        if msg_id:
            message_id = str(msg_id)
            metadata["message_id"] = message_id
    if conversation_id:
        metadata["conversation_id"] = conversation_id
```

**解读**：
- 第 5-14 行：从 conversation_id 和 workflow_run_id 反查 message_id
- 第 16 行：把 conversation_id 也加入 metadata
- **业务价值**：通过 message_id 可以关联到该消息的所有反馈

### 3.3 dify 的工作流 trace 包含完整上下文

**文件位置**：`/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
**核心代码**（行 861-911）：

```python
metadata: dict[str, Any] = {
    "workflow_id": workflow_id,
    "conversation_id": conversation_id,
    "workflow_run_id": workflow_run_id,
    "tenant_id": tenant_id,
    "elapsed_time": workflow_run_elapsed_time,
    "status": workflow_run_status,
    "version": workflow_run_version,
    "total_tokens": total_tokens,
    "file_list": file_list,
    "triggered_from": workflow_run.triggered_from,
    "user_id": user_id,
    "app_id": workflow_run.app_id,
    "app_name": app_name,
    "workspace_name": workspace_name,
}

# ...

workflow_trace_info = WorkflowTraceInfo(
    trace_id=self.trace_id,
    workflow_data=workflow_run.to_dict(),
    # ...
    message_id=message_id,
    # ...
)
```

**解读**：
- 第 1-15 行：metadata 包含完整的执行上下文
- 第 25 行：把 message_id 也加到 trace，方便关联反馈
- **业务价值**：trace 后端（如 Langfuse）可以通过 message_id 关联到用户反馈

## 4. 关键要点总结

- LLM 质量评估：准确性 / 相关性 / 流畅性 / 安全性
- 人工反馈（thumbs up/down）：真实但反馈率低
- 自动评估方法：**LLM-as-a-Judge** / BLEU / 困惑度
- dify 通过 `MessageFeedback` 模型记录用户反馈
- trace 中包含 message_id，可关联到反馈数据
- 批量评估 + 自动报告是持续改进的基础

## 5. 练习题

### 练习 1：基础（必做）

设计一个 dify 应用的评估数据集：包含 10 个测试用例（问题 + 期望答案），用 LLM-as-a-Judge 评估每次响应质量，并输出平均分。

### 练习 2：进阶

阅读 `api/core/ops/ops_trace_manager.py` 的 `message_trace` 方法（行 914-1000），解释 dify 为什么在 trace 中既记录 `message_id` 又记录 `conversation_id`？两者关系是什么？

### 练习 3：挑战（选做）

实现一个 `QualityDashboard`：用 dify 的反馈数据 + 自动评估，实时展示 LLM 应用的：
1. 反馈率（点赞 + 点踩 / 总请求）
2. 好评率（点赞 / 总反馈）
3. 自动评估平均分
4. Top 5 差评案例

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/ops/ops_trace_manager.py`
- LLM-as-a-Judge 论文：https://arxiv.org/abs/2306.05685
- BLEU 论文：https://aclanthology.org/P02-1040.pdf
- OpenAI Evals 框架：https://github.com/openai/evals
- Langfuse 评估功能：https://langfuse.com/docs/scores

---

**文档版本**：v1.0
**最后更新**：2026-07-13