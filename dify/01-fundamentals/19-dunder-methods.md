# 1.1.16 魔术方法：`__init__` / `__repr__` / `__str__` / `__eq__`

> 掌握 Python "dunder methods"（双下划线方法）的使用，让自定义类与 Python 内置协议无缝集成。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解魔术方法在 Python 协议中的角色
- 实现 `__init__` / `__repr__` / `__str__` / `__eq__` / `__hash__`
- 理解对象相等性（==）与同一性（is）的区别
- 在 dify 中识别这些方法的应用

## 📚 前置知识

- Python 基础：类、对象、`self`
- 面向对象基础：封装、继承

## 1. 核心概念

### 1.1 什么是魔术方法？

魔术方法（dunder = double underscore）是 Python 内置的**协议接口**，实现它们可以让自定义类与 Python 内置操作（如 `print()`、`==`、`len()`）无缝协作。

| 魔术方法 | 触发场景 | 示例 |
|---|---|---|
| `__init__` | 构造对象 | `obj = MyClass()` |
| `__repr__` | 开发者视角的字符串 | `>>> obj`（REPL） |
| `__str__` | 用户视角的字符串 | `print(obj)` |
| `__eq__` | 等于比较 | `obj1 == obj2` |
| `__hash__` | 哈希计算 | `hash(obj)` / 放入 set |
| `__len__` | 长度 | `len(obj)` |
| `__getitem__` | 索引 | `obj[0]` |
| `__iter__` | 迭代 | `for x in obj` |
| `__enter__` / `__exit__` | with 块（详见 [11-context-manager](./12-context-manager.md)） | `with obj:` |
| `__call__` | 调用 | `obj()` |

### 1.2 `__init__`：构造函数

```python
class User:
    def __init__(self, name: str, email: str) -> None:
        self.name = name
        self.email = email
```

### 1.3 `__repr__` vs `__str__`

```python
class User:
    def __init__(self, name: str, email: str) -> None:
        self.name = name
        self.email = email

    def __repr__(self) -> str:
        # 开发者视角：尽可能完整、可重建
        return f"User(name={self.name!r}, email={self.email!r})"

    def __str__(self) -> str:
        # 用户视角：友好、可读
        return f"{self.name} <{self.email}>"

u = User("Alice", "alice@example.com")
print(repr(u))  # User(name='Alice', email='alice@example.com')
print(str(u))   # Alice <alice@example.com>
print(u)        # 默认调用 __str__
```

**最佳实践**：至少实现 `__repr__`，让它返回 `ClassName(field=value, ...)` 格式。

### 1.4 `__eq__` 与 `__hash__`：对象相等

**关键规则**：
- 实现 `__eq__` 后，Python **自动把 `__hash__` 设为 None**，导致对象不可哈希
- 如果想让对象可哈希（放入 `set` / 作为 `dict` key），必须**同时实现 `__hash__`**

```python
class Point:
    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point):
            return NotImplemented
        return self.x == other.x and self.y == other.y

    def __hash__(self) -> int:
        return hash((self.x, self.y))

p1 = Point(1, 2)
p2 = Point(1, 2)
print(p1 == p2)  # True
print(hash(p1) == hash(p2))  # True
print({p1, p2})  # {Point(1, 2)}（去重）
```

### 1.5 `==`（相等） vs `is`（同一）

```python
a = [1, 2, 3]
b = [1, 2, 3]
a == b  # True（值相等）
a is b  # False（不同的对象）

c = a
a is c  # True（同一个对象）
```

- `==` 调用 `__eq__`
- `is` 比较对象身份（内存地址），不调用任何方法

## 2. 代码示例

### 2.1 完整的领域模型类

```python
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class WorkflowRun:
    """工作流运行记录。"""
    id: str
    workflow_id: str
    status: str
    inputs: dict
    outputs: dict | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def __repr__(self) -> str:
        return (
            f"WorkflowRun(id={self.id!r}, status={self.status!r}, "
            f"workflow_id={self.workflow_id!r})"
        )

    def __str__(self) -> str:
        return f"Run {self.id}: {self.status}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WorkflowRun):
            return NotImplemented
        return self.id == other.id  # 用业务主键判断相等

    def __hash__(self) -> int:
        return hash(self.id)

run = WorkflowRun(
    id="run-001",
    workflow_id="wf-001",
    status="running",
    inputs={"query": "hello"},
)
print(repr(run))
print(str(run))
```

### 2.2 常见错误：只实现 `__eq__` 忘了 `__hash__`

```python
# ❌ 错误：实现 __eq__ 后对象不可哈希
class BadPoint:
    def __init__(self, x, y):
        self.x, self.y = x, y
    def __eq__(self, other):
        return isinstance(other, BadPoint) and (self.x, self.y) == (other.x, other.y)

p = BadPoint(1, 2)
{p}  # TypeError: unhashable type: 'BadPoint'

# ✅ 正确：同时实现 __hash__
class GoodPoint:
    def __init__(self, x, y):
        self.x, self.y = x, y
    def __eq__(self, other):
        return isinstance(other, GoodPoint) and (self.x, self.y) == (other.x, other.y)
    def __hash__(self):
        return hash((self.x, self.y))

p = GoodPoint(1, 2)
{p}  # {GoodPoint(...)}
```

### 2.3 实现 `__lt__` 让对象可排序

```python
from functools import total_ordering

@total_ordering
class Version:
    def __init__(self, major: int, minor: int, patch: int) -> None:
        self.major, self.minor, self.patch = major, minor, patch

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)

    def __lt__(self, other: "Version") -> bool:
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __repr__(self) -> str:
        return f"Version({self.major}.{self.minor}.{self.patch})"

versions = [Version(1, 0, 0), Version(2, 1, 0), Version(1, 5, 2)]
print(sorted(versions))  # [Version(1.0.0), Version(1.5.2), Version(2.1.0)]
```

`@total_ordering` 自动从 `__eq__` + `__lt__` 推导出 `<=`、`>`、`>=`。

## 3. 关键要点总结

- `__repr__`：开发者视角，返回 `Class(field=value)` 格式，**建议始终实现**
- `__str__`：用户视角，可读性强；不实现则 fallback 到 `__repr__`
- 实现 `__eq__` 后必须**同时实现 `__hash__`**，否则对象不可哈希
- `==` 调用 `__eq__`，`is` 比较对象身份（内存地址）
- `@total_ordering` 装饰器自动补齐比较运算符
- dify 中 SQLAlchemy 模型用 `<...>` 标识 ORM 对象

---

**文档版本**：v1.0
**最后更新**：2026-07-13
