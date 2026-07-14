# 3.2.3 内存分页 vs 分段

> 分页和分段是两种不同的内存管理方式，各有优劣。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解分页（Paging）和分段（Segmentation）的区别
- 掌握分段分页结合的方案
- 能在实际系统中识别两者的应用

## 📚 前置知识

- 06-virtual-memory.md
- 07-memory-allocation.md

## 1. 核心概念

### 1.1 分页（Paging）

**特点**：
- 固定大小的**页**（4KB）
- 物理内存也分成等大的**页框**
- 虚拟地址 = 页号 + 页内偏移

**优点**：
- 简单（硬件支持）
- 无外部碎片

**缺点**：
- 内部碎片（最后一页可能没满）
- 页大小不灵活

### 1.2 分段（Segmentation）

**特点**：
- 按**逻辑**划分（代码段、数据段、堆、栈）
- 每段大小可变
- 虚拟地址 = 段号 + 段内偏移

**优点**：
- 符合程序员视角
- 便于保护（每段独立权限）
- 便于共享

**缺点**：
- 外部碎片
- 段大小可变，分配复杂

### 1.3 分段 vs 分页对比

| 维度 | 分页 | 分段 |
|------|------|------|
| 单位 | 固定大小 | 可变大小 |
| 视角 | 物理 | 逻辑 |
| 碎片 | 内部碎片 | 外部碎片 |
| 共享 | 难 | 易 |
| 保护 | 难 | 易 |
| 硬件支持 | ✓ | ✗（复杂） |

### 1.4 分段 + 分页（现代方案）

**Intel x86 架构**：先分段，再分页

```
虚拟地址
  ↓
[段号][段内偏移]
   ↓    ↓
[段选择子] + [段基址]
   ↓
[线性地址 = 段基址 + 偏移]
   ↓
[页目录号][页号][页内偏移]
   ↓
物理地址
```

**为什么这样设计？**
- 分段提供**保护**（代码段只读，数据段可写）
- 分页提供**虚拟内存**（按页换入换出）

### 1.5 实际系统应用

**x86-64**：
- 段机制基本关闭（平坦模式）
- 主要靠分页（4 级页表）
- 段寄存器（CS、DS）保留用于权限检查

**ARM**：
- 类似 x86，支持段和页
- 现代 OS 用平坦模式（只分页）

## 2. 代码示例

### 2.1 分段模拟

```python
# 文件：segmentation_demo.py
from typing import Optional

class Segment:
    """段。"""
    def __init__(self, base: int, limit: int, perm: str = "RW"):
        self.base = base  # 起始物理地址
        self.limit = limit  # 段大小
        self.perm = perm  # 权限

class Segmentation:
    """分段内存管理。"""

    def __init__(self):
        # 段表：段号 → 段
        self._segments: dict[int, Segment] = {}

    def add_segment(self, seg_num: int, base: int, limit: int, perm: str) -> None:
        self._segments[seg_num] = Segment(base, limit, perm)

    def translate(self, seg_num: int, offset: int, access: str = "R") -> Optional[int]:
        """虚拟地址（段号+偏移）→ 物理地址。"""
        if seg_num not in self._segments:
            return None
        seg = self._segments[seg_num]
        if offset >= seg.limit:
            return None  # 越界
        # 权限检查
        if access not in seg.perm:
            return None  # 权限不足
        return seg.base + offset

# 测试：x86 风格的段
seg = Segmentation()
seg.add_segment(1, 0x1000, 0x1000, "RE")  # 代码段
seg.add_segment(2, 0x2000, 0x500, "RW")   # 数据段

print(f"代码段访问: {seg.translate(1, 0x100, 'R'):x}")   # 0x1100
print(f"数据段访问: {seg.translate(2, 0x200, 'W'):x}")   # 0x2200
print(f"越界: {seg.translate(1, 0x2000, 'R')}")           # None
```

### 2.2 分段 + 分页模拟

