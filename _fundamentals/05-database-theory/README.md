# 05 - 数据库原理

> 超越 SQL 语法的底层原理。理解存储引擎、索引、事务才能设计高性能系统。

## 模块 5.1 关系数据库理论

- [ ] [1.1 关系模型：表 / 元组 / 属性 / 域](./01-relational-model.md)
- [ ] [1.2 关系代数：选择 / 投影 / 联接 / 除](./02-relational-algebra.md)
- [ ] [1.3 函数依赖与范式：1NF / 2NF / 3NF / BCNF](./03-normalization.md)
- [ ] [1.4 范式与反范式的权衡](./04-denormalization.md)

## 模块 5.2 存储引擎

- [ ] [2.1 数据库架构：连接器 / 解析器 / 优化器 / 执行器](./05-architecture.md)
- [ ] [2.2 InnoDB 存储引擎架构](./06-innodb.md)
- [ ] [2.3 MyISAM vs InnoDB 对比](./07-myisam-innodb.md)
- [ ] [2.4 PostgreSQL 存储原理](./08-postgres-storage.md)
- [ ] [2.5 存储格式：行存储 vs 列存储](./09-row-column-store.md)

## 模块 5.3 索引深入

- [ ] [3.1 索引的本质：数据结构的封装](./10-index-basics.md)
- [ ] [3.2 B+ 树索引原理（已学 01-data-structures）](./11-b-plus-tree.md)
- [ ] [3.3 聚簇索引 vs 非聚簇索引](./12-clustered-index.md)
- [ ] [3.4 联合索引与最左前缀](./13-composite-index.md)
- [ ] [3.5 Hash 索引](./14-hash-index.md)
- [ ] [3.6 全文索引：倒排索引](./15-fulltext-index.md)

## 模块 5.4 事务与并发

- [ ] [4.1 ACID 四大特性](./16-acid.md)
- [ ] [4.2 事务隔离级别：RU / RC / RR / Serializable](./17-isolation-levels.md)
- [ ] [4.3 MVCC 多版本并发控制](./18-mvcc.md)
- [ ] [4.4 锁机制：行锁 / 表锁 / 间隙锁](./19-locks.md)
- [ ] [4.5 死锁检测与解决](./20-deadlock-detection.md)
- [ ] [4.6 分布式事务：2PC / 3PC / TCC / Saga](./21-distributed-transaction.md)

## 模块 5.5 查询优化

- [ ] [5.1 EXPLAIN 执行计划](./22-explain.md)
- [ ] [5.2 SQL 优化技巧](./23-sql-optimization.md)
- [ ] [5.3 慢查询日志分析](./24-slow-query.md)

## 🎯 与 dify/ruoyi 关联

- **dify**：用 PostgreSQL + pgvector（向量存储）
- **ruoyi-vue-pro**：用 MySQL + MyBatis Plus
