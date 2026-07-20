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

传统接口用抽象基类（ABC，详见 [23-abc](./25-abc.md)），强制继承关系：

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

## 3. 关键要点总结

- `Protocol` 定义**结构化子类型**：不需要显式继承，只要形状对就行
- `@runtime_checkable` 让 Protocol 支持 `isinstance` 检查
- `Generic[T]` 让类支持类型参数，实现类型安全的多态
- `TypeVar("T", bound=X)` 约束 T 必须是 X 的子类
- dify 中：`Protocol` 用于抽象接口，`Generic` 用于节点等可参数化的实体

---

**文档版本**：v1.0
**最后更新**：2026-07-13
