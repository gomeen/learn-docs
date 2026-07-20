# 小验证：Security 配置 / @PreAuthorize / 数据权限注解

> 覆盖：
- [Security 配置](./28-security-config.md)
- [@PreAuthorize](./29-preauthorize.md)
- [@DataPermission](./30-data-permission-annotation.md)
>
> 预计：30～45 分钟 · 改 ruoyi-vue-pro 仓库

## 背景

注解鉴权与数据权限是业务接口的“最后一公里”。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro`：

1. 给 demo 接口（或现有测试接口）加 `@PreAuthorize("@ss.hasPermission('system:demo:query')")`（权限标识按项目习惯）。
2. 在菜单/权限未分配时验证失败，分配后成功（两种路径都要可复现）。
3. 阅读 `SecurityFilterChain` 配置：说明哪些路径公开、哪些需认证。
4. 找到一处 `@DataPermission` 用法，说明其如何限制“仅本部门数据”。
5. 说明权限标识与库表 `system_menu` 的对应关系。

## 提示

- 权限标识需与库表一致才能分配。
- 改菜单后可能需重新登录刷新权限缓存。
- 数据权限可只读代码 + 一次带权限账号的查询对比。

## 验收标准

- [ ] `@PreAuthorize` 拒绝与放行两种路径可复现
- [ ] Security 配置中公开/认证路径说明正确
- [ ] 对数据权限注解有一处真实代码引用
- [ ] 权限标识与菜单表对应关系说明清楚
- [ ] 无把危险路径误设为 permitAll 并提交

## 延伸（选做）

- 自定义一个权限表达式 bean 方法。
- 给列表接口加 `@DataPermission` 并观察 SQL 变化。
