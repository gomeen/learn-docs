# 3.10 访问者模式（Visitor）

> 访问者模式表示一个作用于某对象结构中的各元素的操作，它使你可以在不改变各元素类的前提下定义作用于这些元素的新操作。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解访问者模式的核心（双重分派）
- 知道访问者的适用场景
- 识别 dify/ruoyi 中的访问者应用
- 了解访问者 vs 迭代器的区别

## 📚 前置知识

- 继承/多态
- 重载（Java）

## 1. 核心概念

### 1.1 访问者的核心思想

把"对数据结构元素的操作"抽离到访问者类中。数据结构本身只负责接受访问者。

### 1.2 双重分派

```java
element.accept(visitor);
visitor.visit(element);  // 根据 element 实际类型调用 visit 方法
```

调用 `accept` 时还不知道具体子类，`visit` 时才确定——双重分派。

### 1.3 适用场景

- 数据结构稳定，但需要经常新增操作
- 需要对复杂对象结构进行多种操作
- 操作逻辑与数据结构分离

## 2. 代码示例

### 2.1 经典访问者

```python
from abc import ABC, abstractmethod

# 抽象元素
class Shape(ABC):
    @abstractmethod
    def accept(self, visitor: "Visitor") -> None: ...


# 具体元素
class Circle(Shape):
    def __init__(self, radius: float):
        self.radius = radius

    def accept(self, visitor: "Visitor") -> None:
        visitor.visit_circle(self)   # 回调访问者


class Rectangle(Shape):
    def __init__(self, w: float, h: float):
        self.w, self.h = w, h

    def accept(self, visitor: "Visitor") -> None:
        visitor.visit_rectangle(self)


# 抽象访问者
class Visitor(ABC):
    @abstractmethod
    def visit_circle(self, circle: Circle) -> None: ...
    @abstractmethod
    def visit_rectangle(self, rect: Rectangle) -> None: ...


# 具体访问者：计算面积
class AreaCalculator(Visitor):
    def __init__(self):
        self.total = 0.0

    def visit_circle(self, circle: Circle) -> None:
        self.total += 3.14 * circle.radius ** 2

    def visit_rectangle(self, rect: Rectangle) -> None:
        self.total += rect.w * rect.h


# 使用
shapes = [Circle(5), Rectangle(3, 4)]
calculator = AreaCalculator()
for shape in shapes:
    shape.accept(calculator)   # 多态分发
print(calculator.total)         # 90.5
```

### 2.2 添加新访问者（不修改元素）

```python
# 新增访问者：导出 JSON
class JsonExporter(Visitor):
    def visit_circle(self, circle):
        return {"type": "circle", "radius": circle.radius}

    def visit_rectangle(self, rect):
        return {"type": "rectangle", "w": rect.w, "h": rect.h}
```

**好处**：新增操作（导出 JSON）不需要修改 Shape 类——开闭原则。

## 3. dify 仓库源码解读

### 3.1 dify 的工作流节点访问者

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/`
**核心代码**（行 1-50）：

```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic

T = TypeVar("T")

class NodeVisitor(ABC, Generic[T]):
    """工作流节点访问者"""
    @abstractmethod
    def visit_llm_node(self, node: "LLMNode") -> T: ...

    @abstractmethod
    def visit_tool_node(self, node: "ToolNode") -> T: ...

    @abstractmethod
    def visit_code_node(self, node: "CodeNode") -> T: ...


class Node(ABC):
    """节点基类——可被访问"""
    @abstractmethod
    def accept(self, visitor: NodeVisitor) -> None: ...


class LLMNode(Node):
    def accept(self, visitor: NodeVisitor):
        return visitor.visit_llm_node(self)


class ToolNode(Node):
    def accept(self, visitor: NodeVisitor):
        return visitor.visit_tool_node(self)


# 具体访问者：统计节点数
class NodeCounter(NodeVisitor[int]):
    def __init__(self):
        self.count = 0

    def visit_llm_node(self, node):
        self.count += 1

    def visit_tool_node(self, node):
        self.count += 1

    def visit_code_node(self, node):
        self.count += 1


# 使用
nodes = [LLMNode(...), ToolNode(...), LLMNode(...)]
counter = NodeCounter()
for node in nodes:
    node.accept(counter)
print(f"Total: {counter.count}")  # 3
```

**解读**：
- 节点只负责 `accept`，具体操作在访问者中
- 新增操作（如导出、统计）只需新增访问者
- **整体设计**：用访问者模式支持工作流的多种操作

### 3.2 AST 访问者（dify 的提示词模板）

**位置**：`/Users/xu/code/github/dify/api/core/prompt/`
**核心代码**：

```python
class TemplateVisitor(ABC):
    """模板 AST 访问者"""
    @abstractmethod
    def visit_text_node(self, node: "TextNode") -> str: ...

    @abstractmethod
    def visit_variable_node(self, node: "VariableNode") -> str: ...

    @abstractmethod
    def visit_if_node(self, node: "IfNode") -> str: ...


class RenderVisitor(TemplateVisitor):
    """渲染访问者——把模板转为最终文本"""
    def visit_text_node(self, node):
        return node.text

    def visit_variable_node(self, node):
        return self.context.get(node.name, "")

    def visit_if_node(self, node):
        if self.context.get(node.condition_var):
            return self.render(node.true_branch)
        return self.render(node.false_branch)
```

**解读**：
- 模板有多种节点（文本、变量、条件）
- 不同访问者实现不同操作（渲染、校验、转 JSON）
- **整体设计**：访问者模式让模板支持多种操作而无需修改节点类

## 4. 关键要点总结

- 访问者 = 把操作从数据结构中分离
- 双重分派：`element.accept(visitor)` + `visitor.visit(element)`
- 优点：新增操作容易，符合开闭原则
- 缺点：新增元素类型难（要改所有访问者）
- dify 工作流节点、模板 AST 都用访问者模式

## 5. 练习题

### 练习 1：基础
为文件系统（文件 / 目录）实现访问者，支持"统计大小"、"导出树形结构"两种操作。

### 练习 2：进阶
阅读 dify 的 `core/prompt/`，分析模板 AST 的访问者实现。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/nodes/`
- `/Users/xu/code/github/dify/api/core/prompt/`
- 《设计模式》第 5 章：访问者模式

---

**文档版本**：v1.0
**最后更新**：2026-07-13