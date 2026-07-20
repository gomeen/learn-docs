# 7.6.2 Agent 间通信协议

> 掌握多 Agent 系统中的通信机制：消息传递、共享状态、消息队列。

## 🎯 学习目标

完成本文档后，你将能够：
- 描述 Agent 间通信的常见方式
- 实现消息传递和共享内存两种模式
- 理解 dify 中 Agent 通信的特殊实现
- 选择合适的通信协议

## 📚 前置知识

- [多 Agent](./38-multi-agent.md)
- [变量系统](./30-workflow-variables.md)
- 消息队列概念（详见 [MQ 核心概念](../../_common/02-mq/01-concepts.md)）
- Python 异步（详见 [async/asyncio](../01-fundamentals/14-async-asyncio.md)）

## 1. 核心概念

### 1.1 Agent 间通信的四种模式

| 模式 | 实现 | 适用 |
|------|------|------|
| **直接调用** | Agent A 调 Agent B 的方法 | 紧密耦合 |
| **共享变量池** | 通过 VariablePool 读写 | dify 工作流 |
| **消息队列** | Redis/RabbitMQ 异步消息（详见 [Redis Pub/Sub 与 Stream](../../_common/01-redis/06-pubsub-stream.md)、[RabbitMQ](../../_common/02-mq/03-rabbitmq.md)） | 分布式 |
| **事件总线** | 发布/订阅模式 | 松耦合 |

### 1.2 dify 的通信模式

dify 通过 **VariablePool**（共享变量池）实现 Agent 间通信：

```
Agent1 输出 → VariablePool → Agent2 输入
```

每个 Agent 节点：
- 读：上游节点的输出
- 写：自己的输出到 VariablePool

### 1.3 消息格式

```python
{
    "from": "agent_1",
    "to": "agent_2",
    "type": "request" | "response" | "event",
    "content": {...},
    "timestamp": "...",
    "trace_id": "...",
}
```

## 2. 代码示例

### 2.1 基于共享内存的通信

```python
class SharedBlackboard:
    """共享黑板：所有 Agent 都能读写"""

    def __init__(self):
        self.data = {}

    def write(self, key: str, value: Any, author: str):
        self.data[key] = {"value": value, "author": author, "timestamp": time.time()}

    def read(self, key: str) -> Any | None:
        item = self.data.get(key)
        return item["value"] if item else None

    def history(self) -> list:
        return list(self.data.values())


# 多 Agent 通过共享黑板协作
board = SharedBlackboard()
agent1.write("analysis", "用户想要...")  # Agent 1 写
analysis = agent2.read("analysis")      # Agent 2 读
agent2.write("conclusion", "结论：...")  # Agent 2 写
```

### 2.2 消息队列模式

```python
import asyncio
from collections import deque


class MessageQueue:
    """简单的消息队列"""

    def __init__(self):
        self.queue = asyncio.Queue()

    async def send(self, message: dict):
        await self.queue.put(message)

    async def receive(self, timeout: float = 1.0) -> dict | None:
        try:
            return await asyncio.wait_for(self.queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None


# 使用
mq = MessageQueue()


async def producer():
    await mq.send({"from": "agent_1", "to": "agent_2", "content": "任务"})


async def consumer():
    while True:
        msg = await mq.receive()
        if msg:
            print(f"收到: {msg}")
        await asyncio.sleep(0.1)
```

### 2.3 事件总线模式

```python
class EventBus:
    """发布/订阅模式"""

    def __init__(self):
        self.subscribers: dict[str, list[callable]] = {}

    def subscribe(self, event_type: str, handler: callable):
        self.subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event_type: str, data: dict):
        for handler in self.subscribers.get(event_type, []):
            handler(data)


# Agent A 发布事件
bus = EventBus()

def on_task_complete(data):
    print(f"任务完成: {data}")

bus.subscribe("task_complete", on_task_complete)
bus.publish("task_complete", {"task_id": "t_1", "result": "ok"})
```

### 2.4 常见错误：Agent 之间循环等待

```python
# ❌ 错误：Agent A 等 Agent B，Agent B 等 Agent A → 死锁
def run(self):
    result_a = self.agent_b.run(...)  # A 等 B
    return result_a

# ✅ 正确：使用超时 + 异步消息
async def run(self):
    result = await asyncio.wait_for(
        self.agent_b.run_async(...),
        timeout=10,
    )
    return result
```

## 3. 关键要点总结

- Agent 间通信模式：直接调用、共享变量、消息队列、事件总线
- dify 用 VariablePool 作为共享变量池
- 消息格式应包含 from/to/type/content 等字段
- 警惕循环等待和死锁

---

**文档版本**：v1.0
**最后更新**：2026-07-13
