# 小验证：Starter 机制与自研骨架

> 覆盖：
- [Starter 机制](./01-starter-mechanism.md)
- [AutoConfiguration](./02-auto-configuration.md)
- [SPI / spring.factories](./03-spi.md)
- [条件装配](./04-conditional.md)
- [自研 Starter 实战](./05-custom-starter-practice.md)
>
> 预计：45～75 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

ruoyi 的 yudao-framework 本质是一组 Starter。先吃透装配机制再读业务。

## 需求

1. 在 `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework` 中任选一个 starter，画出：模块 → AutoConfiguration 类 → `META-INF` 注册文件 → 主要 `@Bean`。
2. 找到一处 `@ConditionalOn*` 的实际用例，说明“什么情况下这个 Bean 不会加载”。
3. 本地新建最小 starter 或 demo-autoconfigure：
   - 配置项 `demo.hello.prefix`
   - 自动配置一个 `HelloService`
   - 用 `spring.factories` 或 Boot 2.7+/3 的 `AutoConfiguration.imports` 注册
4. 在测试应用中引入后，调用 `HelloService` 输出带 prefix 的字符串。

## 提示

- Boot 2.7 仍常见 `spring.factories`；Boot 3 推荐 `AutoConfiguration.imports`。
- 对照 `yudao-spring-boot-starter-web` 的目录布局。

## 验收标准

- [ ] 完成一个真实 starter 的装配路径笔记（含文件路径）
- [ ] 解释清楚至少 1 个条件注解的生效条件
- [ ] 自研/演示 starter 可被测试应用加载
- [ ] 修改配置项能改变 HelloService 行为
- [ ] 能说明 starter 与普通业务模块依赖方向（谁依赖谁）

## 延伸（选做）

- 加 `@ConditionalOnMissingBean` 允许业务覆盖 HelloService。
- 用 spring-boot-configuration-processor 生成元数据。
