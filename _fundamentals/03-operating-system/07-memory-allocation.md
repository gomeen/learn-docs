# 3.2.2 内存分配：malloc / 伙伴系统 / slab

> 内存分配器决定程序如何高效使用物理内存。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 malloc 内部的内存分配策略
- 掌握伙伴系统（Buddy System）和 slab 分配器
- 了解内存碎片的产生和解决
- 能在 dify 中识别内存分配的应用（Python pymalloc）

## 📚 前置知识

- 06-virtual-memory.md

## 1. 核心概念

### 1.1 内存分配的层次

```
用户程序 malloc(1024)
  ↓
C 库（glibc ptmalloc / jemalloc）
  ↓
系统调用 brk() / mmap()
  ↓
内核页分配器（伙伴系统）
  ↓
物理页框
```

### 1.2 连续内存分配

#### 首次适配（First Fit）

从头找第一个足够大的空闲块。

```
空闲链表：[5K][8K][12K][3K][10K]
请求 7K → 分配 8K 块
```

#### 最佳适配（Best Fit）

找最小但足够的空闲块。

```
空闲链表：[5K][8K][12K][3K][10K]
请求 7K → 分配 8K 块（最小但足够）
```

#### 最差适配（Worst Fit）

找最大的空闲块（避免碎片）。

```
空闲链表：[5K][8K][12K][3K][10K]
请求 7K → 分配 12K 块
```

### 1.3 外部碎片 vs 内部碎片

- **外部碎片**：空闲内存总和够，但不连续，无法满足大请求
- **内部碎片**：分配给进程的内存比实际需要的多

```
请求分配 5K，给了 8K → 内部碎片 3K

[已分配 5K] [空闲 1K] [已分配 5K] [空闲 1K]
总空闲 2K，但每个空闲块都 < 5K → 外部碎片
```

### 1.4 伙伴系统（Buddy System）

**思想**：所有块大小都是 2 的幂次，分配和合并简单。

```
分配 100KB（实际给 128KB）：
找 128KB 块 → 没有
找 256KB 块 → 找到 → 切成两个 128KB（伙伴）
分配一个 128KB

合并时只需检查"伙伴"是否也空闲
```

**优点**：
- 合并简单（O(1)）
- 外部碎片少

**缺点**：
- 内部碎片（50% 最坏）

**应用**：Linux 内核页分配器

### 1.5 Slab 分配器

**问题**：伙伴系统粒度太大（页级），不适合小对象。

**Slab 思路**：
- 从伙伴系统分配大块（页）
- 切成等大的"对象"
- 维护**空闲对象链表**

```
分配 50 字节（实际给 64 字节对象）：
[slab 池] → 64B 对象 × 1000
[已分配] [空闲] [已分配] [空闲] [空闲] ...
                ↑ 分配这里
```

**优点**：
- 内部碎片少
- 分配/释放 O(1)
- 适合内核对象（task_struct、inode）

### 1.6 glibc malloc（ptmalloc）

**结构**：
```
arena（分配区）
├── bin[]（空闲链表数组）
│   ├── fastbins（小对象 < 128B）
│   ├── smallbins（小对象）
│   ├── largebins（大对象）
│   └── unsorted bin（临时）
└── top chunk（剩余）
```

**分配流程**：
1. < 128B → fastbin（不合并）
2. < 64KB → bin（合并）
3. ≥ 64KB → mmap 系统调用

### 1.7 Python 的 pymalloc

CPython 也用类似的"pool"机制：
- 每次从 OS 申请 256KB（4 个 64KB 的"arena"）
- 切成 8 字节倍数的"pool"（4KB）
- 再切成"block"（对象）

## 2. 代码示例

### 2.1 简单 malloc 模拟

```python
# 文件：simple_malloc.py
from typing import Optional

class SimpleMalloc:
    """简单内存分配器（首次适配）。"""

    def __init__(self, total_size: int = 1024):
        self._memory = bytearray(total_size)
        self._free_blocks = [(0, total_size)]  # (起始地址, 大小)

    def malloc(self, size: int) -> Optional[int]:
        """分配 size 字节，返回地址。"""
        for i, (addr, block_size) in enumerate(self._free_blocks):
            if block_size >= size:
                # 找到合适的块
                allocated_addr = addr
                # 剩余部分重新加入空闲链表
                remaining = block_size - size
                if remaining > 0:
                    self._free_blocks[i] = (addr + size, remaining)
                else:
                    del self._free_blocks[i]
                return allocated_addr
        return None  # 分配失败

    def free(self, addr: int, size: int) -> None:
        """释放 addr 开始的 size 字节。"""
        self._free_blocks.append((addr, size))
        self._free_blocks.sort()  # 按地址排序

    def stats(self) -> dict:
        """统计信息。"""
        total_free = sum(size for _, size in self._free_blocks)
        num_blocks = len(self._free_blocks)
        return {
            "total_free": total_free,
            "num_blocks": num_blocks,
            "max_free": max((s for _, s in self._free_blocks), default=0),
        }

# 测试
m = SimpleMalloc(1024)
a = m.malloc(100)
b = m.malloc(200)
print(f"a={a}, b={b}")
print(f"stats: {m.stats()}")
```

