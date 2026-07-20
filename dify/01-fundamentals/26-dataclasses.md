# 1.1.20 `dataclass` 数据类

> 掌握 Python 3.7+ 的 `@dataclass`，理解 `frozen` / `slots` / `field` 等高级选项，能看懂 dify 中所有 DTO / 缓存实体的写法。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 `@dataclass` 替代手写 `__init__` / `__repr__` / `__eq__`
- 理解 `frozen=True`（不可变）和 `slots=True`（内存优化）的作用
- 使用 `field(default_factory=...)` 处理可变默认值
- 在 dify 中识别所有 `@dataclass` 用法（DTO、缓存条目、配置）

## 📚 前置知识

- Python 基础：类、类型注解
- [类型系统基础](./08-python-typing-basics.md)
- [魔术方法](./19-dunder-methods.md)

## 1. 核心概念

### 1.1 为什么需要 dataclass

写一个普通类，需要手动写 `__init__`、`__repr__`、`__eq__` 等样板代码：

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Point(x={self.x}, y={self.y})"

    def __eq__(self, other):
        return isinstance(other, Point) and self.x == other.x and self.y == other.y
```

`@dataclass` 是装饰器写法（装饰器原理见 [10-decorator](./11-decorator.md)），帮你**自动生成**这些方法：

```python
from dataclasses import dataclass

@dataclass
class Point:
    x: int
    y: int

# 自动获得 __init__、__repr__、__eq__
p = Point(1, 2)
print(p)            # Point(x=1, y=2)
print(Point(1, 2) == Point(1, 2))  # True
```

### 1.2 `frozen=True`：不可变数据类

```python
@dataclass(frozen=True)
class Vector:
    x: float
    y: float

v = Vector(1.0, 2.0)
v.x = 3.0  # FrozenInstanceError: cannot assign to field 'x'
```

**优点**：
- 不可变 → 可哈希（默认 `frozen` dataclass 自动获得 `__hash__`）
- 线程安全
- 防止意外修改

**注意**：浅冻结，深层嵌套对象仍可修改。

### 1.3 `slots=True`：内存优化（Python 3.10+）

```python
@dataclass(slots=True)
class User:
    id: int
    name: str
```

`slots=True` 等价于手动 `__slots__ = ('id', 'name')`（内存管理见 [29-memory-management](./32-memory-management.md)）：
- 节省内存（每个实例不再有 `__dict__`）
- 加快属性访问
- 不能再添加新属性

### 1.4 `field()`：处理可变默认值

Python 的可变默认值陷阱：

```python
# ❌ 经典陷阱
class A:
    items: list = []  # 所有实例共享同一个 list！
```

`@dataclass` 强制用 `default_factory`：

```python
from dataclasses import dataclass, field

@dataclass
class Order:
    items: list[str] = field(default_factory=list)  # ✅ 每个实例独立的 list
    tags: dict[str, int] = field(default_factory=dict)
```

`field()` 还可以：
- 排除字段（`field(compare=False)` 不参与 `__eq__`）
- 设置别名、metadata 等

### 1.5 继承

```python
@dataclass
class Animal:
    name: str

@dataclass
class Dog(Animal):
    breed: str
```

子类会继承父类的字段。

### 1.6 `asdict` / `astuple` 转换

```python
from dataclasses import dataclass, asdict

@dataclass
class User:
    id: int
    name: str

u = User(1, "Alice")
print(asdict(u))  # {'id': 1, 'name': 'Alice'}
```

## 2. 代码示例

### 2.1 基础 dataclass

```python
from dataclasses import dataclass

@dataclass
class Transaction:
    id: str
    amount: float
    currency: str = "USD"      # 有默认值
    timestamp: float = 0.0     # 有默认值

t = Transaction("tx-001", 99.9)
print(t)  # Transaction(id='tx-001', amount=99.9, currency='USD', timestamp=0.0)
```

### 2.2 不可变 + slots

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Config:
    api_key: str
    timeout: int

c = Config("sk-xxx", 30)
# c.api_key = "sk-yyy"  # FrozenInstanceError
# c.new_attr = 1        # AttributeError: 'Config' object has no attribute 'new_attr'
print(hash(c))  # 可以哈希
```

### 2.3 常见错误：可变默认值

```python
from dataclasses import dataclass, field

# ❌ 错误
@dataclass
class Cache:
    items: list = []  # ValueError: mutable default <class 'list'> is not allowed

# ✅ 正确
@dataclass
class Cache:
    items: list = field(default_factory=list)
```

## 3. 关键要点总结

- `@dataclass` 自动生成 `__init__` / `__repr__` / `__eq__`，省去样板代码
- `frozen=True`：不可变、可哈希、线程安全
- `slots=True`：节省内存、禁止加新属性
- `field(default_factory=...)`：可变默认值的**唯一正确**写法
- **dify 的最佳实践**：缓存条目、结果对象都用 `@dataclass(frozen=True, slots=True)`，配合 `@classmethod` 工厂方法

---

**文档版本**：v1.0
**最后更新**：2026-07-13
