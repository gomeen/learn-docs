# 3.8 备忘录模式（Memento）

> 备忘录模式在不破坏封装性的前提下，捕获对象的内部状态，并在对象之外保存这个状态。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解备忘录模式的核心（状态快照）
- 掌握备忘录的 3 个角色
- 知道备忘录的应用场景（撤销、事务回滚）
- 在 dify/ruoyi 中识别备忘录应用

## 📚 前置知识

- 16-iterator.md
- 序列化基础

## 1. 核心概念

### 1.1 备忘录的 3 个角色

1. **Originator（原发器）**：创建备忘录，恢复状态
2. **Memento（备忘录）**：存储原发器的内部状态
3. **Caretaker（管理者）**：保存备忘录，但不能修改

### 1.2 适用场景

- 需要撤销 / 重做
- 需要事务回滚
- 需要对象状态快照
- 保存对象状态的备份

## 2. 代码示例

### 2.1 经典备忘录：撤销操作

```python
from copy import deepcopy
from dataclasses import dataclass

@dataclass
class EditorMemento:
    """备忘录：保存文本状态"""
    content: str
    cursor_pos: int


class Editor:
    """原发器"""
    def __init__(self):
        self.content = ""
        self.cursor_pos = 0

    def type(self, text: str) -> None:
        self.content = self.content[:self.cursor_pos] + text + self.content[self.cursor_pos:]
        self.cursor_pos += len(text)

    def save(self) -> EditorMemento:
        """创建备忘录"""
        return EditorMemento(deepcopy(self.content), self.cursor_pos)

    def restore(self, memento: EditorMemento) -> None:
        """恢复状态"""
        self.content = memento.content
        self.cursor_pos = memento.cursor_pos


class History:
    """管理者：保存历史快照"""
    def __init__(self):
        self._mementos: list[EditorMemento] = []

    def push(self, memento: EditorMemento) -> None:
        self._mementos.append(memento)

    def pop(self) -> EditorMemento | None:
        return self._mementos.pop() if self._mementos else None


# 使用：撤销
editor = Editor()
history = History()

editor.type("Hello")
history.push(editor.save())     # 保存快照

editor.type(" World")
print(editor.content)            # "Hello World"

editor.restore(history.pop())    # 撤销到 "Hello"
print(editor.content)            # "Hello"
```

### 2.2 数据库事务回滚（备忘录思想）

```python
class Transaction:
    """事务——数据库的备忘录"""

    def __init__(self, db):
        self.db = db
        self.snapshot = None

    def begin(self):
        """保存当前状态"""
        self.snapshot = deepcopy(self.db.state)

    def commit(self):
        """提交——删除快照"""
        self.snapshot = None

    def rollback(self):
        """回滚——恢复快照"""
        if self.snapshot:
            self.db.state = self.snapshot
```

## 3. dify 仓库源码解读

### 3.1 dify 的工作流状态快照

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/graph_engine/`
**核心代码**（行 1-30）：

```python
from copy import deepcopy

class WorkflowState:
    """工作流状态——支持快照和恢复"""

    def __init__(self):
        self.node_outputs: dict = {}      # 各节点的输出
        self.variables: dict = {}          # 变量池
        self.iteration_idx: int = 0        # 迭代索引

    def snapshot(self) -> dict:
        """创建状态快照（备忘录）"""
        return {
            "node_outputs": deepcopy(self.node_outputs),
            "variables": deepcopy(self.variables),
            "iteration_idx": self.iteration_idx,
        }

    def restore(self, snapshot: dict) -> None:
        """恢复状态"""
        self.node_outputs = deepcopy(snapshot["node_outputs"])
        self.variables = deepcopy(snapshot["variables"])
        self.iteration_idx = snapshot["iteration_idx"]


class WorkflowRunner:
    def run_node(self, node_id: str):
        """执行节点前快照（用于失败回滚）"""
        snapshot = self.state.snapshot()      # 备忘录
        try:
            result = self.execute_node(node_id)
            self.state.node_outputs[node_id] = result
        except Exception:
            self.state.restore(snapshot)       # 回滚
            raise
```

**解读**：
- 工作流执行每个节点前都创建快照
- 节点失败时恢复快照——错误隔离
- **整体设计**：用备忘录模式实现节点的错误恢复

### 3.2 dify 的版本控制（文档编辑）

**位置**：`/Users/xu/code/github/dify/api/core/rag/datasource/`
**核心代码**（简化）：

```python
class DocumentVersion:
    """文档版本——备忘录"""
    def __init__(self, content: str, version_no: int):
        self.content = content
        self.version_no = version_no

class Document:
    """原发器"""
    def __init__(self, content: str):
        self.content = content
        self.versions: list[DocumentVersion] = [DocumentVersion(content, 0)]

    def update(self, new_content: str) -> None:
        # 每次更新都保存一个版本
        self.content = new_content
        version_no = len(self.versions)
        self.versions.append(DocumentVersion(new_content, version_no))

    def rollback_to(self, version_no: int) -> None:
        """回滚到指定版本"""
        version = self.versions[version_no]
        self.content = version.content
```

**解读**：
- 文档每次更新保存一个版本（备忘录）
- 支持回滚到任意版本
- **整体设计**：用备忘录实现文档历史版本

## 4. 关键要点总结

- 备忘录 = 状态快照
- 3 角色：Originator、Memento、Caretaker
- 适用：撤销、重做、事务回滚、版本控制
- dify 工作流节点失败回滚、文档版本控制都是备忘录
- 注意深拷贝（避免共享引用）

## 5. 练习题

### 练习 1：基础
为编辑器实现支持多次撤销和重做的备忘录模式（用两个栈）。

### 练习 2：进阶
阅读 dify 的工作流执行器，分析节点的快照和恢复机制。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/graph_engine/`
- 《设计模式》第 5 章：备忘录模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13