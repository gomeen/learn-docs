# 小验证：启动 / 自动配置 / Starter / 配置 / Actuator

> 覆盖：
- [启动流程](./08-startup.md)
- [自动配置](./09-auto-config.md)
- [自定义 Starter](./10-custom-starter.md)
- [配置文件](./11-config.md)
- [Actuator](./12-actuator.md)
- [启动加载器](./13-bootstrap.md)
>
> 预计：45～60 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

理解 Boot 如何把“依赖 + 条件 + 配置”装配成可运行应用，并会用 Actuator 确认起来。

## 需求

在 `/Users/xu/code/github/ruoyi-vue-pro`：

1. 找到一个 `Yudao*AutoConfiguration`，列出它声明的 `@Bean` 与条件注解（`@ConditionalOn*`），笔记路径。
2. 在配置文件中定位一处与该 AutoConfiguration 相关的 `yudao.*` 或 `spring.*` 配置项，改一个无害值并观察行为（或只读说明绑定关系）。
3. 说明 `spring.factories` / `AutoConfiguration.imports` 在本项目（或依赖 jar）中的入口位置。
4. 若 Actuator 已开启，访问 `/actuator/health`（或项目实际路径）确认状态；记录暴露了哪些端点。
5. 书面梳理：从 `main` 到刷新 ApplicationContext 的 4～6 个关键步骤（对照启动文档即可）。

## 提示

- 自动配置类多在 `yudao-framework` 的 starter 中。
- 不要在生产配置里乱关安全端点；仅本地。
- bootstrap 概念：知道与 application 配置加载顺序差异即可。

## 验收标准

- [ ] 至少一个 AutoConfiguration 的路径、Bean、条件注解记录完整
- [ ] 配置项与自动配置的绑定关系可说明
- [ ] 自动配置导入机制入口已定位
- [ ] Actuator health 可访问或说明未开启原因与开启方式
- [ ] 启动流程有 4～6 步书面梳理

## 延伸（选做）

- 自定义一个空 Starter 骨架（`AutoConfiguration.imports` + 条件 Bean）。
- 用 `--debug` 或 `ConditionEvaluationReport` 看条件评估。
