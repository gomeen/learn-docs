# 1.1.21 `itertools` 模块：迭代器工具箱

> 掌握 `itertools` 提供的迭代器工具，能用更少的代码完成切片、分组、笛卡尔积、链式操作，并识别 dify 中的相关用法。

## 🎯 学习目标

完成本文档后，你将能够：
- 熟练使用 `islice` / `chain` / `starmap` / `groupby` / `product` 等核心工具
- 用 `itertools` 替代常见的手写循环逻辑
- 在 dify 中识别 `starmap`、`islice` 等用法

## 📚 前置知识

- Python 基础：迭代器协议（`__iter__` / `__next__`）
- 01-fundamentals/14-generator.md（生成器）

## 1. 核心概念

### 1.1 为什么需要 `itertools`

`itertools` 提供**内存高效**的迭代器工具——所有函数都返回**惰性迭代器**，不一次性生成所有结果。这对处理大数据集至关重要。

| 类别 | 函数 | 作用 |
| --- | --- | --- |
| **无限迭代器** | `count`, `cycle`, `repeat` | 无限序列 |
| **截断迭代器** | `islice`, `takewhile`, `dropwhile` | 切片式访问 |
| **组合迭代器** | `chain`, `zip_longest`, `product` | 组合多个迭代器 |
| **映射迭代器** | `starmap`, `map` | 元素级变换 |
| **过滤迭代器** | `filterfalse`, `compress` | 过滤 |
| **分组迭代器** | `groupby` | 按键分组 |

### 1.2 `chain`：拼接迭代器

```python
from itertools import chain

a = [1, 2, 3]
b = [4, 5]
list(chain(a, b))  # [1, 2, 3, 4, 5]
```

### 1.3 `islice`：迭代器切片

```python
from itertools import islice

# 只能对迭代器用，普通 list 不能用 islice(list, 5)
it = iter([1, 2, 3, 4, 5, 6, 7, 8])
list(islice(it, 3))       # [1, 2, 3]
list(islice(it, 2, 5))    # [3, 4, 5]（从下标 2 开始取 3 个）
```

### 1.4 `starmap`：对每元素解包后调用

```python
from itertools import starmap

# 区别于 map：map(func, iterable)，starmap(func, iterable_of_tuples)
pairs = [(2, 3), (10, 5), (4, 4)]
list(starmap(pow, pairs))  # [8, 100000, 256]
```

### 1.5 `groupby`：分组（**注意：要先排序**）

```python
from itertools import groupby

data = [
    ("fruit", "apple"),
    ("fruit", "banana"),
    ("veg",   "carrot"),
    ("veg",   "lettuce"),
]
# 必须先排序！
data.sort(key=lambda x: x[0])
for key, group in groupby(data, key=lambda x: x[0]):
    print(key, list(group))
# fruit [('fruit', 'apple'), ('fruit', 'banana')]
# veg   [('veg', 'carrot'), ('veg', 'lettuce')]
```

### 1.6 `product`：笛卡尔积

```python
from itertools import product

list(product([1, 2], ['a', 'b']))
# [(1, 'a'), (1, 'b'), (2, 'a'), (2, 'b')]
```

### 1.7 `takewhile` / `dropwhile`：条件截断

```python
from itertools import takewhile, dropwhile

nums = [1, 3, 5, 8, 9, 11]
list(takewhile(lambda x: x % 2 == 1, nums))  # [1, 3, 5]（遇到第一个偶数停）
list(dropwhile(lambda x: x % 2 == 1, nums))  # [8, 9, 11]（跳过所有奇数）
```

## 2. 代码示例

### 2.1 自定义 `chunked`（分批迭代器）

```python
from itertools import islice

def chunked(iterable, size):
    """把迭代器切成 size 大小的批次。"""
    it = iter(iterable)
    while True:
        batch = list(islice(it, size))
        if not batch:
            return
        yield batch

# 测试
for batch in chunked(range(10), 3):
    print(batch)  # [0,1,2], [3,4,5], [6,7,8], [9]
```

### 2.2 `starmap` 批量调用

```python
from itertools import starmap

# 等价于 map(lambda a, b: a + b, [(1,2), (3,4), (5,6)])
pairs = [(1, 2), (3, 4), (5, 6)]
sums = list(starmap(lambda a, b: a + b, pairs))
print(sums)  # [3, 7, 11]
```

### 2.3 常见错误：`groupby` 不排序

