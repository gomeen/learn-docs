# 小验证：Flask 基础与 RESTX

> 覆盖：
> - [02-flask-basics](./03-flask-basics.md)
> - [03-flask-context](./04-flask-context.md)
> - [04-flask-blueprint](./05-flask-blueprint.md)
> - [05-flask-restx](./06-flask-restx.md)
>
> 预计：30～50 分钟 · 本地练习或改 dify 仓库

## 背景

路由、上下文、Blueprint 与 Flask-RESTX 是 dify Controller 外壳的基础。本组先把「注册一个 Resource + 读 request/g」跑通，钩子与错误体系统一放到下一组。

## 需求

在 `/Users/xu/code/github/dify` 改动（本地分支），或等价本地 Flask 小应用：

1. 在现有 console Blueprint/Namespace 下新增**仅本地调试用**的只读端点，例如 `GET /console/api/dev/ping-learning`（路径按项目前缀调整）。
2. 返回 JSON：`{"ok": true, "path": <request.path>, "has_g": <bool>}`；`has_g` 表示能否安全访问 Flask `g`（不必强行写字段）。
3. 用 Flask-RESTX `Resource` + 装饰器注册（与邻近端点风格一致）；若本地小应用则用等价 Blueprint + Resource。
4. 手测：curl 正常 200；`NOTES.md` 记 3 行：Blueprint 名、Namespace、路由装饰器位置。

## 提示

- `api/app_factory.py`、`api/controllers/console/`
- 观察现有 Resource 类与 `RESOURCE_MODULES` 导入
- 不必在本组处理统一错误 JSON（见 [11-*-flask-hooks-errors](./11-*-flask-hooks-errors.md)）

## 验收标准

- [ ] 新端点可 curl 通（或本地 app 可跑）
- [ ] 响应含 `ok` 与 path/`g` 相关信息
- [ ] 注册方式与项目现有 RESTX 模式一致（或 NOTES 写清等价结构）
- [ ] 改动集中、无无关重构；不提交密钥

## 延伸（选做）

为端点补 query 参数模型（Pydantic Query 后缀）并在 Swagger 可见（若环境允许）。
