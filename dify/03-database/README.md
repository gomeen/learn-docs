# 03 - 数据库与 ORM

> Dify 使用 PostgreSQL + SQLAlchemy 2.x + Alembic，理解这三者是后端开发的核心能力。
> **主路径**：全局顺序与「必读/延后」以 [`../LEARNING-PLAN.md`](../LEARNING-PLAN.md) 为准。
> 下方清单是**本分类素材目录**；未列入主计划的篇默认不读。需要做小验证时，优先做主计划点名的 `NN-*-*.md`。

## 🌐 公共部分

| 主题 | 公共文档 | 本项目特定 |
|------|----------|------------|
| SQL 实用与库表设计 | [`_common/21-sql`](../../_common/21-sql/) | PostgreSQL / SQLAlchemy / Alembic / 向量库 |
| 存储引擎 / MVCC 理论 | [`_fundamentals/05-database-theory`](../../_fundamentals/05-database-theory/) | — |

## 前置依赖

- SQL 通用：[`_common/21-sql`](../../_common/21-sql/)

## 模块 3.1 SQL 基础（公共）

- [ ] [1.1 SQL 基础语法：SELECT / INSERT / UPDATE / DELETE](../../_common/21-sql/01-sql-basics.md)
- [ ] [1.2 多表查询：JOIN / 子查询 / UNION](../../_common/21-sql/02-sql-join.md)
- [ ] [1.3 索引原理：B+Tree / Hash / 覆盖索引](../../_common/21-sql/03-sql-index.md)
- [ ] [1.4 事务与隔离级别：ACID / MVCC](../../_common/21-sql/04-sql-transaction.md)
- [ ] [1.5 SQL 性能优化：EXPLAIN / 慢查询分析](../../_common/21-sql/05-sql-performance.md)
- [ ] [1.6 PostgreSQL 特有功能：JSON / 数组 / GIN 索引](./01-postgresql-features.md)

## 模块 3.2 数据库设计（公共）

- [ ] [2.1 三大范式与反范式](../../_common/21-sql/06-normalization.md)
- [ ] [2.2 主键、外键、唯一约束](../../_common/21-sql/07-database-keys.md)
- [ ] [2.3 软删除与硬删除策略](../../_common/21-sql/08-soft-delete.md)
- [ ] [2.4 乐观锁与悲观锁](../../_common/21-sql/09-lock-strategy.md)
- [ ] [2.5 分库分表与读写分离](../../_common/21-sql/10-sharding.md)

## 模块 3.3 SQLAlchemy 2.x

- [ ] [3.1 声明式映射与模型定义](./02-sqlalchemy-mapping.md)
- [ ] [3.2 查询 API：`select()` 表达式风格](./03-sqlalchemy-query.md)
- [ ] [3.3 关系映射：One-to-One / One-to-Many / Many-to-Many](./04-sqlalchemy-relations.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [05-*-sqlalchemy-basics: PostgreSQL 特性与 SQLAlchemy 映射查询](./05-*-sqlalchemy-basics.md)
  - 覆盖：01-postgresql-features.md, 02-sqlalchemy-mapping.md, 03-sqlalchemy-query.md, 04-sqlalchemy-relations.md


- [ ] [3.4 加载策略：`lazy` / `joined` / `selectinload` / `subquery`](./06-sqlalchemy-loading.md)
- [ ] [3.5 会话管理：`Session` 与 `with` 上下文](./07-sqlalchemy-session.md)
- [ ] [3.6 原生 SQL 与混合查询](./08-sqlalchemy-raw-sql.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [09-*-sqlalchemy-loading-session: 加载策略、Session 与原生 SQL](./09-*-sqlalchemy-loading-session.md)
  - 覆盖：06-sqlalchemy-loading.md, 07-sqlalchemy-session.md, 08-sqlalchemy-raw-sql.md


- [ ] [3.7 dify 的 `TypeBase` 基类与模型规范](./10-typebase-model.md)
- [ ] [3.8 dify 多租户查询的 `tenant_id` 过滤实践](./11-multi-tenant-query.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [12-*-models-multitenant: TypeBase 与多租户查询](./12-*-models-multitenant.md)
  - 覆盖：10-typebase-model.md, 11-multi-tenant-query.md


## 模块 3.4 Alembic 数据库迁移

- [ ] [4.1 Alembic 基础：初始化与环境配置](./13-alembic-basics.md)
- [ ] [4.2 自动生成迁移脚本：`alembic revision --autogenerate`](./14-alembic-autogenerate.md)
- [ ] [4.3 数据迁移与回滚策略](./15-alembic-data-migration.md)
- [ ] [4.4 迁移的分支与合并](./16-alembic-branch.md)
- [ ] [4.5 dify 的迁移目录结构分析](./17-alembic-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [18-*-alembic: Alembic 迁移](./18-*-alembic.md)
  - 覆盖：13-alembic-basics.md, 14-alembic-autogenerate.md, 15-alembic-data-migration.md, 16-alembic-branch.md, 17-alembic-in-dify.md


## 模块 3.5 向量数据库

- [ ] [5.1 向量检索基础：余弦相似度 / 向量空间](./19-vector-search.md)
- [ ] [5.2 pgvector：PostgreSQL 向量检索插件](./20-pgvector.md)
- [ ] [5.3 专用向量库：Milvus / Weaviate / Qdrant](./21-vector-databases.md)
- [ ] [5.4 dify 的向量库适配层](./22-vdb-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [23-*-vector-db: 向量检索与 dify VDB 适配层](./23-*-vector-db.md)
  - 覆盖：19-vector-search.md, 20-pgvector.md, 21-vector-databases.md, 22-vdb-in-dify.md


## 🎯 dify 仓库对应位置

- Models：`/Users/xu/code/github/dify/api/models/`
- 模型基类：`/Users/xu/code/github/dify/api/models/base.py`
- 迁移脚本：`/Users/xu/code/github/dify/api/migrations/`
- 数据库配置：`/Users/xu/code/github/dify/api/extensions/ext_database.py`
- 向量库适配：`/Users/xu/code/github/dify/api/core/rag/datasource/vdb/`
