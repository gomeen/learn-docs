# 1.4.3 跳表（SkipList，Redis ZSet 底层）

> 跳表是有序集合的高效实现，Redis ZSet 和 LevelDB 用它做内存索引。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解跳表的多层索引结构
- 掌握跳表的插入、查找、删除 O(log n) 实现
- 知道 Redis ZSet 底层用跳表的原因
- 能在 dify 中识别跳表的应用（任务调度、排行榜）

## 📚 前置知识

- 11-heap.md
- 09-red-black-tree.md

## 1. 核心概念

### 1.1 什么是跳表？

**跳表**（Skip List）是**多层有序链表**，通过空间换时间实现 O(log n) 查找。

```
Level 3: head ---------------------------------------- 50
Level 2: head ----------- 20 ------------------------ 50
Level 1: head ----- 10 -- 20 -------- 30 ------------- 50
Level 0: head -- 5 - 10 - 15 - 20 - 25 - 30 - 40 - 50 - 60
```

**思想**：从最高层开始查找，先大步跨越，再逐层下降。

### 1.2 跳表 vs 平衡树

| 维度 | 跳表 | 红黑树 |
|------|------|--------|
| 实现难度 | **简单** | 复杂 |
| 查找 | O(log n) | O(log n) |
| 插入 | O(log n) | O(log n) |
| 删除 | O(log n) | O(log n) |
| 并发友好 | **天然支持** | 需要复杂锁 |
| 范围查询 | **简单**（链表遍历） | 中序遍历 |
| 内存占用 | 多级指针 | 较小 |

**为什么 Redis ZSet 用跳表？**
- 范围查询多（`ZRANGEBYSCORE`），跳表更简单
- 实现简单，bug 少
- 并发友好（无旋转操作）

### 1.3 跳表的层数

每个节点的层数是**随机**决定的（类似抛硬币）：

```
randomLevel():
    level = 1
    while random() < 0.5 and level < MAX_LEVEL:
        level += 1
    return level
```

**期望复杂度**：每个节点平均有 1.5 层（p=0.5），查找期望 O(log n)。

### 1.4 Redis ZSet 的实现

Redis 的有序集合（ZSet）同时用两种结构：

```
ZSet {
    dict<member, score>      // O(1) 通过 member 查 score
    zskiplist                 // O(log n) 范围查询
}
```

**为什么两者都要？**
- 通过 member 查 score 用字典更快
- 范围查询（按 score）用跳表更快

### 1.5 应用场景

1. **Redis ZSet**：排行榜、限流、延迟队列
2. **LevelDB / RocksDB**：MemTable 内部使用
3. **Apache HBase**：MemStore 实现
4. **任务调度**：按时间排序的任务队列

## 2. 代码示例

### 2.1 跳表实现

```python
# 文件：skiplist.py
import random
from typing import Any, Optional

class SkipListNode:
    __slots__ = ("val", "forward")

    def __init__(self, val: Any, level: int):
        self.val = val
        self.forward: list[Optional['SkipListNode']] = [None] * level

class SkipList:
    """跳表实现：升序排列。"""

    MAX_LEVEL = 16
    P = 0.5  # 每层节点保留概率

    def __init__(self):
        self._head = SkipListNode(None, self.MAX_LEVEL)
        self._level = 0  # 当前最大层数

    def _random_level(self) -> int:
        level = 1
        while random.random() < self.P and level < self.MAX_LEVEL:
            level += 1
        return level

    def insert(self, val: int) -> None:
        """插入元素 - O(log n)。"""
        level = self._random_level()
        new_node = SkipListNode(val, level)

        # 找到每一层的插入位置
        update = [self._head] * self.MAX_LEVEL
        cur = self._head
        for i in range(self._level - 1, -1, -1):
            while cur.forward[i] and cur.forward[i].val < val:
                cur = cur.forward[i]
            update[i] = cur

        # 插入节点
        for i in range(level):
            new_node.forward[i] = update[i].forward[i]
            update[i].forward[i] = new_node

        if level > self._level:
            self._level = level

    def search(self, val: int) -> bool:
        """查找元素 - O(log n)。"""
        cur = self._head
        for i in range(self._level - 1, -1, -1):
            while cur.forward[i] and cur.forward[i].val < val:
                cur = cur.forward[i]
        cur = cur.forward[0]
        return cur is not None and cur.val == val

    def delete(self, val: int) -> bool:
        """删除元素 - O(log n)。"""
        update = [self._head] * self.MAX_LEVEL
        cur = self._head
        for i in range(self._level - 1, -1, -1):
            while cur.forward[i] and cur.forward[i].val < val:
                cur = cur.forward[i]
            update[i] = cur

        target = cur.forward[0]
        if target and target.val == val:
            for i in range(self._level):
                if update[i].forward[i] != target:
                    break
                update[i].forward[i] = target.forward[i]
            # 更新最大层数
            while self._level > 1 and self._head.forward[self._level - 1] is None:
                self._level -= 1
            return True
        return False

    def range_query(self, low: int, high: int) -> list[int]:
        """范围查询 [low, high] - O(log n + k)。"""
        result = []
        cur = self._head
        for i in range(self._level - 1, -1, -1):
            while cur.forward[i] and cur.forward[i].val < low:
                cur = cur.forward[i]
        cur = cur.forward[0]
        while cur and cur.val <= high:
            result.append(cur.val)
            cur = cur.forward[0]
        return result
```

