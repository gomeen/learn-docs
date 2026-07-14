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
- 01-fundamentals/10-decorator.md
- 01-fundamentals/34-descriptor.md

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

装饰器会覆盖原函数的 `__name__` / `__doc__`，用 `@wraps` 保留：

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

`@cached_property` 是基于描述符的属性缓存，第一次访问时计算，之后用缓存：

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

## 3. dify 仓库源码解读

### 3.1 `lru_cache` 缓存 YAML position 映射

**文件位置**：`/Users/xu/code/github/dify/api/core/helper/position_helper.py`
**核心代码**（行 1-25）：

```python
import os
from collections import OrderedDict
from collections.abc import Callable
from functools import lru_cache

from configs import dify_config
from core.tools.utils.yaml_utils import load_yaml_file_cached


@lru_cache(maxsize=128)
def get_position_map(folder_path: str, *, file_name: str = "_position.yaml") -> dict[str, int]:
    """
    Get the mapping from name to index from a YAML file
    :param folder_path:
    :param file_name: the YAML file name, default to '_position.yaml'
    :return: a dict with name as key and index as value
    """
    # FIXME(-LAN-): Cache position maps to prevent file descriptor exhaustion during high-load benchmarks
    position_file_path = os.path.join(folder_path, file_name)
    try:
        yaml_content = load_yaml_file_cached(file_path=position_file_path)
    except Exception:
        yaml_content = []
    positions = [item.strip() for item in yaml_content if item and isinstance(item, str) and item.strip()]
    return {name: index for index, name in enumerate(positions)}
```

**解读**：
- 第 4 行：`from functools import lru_cache`
- 第 10 行：`@lru_cache(maxsize=128)`——缓存 128 个不同的 `folder_path` 调用
- 第 11 行：`*` 强制 `file_name` 只能作为关键字参数传入（避免位置参数歧义）
- 第 18 行：`FIXME` 注释透露：**不加缓存会在高负载压测时把文件描述符用完**
- **应用场景**：dify 的工具列表有 `_position.yaml` 文件记录排序，加缓存避免重复 IO

### 3.2 `lru_cache(maxsize=1)` 缓存节点注册

**文件位置**：`/Users/xu/code/github/dify/api/core/workflow/node_factory.py`
**核心代码**（行 104-128）：

```python
def _import_node_package(package_name: str, *, excluded_modules: frozenset[str] = frozenset()) -> None:
    package = importlib.import_module(package_name)
    for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        if module_name in excluded_modules:
            continue
        importlib.import_module(module_name)


@lru_cache(maxsize=1)
def register_nodes() -> None:
    """Import production node modules so they self-register with ``Node``."""
    _import_node_package("graphon.nodes")
    _import_node_package("core.workflow.nodes")


def get_node_type_classes_mapping() -> Mapping[NodeType, Mapping[str, type[Node]]]:
    """Return a read-only snapshot of the current production node registry.

    The workflow layer owns node bootstrap because it must compose built-in
    `graphon.nodes.*` implementations with workflow-local nodes under
    `core.workflow.nodes.*`. Keeping this import side effect here avoids
    reintroducing registry bootstrapping into lower-level graph primitives.
    """
    register_nodes()
    return Node.get_node_type_classes_mapping()
```

**解读**：
- 第 10 行：`@lru_cache(maxsize=1)`——缓存容量只有 1，因为 `register_nodes()` 是无参数函数
- 第 12-13 行：导入所有 node 模块，每个模块在 import 时会调用 `Node.register(...)` 自注册
- 第 19-21 行：`get_node_type_classes_mapping` 第一次调用时触发注册，之后直接拿缓存
- **设计意图**：node 注册是**幂等且有副作用的**操作，`maxsize=1` 确保整个进程只执行一次

### 3.3 `@wraps` 保留装饰器元信息

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/datasource/retrieval_service.py`
**核心代码**（行 96-107）：

```python
def _propagate_otel_context[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    captured_context = otel_context.get_current()

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        token = otel_context.attach(captured_context)
        try:
            return func(*args, **kwargs)
        finally:
            otel_context.detach(token)

    return wrapper
```

**解读**：
- 第 3 行：捕获当前 OpenTelemetry 上下文（在 worker 线程中）
- 第 5 行：`@functools.wraps(func)`——保留 `func` 的 `__name__`、`__doc__`、`__signature__` 等
- 第 6-10 行：在执行前 attach context，执行后 detach，保证 trace 链路连续
- **为什么需要 `@wraps`**：保留 `__name__` 让 OpenTelemetry 的 trace 能正确显示函数名；保留 `__signature__` 让 IDE 类型提示正常工作

## 4. 关键要点总结

- `@lru_cache(maxsize=N)`：缓存函数结果，参数必须可哈希
- `functools.partial(fn, **kwargs)`：固定部分参数，返回新函数
- `functools.reduce(fn, iterable, init)`：累积归并，类似 fold
- `@functools.wraps(fn)`：装饰器中保留原函数元信息
- `@cached_property`：描述符版缓存，第一次访问计算，之后命中缓存
- dify 大量用 `@lru_cache` 缓存 IO 操作和 node 注册；用 `@wraps` 保留 OpenTelemetry trace 元信息

## 5. 练习题

### 练习 1：基础（必做）

用 `@lru_cache` 实现一个「记忆化的阶乘函数」，比较加缓存前后的运行时间。

```python
from functools import lru_cache
import time

# TODO: 加 lru_cache 装饰 factorial
def factorial(n):
    if n < 2:
        return 1
    return n * factorial(n - 1)

start = time.perf_counter()
for i in range(20):
    factorial(30)
print(f"with cache: {time.perf_counter() - start:.4f}s")
```

### 练习 2：进阶

阅读 `api/tests/unit_tests/services/test_variable_truncator.py` 第 57 行的 `_compact_json_dumps = functools.partial(json.dumps, separators=(",", ":"))`，理解 dify 测试中如何用 `partial` 减少样板代码。

### 练习 3：挑战（选做）

实现一个通用的「带超时的 lru_cache」，缓存结果超过 `ttl` 秒后自动失效（提示：用 `lru_cache` + 自定义包装，或者直接用 `cachetools.TTLCache`）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/helper/position_helper.py`
- `/Users/xu/code/github/dify/api/core/workflow/node_factory.py`
- `/Users/xu/code/github/dify/api/core/rag/datasource/retrieval_service.py`
- Python 官方文档 functools：https://docs.python.org/3/library/functools.html
- functools 源码：https://github.com/python/cpython/blob/main/Lib/functools.py

---

**文档版本**：v1.0
**最后更新**：2026-07-13