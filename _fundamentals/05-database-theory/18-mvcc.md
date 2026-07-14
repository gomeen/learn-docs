# 4.3 MVCC 多版本并发控制

> MVCC（Multi-Version Concurrency Control）是现代数据库实现高并发的核心技术。PostgreSQL 和 MySQL InnoDB 的实现差异显著。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 MVCC 的核心思想（多版本共存）
- 掌握 PostgreSQL 的 MVCC 实现（xmin/xmax）
- 掌握 MySQL InnoDB 的 MVCC 实现（Undo Log + Read View）
- 知道 MVCC 如何解决读-写冲突

## 📚 前置知识

- 16-acid.md
- 17-isolation-levels.md

## 1. 核心概念

### 1.1 MVCC 的核心思想

```
同一行数据在不同时间点有不同的"版本"：

时间轴：  tx1 BEGIN          tx2 BEGIN         tx1 COMMIT
          │                   │                   │
          ├─ INSERT row(v1) ──→│                   │
          │                   ├─ UPDATE row(v2) ───→│
          │                   │                   │
          │ SELECT 看到 v2（最新已提交版本）       │
```

**读不阻塞写，写不阻塞读**——这是 MVCC 的核心优势。

### 1.2 PostgreSQL MVCC

**机制**：
- 每行有隐藏列 `xmin`（插入事务）、`xmax`（删除事务）
- UPDATE = 插入新行 + 标记旧行 xmax
- DELETE = 设置 xmax，不物理删除

**快照（Snapshot）**：
- 事务开始时获取快照（活跃事务列表）
- SELECT 时根据 xmin/xmax + 快照判断可见性

**问题**：
- 表膨胀（死元组）→ 需要 VACUUM 清理
- UPDATE 频繁的表容易膨胀

### 1.3 MySQL InnoDB MVCC

**机制**：
- Undo Log 存储旧版本
- Read View 决定可见性
- ReadView = 当前活跃事务 ID 列表 + min/max

**Read View 规则**：
- `trx_id < min_trx_id` → 可见
- `trx_id > max_trx_id` → 不可见
- 中间状态：看是否在活跃事务列表中

### 1.4 PostgreSQL vs InnoDB MVCC 对比

| 维度 | PostgreSQL | InnoDB |
|------|-----------|--------|
| 旧版本位置 | Heap 中 | Undo Log |
| UPDATE | 插入新行，原行标记 xmax | 标记旧行 + Undo Log |
| 清理 | VACUUM | Purge 线程 |
| 回滚 | 标记 xmax 即可 | 需 Undo Log 回滚 |
| 表膨胀 | 较严重 | 较轻 |

## 2. 代码示例

### 2.1 PostgreSQL MVCC 模拟

```python
class PGHeapTuple:
    def __init__(self, data: dict, xmin: int):
        self.xmin = xmin
        self.xmax = 0
        self.data = data

class PGHeap:
    """PostgreSQL 风格的堆表 MVCC"""

    def __init__(self):
        self.tuples: list[PGHeapTuple] = []
        self.active_txns: set[int] = set()
        self.next_txn_id = 1

    def begin_txn(self) -> int:
        txn_id = self.next_txn_id
        self.next_txn_id += 1
        self.active_txns.add(txn_id)
        return txn_id

    def commit_txn(self, txn_id: int) -> None:
        self.active_txns.discard(txn_id)

    def insert(self, txn_id: int, data: dict) -> None:
        self.tuples.append(PGHeapTuple(data, xmin=txn_id))

    def update(self, txn_id: int, old_data: dict, new_data: dict) -> None:
        # 1. 找到匹配行
        for tup in self.tuples:
            if tup.data == old_data and tup.xmax == 0:
                tup.xmax = txn_id           # 标记删除
                break
        # 2. 插入新版本
        self.insert(txn_id, new_data)

    def select(self, txn_id: int) -> list[dict]:
        """MVCC：根据 xmin/xmax + 活跃事务判断可见性"""
        visible = []
        for tup in self.tuples:
            # xmin 已提交且 xmax 未提交（或无 xmax）
            if tup.xmin not in self.active_txns:
                if tup.xmax == 0 or tup.xmax not in self.active_txns:
                    visible.append(tup.data)
        return visible
```

### 2.2 MVCC 解决读-写冲突

```python
# 场景：tx1 读，tx2 同时写，互不阻塞

# tx1
tx1 = heap.begin_txn()
data = heap.select(tx1)  # 读快照（不会因为 tx2 的写而阻塞）

# tx2 同时执行
tx2 = heap.begin_txn()
heap.update(tx2, old, new)  # 写不阻塞
heap.commit_txn(tx2)

# tx1 仍然看到 tx2 提交前的数据（快照隔离）
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 用 PostgreSQL MVCC（PG 默认行为）

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_database.py`
**核心代码**：

```python
# PostgreSQL MVCC 自动启用——每个事务有独立快照
engine = create_engine(
    dify_config.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=10,
    # PostgreSQL 默认 RC 隔离级别，每个 SELECT 自动获取快照
)
```

**解读**：
- dify 不需要额外配置 MVCC——PG 默认行为
- 同一事务内的多次 SELECT，看到的是事务开始时的快照（取决于隔离级别）

### 3.2 ruoyi 用 InnoDB MVCC（自动）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/`
**核心代码**：

```java
// InnoDB 默认 RR 隔离级别——MVCC 通过 Undo Log + Read View 实现
@Service
public class UserService {
    @Transactional(readOnly = true)
    public AdminUserDO getUser(Long id) {
        return userMapper.selectById(id);
    }
}
```

**解读**：
- `@Transactional(readOnly = true)` 提示 InnoDB 优化（无 Undo Log 写入）
- InnoDB 自动维护 Read View
- ruoyi 的多个查询在同一事务内保证可重复读

## 4. 关键要点总结

- MVCC = 多版本共存，实现读不阻塞写
- PostgreSQL：Heap 中存多版本，靠 VACUUM 清理
- InnoDB：Undo Log 存旧版本，靠 Purge 清理
- dify 用 PG MVCC，ruoyi 用 InnoDB MVCC
- 都需要定期清理（VACUUM / Purge）否则表膨胀

## 5. 练习题

### 练习 1：基础
在 PostgreSQL 中：开启两个事务，一个 UPDATE 不提交，另一个 SELECT，观察是否能读到新值。

### 练习 2：进阶
执行 `VACUUM messages`，观察死元组数量变化。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_database.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/`
- PostgreSQL MVCC：https://www.postgresql.org/docs/current/mvcc.html
- 《PostgreSQL 实战》第 9 章：多版本并发控制

---

**文档版本**：v1.0
**最后更新**：2026-07-13