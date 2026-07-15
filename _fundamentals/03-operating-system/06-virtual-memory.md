# 3.2.1 虚拟内存与分页

> 虚拟内存让每个进程都"独占"巨大地址空间，是现代操作系统的基石。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解虚拟内存的设计动机
- 掌握分页机制（页表、TLB、缺页中断；与分段对比见 [08-paging-segmentation](./08-paging-segmentation.md)）
- 了解虚拟内存的换页（swap）原理（置换算法见 [09-page-replacement](./09-page-replacement.md)）
- 能在 dify 中识别虚拟内存的应用（数据库 Buffer Pool）

## 📚 前置知识

- 01-process.md
- 09-page-replacement.md（推荐）

## 1. 核心概念

### 1.1 为什么需要虚拟内存？

**问题 1：地址空间隔离**
- 进程 A 不能访问进程 B 的内存

**问题 2：内存不足**
- 程序大于物理内存怎么办？

**问题 3：内存碎片**
- 频繁分配/释放导致碎片

**虚拟内存的解决方案**：
- 给每个进程一个**独立的虚拟地址空间**
- 通过 **MMU（内存管理单元）** 映射到物理内存
- 物理内存不够时，**换页**到磁盘

### 1.2 分页机制

**核心思想**：把虚拟地址和物理地址都分成固定大小的**页**（page）。

```
虚拟地址                      物理地址
┌───────────────┐            ┌───────────────┐
│ 页号 | 页内偏移 │            │ 物理页框 | 偏移 │
└───────────────┘            └───────────────┘
       ↓                            ↑
       └──── 页表 MMU 映射 ─────────┘
```

**示例**：
```
虚拟地址 0x1234 → 页号 0x1，偏移 0x234
页表 [0x1] = 0x5000（物理页框 5）
物理地址 = 0x5000 + 0x234 = 0x5234
```

### 1.3 页表

**单级页表**：
```
页号 | 物理页框 | 有效位 | 保护位
  0  |    5    |   1   |  RW
  1  |    9    |   1   |  RW
  2  |   -     |   0   |  --  ← 未映射（缺页）
```

**多级页表**：节省内存（4 级页表，常见于 x86-64）

**倒排页表**：用一个固定大小的表表示所有物理页框

### 1.4 TLB（快表）

**问题**：每次访问内存都要查页表 → **慢**

**解决**：TLB（Translation Lookaside Buffer）缓存常用页表项

```
CPU 访问虚拟地址：
1. 先查 TLB（硬件）
   - 命中 → 直接得到物理地址（快）
   - 未命中 → 查页表（慢）
2. 查页表 → 更新 TLB
```

### 1.5 缺页中断

```
进程访问虚拟地址 → MMU 查页表
                  ↓
                 有效位 = 0 → 缺页中断（Page Fault）
                  ↓
   操作系统处理：
   1. 从磁盘加载缺失的页到物理内存
   2. 更新页表
   3. 重新执行指令
```

**缺页率**：缺页次数 / 访问次数，越低越好。

### 1.6 换页（Swap）

物理内存不足时：
1. 选一个物理页（淘汰）
2. 写回磁盘（如果修改过）
3. 加载新页到物理内存

**换页是慢操作**：磁盘 IO 比内存访问慢 1000 倍。

### 1.7 虚拟内存的优缺点

**优点**：
- 地址空间隔离（安全）
- 程序大于物理内存（虚拟性）
- 共享内存（不同进程的虚拟页映射到同一物理页）

**缺点**：
- 缺页开销大
- TLB miss 开销大
- 复杂的内存管理

## 2. 代码示例

### 2.1 模拟分页

```python
# 文件：paging_demo.py
from typing import Optional

class PageTable:
    """模拟分页系统。"""

    def __init__(self, num_pages: int):
        self._page_size = 4096  # 4KB 页
        self._page_table: list[dict] = [
            {"frame": None, "valid": False, "disk_addr": None}
            for _ in range(num_pages)
        ]
        self._next_frame = 0  # 下一个可用物理页框

    def translate(self, virtual_addr: int) -> Optional[int]:
        """虚拟地址 → 物理地址。"""
        page_num = virtual_addr // self._page_size
        offset = virtual_addr % self._page_size

        if page_num >= len(self._page_table):
            return None  # 越界

        entry = self._page_table[page_num]
        if not entry["valid"]:
            return None  # 缺页

        return entry["frame"] * self._page_size + offset

    def map_page(self, page_num: int, frame: int) -> None:
        """建立虚拟页到物理页框的映射。"""
        if page_num < len(self._page_table):
            self._page_table[page_num] = {
                "frame": frame,
                "valid": True,
                "disk_addr": None,
            }

    def allocate_page(self, page_num: int) -> int:
        """分配物理页框。"""
        frame = self._next_frame
        self._next_frame += 1
        self.map_page(page_num, frame)
        return frame

# 测试
pt = PageTable(num_pages=100)
pt.allocate_page(0)
pt.allocate_page(1)
print(f"虚拟 0x0000 → 物理 0x{pt.translate(0x0000):x}")
print(f"虚拟 0x1234 → 物理 0x{pt.translate(0x1234):x}")
```

