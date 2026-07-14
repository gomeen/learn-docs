# 2.3 MyISAM vs InnoDB 对比

> MyISAM 和 InnoDB 是 MySQL 最常见的两种存储引擎。理解它们的差异，能帮助你做出正确的技术选型。

## 🎯 学习目标

完成本文档后，你将能够：
- 对比 MyISAM 和 InnoDB 的特性差异
- 知道 MyISAM 的适用场景（只读报表）
- 知道 InnoDB 为何成为默认引擎
- 在 ruoyi 中识别默认引擎配置

## 📚 前置知识

- 06-innodb.md
- 事务概念（16-acid.md）

## 1. 核心概念

### 1.1 总览对比

| 特性 | MyISAM | InnoDB |
|------|--------|--------|
| 事务支持 | ❌ 不支持 | ✅ ACID |
| 行级锁 | ❌ 表级锁 | ✅ 行级锁 + 间隙锁 |
| 外键 | ❌ | ✅ |
| MVCC | ❌ | ✅ |
| 崩溃恢复 | ❌ 容易损坏 | ✅ redo log |
| 全文索引 | ✅ 内置 | ✅（MySQL 5.6+） |
| 地理空间 | ✅ | ✅ |
| 索引类型 | 非聚簇 | 聚簇 |
| 计数 COUNT(*) | O(1)（存了行数） | O(N)（需扫描） |
| 适用场景 | 只读报表、数据仓库 | 通用 OLTP |

### 1.2 MyISAM 的特点

**优点**：
- 简单、占用空间小
- COUNT(*) 极快
- 全文索引在 MySQL 5.6 之前是 MyISAM 独有
- 表压缩（MyISAMPACK）效果好

**缺点**：
- 不支持事务，并发写性能差（表锁）
- 崩溃后容易损坏
- 不支持外键约束

### 1.3 InnoDB 的特点

**优点**：
- 完整的事务支持（ACID）
- 行级锁 + MVCC，高并发读写
- 聚簇索引（数据即索引）
- 崩溃恢复能力强（WAL）

**缺点**：
- 比 MyISAM 占用更多空间
- COUNT(*) 较慢（除非有 WHERE 走索引）
- 索引设计要求更高

### 1.4 选型建议

```
OLTP（在线交易） → InnoDB  ← 绝大多数业务场景
只读 / 日志 / 报表 → MyISAM（极少使用）
历史数据归档 → Archive / MyISAM
```

## 2. 代码示例

### 2.1 对比示例：COUNT(*) 的差异

```sql
-- MyISAM 表 users_myisam
SELECT COUNT(*) FROM users_myisam;  -- O(1)：元数据存储了行数

-- InnoDB 表 users_innodb
SELECT COUNT(*) FROM users_innodb;  -- O(N)：需扫描聚簇索引
```

### 2.2 对比示例：并发写入

```python
# MyISAM：表级锁，写串行
# 事务 A 和事务 B 同时更新同一张表，A 未提交时 B 必须等待

# InnoDB：行级锁 + MVCC，并发高
# 事务 A 更新 id=1，事务 B 同时更新 id=2，互不阻塞
```

### 2.3 用 Python 演示锁的差异

```python
import threading
import time

# 模拟 MyISAM 表级锁
class MyISAMTable:
    def __init__(self):
        self._lock = threading.Lock()  # 全局锁
        self.rows = {}

    def update(self, id_, value):
        with self._lock:                 # 整个表串行
            time.sleep(0.1)
            self.rows[id_] = value


# 模拟 InnoDB 行级锁
class InnoDBTable:
    def __init__(self):
        self._row_locks: dict[int, threading.Lock] = {}
        self.rows = {}

    def update(self, id_, value):
        if id_ not in self._row_locks:
            self._row_locks[id_] = threading.Lock()
        with self._row_locks[id_]:       # 只锁单行
            time.sleep(0.1)
            self.rows[id_] = value


# InnoDB 并发更新不同行不会阻塞
innodb = InnoDBTable()
threads = [
    threading.Thread(target=innodb.update, args=(1, "A")),
    threading.Thread(target=innodb.update, args=(2, "B")),
]
[t.start() for t in threads]
[t.join() for t in threads]
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 默认使用 InnoDB

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/sql/postgresql/create_table.sql`（示例）
**核心代码**：

```sql
-- ruoyi 通用建表语句，使用 InnoDB 引擎
CREATE TABLE system_users (
    id BIGINT NOT NULL,
    username VARCHAR(30) NOT NULL,
    password VARCHAR(100) NOT NULL DEFAULT '',
    nickname VARCHAR(30) NOT NULL,
    status TINYINT NOT NULL DEFAULT 0,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uk_username (username)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COMMENT = '用户表';
```

**解读**：
- `ENGINE = InnoDB`：明确指定 InnoDB 引擎（虽然 MySQL 5.5+ 默认就是 InnoDB）
- `DEFAULT CHARSET = utf8mb4`：支持 emoji 和生僻字
- `UNIQUE KEY uk_username`：InnoDB 的二级索引
- **为什么不用 MyISAM**？ruoyi 是 OLTP 系统，需要事务、外键、并发写——MyISAM 完全不满足

## 4. 关键要点总结

- MyISAM 不支持事务、行锁、外键——不适合 OLTP
- InnoDB 是 MySQL 5.5+ 的默认引擎，支持完整 ACID
- InnoDB 的 COUNT(*) 较慢，但有 WHERE 时差异不大
- ruoyi 全部表使用 InnoDB

## 5. 练习题

### 练习 1：基础
查看你的 MySQL 数据库：`SHOW TABLE STATUS WHERE Engine='MyISAM'`，统计 MyISAM 表数量。

### 练习 2：进阶
在 ruoyi 中执行 `SHOW CREATE TABLE system_users\G`，确认引擎为 InnoDB。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/sql/`
- MySQL 官方文档：https://dev.mysql.com/doc/refman/8.0/en/storage-engines.html
- 《高性能 MySQL》第 1 章：MySQL 架构

---

**文档版本**：v1.0
**最后更新**：2026-07-13