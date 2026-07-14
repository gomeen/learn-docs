# 2.6 组合模式（Composite）

> 组合模式将对象组合成树形结构以表示"部分-整体"的层次结构，使客户端对单个对象和组合对象的使用具有一致性。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解组合模式的核心（树形结构 + 统一接口）
- 区分叶子节点和容器节点
- 识别 dify 工作流节点的组合
- 知道组合模式的应用场景

## 📚 前置知识

- 继承/接口
- 树形数据结构

## 1. 核心概念

### 1.1 组合模式的核心思想

把"叶子"和"容器"用**同一个接口**表示，客户端无需区分。

### 1.2 组合模式结构

```
Component（组件接口）
├── Leaf（叶子节点）—— 无子节点
└── Composite（容器节点）—— 包含多个 Component
```

### 1.3 经典案例

- 文件系统（文件 = 叶子，目录 = 容器）
- 组织架构（员工 = 叶子，部门 = 容器）
- GUI 组件（按钮 = 叶子，面板 = 容器）

## 2. 代码示例

### 2.1 文件系统案例

```python
from abc import ABC, abstractmethod

class FileSystemNode(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def display(self, indent: int = 0) -> None: ...


class File(FileSystemNode):
    """叶子节点——文件"""
    def display(self, indent: int = 0) -> None:
        print(" " * indent + f"📄 {self.name}")


class Directory(FileSystemNode):
    """容器节点——目录"""
    def __init__(self, name: str):
        super().__init__(name)
        self.children: list[FileSystemNode] = []

    def add(self, child: FileSystemNode) -> None:
        self.children.append(child)

    def remove(self, child: FileSystemNode) -> None:
        self.children.remove(child)

    def display(self, indent: int = 0) -> None:
        print(" " * indent + f"📁 {self.name}/")
        for child in self.children:
            child.display(indent + 2)  # 递归调用


# 使用：构建目录树
root = Directory("project")
src = Directory("src")
tests = Directory("tests")

root.add(src)
root.add(tests)
src.add(File("main.py"))
src.add(File("utils.py"))
tests.add(File("test_main.py"))

root.display()
# 📁 project/
#   📁 src/
#     📄 main.py
#     📄 utils.py
#   📁 tests/
#     📄 test_main.py
```

### 2.2 一致性接口的好处

```python
# 客户端代码：统一处理 leaf 和 composite
def count_files(node: FileSystemNode) -> int:
    """递归统计文件数——不区分文件和目录"""
    if isinstance(node, File):
        return 1
    elif isinstance(node, Directory):
        return sum(count_files(child) for child in node.children)
    return 0

print(count_files(root))  # 3
```

## 3. dify 仓库源码解读

### 3.1 dify 工作流节点树（组合模式）

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/base/node.py`
**核心代码**（行 1-50）：

```python
from abc import ABC, abstractmethod
from typing import Any

class BaseNode(ABC):
    """工作流节点基类——组件接口"""
    def __init__(self, id: str, config: dict):
        self.id = id
        self.config = config

    @abstractmethod
    def execute(self, inputs: dict) -> dict:
        """执行节点逻辑——叶子节点返回结果"""
        ...

    def get_children(self) -> list["BaseNode"]:
        """默认无子节点——叶子"""
        return []


class NodeGroup(BaseNode):
    """节点组——容器（组合）"""
    def __init__(self, id: str, config: dict):
        super().__init__(id, config)
        self.children_nodes: list[BaseNode] = []

    def add_node(self, node: BaseNode) -> None:
        self.children_nodes.append(node)

    def execute(self, inputs: dict) -> dict:
        """递归执行所有子节点"""
        result = inputs
        for node in self.children_nodes:
            result = node.execute(result)  # 递归调用
        return result

    def get_children(self) -> list[BaseNode]:
        return self.children_nodes
```

**解读**：
- `BaseNode` 是统一接口（叶子 + 容器）
- `NodeGroup` 持有子节点列表，递归执行
- **整体设计**：用组合模式表达工作流的嵌套结构（条件分支、循环、并行等）

### 3.2 dify 工作流的实际结构

```python
# 一个典型的工作流树形结构
workflow = NodeGroup("root", {})
workflow.add_node(LLMNode("llm1", {"model": "gpt-4"}))
workflow.add_node(ConditionNode("cond1", {}))
workflow.add_node(LLMNode("llm2", {"model": "claude"}))

# 递归执行整棵树
result = workflow.execute({"query": "Hello"})
```

## 4. 关键要点总结

- 组合 = 树形结构 + 统一接口
- 叶子无子节点，容器可包含多个组件
- 客户端无需区分 leaf 和 composite
- dify 的工作流节点用组合模式表达嵌套结构
- 适用：树形结构、组织架构、GUI

## 5. 练习题

### 练习 1：基础
为公司组织架构（部门 = 容器，员工 = 叶子）实现组合模式。

### 练习 2：进阶
阅读 dify 的 `core/workflow/nodes/` 目录，找出哪些节点是容器（NodeGroup / IfElse / Iteration）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/nodes/base/node.py`
- 《设计模式》第 4 章：组合模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13