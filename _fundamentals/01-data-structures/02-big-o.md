# 1.1.2 大 O 表示法详解

> 大 O 表示法是描述算法复杂度的"行话"，后端面试必问。

## 🎯 学习目标

完成本文档后，你将能够：
- 准确理解大 O 的数学定义
- 区分 O、Ω、Θ 三个符号
- 掌握常见复杂度的对比
- 能在代码 review 时快速判断复杂度

## 📚 前置知识

- 01-complexity.md

## 1. 核心概念

### 1.1 大 O 的数学定义

**定义**：若存在常数 C 和 n₀，使得对所有 n ≥ n₀，都有 `f(n) ≤ C · g(n)`，则记 `f(n) = O(g(n))`。

**通俗理解**：当 n 足够大时，f(n) 的增长速度**不超过** g(n) 的常数倍。

```
      f(n)
       |
   C·g(n) ___________
       |           /
       |          /  ← f(n) 的增长被 C·g(n) 盖住
       |         /
       |________/_____________→ n
              n₀
```

### 1.2 大 Ω、大 Θ

| 符号 | 含义 | 类比 |
|------|------|------|
| **O(g)** | 上界（不超过） | ≤ |
| **Ω(g)** | 下界（不少于） | ≥ |
| **Θ(g)** | 紧界（同阶） | = |

**举例**：
- 归并排序的时间：`T(n) = Θ(n log n)`（最好、最坏都是 n log n）
- 快速排序：`最好` `Ω(n log n)`，但 `最坏` `O(n²)`

### 1.3 大 O 推导规则

```python
# 规则 1：常数忽略
O(2n + 5) = O(n)

# 规则 2：低阶忽略
O(n² + n + 100) = O(n²)

# 规则 3：顺序代码相加
O(a) + O(b) = O(a + b)
# 取较大者
max(O(a), O(b))

# 规则 4：嵌套代码相乘
for i in range(n):       # O(n)
    for j in range(n):   # O(n)
        print(i, j)      # O(n²)
```

### 1.4 复杂度增长曲线

```
操作数
   |
   |              O(2ⁿ)  ← 算不动
   |          O(n²)
   |       O(n log n)
   |     O(n)
   |   O(log n)
   | O(1)
   |_____________________________________→ n
```

数据规模 100 万时：
- O(1) = 1 次
- O(log n) ≈ 20 次
- O(n) = 100 万次
- O(n log n) ≈ 2000 万次
- O(n²) = 10¹² 次（跑不动）

## 2. 代码示例

### 2.1 不同复杂度的实际差异

```python
# 文件：big_o_compare.py
import time

def constant_time(n):
    """O(1): 无论 n 多大，只做一次操作"""
    return 42 + n  # 不依赖 n 的大小

def linear_time(n):
    """O(n): 遍历 n 次"""
    total = 0
    for i in range(n):
        total += i
    return total

def quadratic_time(n):
    """O(n²): 嵌套循环"""
    count = 0
    for i in range(n):
        for j in range(n):
            count += 1
    return count

# 实测
for n in [100, 1000, 5000]:
    start = time.perf_counter()
    linear_time(n)
    t_linear = time.perf_counter() - start

    start = time.perf_counter()
    quadratic_time(n)
    t_quad = time.perf_counter() - start

    print(f"n={n}: O(n)={t_linear:.6f}s, O(n²)={t_quad:.6f}s")
```

### 2.2 实战：判断代码复杂度

```python
# 例 1：O(1)
def get_first(arr):
    return arr[0]  # 只访问一次

# 例 2：O(n)
def find_max(arr):
    m = arr[0]
    for x in arr:  # 遍历一次
        if x > m:
            m = x
    return m

# 例 3：O(n²)
def has_pair_sum(arr, target):
    for i in arr:          # O(n)
        for j in arr:      # O(n) 嵌套
            if i + j == target:
                return True
    return False

# 优化：O(n) 用哈希表（详见 [13-hash-table](./13-hash-table.md)）
def has_pair_sum_fast(arr, target):
    seen = set()           # O(n) 空间
    for x in arr:          # O(n)
        if target - x in seen:  # O(1) 查找
            return True
        seen.add(x)
    return False
```

## 3. dify 仓库源码解读

### 3.1 复杂度敏感的检索

**文件位置**：`/Users/xu/code/github/dify/api/core/tools/utils/dataset_retriever.py`
**核心代码**（行 50-90）：

```python
def retrieve_segments(
    self,
    query: str,
    top_k: int = 5,
) -> list[Segment]:
    """检索最相关的 top_k 个文档片段。"""
    # Step 1: 向量化查询 - O(1) 远程调用
    query_vector = self.embedding_model.encode(query)

    # Step 2: 在向量库中检索 - O(log n) ANN 搜索
    candidates = self.vector_store.search(
        query_vector,
        top_k=top_k * 3,  # 多取一些，后面还要过滤
    )

    # Step 3: 重排序（rerank）- O(n log n)
    reranked = sorted(
        candidates,
        key=lambda s: self.reranker.score(query, s.content),
        reverse=True,
    )[:top_k]

    return reranked
```

**解读**：
- 第 8 行：embedding 编码调用一次 API → O(1)
- 第 12 行：向量库用 HNSW/IVF 索引 → O(log n)
- 第 19 行：Python 内置 `sorted` → O(n log n)
- **整体复杂度**：O(n log n)，n 为候选数
- **为什么不直接用 O(n²) 的两两比较？** 当候选数 1 万时，n² = 1亿次比较，跑不动

## 4. 关键要点总结

- 大 O 描述**增长率上界**，不是实际时间
- 推导规则：常数忽略、低阶忽略、嵌套相乘、顺序相加取大
- O(1) < O(log n) < O(n) < O(n log n) < O(n²) < O(2ⁿ)
- **面试常考**：判断代码复杂度、优化复杂度
- dify 在向量检索中用 **O(log n)** 的 ANN 索引避免 O(n) 暴力搜索

## 5. 练习题

### 练习 1：基础（必做）

判断下列代码的时间复杂度：

```python
def f1(n):
    for i in range(n):
        print(i)

def f2(n):
    for i in range(n):
        for j in range(n):
            for k in range(n):
                print(i, j, k)

def f3(n):
    i = n
    while i > 1:
        print(i)
        i = i // 2

def f4(arr):
    seen = {}
    for x in arr:
        if x in seen:
            return x
        seen[x] = True
    return None
```

### 练习 2：进阶

阅读 `api/core/tools/utils/dataset_retriever.py` 的 `retrieve_segments`，如果 `top_k * 3 = 10000`，总共需要多少次 rerank 计算？

### 练习 3：挑战（选做）

设计一个算法，找出数组中前 K 大的元素（K 远小于 N）。要求时间复杂度优于 O(n log n)，空间 O(K)。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/tools/utils/dataset_retriever.py`
- 算法导论（第 3 章 函数增长）
- MIT 6.006 课程讲义

---

**文档版本**：v1.0
**最后更新**：2026-07-13