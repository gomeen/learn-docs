# 小验证：多数据源与连接池

> 覆盖：
- [dynamic-datasource](./23-dynamic-datasource.md)
- [@DS](./24-ds-annotation.md)
- [ruoyi 多数据源](./25-ruoyi-multi-ds.md)
- [Druid](./26-druid.md)
- [HikariCP](./27-hikari.md)
- [ruoyi Druid 配置](./28-ruoyi-druid.md)
>
> 预计：45～75 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

连接池与多数据源是生产稳定性关键。以配置阅读 + 小切换验证为主。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro`：

1. 找到主数据源配置（url/username/pool），确认连接池类型（Druid/Hikari）及核心参数（maxActive/maxPoolSize 等）。
2. 阅读多数据源相关配置与 `@DS` 用法；若本地只有单库，写清切换步骤与注意事项。
3. 打开 Druid 监控页（若启用）或通过日志确认连接获取正常。
4. 人为把池最大值设得很小做一次本地实验（可选），观察耗尽时的错误，然后恢复配置。

## 提示

- 不要把错误密码提交到 git。
- `@DS` 在事务下切换可能失效，文档有说明。
- 改池参数后记得重启。

## 验收标准

- [ ] 记录连接池类型与 3 个关键参数
- [ ] 指出多数据源配置位置与 `@DS` 示例
- [ ] 说明事务与数据源切换的限制
- [ ] 应用能正常拿连接完成一次查询
- [ ] 配置实验后已恢复合理值

## 延伸（选做）

- 对比 Druid 与 Hikari 监控能力。
- 配置慢 SQL 防火墙规则做一次拦截测试。
