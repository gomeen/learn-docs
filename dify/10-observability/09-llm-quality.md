# 10.5.3 响应质量评估：人工反馈 / 自动评估

> LLM 应用上线后，如何评估响应质量？人工反馈 + 自动评估是两大核心手段。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 LLM 响应质量的多维度评估
- 掌握人工反馈（thumbs up/down）的实现
- 掌握自动评估（BLEU / 困惑度 / LLM-as-a-Judge）的方法
- 能在 dify 中集成质量评估

## 📚 前置知识

- 10.5.1 LLM 调用追踪（`07-llm-tracing.md`）
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

## 3. 关键要点总结

- LLM 质量评估：准确性 / 相关性 / 流畅性 / 安全性
- 人工反馈（thumbs up/down）：真实但反馈率低
- 自动评估方法：**LLM-as-a-Judge** / BLEU / 困惑度
- dify 通过 `MessageFeedback` 模型记录用户反馈
- trace 中包含 message_id，可关联到反馈数据
- 批量评估 + 自动报告是持续改进的基础

---

**文档版本**：v1.0
**最后更新**：2026-07-13
