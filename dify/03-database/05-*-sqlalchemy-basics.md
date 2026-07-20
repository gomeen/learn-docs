# 小验证：PostgreSQL 特性与 SQLAlchemy 映射查询

> 覆盖：
> - [01-postgresql-features](./01-postgresql-features.md)
> - [02-sqlalchemy-mapping](./02-sqlalchemy-mapping.md)
> - [03-sqlalchemy-query](./03-sqlalchemy-query.md)
> - [04-sqlalchemy-relations](./04-sqlalchemy-relations.md)
>
> 预计：30～50 分钟 · 本地练习

## 背景

SQLAlchemy 2.x 声明式模型与 `select()` 是 dify ORM 日常。本组先在本地引擎（SQLite 也可）建一对多模型并完成基本读写；加载策略与 Session 细则见下一组。

## 需求

1. 本地用 SQLAlchemy 2.x 建两个模型 `Author` / `Book`（一对多），字段含 `id`、时间戳。
2. 使用 `Session` 上下文写入样例数据；用 `select()` 查询某作者的书并打印结果。
3. 对照 `/Users/xu/code/github/dify/api/models/` 任选一模型，在 `NOTES.md` 记录：主键类型、是否软删除、关系定义方式（不必跑迁移）。
4. （可选）在 NOTES 记一条 PostgreSQL 特性与 SQLite 差异（JSON/数组/GIN 任选其一，可只写认知不必跑 PG）。

## 提示

- `DeclarativeBase` / `Mapped` / `mapped_column` / `relationship`
- 仓库：`api/models/base.py`
- 查询用 `select()` 风格，避免遗留 `Query` API

## 验收标准

- [ ] 本地脚本可创建表、插入、查询
- [ ] 一对多关系可从 Author 拿到 Book 列表（或反向）
- [ ] `NOTES.md` 对照至少 1 个 dify 模型字段/关系
- [ ] 代码可重复运行（或明确 drop/create 策略）

## 延伸（选做）

为 `Book` 加唯一约束或复合索引，观察建表 DDL。
