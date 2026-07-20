# 小验证：Security Starter / Token / RBAC 基础

> 覆盖：
- [security starter](./23-security-starter.md)
- [Spring Security 概念](./24-spring-security.md)
- [Token 认证](./25-token-auth.md)
- [RBAC 模型](./26-rbac-model.md)
>
> 预计：30～45 分钟 · 改 ruoyi-vue-pro 仓库

## 背景

安全 starter 决定了登录态与过滤链。先把 Token 调用链和 RBAC 表关系跑通。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro`：

1. 走通一次管理端登录，拿到 accessToken；调用需登录接口，对比无 Token 时的状态码/错误码。
2. 定位 Token 过滤器（或 Authentication 转换处），说明 Token 存在 Redis/DB 的哪一层。
3. 阅读用户-角色-菜单（权限）相关表或 DO，画一张简化 RBAC 关系（3～4 个实体即可）。
4. 定位 security starter 的 AutoConfiguration / 过滤链注册入口。
5. 记录至少 3 类 `permitAll` 路径（Swagger、登录等）。

## 提示

- 本地可关闭验证码便于调试（仅本地配置）。
- 不要提交测试用弱密码到仓库。
- Token 前缀/Header 名以项目为准（常为 `Authorization`）。

## 验收标准

- [ ] 无 Token / 有 Token 行为对比完成
- [ ] 能指出 Token 认证过滤器或等价组件路径
- [ ] Token 存储层说明正确
- [ ] RBAC 关系图/列表清楚
- [ ] 记录至少 3 类 permitAll 路径

## 延伸（选做）

- 画一张从请求进入到 Controller 的 Security 过滤链简图。
- 对比 JWT 自包含与 Token+Redis 会话两种模式在 ruoyi 中的取舍。
