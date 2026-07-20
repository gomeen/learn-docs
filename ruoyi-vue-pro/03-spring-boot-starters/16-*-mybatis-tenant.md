# 小验证：数据权限 / 租户拦截器 / 慢 SQL / ruoyi MyBatis

> 覆盖：
- [数据权限](./12-data-permission.md)
- [租户拦截器](./13-tenant-interceptor.md)
- [慢 SQL](./14-slow-sql.md)
- [ruoyi MyBatis 配置](./15-ruoyi-mybatis.md)
>
> 预计：30～45 分钟 · 改 ruoyi-vue-pro 仓库

## 背景

租户与数据权限拦截器会改写 SQL；慢 SQL 配置帮助发现性能问题。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro` 中：

1. 找出租户拦截器相关类，说明默认如何给 SQL 加 `tenant_id`；找一处 `@TenantIgnore` 或等价忽略点。
2. 找数据权限拦截器入口，说明其与 `@DataPermission` 的关系（可只读代码 + 文档）。
3. 用两个租户账号（或改上下文）验证同表数据隔离，或给出充分代码级证明。
4. 在 mybatis starter 配置中定位慢 SQL 阈值相关配置项。
5. 浏览 `YudaoMybatis*` 或等价配置类，列出 3 个关键定制点（类型处理器、插件、全局配置等）。

## 提示

- 多租户环境注意测试账号所属租户。
- 慢 SQL 阈值可临时调低做实验，测完改回。
- 不要提交仅用于调试的全局关闭租户配置。

## 验收标准

- [ ] 能指出租户 SQL 拦截器类路径
- [ ] 能指出数据权限相关类或注解入口
- [ ] 租户隔离可复现或有充分代码证明
- [ ] 慢 SQL 配置项已定位
- [ ] ruoyi MyBatis 定制点列出 ≥3 个

## 延伸（选做）

- 打开慢 SQL 阈值到极低，故意触发一条慢 SQL 日志。
- 阅读一次数据权限如何拼接 `dept_id IN (...)`。
