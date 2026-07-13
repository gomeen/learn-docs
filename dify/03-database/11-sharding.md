# 3.2.5 分库分表与读写分离

> 在单库优化仍不足时，用明确路由键拆分容量与吞吐，并正视跨分片和副本延迟的代价。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分垂直拆分、水平分片和分区
- 选择稳定且分布均匀的分片键
- 理解读写分离的一致性与故障切换
- 辨认 dify 中任务分片与数据库物理分片的边界

## 📚 前置知识

- [3.1.5 SQL 性能优化](./05-sql-performance.md)
- 一致性哈希与复制的基本概念

## 1. 核心概念

### 1.1 三种拆分不要混淆

垂直拆分按业务域拆库；水平分片把同一表的行分到多个节点；数据库分区仍在一个逻辑表/集群内。分片会把 JOIN、唯一约束、事务和迁移变成分布式问题，因此应在单库索引、归档、分区和缓存之后考虑。

### 1.2 分片键

好分片键应高基数、分布均匀，并出现在大部分查询中。多租户系统常以 `tenant_id` 路由，但超级租户可能造成热点。哈希分片均匀，范围分片便于时间清理，但容易出现尾部热点。

### 1.3 读写分离

写入主库、读取副本能扩展读吞吐，但复制通常异步。刚写后读可能看不到数据；登录、安全校验和写后确认应读主库，允许陈旧的报表/列表才适合副本。

> dify 当前常规模型查询使用统一 `db.engine`。源码中的 `run_shard` 是归档任务的工作划分，不等于数据库已经物理分片。

## 2. 代码示例

### 2.1 确定性哈希路由

```python
from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class Shard:
    primary_url: str
    replica_url: str


SHARDS = [
    Shard("postgresql://primary-0/app", "postgresql://replica-0/app"),
    Shard("postgresql://primary-1/app", "postgresql://replica-1/app"),
    Shard("postgresql://primary-2/app", "postgresql://replica-2/app"),
    Shard("postgresql://primary-3/app", "postgresql://replica-3/app"),
]


def route(tenant_id: str, *, write: bool) -> str:
    digest = sha256(tenant_id.encode()).digest()
    shard = SHARDS[int.from_bytes(digest[:8], "big") % len(SHARDS)]
    return shard.primary_url if write else shard.replica_url


print(route("tenant-a", write=True))
print(route("tenant-a", write=False))
```

**说明**：同一租户稳定落到同一分片；示例只演示路由，生产还要处理扩容重映射、连接池、事务和副本延迟。

## 3. dify 仓库源码解读

### 3.1 归档任务的确定性逻辑分片表达式

**文件位置**：`/Users/xu/code/github/dify/api/repositories/sqlalchemy_api_workflow_run_repository.py`  
**核心代码**（行 104-115）：

```python
    conditions = [tenant_prefix_condition(WorkflowRun.tenant_id, prefix) for prefix in prefixes]
    return sa.or_(*conditions)


def _workflow_run_id_shard_expr() -> sa.ColumnElement[int]:
    normalized_id = func.lower(func.replace(sa.cast(WorkflowRun.id, sa.String()), "-", ""))
    last_hex = func.substr(normalized_id, func.length(normalized_id), 1)
    return sa.case(
        *[(last_hex == hex_digit, shard_value) for hex_digit, shard_value in _HEX_SHARD_VALUES.items()],
        else_=0,
    )

```

**解读**：
- 代码规范化 UUID 并取最后一个十六进制字符。
- `CASE` 把十六进制字符映射为 0-15，用于稳定划分批处理任务。
- 这是查询工作分片，不负责把数据路由到不同数据库。

### 3.2 把分片条件下推到批查询

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
- 查询始终保留时间范围、结束状态、排序和批量限制。
- 租户、工作流和任务分片条件按需追加。
- `expr % shard_total == shard_index` 让多个归档 worker 处理互不重叠的数据子集。

## 4. 关键要点总结

- 物理分片是高成本架构选择，不等于表分区或任务分片
- 分片键决定热点、查询路由和扩容成本
- 读写分离必须处理复制延迟和写后读一致性
- 先优化单库、归档和索引，再评估分片

## 5. 练习题

### 练习 1：基础（必做）

比较按 `tenant_id` 哈希和按创建时间范围分片的优缺点。

### 练习 2：进阶

列出五类必须读主库的请求和五类可读副本的请求。

### 练习 3：挑战（选做）

解释 dify 的 UUID 末位分片为何能并行归档，但为何不是数据库分库分表。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/repositories/sqlalchemy_api_workflow_run_repository.py`
- PostgreSQL 分区：https://www.postgresql.org/docs/current/ddl-partitioning.html
- PostgreSQL 热备读查询：https://www.postgresql.org/docs/current/hot-standby.html

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
