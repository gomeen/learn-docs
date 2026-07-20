# 小验证：IoC / AOP / 事务 / 事件 / Profile

> 覆盖：
- [IoC 与依赖注入](./01-ioc.md)
- [Bean 生命周期](./02-bean-lifecycle.md)
- [AOP](./03-aop.md)
- [事务管理](./04-transaction.md)
- [事件机制](./05-event.md)
- [Profile](./06-profile.md)
>
> 预计：45～60 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

在 ruoyi-vue-pro 中定位 Spring 核心装配点，并做一个最小可运行的 AOP + 事件 + Profile 验证。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro` 中完成（可用独立 demo 模块，但优先在 yudao 结构内改）：

1. **定位 Bean**：找一个业务 Service，说明其注入方式（构造器/字段）与所在配置扫描路径。
2. **AOP**：新增切面（或在 demo 包），拦截某个 Service 的 public 方法，打印方法名与耗时；确保被 Spring 管理。
3. **事件**：定义 `DemoCreatedEvent`，在 Service 内 `publishEvent`，写 `@EventListener` 消费并打日志。
4. **Profile**：在 `application-local.yaml`（或现有 local profile）增加 `demo.feature-enabled`，用 `@ConfigurationProperties` 或 `@Value` 读取；切到非 local 时默认关闭。
5. **事务观察（只读）**：找一处 `@Transactional` 的 Service 方法，说明其传播行为与会回滚的异常类型。

## 提示

- 切面注意代理限制：同类自调用不会走 AOP。
- 改代码后只启动必要模块；不要提交无关格式化。
- Bean 生命周期：知道 `@PostConstruct` / `InitializingBean` 出现时机即可。

## 验收标准

- [ ] 能指出至少一个 Bean 的注入与扫描路径
- [ ] 切面日志在调用目标方法时出现，耗时可打印
- [ ] 事件发布后监听器被触发（日志可证）
- [ ] Profile 配置在 local 生效，切换 profile 行为可说明
- [ ] 对一处 `@Transactional` 的传播/回滚有书面说明（3～5 行）

## 延伸（选做）

- 给切面加 `@Order` 并观察与现有切面顺序。
- 用 `@TransactionalEventListener` 对比默认事件时机。
