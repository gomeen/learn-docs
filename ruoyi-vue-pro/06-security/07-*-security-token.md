# 小验证：注解权限 / 过滤器 / Token 登录流

> 覆盖：
- [@PreAuthorize](./01-preauthorize.md)
- [自定义 Filter](./02-custom-filter.md)
- [Token + Redis](./03-token-redis.md)
- [TokenUtils](./04-token-utils.md)
- [登录流程](./05-login-flow.md)
- [社交登录](./06-social-login.md)
>
> 预计：60～90 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

本目录现有文档聚焦权限注解、Token 与登录。把登录到鉴权链路跑通。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro`：

1. 完成账号密码登录，记录 Token 在响应与后续请求头中的位置。
2. 在 Redis 中定位 Token 对应 key（前缀+token），删除后再次请求应失败。
3. 给接口加/调整 `@PreAuthorize`，验证无权限失败。
4. 阅读自定义 Token Filter，画出：请求 → Filter → SecurityContext → Controller。
5. 社交登录：只需定位 OAuth/社交绑定相关类，写清扩展点（不必真接微信）。

## 提示

- 本地关闭验证码/验证码打日志便于调试。
- 删除 Redis key 仅限自己的测试 Token。

## 验收标准

- [ ] 登录成功拿到 Token
- [ ] Redis 删 Token 后接口拒绝
- [ ] 权限注解拒绝可复现
- [ ] Filter 链路简图完成
- [ ] 社交登录扩展点路径记录

## 延伸（选做）

- 实现 Token 刷新接口调用一次。
- 对比 JWT 无状态与 Token+Redis 有状态优劣。
