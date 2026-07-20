# 21 - SQL 与库表设计（工程向）

> 能写对 SQL、会做表设计与分片选型。  
> 存储引擎、B+Tree、MVCC、隔离级别实现等 **Mastery** 在 [`../../_fundamentals/05-database-theory/`](../../_fundamentals/05-database-theory/)。

## 📐 分层

| 内容 | 归属 |
|------|------|
| 关系代数、范式理论细节、InnoDB/PG 存储、索引结构、MVCC、锁实现 | `_fundamentals/05-database-theory` |
| SQL 语法、实用索引/事务、软删、乐观锁、分片选型 | **本分类** |

## 知识点

- [ ] [1.1 SQL 基础：SELECT / INSERT / UPDATE / DELETE](./01-sql-basics.md) ← **本层 Mastery**
- [ ] [1.2 多表查询：JOIN / 子查询 / UNION](./02-sql-join.md)
- [ ] [1.3 索引（工程用法）](./03-sql-index.md) · 结构原理见 [fundamentals 索引](../../_fundamentals/05-database-theory/10-index-basics.md)
- [ ] [1.4 事务（工程用法）](./04-sql-transaction.md) · ACID/MVCC 见 [fundamentals 事务](../../_fundamentals/05-database-theory/16-acid.md)
- [ ] [1.5 SQL 性能优化（工程）](./05-sql-performance.md) · 亦见 [EXPLAIN](../../_fundamentals/05-database-theory/22-explain.md)
- [ ] [1.6 范式与反范式（工程权衡）](./06-normalization.md) · 理论见 [fundamentals 范式](../../_fundamentals/05-database-theory/03-normalization.md)
- [ ] [1.7 主键、外键、唯一约束](./07-database-keys.md)
- [ ] [1.8 软删除与硬删除](./08-soft-delete.md) ← **本层 Mastery**
- [ ] [1.9 乐观锁与悲观锁（应用）](./09-lock-strategy.md) · 锁机制见 [fundamentals 锁](../../_fundamentals/05-database-theory/19-locks.md)
- [ ] [1.10 分库分表与读写分离](./10-sharding.md) ← **本层 Mastery**

## 🔗 项目特定

- **dify**：PostgreSQL / SQLAlchemy / Alembic → [`../../dify/03-database/`](../../dify/03-database/)
- **ruoyi**：MyBatis Plus → [`../../ruoyi-vue-pro/04-database/`](../../ruoyi-vue-pro/04-database/)
