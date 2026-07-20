# 7.6.4 dify 的 Chatflow vs Workflow 对比

> 深入理解 dify 中 Chatflow 与 Workflow 的核心差异，以及各自适用场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 描述 Chatflow 与 Workflow 的核心差异
- 选择合适的应用类型
- 理解 Chatflow 中的会话管理
- 看懂 dify 中两种应用类型的代码实现

## 📚 前置知识

- [Workflow Engine](./28-workflow-engine.md)
- [变量系统](./30-workflow-variables.md)
- 流式输出（详见 [SSE](../../_common/14-api-protocols/04-sse.md)、[流式输出](../06-llm-and-ai/32-streaming-sse.md)）

## 1. 核心概念

### 1.1 Workflow vs Chatflow

| 维度 | Workflow | Chatflow |
|------|----------|----------|
| 输入 | 单次（一次输入一次性处理） | 多轮（持续对话） |
| 输出 | 单次返回 | 流式返回 |
| 会话状态 | 无 | 有（conversation_id） |
| 触发方式 | API/手动 | 用户消息 |
| 典型场景 | 数据处理、定时任务 | 智能客服、对话机器人 |

### 1.2 Chatflow 的特殊节点

Chatflow 在 Workflow 基础上增加：
- **对话历史**节点：读取多轮对话
- **会话变量**：跨轮次保持
- **Answer 节点**：流式输出给用户

### 1.3 Chatflow 的工作原理

```
用户消息 1 → Chatflow 节点 1 → 节点 2 → Answer 节点 → 用户
                                                          ↓
用户消息 2 → Chatflow 节点 1 → 节点 2 → Answer 节点 → 用户
（同样的流程，但能访问对话历史）
```

## 2. 代码示例

### 2.1 Workflow 应用骨架

```python
class WorkflowApp:
    """单次执行的工作流应用"""

    def __init__(self, workflow_def):
        self.workflow = workflow_def

    def run(self, inputs: dict) -> dict:
        """执行一次，返回结果"""
        result = self.workflow.run(inputs)
        return {"answer": result.get("text")}


# 使用
app = WorkflowApp(workflow_def)
output = app.run({"query": "Dify 是什么？"})  # 单次调用
```

### 2.2 Chatflow 应用骨架

```python
class ChatflowApp:
    """多轮对话的 Chatflow 应用"""

    def __init__(self, chatflow_def):
        self.chatflow = chatflow_def

    def chat(self, user_message: str, conversation_id: str, user_id: str):
        """处理一轮对话"""

        # 1. 加载会话历史（从 DB）
        history = self._load_history(conversation_id)

        # 2. 注入到 variable pool
        inputs = {
            "query": user_message,
            "conversation_id": conversation_id,
            "history": history,
        }

        # 3. 执行 chatflow（流式）
        for event in self.chatflow.run_stream(inputs):
            if event.type == "message":
                yield event.content  # 流式返回给用户

        # 4. 保存本轮对话到历史
        self._save_message(conversation_id, user_message, ...)
```

### 2.3 Chatflow 中的会话历史管理

```python
class ConversationMemory:
    """对话历史管理"""

    def __init__(self, db_session):
        self.db = db_session

    def load(self, conversation_id: str, limit: int = 10) -> list[dict]:
        """加载最近 N 条消息"""
        messages = self.db.query(Message).filter_by(
            conversation_id=conversation_id
        ).order_by(Message.created_at.desc()).limit(limit).all()
        return [{"role": m.role, "content": m.content} for m in reversed(messages)]

    def save(self, conversation_id: str, role: str, content: str):
        """保存一条消息"""
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=datetime.now(),
        )
        self.db.add(msg)
        self.db.commit()
```

### 2.4 常见错误：Chatflow 当 Workflow 用

```python
# ❌ 错误：Chatflow 处理单次任务，浪费了会话能力
chatflow_app.chat("处理这 100 个文档", conversation_id="none")

# ✅ 正确：根据场景选择应用类型
# 一次性任务 → Workflow
# 多轮对话 → Chatflow
```

## 3. 关键要点总结

- Workflow：单次执行，无状态，适合批处理
- Chatflow：多轮对话，有会话状态，适合交互
- Chatflow 比 Workflow 多 `conversation_id`、对话历史、流式输出
- dify 在应用层用不同的 AppGenerateEntity 区分

---

**文档版本**：v1.0
**最后更新**：2026-07-13
