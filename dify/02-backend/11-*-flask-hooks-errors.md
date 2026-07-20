# 小验证：Flask 钩子、错误处理与 dify Controller

> 覆盖：
> - [06-flask-hooks](./08-flask-hooks.md)
> - [07-flask-error-handling](./09-flask-error-handling.md)
> - [08-flask-in-dify](./10-flask-in-dify.md)
>
> 预计：30～50 分钟 · 本地练习或改 dify 仓库

## 背景

`before_request` / 错误处理器决定 request_id 与统一错误 JSON 形态。本组在 [07-*-flask-core](./07-*-flask-core.md) 的端点之上，把可追踪字段与非法参数错误体做齐。

## 需求

在 `/Users/xu/code/github/dify` 改动（本地分支）：

1. 为调试端点（可复用 07-*-flask-core 的 `ping-learning`，或新建等价路由）保证响应含可追踪字段：`request_id` 从 `g` 读取；若项目已有中间件/钩子则复用，否则**仅在本 Blueprint 小范围** `before_request` 设置。
2. 要求 query `n` 为整数；非法输入返回**项目一致**的错误 JSON（复用现有 error handler / 异常类，不要裸 `abort(400)` 后格式不一致）。
3. 手测或最小测试：正常 200（含 request 相关字段）、非法 `n` 得 4xx 且 body 结构统一。
4. `NOTES.md` 记：错误类/handler 路径 + 与 07-*-flask-core 端点的关系。

## 提示

- 错误类可参考 `controllers` 与 `libs/exception`（以仓库实际为准）
- 钩子优先挂在你加的 blueprint，避免污染全局
- Controller 层模式见 `08-flask-in-dify`

## 验收标准

- [ ] 正常响应含可追踪 request 字段
- [ ] 非法参数返回统一错误结构
- [ ] 钩子范围可控（未误伤无关路由，或有说明）
- [ ] 改动集中；不提交密钥

## 延伸（选做）

为该端点补一条 pytest（test client），挂到现有测试布局下。
