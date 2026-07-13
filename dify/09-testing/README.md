# 09 - 测试与质量保障

> 测试是工程实践的核心。Dify 后端使用 pytest，按 TDD 流程开发。

## 前置依赖

- `01-fundamentals` 全部
- `02-backend` 的分层架构

## 模块 9.1 测试基础理论

- [ ] [1.1 测试金字塔：单元 / 集成 / E2E](./01-testing-pyramid.md)
- [ ] [1.2 TDD：红绿重构](./02-tdd.md)
- [ ] [1.3 测试覆盖率：行覆盖 / 分支覆盖 / 路径覆盖](./03-coverage.md)
- [ ] [1.4 Arrange-Act-Assert 测试结构](./04-aaa-pattern.md)

## 模块 9.2 pytest 实战

- [ ] [2.1 pytest 基础：`test_` 函数与断言](./05-pytest-basics.md)
- [ ] [2.2 pytest Fixture：`@pytest.fixture` 与作用域](./06-pytest-fixture.md)
- [ ] [2.3 pytest 参数化：`@pytest.mark.parametrize`](./07-pytest-parametrize.md)
- [ ] [2.4 pytest Mock：`monkeypatch` / `unittest.mock`](./08-pytest-mock.md)
- [ ] [2.5 pytest 插件：`pytest-cov` / `pytest-asyncio`](./09-pytest-plugins.md)
- [ ] [2.6 dify 的测试目录结构与规范](./10-pytest-in-dify.md)

## 模块 9.3 集成测试与端到端测试

- [ ] [3.1 集成测试：数据库与外部服务](./11-integration-test.md)
- [ ] [3.2 测试数据库：事务回滚与 fixture](./12-test-database.md)
- [ ] [3.3 E2E 测试：Playwright / Cypress](./13-e2e-test.md)
- [ ] [3.4 dify 的 E2E 测试配置](./14-e2e-in-dify.md)

## 模块 9.4 测试专项

- [ ] [4.1 性能测试：Locust / k6 / JMeter](./15-performance-test.md)
- [ ] [4.2 压力测试与基准测试](./16-stress-test.md)
- [ ] [4.3 安全测试：OWASP ZAP / Bandit](./17-security-test.md)
- [ ] [4.4 LLM 应用测试：响应质量评估](./18-llm-test.md)

## 模块 9.5 代码质量

- [ ] [5.1 Lint 工具：Ruff / Flake8 / Black](./19-lint-tools.md)
- [ ] [5.2 类型检查：mypy / pyright](./20-type-check.md)
- [ ] [5.3 Pre-commit Hook](./21-pre-commit.md)
- [ ] [5.4 dify 的 lint / type-check / test 三件套](./22-quality-in-dify.md)

## 🎯 dify 仓库对应位置

- 后端测试：`/Users/xu/code/github/dify/api/tests/`
- pytest 配置：`/Users/xu/code/github/dify/api/pyproject.toml`
- Makefile：`/Users/xu/code/github/dify/api/Makefile`
- E2E 测试：`/Users/xu/code/github/dify/api/tests/integration_tests/`
- CI 中的测试：`/Users/xu/code/github/dify/.github/workflows/`
