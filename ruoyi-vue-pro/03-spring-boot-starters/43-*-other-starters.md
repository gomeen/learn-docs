# 小验证：Web / 多租户 / Job / 监控 Starter

> 覆盖：
- [Web 增强](./39-web-starter.md)
- [多租户](./40-tenant.md)
- [XXL-Job](./41-xxl-job.md)
- [监控](./42-monitor.md)
>
> 预计：30～45 分钟 · 改 ruoyi-vue-pro 仓库

## 背景

横向能力 starter：Web 增强、租户、定时任务与监控。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro` 完成：

1. **多租户**：切换两个租户登录（或改上下文），验证同表数据隔离；找到 `@TenantIgnore` 的一处合理使用场景。
2. **Web**：说明 Web starter 相对原生 Spring MVC 增强了什么（至少 3 点：如全局异常、XSS、API 日志等，以代码为准）。
3. **XXL-Job**：找到任务处理器注解与注册方式，说明如何新增一个 demo handler（可只写代码不调度）。
4. **监控**：打开 Actuator/Prometheus 端点之一，拿到健康或指标输出；或定位 monitor starter 配置。
5. 列出本批 4 个主题各自对应的 Maven 模块路径。

## 提示

- 租户测试请用本地库。
- Job 调度中心未启动时允许代码级完成。
- 监控端点注意安全暴露范围。

## 验收标准

- [ ] 多租户隔离现象可复现或有充分代码级证明
- [ ] Web starter 增强点 ≥3 且有代码依据
- [ ] Job 扩展点路径明确
- [ ] 监控端点或配置已验证/定位
- [ ] 模块路径列表完整

## 延伸（选做）

- 本地跑通一个 XXL handler 日志。
- 给健康检查加一个自定义 `HealthIndicator`。
