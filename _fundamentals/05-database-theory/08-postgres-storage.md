# 2.4 PostgreSQL 存储原理

> PostgreSQL 是 dify 的默认数据库。其 MVCC、TOAST、Heap-Only Tuple 等机制与 MySQL InnoDB 有显著差异。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 PostgreSQL 的存储结构（Heap 表、TOAST）
- 理解 PostgreSQL 的 MVCC 实现（xmin/xmax）
- 知道 WAL 在 PostgreSQL 中的作用
- 在 dify 中识别 PostgreSQL 的特殊数据类型

## 📚 前置知识

- 05-architecture.md
- 18-mvcc.md

## 1. 核心概念

### 1.1 PostgreSQL 物理存储

```
表（Heap File）
├── 每个表/索引对应一个或多个文件
├── 默认 1 GB 切分（pg_relation_filepath）
└── 行格式：HeapTuple（包含 xmin/xmax 系统列）

特殊表空间
├── TOAST：大字段（>2KB）单独存储
├── FSM（Free Space Map）：可用空间追踪
└── VM（Visibility Map）：可见性位图（加速 VACUUM）

WAL（Write-Ahead Log）
├── pg_wal/ 目录下的 WAL 文件
└── 默认 16 MB 一个文件
```

### 1.2 Heap Tuple 的隐藏列

每张表的行（HeapTuple）都有 6 个隐藏列：

| 列 | 类型 | 说明 |
|----|------|------|
| `xmin` | xid | 插入此行的事务 ID |
| `xmax` | xid | 删除此行的事务 ID（0 表示未删除） |
| `cmin` | int | 插入命令 ID（同一事务内的版本） |
| `cmax` | int | 删除命令 ID |
| `tableoid` | oid | 表的 OID |
| `ctid` | tid | 行物理位置（块号+块内偏移） |

### 1.3 PostgreSQL MVCC 特点

**与 MySQL InnoDB 的差异**：
- MySQL：回滚段（Undo Log）存储旧版本
- PostgreSQL：直接在 Heap 中保留旧版本（多版本并存）

**优点**：读不阻塞写、写不阻塞读
**缺点**：需要 VACUUM 清理死元组（Dead Tuple）

### 1.4 TOAST

超过 2 KB 的字段（TEXT、BYTEA、JSON 等）会被自动"烤"到 TOAST 表：
- TOAST 是后台透明完成的
- 支持压缩和外部存储

## 2. 代码示例

### 2.1 查看表的物理文件

```sql
-- 查看表对应的文件路径
SELECT pg_relation_filepath('accounts');
-- 输出：base/16384/16385

-- 查看表大小
SELECT pg_size_pretty(pg_total_relation_size('accounts'));

-- 查看隐藏列
SELECT xmin, xmax, ctid, * FROM accounts LIMIT 1;
```

### 2.2 演示 MVCC 的多版本

```python
# 模拟 PostgreSQL 的 Heap Tuple
class HeapTuple:
    def __init__(self, data: dict, xmin: int, xmax: int = 0):
        self.xmin = xmin          # 插入事务
        self.xmax = xmax          # 删除事务（0 = 仍可见）
        self.data = data

# 同一行的不同版本同时存在于 Heap 中
heap = []
heap.append(HeapTuple({"name": "Alice", "age": 30}, xmin=100))
heap.append(HeapTuple({"name": "Alice", "age": 31}, xmin=105))  # UPDATE 后的新版本

# 事务 110 SELECT 时，根据活跃事务快照决定看哪个版本
```

### 2.3 死元组与 VACUUM

```python
# PostgreSQL 的 UPDATE 不直接修改原行，而是插入新版本、标记旧版本 xmax
# 死元组（Dead Tuple）需要 VACUUM 清理

# 查看死元组比例
dead_tuple_sql = """
SELECT schemaname, relname,
       n_live_tup, n_dead_tup,
       round(100 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_ratio
FROM pg_stat_user_tables
WHERE n_dead_tup > 0
ORDER BY n_dead_tup DESC;
"""
```

## 3. dify 仓库源码解读

### 3.1 dify 使用 PostgreSQL + pgvector

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_database.py`
**核心代码**（行 1-40）：

```python
from sqlalchemy import create_engine

from configs import dify_config

# 默认 PostgreSQL——支持 JSONB、pgvector 等高级特性
engine = create_engine(
    dify_config.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    json_serializer=None,  # 使用 PostgreSQL 原生 JSONB
)

# SQLAlchemy 2.0 风格的 session
db = scoped_session(sessionmaker(bind=engine))
```

**配置文件**（`/Users/xu/code/github/dify/api/configs/middleware/__init__.py`）：

```python
# PostgreSQL + pgvector 是 dify 的默认配置
SQLALCHEMY_DATABASE_URI = os.getenv(
    "DB_CONNECTION_STRING",
    "postgresql+psycopg2://postgres:difyai123456@localhost:5432/dify",
)
```

**解读**：
- 默认使用 PostgreSQL（不是 MySQL）——因为需要 `JSONB`、`pgvector`（向量检索）
- `pgvector` 用于 RAG（检索增强生成）场景的向量相似度搜索
- **整体架构**：PostgreSQL 同时承担业务库 + 向量库双重角色

### 3.2 dify 的 JSONB 字段

**文件位置**：`/Users/xu/code/github/dify/api/models/model.py`
**核心代码**（行 30-60）：

```python
from sqlalchemy.dialects.postgresql import JSONB

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(36), index=True)
    inputs: Mapped[dict] = mapped_column(JSONB)   # PostgreSQL 原生 JSONB
    answer: Mapped[str] = mapped_column(Text)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
```

**解读**：
- 第 7 行：`JSONB` 是 PostgreSQL 特有类型，支持 JSON 索引和 GIN 查询
- 比 MySQL 的 JSON 类型更强大（可索引、可函数计算）
- 这是 dify 选择 PostgreSQL 的关键原因之一

## 4. 关键要点总结

- PostgreSQL 用 Heap 表 + 隐藏列（xmin/xmax）实现 MVCC
- 旧版本直接保留在 Heap 中，需要 VACUUM 清理死元组
- TOAST 自动处理大字段（>2KB）
- dify 选择 PostgreSQL 是因为 JSONB + pgvector
- ruoyi 也支持 PostgreSQL（通过 MyBatis Plus 的方言适配）

## 5. 练习题

### 练习 1：基础
查看 dify 的 `accounts` 表：`SELECT xmin, xmax, * FROM accounts LIMIT 1`，观察隐藏列。

### 练习 2：进阶
执行 `VACUUM ANALYZE messages`，观察死元组数量变化。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_database.py`
- `/Users/xu/code/github/dify/api/models/model.py`
- PostgreSQL 官方文档：https://www.postgresql.org/docs/current/storage.html
- 《PostgreSQL 实战》第 4 章：存储结构

---

**文档版本**：v1.0
**最后更新**：2026-07-13