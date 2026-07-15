# 7.4.4 Reflection 自我反思

> 理解 Reflection 模式：让 Agent 自我审视和修正，提升输出质量。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Reflection 的核心思想：自我评估 + 修正
- 写出 Reflection 的 Prompt 模板
- 实现 Self-RAG、Reflexion 等具体方法
- 了解 dify 中可能的实现位置

## 📚 前置知识

- [ReAct 深入](./19-react-deep-dive.md)
- [Plan-and-Execute](./20-plan-execute.md)

## 1. 核心概念

### 1.1 什么是 Reflection？

Reflection 是一种让 Agent **检查自己的输出并修正**的模式：

```
生成初稿 → 自我评估 → 不满意则重写 → 输出
```

### 1.2 Reflection 的三种形式

| 方法 | 思路 | 复杂度 |
|------|------|--------|
| **Self-Evaluation** | LLM 评估自己的输出 | 低 |
| **Reflexion** | 多次试错 + 反思失败原因 | 中 |
| **Self-RAG** | 检索阶段也自我反思是否需要 | 高 |

### 1.3 Self-RAG 的核心

Self-RAG 在检索阶段增加一个"是否需要检索"的判断：

```
用户问题 → 判断是否需要检索？
  → 不需要 → 直接回答
  → 需要 → 检索 → 评估检索质量 → 检索不好则改写查询再检索
```

## 2. 代码示例

### 2.1 简单 Self-Evaluation

```python
SELF_EVAL_PROMPT = """评估以下回答的质量：
1. 是否完整回答了用户问题？
2. 是否存在事实错误？
3. 是否过于冗长？

原始问题：{query}
回答：{answer}

如果存在严重问题（事实错误、未回答问题），输出"需要改进"+ 具体建议。
否则输出"通过"。"""


def self_evaluate(query: str, answer: str, llm) -> tuple[bool, str]:
    prompt = SELF_EVAL_PROMPT.format(query=query, answer=answer)
    response = llm.invoke(prompt)
    needs_revision = "需要改进" in response
    return not needs_revision, response
```

### 2.2 Reflexion：失败反思

```python
REFLEXION_PROMPT = """上一次的尝试失败了，分析原因并提出改进方案。

任务：{task}
上一次尝试：{last_attempt}
失败原因：{error}

请回答：
1. 失败的根本原因是什么？
2. 下一次应该怎么调整？

反思："""


def reflexion(task: str, last_attempt: str, error: str, llm, max_trials=3):
    reflection = ""
    for i in range(max_trials):
        # 1. 基于反思生成新尝试
        new_prompt = f"{reflection}\n\n任务：{task}\n请基于以上反思重新尝试："
        attempt = llm.invoke(new_prompt)

        # 2. 评估新尝试
        success, eval_msg = self_evaluate(task, attempt, llm)
        if success:
            return attempt

        # 3. 生成新反思
        reflection = llm.invoke(
            REFLEXION_PROMPT.format(task=task, last_attempt=attempt, error=eval_msg)
        )
    return attempt
```

### 2.3 Self-RAG：判断是否需要检索

```python
class SelfRAG:
    """Self-RAG：让 LLM 自己判断是否需要检索"""

    DECIDE_PROMPT = """判断以下问题是否需要检索外部知识。
仅当问题涉及具体事实、专业知识或最新信息时，回答"是"。
如果是通用闲聊、常识性问题，回答"否"。

问题：{query}

是否需要检索（是/否）："""

    def __init__(self, llm, retriever):
        self.llm = llm
        self.retriever = retriever

    def ask(self, query: str) -> str:
        # 1. 判断是否需要检索
        decision = self.llm.invoke(self.DECIDE_PROMPT.format(query=query))

        if "是" in decision:
            # 2. 检索
            docs = self.retriever.search(query, top_k=5)
            # 3. 评估检索质量
            quality = self._eval_retrieval(query, docs)
            if quality < 0.5:
                # 检索质量差，改写 query 再检索
                new_query = self.llm.invoke(f"改写以下查询以更好检索：{query}")
                docs = self.retriever.search(new_query, top_k=5)
            context = "\n".join(docs)
            return self.llm.invoke(f"基于：{context}\n回答：{query}")
        else:
            return self.llm.invoke(query)
```

### 2.4 常见错误：Reflection 永远说不满意

```python
# ❌ 错误：Reflection 标准太高，陷入无限循环
while not perfect(answer):  # 完美是达不到的
    answer = reflect(answer)

# ✅ 正确：限制最大次数 + 接受"足够好"
for i in range(max_reflection):
    answer = reflect(answer)
    if good_enough(answer):
        break
```

## 3. dify 仓库源码解读

### 3.1 Agent 输出解析中的反思

**文件位置**：`/Users/xu/code/github/dify/api/core/agent/output_parser/`（节选）
**核心代码**（示意）：

```python
class AgentOutputParser:
    """解析 Agent 输出，如果解析失败可让 LLM 重新生成"""

    def parse(self, text: str, llm, retry: int = 0) -> dict:
        try:
            return self._parse(text)
        except ParseError:
            if retry < self.max_retry:
                # 让 LLM 重新生成，附带错误信息
                retry_prompt = f"上一次的输出格式有误：\n{text}\n请按正确格式重新生成。"
                new_text = llm.invoke(retry_prompt)
                return self.parse(new_text, llm, retry + 1)
            raise
```

**解读**：
- dify 的 Agent 解析失败时会让 LLM 重新生成
- 这是 "Reflection" 的轻量实现
- 限制最大重试次数避免死循环

## 4. 关键要点总结

- Reflection = 自我评估 + 修正
- 三种形式：Self-Eval（轻）、Reflexion（中）、Self-RAG（重）
- 必须限制最大重试次数，避免死循环
- dify 在 Agent 输出解析失败时使用类似的"重试反思"机制

## 5. 练习题

### 练习 1：基础（必做）

实现一个 Self-Evaluation 函数：让 LLM 评估自己的回答是否合格，不合格则让 LLM 重写。

### 练习 2：进阶

实现 Reflexion：让 Agent 失败 3 次后能反思失败原因，调整策略。

### 练习 3：挑战（选做）

实现 Self-RAG：让 LLM 先判断"是否需要检索"，再决定走哪条路径。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/agent/output_parser/`
- `/Users/xu/code/github/dify/api/core/agent/cot_agent_runner.py`
- Reflexion 论文：https://arxiv.org/abs/2303.11381
- Self-RAG 论文：https://arxiv.org/abs/2310.11511

---

**文档版本**：v1.0
**最后更新**：2026-07-13