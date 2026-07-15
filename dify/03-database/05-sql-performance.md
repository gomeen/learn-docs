# 3.1.5 SQL 性能优化：EXPLAIN / 慢查询分析

> 从执行计划而不是直觉出发，定位扫描、连接、排序和数据量估算中的真正瓶颈。

## 🎯 学习目标

完成本文档后，你将能够：
- 读懂 EXPLAIN 的节点、成本、估算行数
- 安全使用 EXPLAIN ANALYZE 与 BUFFERS
- 识别 N+1、全表扫描、大排序和无界分页
- 能联系 dify 查询与索引判断优化方向

## 📚 前置知识

- [3.1.3 索引原理](./03-sql-index.md)
- [3.1.4 事务与隔离级别](./04-sql-transaction.md)

## 1. 核心概念

### 1.1 执行计划是树

计划从叶子扫描数据，再经过 Join、Sort、Aggregate 等节点向上产出结果。`cost=a..b` 是优化器估算，不是毫秒；`rows` 是估算基数。估算与 `actual rows` 差异很大时，应检查统计信息和数据倾斜。

### 1.2 EXPLAIN ANALYZE 的关键字段

`ANALYZE` 会真实执行语句；对写语句必须包在可回滚事务中。重点看：
- `actual time` 与 `loops`：节点真实耗时及执行次数；
- `Buffers`：缓存命中与磁盘读取；
- `Rows Removed by Filter`：扫描后丢弃过多；
- Sort Method：是否发生磁盘排序。

### 1.3 优化顺序

先减少数据量和查询次数，再考虑索引与 SQL 细节。常见顺序是：消除 N+1 → 增加正确过滤 → 选择必要列 → 调整索引 → 验证计划。优化前后应使用相同参数与近似生产数据。

## 2. 代码示例

### 2.1 用执行计划比较查询路径

```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL,
    action TEXT NOT NULL
);

CREATE INDEX audit_tenant_time_idx
ON audit_logs (tenant_id, created_at DESC);

EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id, created_at, action
FROM audit_logs
WHERE tenant_id = '00000000-0000-0000-0000-000000000001'
  AND created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
ORDER BY created_at DESC
LIMIT 50;
```

**说明**：在测试库执行并观察是否使用复合索引、估算行数是否接近实际值，以及读取了多少缓冲页。

## 3. dify 仓库源码解读

### 3.1 避免加载实体的 COUNT 查询

**文件位置**：`/Users/xu/code/github/dify/api/models/dataset.py`  
**核心代码**（行 214-230）：

```python
    @property
    def total_documents(self):
        return db.session.scalar(select(func.count(Document.id)).where(Document.dataset_id == self.id)) or 0

    @property
    def total_available_documents(self):
        return (
            db.session.scalar(
                select(func.count(Document.id)).where(
                    Document.dataset_id == self.id,
                    Document.indexing_status == "completed",
                    Document.enabled == True,
                    Document.archived == False,
                )
            )
            or 0
        )
```

**解读**：
- 这里只查询 `count(Document.id)`，不会把文档对象及大字段加载到 Python。
- 状态、启用和归档条件在数据库侧尽早过滤。
- 若该属性在列表中逐个调用，仍可能形成 N+1，需要在上层批量聚合（ORM 加载策略详见 [加载策略](./15-sqlalchemy-loading.md)）。

### 3.2 面向索引的游标批处理

**文件位置**：`/Users/xu/code/github/dify/api/repositories/sqlalchemy_api_workflow_run_repository.py`  
**核心代码**（行 454-482）：

```python
            stmt = (
                select(WorkflowRun)
                .where(
                    WorkflowRun.created_at < end_before,
                    WorkflowRun.status.in_(WorkflowExecutionStatus.ended_values()),
                )
                .order_by(WorkflowRun.created_at.asc(), WorkflowRun.id.asc())
                .limit(batch_size)
            )
            if run_types is not None:
                if not run_types:
                    return []
                stmt = stmt.where(WorkflowRun.type.in_(run_types))

            if start_from:
                stmt = stmt.where(WorkflowRun.created_at >= start_from)

            if tenant_ids:
                stmt = stmt.where(WorkflowRun.tenant_id.in_(tenant_ids))

            if tenant_prefixes:
                stmt = stmt.where(_tenant_prefix_condition(tenant_prefixes))

            if workflow_ids:
                stmt = stmt.where(WorkflowRun.workflow_id.in_(workflow_ids))

            if run_shard_index is not None and run_shard_total is not None:
                stmt = stmt.where((_workflow_run_id_shard_expr() % run_shard_total) == run_shard_index)

```

**解读**：
- 查询按 `created_at, id` 排序并限制批量大小，避免一次加载全部归档记录。
- 各种可选条件按需追加，能尽早缩小扫描范围。
- 第 481-482 行把工作分片条件下推到 SQL，减少每个 worker 读取的数据。

## 4. 关键要点总结

- 执行计划的节点、基数和循环次数比 SQL 外观更重要
- EXPLAIN ANALYZE 会实际执行，写语句需谨慎
- 先减少查询次数与数据量，再调索引
- 所有优化都要在代表性数据和参数上复测

## 5. 练习题

### 练习 1：基础（必做）

对一个带 WHERE 和 ORDER BY 的查询执行 `EXPLAIN (ANALYZE, BUFFERS)` 并标注最慢节点。

### 练习 2：进阶

构造一个 N+1 查询，再改成 JOIN 或批量查询。

### 练习 3：挑战（选做）

分析 dify 的归档批查询需要哪些复合索引，并与模型定义核对。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/dataset.py`
- `/Users/xu/code/github/dify/api/repositories/sqlalchemy_api_workflow_run_repository.py`
- PostgreSQL EXPLAIN：https://www.postgresql.org/docs/current/sql-explain.html
- PostgreSQL 执行计划：https://www.postgresql.org/docs/current/using-explain.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
