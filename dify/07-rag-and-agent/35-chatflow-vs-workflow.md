# 7.6.4 dify 的 Chatflow vs Workflow 对比

> 深入理解 dify 中 Chatflow 与 Workflow 的核心差异，以及各自适用场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 描述 Chatflow 与 Workflow 的核心差异
- 选择合适的应用类型
- 理解 Chatflow 中的会话管理
- 看懂 dify 中两种应用类型的代码实现

## 📚 前置知识

- 07-rag-and-agent/24-workflow-engine.md
- 07-rag-and-agent/26-workflow-variables.md

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

## 3. dify 仓库源码解读

### 3.1 应用类型定义

**文件位置**：`/Users/xu/code/github/dify/api/core/app/apps/`（目录示意）
**结构**：

```
apps/
├── advanced_chat/         # Chatflow 应用
├── chat/                  # 简单 Chat 应用
├── completion/            # Completion 应用
├── workflow/              # Workflow 应用
└── agent_chat/            # Agent Chat 应用
```

**解读**：
- `advanced_chat` 就是 Chatflow
- `workflow` 是 Workflow
- `agent_chat` 是基于 Agent 的 Chatflow
- 不同应用类型有不同的执行入口和事件流

### 3.2 Chatflow 的会话上下文

**文件位置**：`/Users/xu/code/github/dify/api/core/app/entities/app_invoke_entities.py`（节选）
**核心代码**（示意）：

```python
class AdvancedChatAppGenerateEntity:
    """Chatflow 应用的运行实体"""
    app_config: AdvancedChatAppConfig
    conversation_id: str | None = None
    message_id: str | None = None
    inputs: dict[str, Any]  # 用户输入
    query: str              # 用户消息
    user_id: str
    files: list[File]       # 用户上传的文件
```

**解读**：
- Chatflow 比 Workflow 多 `conversation_id`、`message_id`、`files` 等字段
- `query` 是用户当前轮的消息
- `inputs` 是用户自定义变量（Start 节点的输入）

### 3.3 系统变量中的对话相关字段

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/system_variables.py`（行 22-40）
**核心代码**：

```python
class SystemVariableKey(StrEnum):
    QUERY = "query"
    FILES = "files"
    CONVERSATION_ID = "conversation_id"
    USER_ID = "user_id"
    DIALOGUE_COUNT = "dialogue_count"
    APP_ID = "app_id"
    WORKFLOW_ID = "workflow_id"
    WORKFLOW_EXECUTION_ID = "workflow_run_id"
    TIMESTAMP = "timestamp"
    ...
```

**解读**：
- `CONVERSATION_ID` 是会话的唯一标识
- `DIALOGUE_COUNT` 是当前是第几轮对话
- Chatflow 的节点可以读取这些系统变量，自动获得会话上下文

### 3.4 对话历史读取节点

**文件位置**：`/Users/xu/code/github/dify/api/core/app/entities/app_invoke_entities.py`（示意）
**核心代码**（示意）：

```python
class ConversationMemoryConfig:
    """对话历史配置"""
    enabled: bool = True
    max_messages: int = 10  # 保留最近 N 条


def get_conversation_history(conversation_id: str, limit: int = 10):
    """从 DB 读取对话历史"""
    return Message.query.filter_by(
        conversation_id=conversation_id
    ).order_by(Message.created_at.desc()).limit(limit).all()
```

**解读**：
- Chatflow 的对话历史由 dify 自动管理
- 默认保留最近 N 条，可在节点配置中调整
- 通过 system variable 的 `conversation_id` 找到对应会话

## 4. 关键要点总结

- Workflow：单次执行，无状态，适合批处理
- Chatflow：多轮对话，有会话状态，适合交互
- Chatflow 比 Workflow 多 `conversation_id`、对话历史、流式输出
- dify 在应用层用不同的 AppGenerateEntity 区分

## 5. 练习题

### 练习 1：基础（必做）

设计 Workflow：用户上传文件 → 知识检索 → LLM 生成报告 → 邮件发送。

### 练习 2：进阶

设计 Chatflow：用户聊天 → 知识检索 → LLM 回答（带对话历史）→ 流式输出。

### 练习 3：挑战（选做）

思考题：什么场景下应该用 Chatflow 而不是 Workflow？列出 3 个典型场景。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/app/apps/advanced_chat/`
- `/Users/xu/code/github/dify/api/core/app/apps/workflow/`
- `/Users/xu/code/github/dify/api/core/workflow/system_variables.py`
- `/Users/xu/code/github/dify/api/core/app/entities/app_invoke_entities.py`

---

**文档版本**：v1.0
**最后更新**：2026-07-13