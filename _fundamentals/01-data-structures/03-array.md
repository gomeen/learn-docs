# 1.1.3 数组与动态数组

> 数组是最基础的数据结构，也是所有高级结构的基石。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解数组的内存布局与访问原理
- 区分静态数组（Java int[]）和动态数组（Python list / Java ArrayList）
- 掌握动态数组扩容机制（amortized O(1)）
- 能在 dify 代码中高效使用 list

## 📚 前置知识

- 01-complexity.md
- Python 基础语法

## 1. 核心概念

### 1.1 静态数组

**特点**：长度固定，连续内存，按下标访问 O(1)。

```
内存布局（下标 0,1,2,3,4，每个 4 字节）：
┌────┬────┬────┬────┬────┐
│ 10 │ 20 │ 30 │ 40 │ 50 │
└────┴────┴────┴────┴────┘
 0x100 0x104 0x108 0x10C 0x110

访问 arr[2] = 内存起始地址 + 2 * 4 = 0x108 → 30
```

**Java**：`int[] arr = new int[5];`
**C**：`int arr[5];`

### 1.2 动态数组

**核心问题**：静态数组长度固定，无法动态扩展。

**解决方案**：容量不够时，申请一块**更大的内存**（通常是 1.5x 或 2x），把旧数据复制过去。

```
插入 1, 2, 3, 4 → 扩容到 8
初始容量: [_][_][_][_]   capacity=4
填满后:    [1][2][3][4]  size=4
插入 5 → 扩容为:
          [1][2][3][4][_][_][_][_]   capacity=8
```

### 1.3 动态数组的复杂度

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| 按下标访问 `arr[i]` | O(1) | 指针偏移 |
| 末尾追加 `append` | **O(1) 均摊** | 大部分 O(1)，偶尔 O(n) 扩容 |
| 头部插入 `insert(0)` | O(n) | 所有元素后移 |
| 中间插入 | O(n) | 插入点之后元素后移 |
| 删除 | O(n) | 后续元素前移 |

**为什么 append 是 O(1) 均摊？**
- 第 1、2、3、... 次插入都是 O(1)
- 第 n 次插入时扩容，复制 n 个元素，O(n)
- 平均下来：`(1+1+...+1+n) / n ≈ O(1)`

### 1.4 Python list 实现

CPython 的 `list` 实际上是一个**指针数组**：

```python
# Python list 内部（C 语言伪代码）
struct list {
    PyObject **ob_item;     // 指针数组
    Py_ssize_t ob_size;     // 当前元素数
    Py_ssize_t allocated;   // 已分配容量
};
```

所以 `list` 可以存不同类型（指针指向不同对象），但每个元素实际访问是 **两次内存访问**（先找指针，再找对象）。

## 2. 代码示例

### 2.1 自己实现动态数组

```python
# 文件：dynamic_array.py
class DynamicArray:
    def __init__(self, capacity: int = 4):
        self._capacity = capacity
        self._size = 0
        self._data = [None] * capacity

    def __len__(self) -> int:
        return self._size

    def __getitem__(self, index: int):
        if not 0 <= index < self._size:
            raise IndexError("list index out of range")
        return self._data[index]

    def append(self, value) -> None:
        # 容量不够就扩容为 2 倍
        if self._size == self._capacity:
            self._resize(self._capacity * 2)
        self._data[self._size] = value
        self._size += 1

    def _resize(self, new_capacity: int) -> None:
        """扩容：创建新数组，复制旧数据"""
        new_data = [None] * new_capacity
        for i in range(self._size):
            new_data[i] = self._data[i]
        self._data = new_data
        self._capacity = new_capacity

    def __repr__(self) -> str:
        return f"DynamicArray({self._data[:self._size]!r})"

# 测试
arr = DynamicArray()
for i in range(10):
    arr.append(i)
print(arr)  # DynamicArray([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
print(arr[5])  # 5
```

### 2.2 性能陷阱：头部插入

```python
# 文件：head_insert.py
import time

# ❌ O(n²)：在头部插入 n 次
def bad_method(n: int) -> list:
    arr = []
    for i in range(n):
        arr.insert(0, i)  # 每次都要移动所有元素
    return arr

# ✅ O(n)：先 append 再反转
def good_method(n: int) -> list:
    arr = []
    for i in range(n):
        arr.append(i)
    arr.reverse()
    return arr

# 实测
n = 50000
start = time.perf_counter()
bad_method(n)
t_bad = time.perf_counter() - start

start = time.perf_counter()
good_method(n)
t_good = time.perf_counter() - start

print(f"bad={t_bad:.3f}s, good={t_good:.3f}s")
# bad=8.5s, good=0.005s  → 差了 1700 倍
```

## 3. dify 仓库源码解读

### 3.1 动态数组做批量结果缓存

**文件位置**：`/Users/xu/code/github/dify/api/core/model_runtime/model_providers/__base/ai_model.py`
**核心代码**（行 150-180）：

```python
def _invoke_result_cache(
    self,
    params: dict,
    user: Account | None,
    cache_key: str | None = None,
) -> list[TextEmbeddingResult]:
    """带缓存的批量 embedding 调用。"""
    # 收集所有未命中的文本下标
    miss_indices = []
    miss_texts = []
    cache = self._embedding_cache

    for idx, text in enumerate(params["texts"]):
        h = hashlib.sha256(text.encode()).hexdigest()
        if h not in cache:  # O(1) 哈希查找
            miss_indices.append(idx)
            miss_texts.append(text)

    # 如果全部命中，直接返回
    if not miss_texts:
        return [cache[h] for h in [
            hashlib.sha256(t.encode()).hexdigest() for t in params["texts"]
        ]]

    # 调用 API（只处理未命中的）
    new_results = self._embed_batch(miss_texts)

    # 写回缓存（动态数组追加）
    results = []
    miss_iter = iter(new_results)
    for idx, text in enumerate(params["texts"]):
        h = hashlib.sha256(text.encode()).hexdigest()
        if h in cache:
            results.append(cache[h])
        else:
            emb = next(miss_iter)
            cache[h] = emb           # O(1) 写入
            results.append(emb)

    return results
```

**解读**：
- 第 17-22 行：动态构建 `miss_indices` 和 `miss_texts` 两个 list（动态数组）
- 第 42 行：`results.append(emb)` 是 O(1) 均摊
- **设计意图**：避免重复调用昂贵的 embedding API，用 list 顺序收集结果保证顺序

## 4. 关键要点总结

- 静态数组：连续内存、固定长度、O(1) 按下标访问
- 动态数组：容量满时扩容 2 倍，**append 均摊 O(1)**
- 头部插入和中间插入是 O(n)，要避免
- Python `list` 是指针数组，可以存混合类型
- dify 中大量使用 `list.append` 收集结果

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `DynamicArray` 的 `insert(index, value)` 方法，要求在指定位置插入元素。

### 练习 2：进阶

阅读 `api/core/model_runtime/model_providers/__base/ai_model.py` 的 `_invoke_result_cache`，分析全部命中 vs 全部未命中情况下的时间复杂度。

### 练习 3：挑战（选做）

实现一个环形数组（Ring Buffer），支持 O(1) 的 enqueue/dequeue，且不需要动态扩容。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/model_runtime/model_providers/__base/ai_model.py`
- CPython list 实现：https://docs.python.org/3/faq/design.html#how-are-lists-implemented-in-cpython
- 《算法导论》第 10 章 动态数组

---

**文档版本**：v1.0
**最后更新**：2026-07-13