### 2.2 伙伴系统模拟

```python
# 文件：buddy_system.py
from typing import Optional

class BuddySystem:
    """伙伴系统分配器。"""

    def __init__(self, total_kb: int = 1024):
        # 块大小必须是 2 的幂
        self._max_order = total_kb.bit_length() - 1
        # 每个 order 的空闲链表
        self._free_lists: list[list[int]] = [[] for _ in range(self._max_order + 1)]
        # 初始：整个内存作为一个最大块
        self._free_lists[self._max_order].append(0)

    def _addr_to_order(self, addr: int, order: int) -> int:
        """根据地址找伙伴。"""
        # 伙伴地址 = addr XOR block_size
        block_size = 1 << order
        return addr ^ block_size

    def alloc(self, size_kb: int) -> Optional[int]:
        """分配 size_kb KB。"""
        # 找最合适的 order
        order = (size_kb - 1).bit_length()
        if order > self._max_order:
            return None

        # 找可用块
        for o in range(order, self._max_order + 1):
            if self._free_lists[o]:
                # 取出一个块
                addr = self._free_lists[o].pop()
                # 切分直到合适的 order
                while o > order:
                    o -= 1
                    buddy = addr + (1 << o)
                    self._free_lists[o].append(buddy)
                return addr
        return None

    def free(self, addr: int, order: int) -> None:
        """释放 addr 处的 order 大小的块。"""
        # 尝试合并伙伴
        while order < self._max_order:
            buddy = self._addr_to_order(addr, order)
            if buddy in self._free_lists[order]:
                # 伙伴空闲，合并
                self._free_lists[order].remove(buddy)
                addr = min(addr, buddy)
                order += 1
            else:
                break
        self._free_lists[order].append(addr)

# 测试
bs = BuddySystem(1024)
a = bs.alloc(100)  # 实际给 128KB
b = bs.alloc(200)  # 实际给 256KB
print(f"a={a}, b={b}")
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Python 对象内存（pymalloc）

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/embedding/cached_embedding.py`
**核心代码**（行 1-40）：

```python
import sys
from typing import Any

# dify 用 Python 对象存储 embedding 向量
# 每个向量是 1536 维 float（OpenAI ada-002）
# 实际占用：1536 * 8 = 12KB（每个 float 8 字节）

class CachedEmbedding:
    """Embedding 缓存 - 大量 Python 对象。"""

    def __init__(self, max_size: int = 1000):
        # 存储 1000 个 embedding，每个 12KB
        # 总内存：~12MB
        self._cache: dict[str, list[float]] = {}

    def get_memory_usage(self) -> dict:
        """统计内存使用（用 sys.getsizeof）。"""
        total = 0
        for key, vec in self._cache.items():
            total += sys.getsizeof(key) + sys.getsizeof(vec)
            # 注意：list 本身只是指针数组，实际数据更大
        return {
            "total_bytes": total,
            "num_cached": len(self._cache),
            "avg_bytes_per_vec": total / len(self._cache) if self._cache else 0,
        }


# Python 内存管理的层次：
# 1. CPython 对象（小对象 < 512B）→ pymalloc（slab-like）
# 2. CPython 对象（大对象）→ 系统 malloc（glibc ptmalloc）
# 3. 大数组 → mmap 系统调用
#
# dify 的 embedding 向量（12KB）→ 走系统 malloc → ptmalloc → buddy system

# 内存优化建议：
# - 用 numpy 数组代替 list（连续内存，更快）
# - 用 __slots__ 减少对象内存（避免 dict）
# - 定期清理大对象（gc.collect()）
```

**解读**：
- 第 11 行：每个 embedding 占 12KB，走系统 malloc
- **Python 内存层次**：pymalloc（小对象）→ 系统 malloc（glibc）→ 伙伴系统
- **设计意图**：dify 缓存大量 embedding，需要关注内存使用

## 4. 关键要点总结

- **内存分配策略**：首次适配、最佳适配、最差适配
- **伙伴系统**：2 的幂大小块，合并简单（Linux 页分配）
- **Slab**：对象池，适合小对象（内核对象）
- **glibc malloc**：fastbin + smallbin + largebin + mmap
- Python pymalloc 类似 slab 思路
- dify 用 Python 缓存 embedding，注意内存使用

## 5. 练习题

### 练习 1：基础（必做）

用 Python 模拟首次适配和最佳适配，对比碎片率。

### 练习 2：进阶

阅读 `api/core/rag/embedding/cached_embedding.py`，说明 dify 缓存 embedding 时如何避免内存泄漏。

### 练习 3：挑战（选做）

实现 Slab 分配器：从大块中分配等大小对象，维护空闲链表。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/embedding/cached_embedding.py`
- 《操作系统概念》第 9 章 虚拟内存
- glibc malloc 内部：https://sourceware.org/glibc/wiki/MallocInternals

---

**文档版本**：v1.0
**最后更新**：2026-07-13