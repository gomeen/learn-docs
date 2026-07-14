# 3.9 中介者模式（Mediator）

> 中介者模式用一个中介对象封装一系列对象交互，使各对象不需要显式地相互引用。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解中介者模式的核心（集中式通信）
- 区分中介者 vs 观察者 vs 外观
- 知道中介者的优缺点
- 在 dify/ruoyi 中识别中介者应用

## 📚 前置知识

- 15-observer.md
- 09-facade.md

## 1. 核心概念

### 1.1 中介者的核心思想

把网状的直接调用关系，改为通过**中介者**集中通信。对象之间互不感知，只与中介者通信。

### 1.2 中介者 vs 外观

| 维度 | 中介者 | 外观 |
|------|--------|------|
| 方向 | 双向通信 | 单向调用 |
| 同事类之间 | 互不知道 | 调用者不知道内部 |
| 目的 | 解耦同事类 | 简化客户端 |

### 1.3 适用场景

- 对象之间通信复杂，网状结构
- 多个对象互相依赖，难以复用
- 想集中控制交互逻辑

## 2. 代码示例

### 2.1 聊天室中介者

```python
from abc import ABC, abstractmethod
from collections import defaultdict

class Colleague(ABC):
    def __init__(self, mediator: "Mediator"):
        self.mediator = mediator

    @abstractmethod
    def send(self, msg: str) -> None: ...

    @abstractmethod
    def receive(self, msg: str) -> None: ...


class Mediator(ABC):
    @abstractmethod
    def send(self, msg: str, sender: Colleague) -> None: ...


class ChatRoom(Mediator):
    """具体中介者：聊天室"""
    def __init__(self):
        self._members: dict[str, Colleague] = {}

    def register(self, colleague: Colleague) -> None:
        self._members[colleague.name] = colleague

    def send(self, msg: str, sender: Colleague) -> None:
        # 转发给所有其他成员
        for name, member in self._members.items():
            if member is not sender:
                member.receive(f"[{sender.name}] {msg}")


class User(Colleague):
    def __init__(self, name: str, mediator: Mediator):
        super().__init__(mediator)
        self.name = name

    def send(self, msg: str) -> None:
        print(f"{self.name} 发送: {msg}")
        self.mediator.send(msg, self)  # 通过中介者

    def receive(self, msg: str) -> None:
        print(f"{self.name} 收到: {msg}")


# 使用：用户之间通过聊天室通信
room = ChatRoom()
alice = User("Alice", room)
bob = User("Bob", room)
charlie = User("Charlie", room)

room.register(alice)
room.register(bob)
room.register(charlie)

alice.send("Hello!")  # Bob 和 Charlie 收到
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的工作流图引擎（中介者）

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/graph_engine/`
**核心代码**（行 1-50）：

```python
class GraphEngine:
    """工作流图引擎——节点间通信的中介者"""

    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self.nodes: dict[str, "Node"] = {}
        self.state = WorkflowState()

    def run(self, entry_inputs: dict) -> dict:
        """驱动工作流执行——所有节点通过 engine 通信"""
        ready_nodes = self._get_ready_nodes()
        for node_id in ready_nodes:
            # 1. 收集输入（通过 engine 中介）
            inputs = self._collect_inputs(node_id)

            # 2. 执行节点
            result = self.nodes[node_id].execute(inputs)

            # 3. 写入输出（通过 engine 中介）
            self.state.node_outputs[node_id] = result
        return self.state.node_outputs

    def _collect_inputs(self, node_id: str) -> dict:
        """收集节点输入——通过 engine 查找前置节点的输出"""
        inputs = {}
        for upstream_id in self._get_upstream_nodes(node_id):
            inputs[upstream_id] = self.state.node_outputs.get(upstream_id)
        return inputs
```

**解读**：
- 节点之间不直接通信，全部通过 `GraphEngine`（中介者）
- 节点只关心自己的输入/输出，不关心其他节点
- **整体设计**：用中介者解耦节点之间的网状依赖

### 3.2 ruoyi 的 EventBus（事件中介者）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/`
**核心代码**：

```java
@Component
public class ApplicationEventMulticaster {
    /** Spring 事件中介——多播器（中介者）*/

    public void multicastEvent(ApplicationEvent event) {
        // 1. 找到所有订阅者
        Collection<ApplicationListener<?>> listeners = getApplicationListeners(event);

        // 2. 通知所有订阅者
        for (ApplicationListener<?> listener : listeners) {
            listener.onApplicationEvent(event);
        }
    }
}

// 发布者不知道订阅者——通过 EventMulticaster 中介
```

**解读**：
- Spring 的 `ApplicationEventMulticaster` 是事件中介者
- 发布者只管发布事件，订阅者只管监听
- **整体设计**：事件中介者解耦发布者和订阅者

## 4. 关键要点总结

- 中介者 = 集中式通信
- 同事类之间不直接通信
- 优点：解耦、复用、简化通信
- 缺点：中介者本身可能很复杂（上帝对象）
- dify 工作流图引擎、Spring 事件多播器都是中介者

## 5. 练习题

### 练习 1：基础
为飞机场（飞机、塔台、跑道）实现中介者模式，所有飞机通过塔台协调起降。

### 练习 2：进阶
阅读 dify 的 `GraphEngine`，分析节点间的通信如何通过中介者完成。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/graph_engine/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/`
- 《设计模式》第 5 章：中介者模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13