```python
# 文件：segment_paging_demo.py
class SegPagingSystem:
    """分段 + 分页内存管理（x86 风格）。"""

    def __init__(self, page_size: int = 4096):
        self._page_size = page_size
        # 段表：段号 → (页表基址, 段大小)
        self._segment_table: dict[int, tuple[dict, int]] = {}

    def add_segment(self, seg_num: int, pages: dict, limit: int) -> None:
        """pages: {页号: 物理页框}"""
        self._segment_table[seg_num] = (pages, limit)

    def translate(self, seg_num: int, offset: int) -> int:
        """段号 + 偏移 → 物理地址（先分段再分页）。"""
        if seg_num not in self._segment_table:
            raise ValueError("段不存在")

        page_table, limit = self._segment_table[seg_num]
        if offset >= limit:
            raise ValueError("越界")

        # 1. 分段：段内偏移 = offset
        # 2. 分页：把 offset 拆成页号 + 页内偏移
        page_num = offset // self._page_size
        page_offset = offset % self._page_size

        if page_num not in page_table:
            raise ValueError("缺页")

        # 3. 物理地址 = 物理页框 * 页大小 + 页内偏移
        frame = page_table[page_num]
        return frame * self._page_size + page_offset

# 测试
sys = SegPagingSystem(page_size=4096)
# 段 1：3 页（0→10, 1→11, 2→12）
sys.add_segment(1, {0: 10, 1: 11, 2: 12}, limit=4096 * 3)

print(f"段1偏移0: 物理 0x{sys.translate(1, 0):x}")
print(f"段1偏移4096: 物理 0x{sys.translate(1, 4096):x}")  # 跳到页 1
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Python 内存（分页机制）

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_database.py`
**核心代码**（行 50-90）：

```python
from sqlalchemy.pool import QueuePool

# Python 的内存管理：
# 1. Python 对象（小）→ pymalloc（按 size class 分页）
# 2. Python 对象（大）→ glibc malloc（伙伴系统）
# 3. 内存映射（mmap）→ 内核虚拟内存（分页）

# dify 的内存使用模式：
class MemoryConfig:
    """dify 的内存配置。"""

    # Python 对象大小：分页分配
    pymalloc_size_classes = [8, 16, 32, 64, 128, 256, 512]

    # 大对象（> 512B）：通过系统 malloc
    # mmap 阈值：256KB（glibc 默认）
    mmap_threshold = 256 * 1024

    # PostgreSQL 缓存：分页式缓存
    pg_shared_buffers = "256MB"  # 8KB 页

    @classmethod
    def estimate_memory(cls, num_vectors: int) -> dict:
        """估算向量存储的内存使用。"""
        # 每个 embedding 向量：1536 维 * 8 字节 = 12KB
        bytes_per_vec = 1536 * 8
        # 总内存
        total = num_vectors * bytes_per_vec
        return {
            "num_vectors": num_vectors,
            "total_mb": total / 1024 / 1024,
            "pages_4kb": total / 4096,  # 按 4KB 页计算
        }


# PostgreSQL 内部用 8KB 页：
# - 表数据：按 8KB 页存储
# - 索引：按 8KB 页存储
# - shared_buffers：缓存这些页
```

**解读**：
- 第 16 行：Python pymalloc 按 8 字节倍数分页
- 第 19 行：mmap 阈值 256KB
- 第 22 行：PG 页大小 8KB（vs Linux 4KB）
- **设计意图**：dify 用 Python 处理数据，理解内存分页有助于性能优化

## 4. 关键要点总结

- **分页**：固定大小页，简单，硬件支持好
- **分段**：按逻辑分，可变大小，便于保护共享
- **现代方案**：分段 + 分页结合（x86 风格）
- x86-64 主要靠分页（4 级页表），段机制基本关闭
- Python pymalloc 类似"分页"
- PostgreSQL 用 8KB 页

## 5. 练习题

### 练习 1：基础（必做）

对比分页和分段，画出两者的虚拟地址到物理地址的映射过程。

### 练习 2：进阶

阅读 `api/extensions/ext_database.py`，说明 PostgreSQL 的 8KB 页与 Linux 的 4KB 页的区别。

### 练习 3：挑战（选做）

实现一个完整的分段 + 分页系统，支持段表 + 多级页表。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_database.py`
- 《操作系统概念》第 9 章 虚拟内存
- x86 虚拟内存：Intel 手册卷 3

---

**文档版本**：v1.0
**最后更新**：2026-07-13