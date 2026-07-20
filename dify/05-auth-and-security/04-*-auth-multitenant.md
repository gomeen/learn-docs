# 小验证：资源所有权与 dify 认证流程

> 覆盖：
> - [11-resource-ownership](./01-resource-ownership.md)
> - [12-auth-in-dify](./02-auth-in-dify.md)
>
> 预计：45～90 分钟 · 本地练习或改 dify 仓库

## 背景

多租户下认证与资源所有权决定能否越权访问。验证：跟读登录/鉴权链路，并堵住或演示一处所有权检查。

## 需求

在 `/Users/xu/code/github/dify`：

1. 追踪一次 console 请求：鉴权装饰器 → 当前用户/租户上下文 → service 取资源；写 `NOTES.md` 序列。
2. 找一个「按 id 取资源」的接口，确认是否校验属于当前 tenant/account；若已有，记录检查点；若可改进，补上 `404/403` 与项目一致的错误（避免泄露资源是否存在的策略与项目保持一致）。
3. 手写 3 条越权测试用例描述（即使暂不自动化）：跨租户 id、跨用户私有资源、未登录。

## 提示

- `api/libs/login.py`、`api/controllers/console/auth.py`
- `api/libs/tenant_id.py`（若存在）
- 所有权检查应在 service 或统一依赖中，而不仅是前端隐藏按钮

## 验收标准

- [ ] 鉴权链路文档化且路径真实
- [ ] 至少 1 处所有权/租户检查被确认或加固
- [ ] 3 条越权用例描述清楚期望状态码
- [ ] 不在日志打印 token/密码

## 延伸（选做）

对比 Cookie Session 与 Bearer Token 在 console vs service_api 的差异（读代码）。
