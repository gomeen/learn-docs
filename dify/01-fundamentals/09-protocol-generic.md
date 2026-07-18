# 1.1.9 `Protocol` 与 `Generic`：行为抽象与泛型

> 用 `Protocol` 实现鸭子类型的静态检查，用 `Generic` 让类支持多种类型参数。

## 🎯 学习目标

完成本文档后，你将能够：

- 理解 `Protocol`（结构化子类型）与传统继承的区别
- 定义和使用 `Generic[T]` 类
- 识别 dify 中"行为接口"的设计模式
- 能看懂 dify 中复杂的泛型签名

## 📚 前置知识

- 01-fundamentals/01-python-typing-basics.md
- 02-typeddict.md
- 面向对象基础：继承、多态

## 1. 核心概念

### 1.1 为什么需要 `Protocol`？

传统接口用抽象基类（ABC，详见 [35-abc](./35-abc.md)），强制继承关系：

```python
from abc import ABC, abstractmethod

class Drawable(ABC):
    @abstractmethod
    def draw(self) -> None: ...

class Circle(Drawable):  # 必须显式继承
    def draw(self) -> None:
        print("drawing circle")
```

但很多对象**碰巧有相同方法**，却无法或不方便继承同一基类（如内置类型、第三方类）。`Protocol` 实现**结构化子类型**（鸭子类型的静态版）：

```python
from typing import Protocol

class Drawable(Protocol):
    def draw(self) -> None: ...

# 不需要继承，只要"形状"对就行
def render(obj: Drawable) -> None:
    obj.draw()

class Circle:
    def draw(self) -> None:
        print("drawing circle")

render(Circle())  # ✅ mypy 通过
```

### 1.2 `Generic[T]`：参数化类型

让类支持类型参数，实现真正的"类型安全的多态"：

```python
from typing import Generic, TypeVar

T = TypeVar("T")

class Container(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value

    def get(self) -> T:
        return self.value

c_int: Container[int] = Container(42)
c_str: Container[str] = Container("hello")

reveal_type(c_int.get())  # int
reveal_type(c_str.get())  # str
```

### 1.3 `TypeVar` 的边界：`bound`

限制类型变量必须继承某类：

```python
from typing import TypeVar

# T 必须是 Number 的子类
T = TypeVar("T", bound="Number")

def add(a: T, b: T) -> T:
    return a + b
```

### 1.4 `Protocol` + `Generic`：可参数化的协议

```python
from typing import Generic, Protocol, TypeVar

T = TypeVar("T")

class Repository(Protocol[T]):
    """仓储接口：提供增删改查能力。"""
    def get(self, id: str) -> T | None: ...
    def save(self, entity: T) -> None: ...
    def delete(self, id: str) -> None: ...
```

## 2. 代码示例

### 2.1 基础 `Protocol`

```python
from typing import Protocol

class Closable(Protocol):
    def close(self) -> None: ...

def cleanup(resource: Closable) -> None:
    """统一的资源清理。"""
    resource.close()

# 内置文件对象天然满足
with open("/tmp/test.txt", "w") as f:
    cleanup(f)  # ✅ 文件对象有 close()

# 自定义类
class Database:
    def close(self) -> None:
        print("db closed")

cleanup(Database())  # ✅ 满足 Protocol
```

### 2.2 `Generic` 容器

```python
from typing import Generic, TypeVar

T = TypeVar("T")

class Result(Generic[T]):
    """统一的结果包装：成功带数据，失败带错误。"""
    def __init__(self, data: T | None = None, error: str | None = None) -> None:
        self.data = data
        self.error = error

    @property
    def is_success(self) -> bool:
        return self.error is None

# 类型推断
result_int: Result[int] = Result(data=42)
result_str: Result[str] = Result(error="oops")

# IDE 能正确推断 result_int.data 的类型
if result_int.is_success:
    reveal_type(result_int.data)  # int | None
```

### 2.3 常见错误：`Generic[T]` 与具体类型混用

```python
# ❌ 错误：实例化时未指定类型参数
class Box(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value

box = Box(42)  # mypy 推断为 Box[int]，但显式更好

# ✅ 推荐：显式标注
box: Box[int] = Box(42)
```

## 3. dify 仓库源码解读

