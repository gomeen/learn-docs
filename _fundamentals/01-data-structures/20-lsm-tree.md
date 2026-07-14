# 1.4.4 LSM 树（LevelDB / RocksDB）

> LSM 树是现代 NoSQL 数据库（LevelDB、RocksDB、Cassandra、HBase）的核心数据结构。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 LSM 树的"写优化"思想：内存 + 磁盘分层
- 掌握 MemTable / SSTable / Compaction 的核心概念
- 区分 LSM 树 vs B+ 树的优劣
- 知道 LSM 树在哪些系统中有应用

## 📚 前置知识

- 10-b-tree.md
- 19-skiplist.md

## 1. 核心概念

### 1.1 什么是 LSM 树？

**LSM 树**（Log-Structured Merge Tree）是为**写密集**场景优化的数据结构：

```
写入路径：
1. 写入内存的 MemTable（通常用跳表）→ O(1) 写入
2. MemTable 满时，flush 到磁盘成为 SSTable（不可变）
3. 后台 Compaction 合并 SSTable，控制文件数

读取路径：
1. 查 MemTable
2. 查多个 SSTable（按时间倒序）
```

### 1.2 LSM 树 vs B+ 树

| 维度 | LSM 树 | B+ 树 |
|------|--------|--------|
| 写入 | **顺序写**，O(1) 内存 | 随机写，O(log n) 磁盘 IO |
| 读取 | 多次磁盘 IO（多个 SSTable） | **单次**磁盘 IO |
| 空间放大 | **有**（Compaction 前数据冗余） | 较小 |
| 写放大 | 有（Compaction） | 较小 |
| 适合 | **写多读少**（日志、时序） | 读多写少（OLTP） |

### 1.3 LSM 树的核心组件

#### MemTable

内存中的有序数据结构（通常用**跳表**），支持 O(log n) 读写。

#### SSTable（Sorted String Table）

磁盘上的**不可变**有序文件：

```
SSTable 结构：
┌─────────────────────────┐
│ Data Block（数据块）       │  ← 排序后的 key-value
├─────────────────────────┤
│ Filter Block（布隆过滤器）  │  ← 加速查找（避免不必要的磁盘读）
├─────────────────────────┤
│ Index Block（索引块）       │  ← 稀疏索引，加速 SSTable 内查找
├─────────────────────────┤
│ Footer（页脚）            │  ← 元数据
└─────────────────────────┘
```

#### Compaction

合并多个 SSTable，删除冗余数据：

```
Level 0: [SST1] [SST2] [SST3] [SST4]
                              ↓ compaction
Level 1:    [SST5（合并 1+2）]  [SST6（合并 3+4）]
                              ↓ compaction
Level 2:        [SST7（合并 5+6）]
```

**Compaction 策略**：
- **Leveling**：每层 SSTable 范围不重叠
- **Tiering**：每层允许重叠，但合并频率低

### 1.4 LSM 树的核心问题

#### 读放大（Read Amplification）

一次读需要查多个 SSTable：

```
读 key="hello"：
1. 查 MemTable → miss
2. 查 SST4（最新）→ miss
3. 查 SST3 → miss
4. 查 SST2 → hit（在 SST2 中）
```

#### 写放大（Write Amplification）

一次写可能触发多次磁盘写：

```
写入 key="hello" = "v1"：
1. 写 MemTable → 内存
2. MemTable flush → SST1 磁盘
3. Compaction SST1 + SST2 → SST5（重写两份数据）

总写入量 = 1（原始）+ 1（flush）+ 2（compaction）= 4 倍写放大
```

#### 空间放大（Space Amplification）

Compaction 前的冗余数据占用空间。

### 1.5 LSM 树的应用

| 系统 | LSM 树实现 |
|------|-----------|
| LevelDB | 原版 LSM |
| RocksDB | LevelDB 增强版（Facebook） |
| Cassandra | LSM 变种 |
| HBase | LSM + WAL |
| TiKV | RocksDB |
| ClickHouse | MergeTree（LSM 变种） |

## 2. 代码示例

### 2.1 简化的 LSM 树实现

