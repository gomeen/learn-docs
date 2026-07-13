# 03 - 数据库与 ORM

> Dify 使用 PostgreSQL + SQLAlchemy 2.x + Alembic，理解这三者是后端开发的核心能力。

## 前置依赖

- `01-fundamentals` 中的 SQL 基础

## 模块 3.1 SQL 基础

- [ ] [1.1 SQL 基础语法：SELECT / INSERT / UPDATE / DELETE](./01-sql-basics.md)
- [ ] [1.2 多表查询：JOIN / 子查询 / UNION](./02-sql-join.md)
- [ ] [1.3 索引原理：B+Tree / Hash / 覆盖索引](./03-sql-index.md)
- [ ] [1.4 事务与隔离级别：ACID / MVCC](./04-sql-transaction.md)
- [ ] [1.5 SQL 性能优化：EXPLAIN / 慢查询分析](./05-sql-performance.md)
- [ ] [1.6 PostgreSQL 特有功能：JSON / 数组 / GIN 索引](./06-postgresql-features.md)

## 模块 3.2 数据库设计

- [ ] [2.1 三大范式与反范式](./07-database-normalization.md)
- [ ] [2.2 主键、外键、唯一约束](./08-database-keys.md)
- [ ] [2.3 软删除与硬删除策略](./09-soft-delete.md)
- [ ] [2.4 乐观锁与悲观锁](./10-lock-strategy.md)
- [ ] [2.5 分库分表与读写分离](./11-sharding.md)

## 模块 3.3 SQLAlchemy 2.x

- [ ] [3.1 声明式映射与模型定义](./12-sqlalchemy-mapping.md)
- [ ] [3.2 查询 API：`select()` 表达式风格](./13-sqlalchemy-query.md)
- [ ] [3.3 关系映射：One-to-One / One-to-Many / Many-to-Many](./14-sqlalchemy-relations.md)
- [ ] [3.4 加载策略：`lazy` / `joined` / `selectinload` / `subquery`](./15-sqlalchemy-loading.md)
- [ ] [3.5 会话管理：`Session` 与 `with` 上下文](./16-sqlalchemy-session.md)
- [ ] [3.6 原生 SQL 与混合查询](./17-sqlalchemy-raw-sql.md)
- [ ] [3.7 dify 的 `TypeBase` 基类与模型规范](./18-typebase-model.md)
- [ ] [3.8 dify 多租户查询的 `tenant_id` 过滤实践](./19-multi-tenant-query.md)

## 模块 3.4 Alembic 数据库迁移

- [ ] [4.1 Alembic 基础：初始化与环境配置](./20-alembic-basics.md)
- [ ] [4.2 自动生成迁移脚本：`alembic revision --autogenerate`](./21-alembic-autogenerate.md)
- [ ] [4.3 数据迁移与回滚策略](./22-alembic-data-migration.md)
- [ ] [4.4 迁移的分支与合并](./23-alembic-branch.md)
- [ ] [4.5 dify 的迁移目录结构分析](./24-alembic-in-dify.md)

## 模块 3.5 向量数据库

- [ ] [5.1 向量检索基础：余弦相似度 / 向量空间](./25-vector-search.md)
- [ ] [5.2 pgvector：PostgreSQL 向量检索插件](./26-pgvector.md)
- [ ] [5.3 专用向量库：Milvus / Weaviate / Qdrant](./27-vector-databases.md)
- [ ] [5.4 dify 的向量库适配层](./28-vdb-in-dify.md)

## 🎯 dify 仓库对应位置

- Models：`/Users/xu/code/github/dify/api/models/`
- 模型基类：`/Users/xu/code/github/dify/api/models/base.py`
- 迁移脚本：`/Users/xu/code/github/dify/api/migrations/`
- 数据库配置：`/Users/xu/code/github/dify/api/extensions/ext_database.py`
- 向量库适配：`/Users/xu/code/github/dify/api/core/rag/datasource/vdb/`