```python
from itertools import groupby

data = [("a", 1), ("b", 2), ("a", 3)]  # 未排序
for k, g in groupby(data, key=lambda x: x[0]):
    print(k, list(g))
# a [('a', 1)]
# b [('b', 2)]
# a [('a', 3)]    ← bug！同一 key 被分到了两组

# ✅ 先排序
data.sort(key=lambda x: x[0])
for k, g in groupby(data, key=lambda x: x[0]):
    print(k, list(g))
# a [('a', 1), ('a', 3)]
# b [('b', 2)]
```

## 3. dify 仓库源码解读

### 3.1 `starmap` 批量构建 Redis 锁 key

**文件位置**：`/Users/xu/code/github/dify/api/core/trigger/utils/locks.py`
**核心代码**（行 1-13）：

```python
from collections.abc import Sequence
from itertools import starmap


def build_trigger_refresh_lock_key(tenant_id: str, subscription_id: str) -> str:
    """Build the Redis lock key for trigger subscription refresh in-flight protection."""
    return f"trigger_provider_refresh_lock:{tenant_id}_{subscription_id}"


def build_trigger_refresh_lock_keys(pairs: Sequence[tuple[str, str]]) -> list[str]:
    """Build Redis lock keys for a sequence of (tenant_id, subscription_id) pairs."""
    return list(starmap(build_trigger_refresh_lock_key, pairs))
```

**解读**：
- 第 1 行：使用 `from collections.abc import Sequence` 接受任意序列类型（list / tuple）
- 第 5-7 行：单 key 构造函数
- 第 10-13 行：`starmap(build_trigger_refresh_lock_key, pairs)` 把 `(tenant_id, subscription_id)` 元组**自动解包**为两个位置参数
- **等价于**：`list(map(lambda p: build_trigger_refresh_lock_key(*p), pairs))`，但 `starmap` 更声明式
- **应用场景**：trigger 订阅刷新时，需要为每个 (tenant, subscription) 对生成 Redis 锁 key，避免并发刷新冲突

### 3.2 `islice` 实现自定义分批迭代器

**文件位置**：`/Users/xu/code/github/dify/api/tasks/rag_pipeline/rag_pipeline_run_task.py`
**核心代码**（行 32-37）：

```python
def chunked(iterable: Sequence, size: int):
    it = iter(iterable)
    return iter(lambda: list(islice(it, size)), [])
```

**解读**：
- 第 1-4 行：用一个**奇技淫巧**实现分批迭代器
- 第 3 行：`iter(callable, sentinel)`——反复调用 `lambda` 直到返回 sentinel
- 第 3 行：`list(islice(it, size))` 返回 `[]` 时停止迭代（因为 sentinel 就是 `[]`）
- **妙处**：整个函数只用 4 行，且完全惰性——不会预先把所有元素加载到内存
- **应用场景**：RAG pipeline 任务把 invoke entities 列表传给 Celery，需要分批处理避免内存爆

## 4. 关键要点总结

- `itertools` 函数返回**惰性迭代器**，内存友好
- `chain` 拼接、`islice` 切片、`starmap` 解包、`groupby` 分组、`product` 笛卡尔积
- `groupby` 必须先排序
- dify 用 `starmap` 构建 Redis 锁 key 列表，用 `islice` 实现自定义 `chunked`
- 自定义 `chunked`：`iter(lambda: list(islice(it, n)), [])` 是 Python 社区的经典一行实现

## 5. 练习题

### 练习 1：基础（必做）

用 `itertools.product` 生成 6 位十进制密码的所有可能组合（提示：用 `range(10)` 三次），统计总共有多少个（应输出 1000000）。

```python
from itertools import product

count = sum(1 for _ in product(range(10), repeat=6))
print(count)  # 1000000
```

### 练习 2：进阶

修改练习 1，只生成「前两位相同」的密码（例如 110000、221234）。用 `itertools` 实现，要求内存高效。

### 练习 3：挑战（选做）

阅读 dify 的 `api/controllers/openapi/workspaces.py`，理解 `from itertools import starmap` 是怎么用的（提示：搜索 `starmap`），并画出完整的调用链。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/trigger/utils/locks.py`
- `/Users/xu/code/github/dify/api/tasks/rag_pipeline/rag_pipeline_run_task.py`
- Python 官方文档 itertools：https://docs.python.org/3/library/itertools.html
- 「Python 工匠」itertools 篇：https://github.com/piglei/one-python-craftsman

---

**文档版本**：v1.0
**最后更新**：2026-07-13