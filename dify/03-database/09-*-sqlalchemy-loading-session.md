# 小验证：加载策略、Session 与原生 SQL

> 覆盖：
> - [05-sqlalchemy-loading](./06-sqlalchemy-loading.md)
> - [06-sqlalchemy-session](./07-sqlalchemy-session.md)
> - [07-sqlalchemy-raw-sql](./08-sqlalchemy-raw-sql.md)
>
> 预计：30～50 分钟 · 本地练习

## 背景

N+1、Session 生命周期与参数化原生 SQL 是线上性能与安全的高频坑。本组在已有 Author/Book（或新建）上演示加载差异与安全 raw SQL。

## 需求

1. 演示一次 N+1：无 `selectinload`/`joinedload` 时的查询次数（可 `echo=True`），再改为 eager load，截取 SQL 日志关键几行到 `NOTES.md`。
2. 用 `with Session(...)` 明确：提交 / 回滚 / 关闭策略；人为制造一次未 commit 就读不到的情况（或写清为何当前策略不会发生）。
3. 用 `session.execute(text(...))` **参数绑定** 做一次查询；在 NOTES 用 2～3 行对比字符串拼接的风险。
4. 对照仓库 `api/extensions/ext_database.py`（或实际 Session 工厂），记一行：dify 如何拿 engine/session。

## 提示

- `selectinload` 与 `joinedload` 适用场景不同
- `text("... WHERE id = :id")` + `{"id": ...}`
- 不要在练习里连接生产库

## 验收标准

- [ ] 能指出 N+1 与 eager 的 SQL 日志差异
- [ ] Session 在 with 结束时的提交/关闭策略说得清
- [ ] raw SQL 使用绑定参数（无拼接用户输入）
- [ ] NOTES 含仓库 Session/engine 锚点

## 延伸（选做）

试 `subqueryload` 或 `raise` 加载策略，记一句适用场景。
