# 小验证：TypeBase 与多租户查询

> 覆盖：
> - [08-typebase-model](./10-typebase-model.md)
> - [09-multi-tenant-query](./11-multi-tenant-query.md)
>
> 预计：45～75 分钟 · 本地练习或改 dify 仓库

## 背景

dify 模型基类与 `tenant_id` 过滤是数据隔离的底线。验证：读懂基类，并写出带租户过滤的查询改动或复现。

## 需求

在 `/Users/xu/code/github/dify`：

1. 阅读 `api/models/base.py`（及常用 mixin），整理 TypeBase/基类提供的公共字段与方法到 `NOTES.md`。
2. 找一处 list 查询，确认是否过滤 `tenant_id`；若已有，写清过滤点；若你发现测试代码里有未过滤示例，记录风险。
3. 做一个**安全的**小改动：为某查询补充显式 `tenant_id == ...`（若已存在则改为抽取 `_tenant_filter(stmt, tenant_id)` 纯函数并复用一处），避免行为变化。

## 提示

- `api/models/base.py`
- 服务层查询中的 `tenant_id`
- 切勿在无鉴权上下文硬编码租户

## 验收标准

- [ ] `NOTES.md` 列出基类关键字段 ≥ 3 个
- [ ] 指出至少 1 条真实查询的租户过滤位置
- [ ] 改动不扩大查询结果范围（无越权）
- [ ] 有前后 SQL 或代码 diff 说明

## 延伸（选做）

讨论：为何不能只靠前端传 tenant_id？（写 3 条）
