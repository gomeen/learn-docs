# 小验证：多租户 · 中间件 · 适配器 · 策略工厂

> 覆盖：
> - [14-multi-tenancy](./18-multi-tenancy.md)
> - [15-middleware-pattern](./19-middleware-pattern.md)
> - [16-adapter-pattern](./20-adapter-pattern.md)
> - [17-strategy-factory](./21-strategy-factory.md)
>
> 预计：60～90 分钟 · 本地练习或改 dify 仓库

## 背景

多租户隔离与适配器/策略是 dify 对接多模型、多外部服务的骨架。验证重点：定位 tenant 边界，并做一个最小策略分支。

## 需求

在 `/Users/xu/code/github/dify`：

1. 找到一处查询或服务调用，确认 `tenant_id`（或等价工作空间上下文）如何传入，写 `NOTES.md` 说明「若漏传会发生什么」。
2. 实现一个**最小**策略或适配器改动（选一）：
   - 为某 factory/registry 增加一个明显的 dummy provider/strategy（仅 dev/test 可见或默认不启用），或
   - 在现有 middleware/钩子旁路增加调试日志字段（确认不会在生产默认开启）。
3. 保证默认配置路径行为不变。

## 提示

- 租户：`api/models/`、`api/libs/login.py`、service 层查询
- 适配器/策略：`api/core/model_runtime/`、工具 provider 等
- 中间件：`api/extensions/`

## 验收标准

- [ ] `NOTES.md` 写清 tenant 传递路径（含文件路径）
- [ ] 代码改动默认关闭或行为兼容
- [ ] 能说明适配器边界：业务核心不直接依赖具体第三方 SDK 类型（举 1 例）
- [ ] 无硬编码真实密钥

## 延伸（选做）

画一张简易序列图：Request → Auth → tenant 上下文 → Service → Provider。