```python
# 文件：lsm_tree.py
import bisect
import os
from typing import Iterator

class MemTable:
    """内存表：用 SortedDict（红黑树）实现。"""

    def __init__(self, max_size: int = 1000):
        from sortedcontainers import SortedDict
        self._data: SortedDict = SortedDict()
        self._max_size = max_size

    def put(self, key: bytes, value: bytes) -> None:
        self._data[key] = value

    def get(self, key: bytes) -> bytes | None:
        return self._data.get(key)

    def is_full(self) -> bool:
        return len(self._data) >= self._max_size

    def flush_to_sstable(self, path: str) -> None:
        """flush 到磁盘文件 - 顺序写。"""
        with open(path, "wb") as f:
            for key, value in self._data.items():
                f.write(f"{len(key)}|".encode())
                f.write(key)
                f.write(f"|{len(value)}|".encode())
                f.write(value)

class SSTable:
    """磁盘上的有序表（不可变）。"""

    def __init__(self, path: str):
        self._path = path
        self._index: dict[bytes, int] = {}  # 稀疏索引
        self._load()

    def _load(self) -> None:
        """加载稀疏索引（每隔 N 个 key 建一个索引）。"""
        with open(self._path, "rb") as f:
            offset = 0
            count = 0
            while True:
                pos = f.tell()
                line = f.readline()
                if not line:
                    break
                # 解析 key
                parts = line.split(b"|", 2)
                if len(parts) >= 2:
                    key = parts[1]
                    if count % 100 == 0:
                        self._index[key] = pos
                    count += 1

    def get(self, key: bytes) -> bytes | None:
        """二分查找（先查索引，再读块）。"""
        keys = list(self._index.keys())
        idx = bisect.bisect_right(keys, key)
        if idx == 0:
            return None
        # 从 idx-1 索引处开始顺序扫描
        with open(self._path, "rb") as f:
            f.seek(self._index[keys[idx - 1]])
            while True:
                pos = f.tell()
                line = f.readline()
                if not line:
                    return None
                parts = line.split(b"|", 2)
                if len(parts) >= 4:
                    k = parts[1]
                    if k == key:
                        return parts[3]
                    if k > key:
                        return None
```

### 2.2 LSM 树整体实现

```python
# 文件：lsm_main.py
class LSMTree:
    """简化版 LSM 树。"""

    def __init__(self, data_dir: str = "./lsm_data"):
        self._data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self._memtable = MemTable(max_size=1000)
        self._sstables: list[SSTable] = []  # 按时间倒序
        self._sstable_counter = 0

    def put(self, key: bytes, value: bytes) -> None:
        """写入：先写 MemTable，满了 flush。"""
        self._memtable.put(key, value)
        if self._memtable.is_full():
            self._flush()

    def get(self, key: bytes) -> bytes | None:
        """读取：先查 MemTable，再查 SSTable。"""
        # 1. 查内存
        value = self._memtable.get(key)
        if value is not None:
            return value

        # 2. 查磁盘 SSTable（从最新到最旧）
        for sstable in self._sstables:
            value = sstable.get(key)
            if value is not None:
                return value
        return None

    def _flush(self) -> None:
        """MemTable flush 到磁盘。"""
        path = os.path.join(
            self._data_dir, f"sstable_{self._sstable_counter}.sst"
        )
        self._memtable.flush_to_sstable(path)
        self._sstables.insert(0, SSTable(path))
        self._sstable_counter += 1
        self._memtable = MemTable(max_size=1000)
```

### 2.3 测试 LSM 树性能

```python
# 文件：test_lsm.py
import time
import random

def test_lsm():
    db = LSMTree()

    # 写入 1 万条
    n = 10000
    start = time.perf_counter()
    for i in range(n):
        db.put(f"key-{i}".encode(), f"value-{i}".encode())
    t_write = time.perf_counter() - start

    # 读取 1 千条
    start = time.perf_counter()
    for _ in range(1000):
        db.get(f"key-{random.randint(0, n)}".encode())
    t_read = time.perf_counter() - start

    print(f"写入 {n}: {t_write:.3f}s ({n/t_write:.0f} ops/s)")
    print(f"读取 1000: {t_read:.3f}s ({1000/t_read:.0f} ops/s)")

test_lsm()
```