### 2.2 TLB 模拟

```python
# 文件：tlb_demo.py
from collections import OrderedDict

class TLB:
    """TLB（快表）模拟：最近最少使用替换。"""

    def __init__(self, capacity: int = 16):
        self._capacity = capacity
        self._cache: OrderedDict[int, int] = OrderedDict()  # vpn → pfn
        self._hits = 0
        self._misses = 0

    def lookup(self, vpn: int) -> int | None:
        """查 TLB。"""
        if vpn in self._cache:
            self._hits += 1
            self._cache.move_to_end(vpn)  # LRU
            return self._cache[vpn]
        self._misses += 1
        return None

    def update(self, vpn: int, pfn: int) -> None:
        """更新 TLB。"""
        if vpn in self._cache:
            self._cache.move_to_end(vpn)
        else:
            if len(self._cache) >= self._capacity:
                self._cache.popitem(last=False)  # 淘汰最久未用
            self._cache[vpn] = pfn

    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / total if total > 0 else 0,
        }
```

## 3. dify 仓库源码解读

### 3.1 dify 的 PostgreSQL Buffer Pool（虚拟内存思想）

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_database.py`
**核心代码**（行 1-50）：

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

def setup_database(database_url: str):
    """配置数据库连接池。

    dify 用 SQLAlchemy 的 QueuePool（类似虚拟内存的"缓存"思想）：

    1. 连接池预创建 N 个数据库连接（类比"物理页框"）
    2. 查询时从池中取出连接（类比"TLB 命中"）
    3. 用完归还（类比"换页"）
    4. 池满了则等待或创建新连接

    这种连接池的设计：
    - 避免每次查询都创建连接（慢）
    - 控制并发连接数（防止数据库过载）
    - 类似虚拟内存的"页缓存"
    """
    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=20,         # 池大小
        max_overflow=10,      # 最大溢出
        pool_timeout=30,      # 获取连接超时
        pool_recycle=3600,    # 连接回收时间
    )
    return engine


# dify 的查询流程：
def get_user(user_id: str) -> dict:
    """获取用户信息 - 用连接池。"""
    with engine.connect() as conn:  # 从池中获取连接
        result = conn.execute(
            "SELECT * FROM users WHERE id = %s",
            (user_id,)
        )
        return result.fetchone()
    # 连接自动归还池中


# PostgreSQL 内部也用"虚拟内存"：
# - shared_buffers：缓存数据页（类似物理页框）
# - effective_cache_size：操作系统缓存（虚拟内存）
# - work_mem：排序等操作的内存
```

**解读**：
- 第 19 行：`pool_size=20`：连接池大小
- 第 20 行：`max_overflow=10`：超出时的最大创建数
- **设计意图**：连接池是数据库的"虚拟内存"，避免频繁创建连接
- **PG 内部也用虚拟内存**：`shared_buffers` 缓存数据页

## 4. 关键要点总结

- **虚拟内存**：进程独享地址空间，通过 MMU 映射到物理内存
- **分页**：固定大小页（4KB），通过页表映射
- **TLB**：缓存页表项，命中率高
- **缺页**：页不在物理内存，从磁盘加载
- **Swap**：物理内存不足时换页到磁盘
- dify 连接池 = 数据库的"虚拟内存"

## 5. 练习题

### 练习 1：基础（必做）

模拟页表：虚拟地址 `0x1234`，页大小 4KB，页表项 `1 → 5`，求物理地址。

### 练习 2：进阶

阅读 `api/extensions/ext_database.py`，说明 dify 的连接池如何体现"缓存/虚拟内存"思想。

### 练习 3：挑战（选做）

实现一个完整的 TLB + 页表模拟，支持 LRU 替换，统计命中率。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_database.py`
- 《操作系统概念》第 9 章 虚拟内存
- PostgreSQL 内存配置：https://www.postgresql.org/docs/current/runtime-config-resource.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13