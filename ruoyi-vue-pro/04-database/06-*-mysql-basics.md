# 小验证：MySQL 基础与设计

> 覆盖：
- [MySQL 基础](./01-mysql-basics.md)
- [事务与隔离级别](./02-mysql-transaction.md)
- [索引原理](./03-mysql-index.md)
- [慢查询](./04-mysql-slow-query.md)
- [三大范式](./05-normalization.md)
>
> 预计：45～75 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

先脱离 ORM，直接用 SQL 验证索引、事务与慢查询分析，再对照 ruoyi 表设计。

## 需求

在本地 MySQL（可用 ruoyi 的 SQL 初始化库）：

1. 选 `system_user` 或等价用户表，写：按用户名等值查、按 `create_time` 范围查的 SQL。
2. 对上述 SQL 做 `EXPLAIN`，记录是否走索引、type/rows 关键字段。
3. 开一个事务：更新一行但不提交；另一会话读同一行，观察在当前隔离级别下的读现象；结束后回滚。
4. 打开 slow query 相关配置（或 `EXPLAIN ANALYZE`），解释一条可能的慢查询原因。
5. 对照 ruoyi 某业务表（如订单/用户），指出主键、唯一键、租户字段设计如何满足范式/反范式权衡。

## 提示

- 勿在共享环境做长时间未提交事务。
- EXPLAIN 结果随数据量变化，重在会读。
- SQL 脚本目录：`{RUOYI}/sql/`。

## 验收标准

- [ ] 两条业务 SQL + EXPLAIN 结果留存
- [ ] 事务并发读现象有记录（隔离级别写明）
- [ ] 能解释至少 1 个索引命中/未命中原因
- [ ] 对一张 ruoyi 表的键设计有简短点评
- [ ] 不破坏本地数据（回滚或可恢复）

## 延伸（选做）

- 构造未走索引的模糊查询 `%xx`，对比改写。
- 用 `SHOW INDEX` 列出用户表索引。
