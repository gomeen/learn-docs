# 5.3 慢查询日志分析

> 慢查询日志是定位性能问题的"黑匣子"。学会分析慢查询日志，能快速找出性能瓶颈。

## 🎯 学习目标

完成本文档后，你将能够：
- 开启 PostgreSQL / MySQL 的慢查询日志
- 读懂慢查询日志的字段
- 用工具分析慢查询（pg_stat_statements / mysqldumpslow）
- 在 dify/ruoyi 中定位慢查询

## 📚 前置知识

- 22-explain.md
- 23-sql-optimization.md

## 1. 核心概念

### 1.1 慢查询日志是什么？

数据库自动记录所有执行时间超过阈值的 SQL，便于事后分析。

### 1.2 PostgreSQL 慢查询日志

**开启方式**：

```sql
-- postgresql.conf
log_min_duration_statement = 1000   -- 记录 > 1s 的 SQL
log_statement = 'all'                -- 记录所有 SQL（开发环境）
auto_explain.log_min_duration = 1000 -- 自动 EXPLAIN
```

**关键扩展**：`pg_stat_statements`
- 记录所有 SQL 的统计信息（执行次数、平均耗时、I/O 等）
- 聚合视图，不依赖日志

```sql
-- 启用 pg_stat_statements
CREATE EXTENSION pg_stat_statements;

-- 查询最耗时的 SQL
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC LIMIT 10;
```

### 1.3 MySQL 慢查询日志

**开启方式**：

```ini
# my.cnf
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow.log
long_query_time = 1      # 记录 > 1s 的 SQL
log_queries_not_using_indexes = 1
```

**分析工具**：`mysqldumpslow`

```bash
mysqldumpslow -s t /var/log/mysql/slow.log  # 按耗时排序
```

### 1.4 慢查询处理流程

```
1. 开启慢查询日志
   ↓
2. 收集慢查询样本
   ↓
3. 用工具聚合（pg_stat_statements / mysqldumpslow）
   ↓
4. EXPLAIN 分析
   ↓
5. 优化（建索引、改写 SQL）
   ↓
6. 验证效果
```

## 2. 代码示例

### 2.1 PostgreSQL 慢查询分析（pg_stat_statements）

```sql
-- 1. 启用扩展
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- 2. 重置统计
SELECT pg_stat_statements_reset();

-- 3. 等待一段时间后查询
SELECT
    substring(query, 1, 80) AS query_preview,
    calls,
    round(mean_exec_time::numeric, 2) AS avg_ms,
    round(total_exec_time::numeric, 2) AS total_ms,
    rows
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### 2.2 MySQL 慢查询分析

```bash
# 1. 查看慢查询是否开启
SHOW VARIABLES LIKE 'slow_query%';

# 2. 分析日志
mysqldumpslow -s t -t 10 /var/log/mysql/slow.log

# 输出示例：
# Count: 5  Time=3.20s (16s)  Lock=0.00s (0s)
#   SELECT * FROM messages WHERE conversation_id='N'
```

### 2.3 Python 慢查询监控

```python
import time
from contextlib import contextmanager

SLOW_THRESHOLD_MS = 1000

@contextmanager
def slow_query_monitor(query: str):
    """监控单条 SQL 的执行时间"""
    start = time.time()
    try:
        yield
    finally:
        elapsed_ms = (time.time() - start) * 1000
        if elapsed_ms > SLOW_THRESHOLD_MS:
            logger.warning(
                "Slow query detected",
                extra={
                    "query": query[:200],
                    "duration_ms": elapsed_ms,
                },
            )


# 使用
with slow_query_monitor("SELECT * FROM messages"):
    result = session.execute(text("SELECT * FROM messages"))
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的 SQL 日志（SQLAlchemy echo）

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_database.py`
**核心代码**：

```python
engine = create_engine(
    dify_config.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=10,
    # 开发环境可以开启 echo=True 打印所有 SQL
    # 生产环境不开启（影响性能）
    echo=dify_config.DEBUG,  # DEBUG = True 时打印 SQL
)
```

**解读**：
- `echo=True` 让 SQLAlchemy 打印所有 SQL（开发用）
- 生产环境依赖 PostgreSQL `log_min_duration_statement`
- **整体设计**：开发用 echo，生产用 PG 慢查询日志

### 3.2 ruoyi 的慢 SQL 监控

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-monitor/`
**核心代码**：

```java
@Aspect
@Component
public class SqlPerformanceMonitor {
    // 拦截慢 SQL
    @Around("execution(* javax.sql.DataSource.getConnection())")
    public Object monitorSql(ProceedingJoinPoint pjp) throws Throwable {
        long start = System.currentTimeMillis();
        try {
            return pjp.proceed();
        } finally {
            long cost = System.currentTimeMillis() - start;
            if (cost > 500) {  // > 500ms 记录
                log.warn("Slow SQL took {}ms", cost);
            }
        }
    }
}
```

**解读**：
- Spring AOP 拦截数据源连接
- 慢 SQL 自动记录到日志
- **整体设计**：用 AOP 自动监控，无需业务代码改动

## 4. 关键要点总结

- 慢查询日志是定位性能问题的关键
- PostgreSQL 用 `pg_stat_statements`，MySQL 用慢查询日志
- 阈值通常设 100-1000ms
- dify 用 SQLAlchemy echo + PG 日志，ruoyi 用 Spring AOP 监控
- 慢查询处理流程：记录 → 聚合 → EXPLAIN → 优化

## 5. 练习题

### 练习 1：基础
在你的数据库中执行：`SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 5;`

### 练习 2：进阶
为 dify 的 `Message` 查询设计一个慢查询监控点。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_database.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-monitor/`
- pg_stat_statements：https://www.postgresql.org/docs/current/pgstatstatements.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13