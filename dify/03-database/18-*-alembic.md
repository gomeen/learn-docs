# 小验证：Alembic 迁移

> 覆盖：
> - [10-alembic-basics](./13-alembic-basics.md)
> - [11-alembic-autogenerate](./14-alembic-autogenerate.md)
> - [12-alembic-data-migration](./15-alembic-data-migration.md)
> - [13-alembic-branch](./16-alembic-branch.md)
> - [14-alembic-in-dify](./17-alembic-in-dify.md)
>
> 预计：60～90 分钟 · 本地练习或改 dify 仓库

## 背景

Schema 变更必须可重复、可回滚。验证：读懂 dify 迁移目录，并生成一份**不会真正提交到主干**的练习迁移草稿。

## 需求

1. 阅读 `/Users/xu/code/github/dify/api/migrations/` 结构与近期一份迁移，在 `NOTES.md` 说明 upgrade/downgrade 做了什么。
2. 在本地分支：为某练习用表或**可空新列**起草迁移（`alembic revision` 手写即可）；`downgrade` 必须完整。
3. 若不能连真实 PG，仍需保证迁移脚本语法完整，并说明你将如何 dry-run。
4. 写清数据迁移与纯 schema 迁移的区别（结合文档 12）。

## 提示

- `api/migrations/env.py`
- 禁止在练习中对共享环境强制 upgrade
- 可空列 / 默认值策略优先，避免锁表长事务（概念写在 NOTES）

## 验收标准

- [ ] `NOTES.md` 解读 1 份真实迁移
- [ ] 新迁移含成对的 upgrade/downgrade
- [ ] 说明如何回滚
- [ ] 未把本地 alembic 版本强推到公共数据库

## 延伸（选做）

模拟：先加可空列 → 回填数据迁移 → 再改非空，分三步迁移的理由。