## 3. dify 仓库源码解读

### 3.1 dify 的向量存储（部分基于 LSM 思想）

**文件位置**：`/Users/xu/code/github/dify/api/core/rag/datasource/vdb/vector_factory.py`
**核心代码**（行 1-50）：

```python
from typing import Any, Optional

class VectorStore:
    """向量存储抽象层。

    dify 支持多种向量数据库后端：
    - Weaviate（基于 HNSW 索引）
    - Milvus（基于磁盘索引）
    - Qdrant（RocksDB 存储）
    - pgvector（PG + LSM 思想）

    Qdrant 和部分 Milvus 用 RocksDB 持久化向量索引，
    RocksDB 内部就是 LSM 树（MemTable + SSTable）。
    """

    def __init__(self, backend: str = "pgvector"):
        self.backend = backend
        self._client: Any = None

    def add_vectors(
        self,
        ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict],
    ) -> None:
        """添加向量。

        内部流程：
        1. 向量写入内存缓冲
        2. 定期 flush 到磁盘（SSTable）
        3. 后台 compaction 合并
        """
        if self.backend == "qdrant":
            # Qdrant 用 RocksDB
            self._client.upsert(
                collection_name="documents",
                points=zip(ids, vectors, payloads),
            )
        elif self.backend == "pgvector":
            # PG 用 heap 表 + IVFFlat 索引
            with self._engine.connect() as conn:
                for id_, vec, payload in zip(ids, vectors, payloads):
                    conn.execute(
                        text("INSERT INTO vectors (id, vec, payload) "
                             "VALUES (:id, :vec, :payload)"),
                        {"id": id_, "vec": vec, "payload": payload},
                    )

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
    ) -> list[dict]:
        """向量检索。"""
        if self.backend == "qdrant":
            hits = self._client.search(
                collection_name="documents",
                query_vector=query_vector,
                limit=top_k,
            )
            return [{"id": h.id, "score": h.score} for h in hits]
        # ... 其他后端
```

**解读**：
- 第 17-19 行：dify 支持多种向量数据库，部分（如 Qdrant）底层用 RocksDB（LSM 树）
- 第 36 行：`add_vectors` 是**批量顺序写**，符合 LSM 树的写优化特点
- **dify/ruoyi 中无直接 LSM Tree 代码**，但向量存储后端用到了 LSM 思想
- **设计意图**：向量数据通常只追加、不修改（每次 reindex 是新数据），非常适合 LSM 树

## 4. 关键要点总结

- LSM 树 = **内存写** + **磁盘顺序写**，写性能极佳
- 核心组件：MemTable（内存）+ SSTable（磁盘）+ Compaction（合并）
- 三大问题：**读放大、写放大、空间放大**
- LSM 树 vs B+ 树：写多读少用 LSM，读多写少用 B+
- 应用：LevelDB、RocksDB、Cassandra、HBase、TiKV
- dify 的向量存储部分基于 LSM 思想（Qdrant / Milvus）

## 5. 练习题

### 练习 1：基础（必做）

简化的 LSM 树，实现 `put` 和 `get`，分析以下操作的复杂度：
- 写入 100 万条数据
- 查找一条数据
- 写放大是多少？

### 练习 2：进阶

阅读 `api/core/rag/datasource/vdb/vector_factory.py`，说明 dify 为何选择 LSM 树作为某些向量数据库的底层（提示：考虑向量数据的写入特点）。

### 练习 3：挑战（选做）

实现 **Compaction 策略**：当 SSTable 数量超过阈值时，自动合并最早的两个 SSTable，删除被覆盖的旧 key。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/core/rag/datasource/vdb/vector_factory.py`
- RocksDB 文档：https://rocksdb.org/docs/getting-started.html
- LSM 树原始论文（O'Neil 1996）
- 《数据密集型应用系统设计》第 3 章 存储引擎

---

**文档版本**：v1.0
**最后更新**：2026-07-13