# 小验证：DDD 在 dify 中的分层

> 覆盖：
> - [01-ddd-in-dify](./01-ddd-in-dify.md)
>
> 预计：45～90 分钟 · 本地练习或改 dify 仓库

## 背景

dify 后端按 Controller → Service → Core/Domain 分层。本组只对应一篇项目文，验证目标是能在仓库里定位一层边界并做一次无行为破坏的小梳理。

## 需求

在 `/Users/xu/code/github/dify` 中完成（建议新建 git 分支，勿提交）：

1. 任选一个简单只读 API（例如 console 下某个 list/detail），画清调用链：controller 函数 → service → model/core。
2. 在 **不改变对外 JSON 契约** 的前提下，把 controller 里若存在的「明显业务判断」下沉到 service 一处小函数（若该入口已经很干净，则改为：为 service 抽一个纯函数 `_normalize_xxx` 并替换原内联逻辑）。
3. 在 PR 描述草稿（本地 `NOTES.md`）写清：哪层不该依赖 Flask `request`、哪层可以碰 ORM。

## 提示

- 入口参考：`/Users/xu/code/github/dify/api/controllers/`
- 服务层：`/Users/xu/code/github/dify/api/services/`
- 领域/core：`/Users/xu/code/github/dify/api/core/`
- 先读 `api/AGENTS.md` 中的分层约定

## 验收标准

- [ ] 书面调用链（5～15 行）路径正确，能对应到真实文件
- [ ] 代码改动编译/导入级无误；控制器不再新增业务分支（或说明为何无需改）
- [ ] `NOTES.md` 明确三层依赖方向
- [ ] 未改数据库 schema、未改外部 API 字段名

## 延伸（选做）

补充：标出该链路是否经过 Celery 或外部 HTTP，并说明为何放在该层。
