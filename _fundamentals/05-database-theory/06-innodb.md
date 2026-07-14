# 2.2 InnoDB 存储引擎架构

> InnoDB 是 MySQL 默认的事务型存储引擎。理解其架构是 MySQL 性能调优的前提。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 InnoDB 的内存结构（Buffer Pool、Change Buffer、Log Buffer）
- 掌握 InnoDB 的磁盘结构（表空间、redo log、undo log）
- 理解数据修改时各组件的协作流程
- 在 ruoyi 中识别 InnoDB 相关配置

## 📚 前置知识

- 05-architecture.md
- 事务概念（16-acid.md）

## 1. 核心概念

### 1.1 InnoDB 整体架构

```
┌─────────────────────────┐
│      MySQL Server        │
├─────────────────────────┤
│  连接器 / 解析器 / 优化器 │
├─────────────────────────┤
│      InnoDB 引擎         │
│ ┌─────────────────────┐ │
│ │   内存结构           │ │
│ │  Buffer Pool        │ │ ← 缓存数据页/索引页
│ │  Change Buffer      │ │ ← 缓存二级索引变更
│ │  Log Buffer         │ │ ← 缓存 redo log
│ │  Adaptive Hash Idx  │ │
│ └─────────────────────┘ │
│ ┌─────────────────────┐ │
│ │   磁盘结构           │ │
│ │  System Tablespace  │ │ ← ibdata1
│ │  File-Per-Table     │ │ ← .ibd
│ │  Redo Log           │ │ ← ib_logfile*
│ │  Undo Log           │ │
│ │  Doublewrite Buffer │ │
│ └─────────────────────┘ │
└─────────────────────────┘
```

### 1.2 内存结构

| 组件 | 大小（默认） | 作用 |
|------|-------------|------|
| Buffer Pool | 128 MB | 缓存数据页和索引页 |
| Change Buffer | 25% of BP | 缓存非唯一二级索引的变更 |
| Log Buffer | 16 MB | 缓冲 redo log 写入 |
| Adaptive Hash Index | BP 的一部分 | 自动哈希索引（热数据） |

### 1.3 磁盘结构

| 文件 | 作用 |
|------|------|
| ibdata1（系统表空间） | 存储数据字典、双写缓冲、undo log（默认） |
| .ibd（独占表空间） | 每个表的独立数据文件 |
| ib_logfile0/1（redo log） | 崩溃恢复 |
| undo log | MVCC、回滚 |

### 1.4 数据修改流程（WAL）

```
UPDATE users SET name='X' WHERE id=1
  │
  ├─> 1. 加载数据页到 Buffer Pool
  ├─> 2. 修改 Buffer Pool 中的页（脏页）
  ├─> 3. 写 undo log（旧版本，用于回滚/MVCC）
  ├─> 4. 写 redo log（物理日志，用于崩溃恢复）
  ├─> 5. 写 binlog（逻辑日志，用于主从复制）
  └─> 6. 后台线程 checkpoint 把脏页刷盘
```

**WAL（Write-Ahead Logging）**：先写日志再写数据，保证持久性。

## 2. 代码示例

### 2.1 Buffer Pool 模拟

```python
from collections import OrderedDict
from typing import Any

class BufferPool:
    """简化的 Buffer Pool（LRU 淘汰）"""

    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.cache: OrderedDict[int, dict] = OrderedDict()  # page_id → page

    def get_page(self, page_id: int) -> dict:
        """读页：缓存命中直接返回，否则从磁盘加载"""
        if page_id in self.cache:
            self.cache.move_to_end(page_id)
            return self.cache[page_id]
        page = self._load_from_disk(page_id)
        if len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)  # 淘汰最久未用
        self.cache[page_id] = page
        return page

    def update_page(self, page_id: int, data: dict) -> None:
        """修改页：先改内存，标脏页（异步刷盘）"""
        self.get_page(page_id).update(data)
        # 实际中会标记 dirty=True，等待 checkpoint 刷盘

    def _load_from_disk(self, page_id: int) -> dict:
        return {"page_id": page_id, "data": f"row_{page_id}"}


# 使用
pool = BufferPool(capacity=3)
pool.update_page(1, {"name": "Alice"})  # 加载 + 修改
pool.update_page(2, {"name": "Bob"})
print(pool.get_page(1))  # 缓存命中
```

### 2.2 WAL 写日志模拟

```python
import time

class WAL:
    """Write-Ahead Log 简化版"""
    def __init__(self):
        self.log: list[tuple[float, str, str]] = []  # (timestamp, op, data)

    def append(self, op: str, data: str) -> None:
        """先写日志"""
        self.log.append((time.time(), op, data))

    def apply_to_disk(self) -> None:
        """checkpoint 时刷盘"""
        # 实际中会调用 fsync
        print(f"刷盘 {len(self.log)} 条日志")
        self.log.clear()

    def recover(self) -> None:
        """崩溃恢复：重做所有日志"""
        for ts, op, data in self.log:
            print(f"恢复: {op} {data}")


wal = WAL()
wal.append("UPDATE", "users SET name='X' WHERE id=1")
wal.append("INSERT", "orders (...)")
wal.apply_to_disk()
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的 MySQL InnoDB 配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`
**核心代码**（行 1-40）：

```java
@AutoConfiguration
public class YudaoMybatisAutoConfiguration {

    /**
     * 数据源配置（连接 MySQL / PostgreSQL）
     */
    @Bean
    @Primary
    public DataSource dataSource(DataSourceProperties properties) {
        HikariDataSource dataSource = new HikariDataSource();
        dataSource.setJdbcUrl(properties.getUrl());
        dataSource.setUsername(properties.getUsername());
        dataSource.setPassword(properties.getPassword());
        // 连接池配置——对应 InnoDB 的"连接器"
        dataSource.setMaximumPoolSize(20);
        dataSource.setMinimumIdle(5);
        dataSource.setConnectionTimeout(30000);
        return dataSource;
    }
}
```

**解读**：
- 使用 HikariCP 连接池——管理 MySQL 连接（对应连接器）
- `MaximumPoolSize=20`——InnoDB 服务端还会有自己的连接线程
- **整体设计**：应用层连接池 + 服务端 InnoDB 共同管理连接资源

## 4. 关键要点总结

- InnoDB 是 MySQL 默认的事务型存储引擎
- 内存结构（Buffer Pool）+ 磁盘结构（表空间、redo log、undo log）
- WAL：先写日志再写数据，保证持久性
- Change Buffer 优化二级索引写入
- ruoyi 使用 HikariCP 连接池管理 MySQL 连接

## 5. 练习题

### 练习 1：基础
执行 `SHOW ENGINE INNODB STATUS`，查看 Buffer Pool 命中率。

### 练习 2：进阶
阅读 ruoyi 的 `yudao-spring-boot-starter-mybatis` 模块，分析它如何配置 MySQL 连接池。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-spring-boot-starter-mybatis/`
- MySQL 官方文档：https://dev.mysql.com/doc/refman/8.0/en/innodb-architecture.html
- 《MySQL 技术内幕：InnoDB 存储引擎》第 2 章

---

**文档版本**：v1.0
**最后更新**：2026-07-13