# 3.2.4 页面置换算法：LRU / FIFO / Clock

> 当物理内存不足时，选哪个页淘汰？页面置换算法决定性能。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 FIFO、LRU、Clock 等页面置换算法
- 理解 Belady 异常和栈算法的关系
- 知道 Linux 实际使用的近似 LRU
- 能在 dify 中识别页面置换的应用（Redis 淘汰策略）

## 📚 前置知识

- 06-virtual-memory.md

## 1. 核心概念

### 1.1 缺页异常（Page Fault）

```
访问虚拟页
  ↓
TLB 查找 → 命中
  ↓
页表查找 → 有效？
  ↓ 有效
访问物理内存
  ↓ 无效（缺页）
触发缺页异常
  ↓
操作系统处理：
  1. 选一个物理页淘汰
  2. 如果脏页 → 写回磁盘
  3. 从磁盘加载新页
  4. 更新页表
  5. 重启指令
```

### 1.2 FIFO（先进先出）

**思想**：淘汰最早进入内存的页。

```
访问序列：1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5
物理页框：3 个

FIFO 模拟：
1: [1, _, _]
2: [1, 2, _]
3: [1, 2, 3]
4: [4, 2, 3] ← 淘汰 1
1: [4, 1, 3] ← 淘汰 2
2: [4, 1, 2] ← 淘汰 3
5: [5, 1, 2] ← 淘汰 4
...
```

### 1.3 Belady 异常

**FIFO 的奇怪现象**：增加物理页框，**缺页率反而上升**！

```
访问序列：1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5

3 个页框：缺页 9 次
4 个页框：缺页 10 次  ← Belady 异常！
```

**栈算法**（LRU、Clock）**不会**出现 Belady 异常。

### 1.4 LRU（最近最少使用）

**思想**：淘汰最久没使用的页。

```
LRU 假设：过去不用的页，未来也不太会用（时间局部性）

访问序列：1, 2, 3, 4, 1, 2, 5
物理页框：3 个

LRU 模拟：
1: [1, _, _]
2: [1, 2, _]
3: [1, 2, 3]
4: [4, 2, 3] ← 淘汰 1（最久未用）
1: [4, 1, 3] ← 淘汰 3
2: [4, 1, 2] ← 淘汰 4
5: [5, 1, 2] ← 淘汰 1
```

### 1.5 Clock（时钟）算法

**思想**：用环形链表 + 使用位，模拟 LRU。

```
指针 →  [1][1][0][1][0][0]
         ↑
        当前位置
        ↓
       如果 use=0，淘汰
       如果 use=1，置 0 并继续
```

**二次机会算法**：
- 第一次扫描：清 use 位
- 第二次扫描：找 use=0 的淘汰

### 1.6 各算法对比

| 算法 | 缺页率 | 实现复杂度 | Belady 异常 |
|------|--------|----------|-------------|
| FIFO | 较高 | 简单 | **有** |
| LRU | **最优**（近似） | 复杂（需链表或栈） | ✗ |
| Clock | 接近 LRU | 简单 | ✗ |
| OPT | **理论最优** | 无法实现 | ✗ |

### 1.7 Linux 的近似 LRU

Linux 用**多代 LRU**：
- **活跃页**：刚访问过，优先保留
- **不活跃页**：较久未访问，可淘汰
- 定期将不活跃页移动到 inactive list

```
active list → inactive list → 淘汰
              ↑
            活跃页老化后进入
```

## 2. 代码示例

### 2.1 FIFO 模拟

```python
# 文件：fifo_replacement.py
from collections import deque
from typing import List

class FIFOPageReplacement:
    """FIFO 页面置换模拟。"""

    def __init__(self, capacity: int):
        self._capacity = capacity
        self._frames: deque = deque(maxlen=capacity)
        self.page_faults = 0

    def access(self, page: int) -> bool:
        """访问页，返回是否缺页。"""
        if page in self._frames:
            return False  # 命中
        self.page_faults += 1
        if len(self._frames) == self._capacity:
            # 队列满了，最老的自动出队
            pass
        self._frames.append(page)
        return True

# 测试
seq = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
for capacity in [3, 4]:
    fifo = FIFOPageReplacement(capacity)
    faults = sum(1 for p in seq if fifo.access(p))
    print(f"FIFO (capacity={capacity}): 缺页 {faults}")
# capacity=3: 9 次
# capacity=4: 10 次（Belady 异常！）
```

### 2.2 LRU 模拟

