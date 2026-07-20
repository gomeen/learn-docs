# 1.1.22 `functools` 模块：`lru_cache` / `partial` / `reduce` / `wraps`

> 掌握 `functools` 的核心工具，能用缓存、偏函数、函数组合等高级技巧简化代码。

## 🎯 学习目标

完成本文档后，你将能够：
- 用 `@lru_cache` 缓存函数结果，避免重复计算
- 用 `functools.partial` 固定部分参数，构造新函数
- 用 `functools.reduce` 做累积归并
- 在 dify 中识别 `lru_cache`、`wraps`、`partial` 的应用

## 📚 前置知识

- Python 基础：函数、装饰器
- [装饰器](./11-decorator.md)
- [描述符](./24-descriptor.md)

## 1. 核心概念

### 1.1 `@lru_cache`：最近最少使用缓存

`lru_cache(maxsize=128)` 装饰函数，自动缓存最近的 `maxsize` 个结果（按参数哈希）。

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def fib(n):
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

print(fib(100))  # 354224848179261915075（瞬间返回，没缓存要几小时）
```

**注意**：
- 参数必须是**可哈希的**（list / dict 不能直接作为参数）
- 默认 `maxsize=128`，设为 `None` 时无限制

### 1.2 `functools.partial`：偏函数

固定函数的一部分参数，返回新函数：

```python
from functools import partial

def power(base, exp):
    return base ** exp

square = partial(power, exp=2)
cube = partial(power, exp=3)

print(square(5))  # 25
print(cube(5))    # 125
```

**典型应用**：把「通用函数」特化为「专用函数」。

### 1.3 `functools.reduce`：累积归并

`reduce(func, iterable)` 把 `iterable` 中的元素累积地喂给 `func`：

```python
from functools import reduce

nums = [1, 2, 3, 4, 5]
sum_all = reduce(lambda acc, x: acc + x, nums, 0)  # 15
product = reduce(lambda acc, x: acc * x, nums, 1)  # 120
```

`reduce(f, [a, b, c, d], init)` 等价于 `f(f(f(f(init, a), b), c), d)`。

### 1.4 `@wraps`：保留原函数元信息

装饰器会覆盖原函数的 `__name__` / `__doc__`，用 `@wraps` 保留（装饰器完整原理见 [10-decorator](./11-decorator.md)；本文聚焦 `functools` 工具箱）：

```python
from functools import wraps

def my_decorator(func):
    @wraps(func)  # ✅ 复制 func 的 __name__、__doc__ 到 wrapper
    def wrapper(*args, **kwargs):
        print(f"calling {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@my_decorator
def hello():
    """Say hello."""
    pass

print(hello.__name__)  # 'hello'（不是 'wrapper'）
print(hello.__doc__)   # 'Say hello.'
```

### 1.5 `@cached_property`：缓存属性

`@cached_property` 是基于描述符的属性缓存（描述符协议见 [22-descriptor](./24-descriptor.md)），第一次访问时计算，之后用缓存：

```python
from functools import cached_property

class Heavy:
    @cached_property
    def data(self):
        print("computing...")
        return [x ** 2 for x in range(1_000_000)]

h = Heavy()
h.data  # 触发计算
h.data  # 用缓存
```

### 1.6 `total_ordering`：自动生成比较方法

定义 `__eq__` 和一个比较方法（如 `__lt__`），自动补齐其他：

```python
from functools import total_ordering

@total_ordering
class Student:
    def __init__(self, score):
        self.score = score
    def __eq__(self, other):
        return self.score == other.score
    def __lt__(self, other):
        return self.score < other.score
    # 自动获得 __le__、__gt__、__ge__
```

## 2. 代码示例

### 2.1 `lru_cache` 加速计算

```python
from functools import lru_cache

@lru_cache(maxsize=None)
def parse_config(path: str) -> dict:
    """解析配置文件。相同 path 不会重复读取。"""
    print(f"reading {path}...")
    return {"path": path, "data": "..."}

# 第一次：实际读文件
parse_config("/etc/app.yaml")
# 第二次：直接返回缓存
parse_config("/etc/app.yaml")  # 不打印 "reading..."
```

### 2.2 `partial` 特化函数

```python
from functools import partial
import json

# 特化：紧凑 JSON 序列化（无空格）
compact_dump = partial(json.dumps, separators=(",", ":"))
print(compact_dump({"a": 1, "b": 2}))  # '{"a":1,"b":2}'
```

### 2.3 `reduce` 做扁平化

```python
from functools import reduce

nested = [[1, 2], [3, 4], [5, [6, 7]]]

# 扁平化：reduce + 列表合并
flat = reduce(lambda acc, item: acc + (item if isinstance(item, list) else [item]),
              nested, [])
print(flat)  # [1, 2, 3, 4, 5, 6, 7]
```

### 2.4 常见错误：`lru_cache` 用 list 作为参数

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def process(items: list):  # list 不可哈希
    return sum(items)

process([1, 2, 3])  # TypeError: unhashable type: 'list'

# ✅ 改成 tuple（可哈希）
@lru_cache(maxsize=128)
def process(items: tuple):
    return sum(items)
process((1, 2, 3))  # OK
```

## 3. 关键要点总结

- `@lru_cache(maxsize=N)`：缓存函数结果，参数必须可哈希
- `functools.partial(fn, **kwargs)`：固定部分参数，返回新函数
- `functools.reduce(fn, iterable, init)`：累积归并，类似 fold
- `@functools.wraps(fn)`：装饰器中保留原函数元信息
- `@cached_property`：描述符版缓存，第一次访问计算，之后命中缓存
- dify 大量用 `@lru_cache` 缓存 IO 操作和 node 注册；用 `@wraps` 保留 OpenTelemetry trace 元信息

---

**文档版本**：v1.0
**最后更新**：2026-07-13