### 2.2 用跳表实现排行榜

```python
# 文件：leaderboard.py
class Leaderboard:
    """用跳表实现排行榜：分数降序排列。

    实际 Redis ZSet 就是这样用的。
    """

    def __init__(self):
        # 跳表按 (-score, user_id) 排序，分数高的在前
        self._sl = SkipList()  # 假设支持自定义排序
        self._user_score: dict[str, int] = {}

    def add_score(self, user_id: str, score: int) -> None:
        """添加或更新分数。"""
        old_score = self._user_score.get(user_id)
        if old_score is not None:
            self._sl.delete((-old_score, user_id))
        self._sl.insert((-score, user_id))
        self._user_score[user_id] = score

    def top_k(self, k: int) -> list[tuple[str, int]]:
        """获取前 K 名。"""
        # 实际需要反向遍历，这里简化
        # ... 返回 [(user_id, score), ...]
        pass

    def get_rank(self, user_id: str) -> int | None:
        """获取用户排名。"""
        # 跳表的 rank 操作：O(log n)
        score = self._user_score.get(user_id)
        if score is None:
            return None
        # 简化：实际需要遍历计数
        return None
```

### 2.3 测试跳表性能

```python
# 文件：test_skiplist.py
import time
import random

def test_skip_list():
    sl = SkipList()
    n = 100000
    data = list(range(n))
    random.shuffle(data)

    # 插入
    start = time.perf_counter()
    for x in data:
        sl.insert(x)
    t_insert = time.perf_counter() - start

    # 查找
    start = time.perf_counter()
    for _ in range(10000):
        sl.search(random.randint(0, n))
    t_search = time.perf_counter() - start

    # 范围查询
    start = time.perf_counter()
    result = sl.range_query(1000, 5000)
    t_range = time.perf_counter() - start

    print(f"插入 {n} 个: {t_insert:.3f}s")
    print(f"查找 10000 次: {t_search:.3f}s")
    print(f"范围查询 [1000, 5000]: {t_range:.6f}s, 结果 {len(result)} 个")

test_skip_list()
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Redis ZSet 用法（基于跳表）

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 180-205）：

```python
def zadd(
    self,
    name: str | bytes,
    mapping: dict[str | bytes | int | float, float | int | str | bytes],
    nx: bool = False,
    xx: bool = False,
    ch: bool = False,
    incr: bool = False,
    gt: bool = False,
    lt: bool = False,
) -> Any:
    """Redis ZADD 命令：向有序集合添加成员。

    Redis ZSet 底层是**跳表 + 字典**：
    - 跳表：按 score 排序，支持范围查询
    - 字典：按 member 查 score，O(1)

    dify 的典型用法：
    - 任务优先级队列（score = priority）
    - 时间线（score = timestamp）
    - 排行榜（score = 分数）
    """
    return self._require_client().zadd(
        _serialize_redis_name_arg(name, self._get_prefix()),
        cast(Any, mapping),
        nx=nx, xx=xx, ch=ch, incr=incr, gt=gt, lt=lt,
    )

def zrange(
    self,
    name: str | bytes,
    start: int,
    end: int,
    desc: bool = False,
    withscores: bool = False,
    score_cast_func: callable = float,
) -> Any:
    """Redis ZRANGE 命令：按排名范围获取。"""
    return self._require_client().zrange(
        _serialize_redis_name_arg(name, self._get_prefix()),
        start, end, desc=desc,
        withscores=withscores,
        score_cast_func=score_cast_func,
    )
```

**解读**：
- 第 17 行：dify 的 Redis 客户端封装了 `zadd`，底层 Redis 用跳表
- 第 23 行：`zrange` 利用跳表做范围查询，O(log n + k)
- **dify 的实际应用**：
  - **任务队列**：score = 优先级时间戳，worker 按 score 拉取任务
  - **应用限流**：滑动窗口（用 ZSet + 时间戳）
  - **延迟队列**：score = 执行时间戳，定时扫描
- **设计意图**：Redis ZSet 的有序性 + 范围查询 + 跳表的 O(log n) 复杂度，正好满足 dify 的需求

## 4. 关键要点总结

- 跳表：多层有序链表，**空间换时间**实现 O(log n) 操作
- 实现简单，**并发友好**，范围查询天然支持
- Redis ZSet = 跳表 + 字典（兼顾 O(1) 按 member 查询和 O(log n) 范围查询）
- dify 用 Redis ZSet 做任务队列、限流、延迟队列
- 跳表 vs 红黑树：实现更简单，并发友好，范围查询更直接

## 5. 练习题

### 练习 1：基础（必做）

实现跳表的 `delete(val)` 方法，处理所有边界情况（节点不在表中，节点是头节点等）。

### 练习 2：进阶

阅读 `api/extensions/ext_redis.py` 的 `zadd` 和 `zrange` 方法，说明 dify 用 Redis ZSet 实现任务优先级队列的具体方案（如何用 score 表示优先级？）。

### 练习 3：挑战（选做）

实现一个**并发安全的跳表**（用细粒度锁或 lock-free 算法）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- Redis 跳表实现：https://github.com/redis/redis/blob/unstable/src/t_zset.c
- Pugh 原始论文（1990）
- 《Redis 设计与实现》第 5 章 跳跃表

---

**文档版本**：v1.0
**最后更新**：2026-07-13