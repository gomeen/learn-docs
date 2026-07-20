# 小验证：集成 / E2E / LLM 测试

> 覆盖：
> - [07-integration-test](./08-integration-test.md)
> - [08-test-database](./09-test-database.md)
> - [09-e2e-test](./10-e2e-test.md)
> - [10-e2e-in-dify](./11-e2e-in-dify.md)
> - [11-llm-test](./12-llm-test.md)
>
> 预计：60～90 分钟 · 本地练习或改 dify 仓库

## 背景

集成与 E2E 成本更高，要会选边界。验证：设计一路径测试金字塔落点，并写一个 DB 事务回滚式集成测试草案。

## 需求

1. `NOTES.md`：为「创建应用 → 发送消息」选单元/集成/E2E 各自测什么、不测什么。
2. 写（或在仓库补）一个集成测试草案：使用事务回滚或测试 DB fixture 的模式（按项目现有模式对齐）。
3. LLM 测试：对「输出需包含引用标记」写 deterministic 检查器；模型侧用 fake response。
4. 记录 dify E2E 目录与启动依赖。

## 提示

- `api/tests/integration_tests/`
- LLM 测试避免金标死板全等，除非 freeze fake

## 验收标准

- [ ] 金字塔分工表清楚
- [ ] 集成测试草案可运行或逐步可运行
- [ ] fake LLM 断言稳定
- [ ] E2E 依赖说明不臆造

## 延伸（选做）

为 flaky 测试设计重试与隔离策略说明。