### 3.1 工作流节点的抽象接口

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/nodes/base/node.py`
**核心代码**（行 1-40）：

```python
from abc import abstractmethod
from typing import Generic, TypeVar

from core.workflow.entities.base_node_data_entities import BaseNodeData
from core.workflow.entities.workflow_node_execution import (
    WorkflowNodeExecutionStatus,
)

_NodeDataT = TypeVar("_NodeDataT", bound=BaseNodeData)

class BaseNode(Generic[_NodeDataT]):
    """所有工作流节点的基类。"""

    _node_data: _NodeDataT

    def __init__(
        self,
        node_id: str,
        config: "HttpRequestNodeConfig",
        data: _NodeDataT,
        **kwargs,
    ) -> None:
        self.node_id = node_id
        self._node_data = data
```

**解读**：

- 第 13 行：`TypeVar("_NodeDataT", bound=BaseNodeData)` 限制类型变量必须是 `BaseNodeData` 子类
- 第 17 行：`Generic[_NodeDataT]` 让每个子类保留自己的节点数据类型
- **关键设计**：通过泛型基类实现"不同节点类型有不同 data 类型"，避免 `Any` 滥用

### 3.2 缓存协议的 Protocol 模式

**文件位置**：`/Users/xu/code/github/dify/api/core/cache/cache.py`
**核心代码**（行 1-30）：

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Cache(Protocol):
    """缓存抽象接口，所有缓存实现（Redis、内存）都要满足。"""

    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, ttl: int | None = None) -> None: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...

# 实现类不需要继承，只要"形状"对
class RedisCache:
    def get(self, key: str) -> str | None:
        ...
    def set(self, key: str, value: str, ttl: int | None = None) -> None:
        ...
    def delete(self, key: str) -> None:
        ...
    def exists(self, key: str) -> bool:
        ...

# isinstance 检查可以工作
assert isinstance(RedisCache(), Cache)  # ✅ runtime_checkable
```

**解读**：

- 第 3 行：`@runtime_checkable` 让 Protocol 支持 `isinstance` 检查
- **关键设计**：dify 中多种缓存实现（Redis、本地内存）通过 Protocol 抽象，运行时无需关心具体类型

## 4. 关键要点总结

- `Protocol` 定义**结构化子类型**：不需要显式继承，只要形状对就行
- `@runtime_checkable` 让 Protocol 支持 `isinstance` 检查
- `Generic[T]` 让类支持类型参数，实现类型安全的多态
- `TypeVar("T", bound=X)` 约束 T 必须是 X 的子类
- dify 中：`Protocol` 用于抽象接口，`Generic` 用于节点等可参数化的实体

## 5. 练习题

### 练习 1：基础（必做）

定义一个 `Serializable` Protocol，要求有 `to_dict() -> dict` 和 `from_dict(data: dict) -> Self` 方法，然后定义两个不继承该 Protocol 但满足形状的类，证明 `isinstance` 检查通过。

```python
from typing import Protocol, runtime_checkable, Self

@runtime_checkable
class Serializable(Protocol):

  def to_dict(self) -> dict:
    ...

  @classmethod
  def from_dict(cls, data:dict) => Self
    ...

class A:
  def __init__(self, name:str, age:int) -> None:
    self.name = name
    self.age = age

  def to_dict(self) -> dict:
    return {"name": self.name, "age":self.age}

  @classmethod
  def from_dict(cls, data:dict) => Self
    return cls(data['name'],data['age'])

assert isinstance(A('alice', 30),Serializable)
```

### 练习 2：进阶

阅读 `/Users/xu/code/github/dify/api/core/workflow/nodes/base/node.py`，画出 `BaseNode` 的继承体系（提示：搜索 `class.*Node(BaseNode)`）。

### 练习 3：挑战（选做）

为 dify 设计一个 `Storage` Protocol，包含 `read`、`write`、`delete` 方法，然后用 Generic 写一个 `StorageManager[T: Storage]` 包装类，提供 `register(name, storage)` 和 `get(name) -> T` 方法。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/workflow/nodes/base/node.py`
- `/Users/xu/code/github/dify/api/core/cache/cache.py`
- Python 官方文档：https://docs.python.org/3/library/typing.html#typing.Protocol
- PEP 544（Protocol）：https://peps.python.org/pep-0544/

---

**文档版本**：v1.0
**最后更新**：2026-07-13