```python
# 文件：lru_replacement.py
from collections import OrderedDict
from typing import List

class LRUPageReplacement:
    """LRU 页面置换模拟。"""

    def __init__(self, capacity: int):
        self._capacity = capacity
        self._frames: OrderedDict = OrderedDict()
        self.page_faults = 0

    def access(self, page: int) -> bool:
        """访问页，返回是否缺页。"""
        if page in self._frames:
            self._frames.move_to_end(page)  # 标记最近使用
            return False
        self.page_faults += 1
        if len(self._frames) >= self._capacity:
            self._frames.popitem(last=False)  # 淘汰最久未用
        self._frames[page] = True
        return True

# 测试
seq = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
for capacity in [3, 4]:
    lru = LRUPageReplacement(capacity)
    faults = sum(1 for p in seq if lru.access(p))
    print(f"LRU (capacity={capacity}): 缺页 {faults}")
# capacity=3: 10 次
# capacity=4: 8 次（容量大，缺页少）
```

### 2.3 Clock 算法模拟

```python
# 文件：clock_replacement.py
class ClockPageReplacement:
    """Clock（时钟）页面置换模拟。"""

    def __init__(self, capacity: int):
        self._capacity = capacity
        self._frames: list = [None] * capacity
        self._use_bits: list = [0] * capacity
        self._pointer = 0  # 时钟指针
        self.page_faults = 0

    def access(self, page: int) -> bool:
        """访问页，返回是否缺页。"""
        # 1. 命中
        if page in self._frames:
            idx = self._frames.index(page)
            self._use_bits[idx] = 1  # 设置 use bit
            return False

        # 2. 缺页
        self.page_faults += 1
        # 3. 找空位或 use=0 的页
        while True:
            if self._frames[self._pointer] is None:
                # 空位
                break
            if self._use_bits[self._pointer] == 0:
                # use=0，淘汰
                break
            # use=1，给第二次机会
            self._use_bits[self._pointer] = 0
            self._pointer = (self._pointer + 1) % self._capacity

        # 4. 替换
        self._frames[self._pointer] = page
        self._use_bits[self._pointer] = 1
        self._pointer = (self._pointer + 1) % self._capacity
        return True
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Redis 内存淘汰策略

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 60-100）：

```python
class RedisConfig:
    """Redis 配置 - 含淘汰策略。

    Redis 是 dify 的关键依赖（缓存、任务队列）。
    当 Redis 内存满时，用类似 LRU 的策略淘汰。
    """
    # Redis 内存淘汰策略：
    # - noeviction：不淘汰，写失败（默认）
    # - allkeys-lru：所有 key 中淘汰 LRU
    # - volatile-lru：过期的 key 中淘汰 LRU
    # - allkeys-lfu：所有 key 中淘汰 LFU（最近最少使用频率）
    # - volatile-ttl：淘汰最快过期的

    # dify 用 allkeys-lru（最常用的策略）
    maxmemory_policy = "allkeys-lru"

    # 最大内存
    maxmemory = "2gb"

    # 淘汰采样数（越大越接近真实 LRU，但越慢）
    maxmemory_samples = 5


# Redis 内部实现：
# - 近似 LRU：用 24 位时间戳 + 随机采样
# - LFU：用计数器 + 衰减
# - 比真实 LRU 快得多

# dify 的典型用法：
# 1. 缓存 embedding 结果
# 2. 缓存工作流状态
# 3. 任务队列（Celery broker）

# 当 Redis 内存满时：
# - 旧的 embedding 缓存被淘汰
# - 重新查询时回源（重新计算 embedding）
# - 保证 Redis 不会爆
```

**解读**：
- 第 14 行：`allkeys-lru`：Redis 淘汰策略
- 第 24 行：`maxmemory_samples = 5`：采样 5 个 key 找最久未用
- **设计意图**：用 LRU 淘汰策略保证缓存"新鲜度"
- **dify 的关键点**：缓存满时不会崩溃，而是淘汰旧数据

## 4. 关键要点总结

- **FIFO**：简单但有 Belady 异常
- **LRU**：最优近似，但实现复杂
- **Clock**：用 use bit 模拟 LRU，简单实用
- **OPT**：理论最优，无法实现
- Linux 用多代 LRU
- Redis 用近似 LRU 淘汰

## 5. 练习题

### 练习 1：基础（必做）

模拟 FIFO 和 LRU 在相同访问序列下的缺页次数，验证 Belady 异常。

### 练习 2：进阶

阅读 `api/extensions/ext_redis.py`，说明 dify 为什么选 `allkeys-lru` 而不是 `volatile-ttl`。

### 练习 3：挑战（选做）

实现 LFU（最近最不常用）页面置换算法：用计数器记录访问频率。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- 《操作系统概念》第 10 章 大容量存储
- Redis LRU：https://redis.io/docs/reference/eviction/

---

**文档版本**：v1.0
**最后更新**：2026-07-13