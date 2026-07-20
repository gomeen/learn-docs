# 09 - 测试与质量保障

> 测试是工程实践的核心。Dify 后端使用 pytest，按 TDD 流程开发。
> **主路径**：全局顺序与「必读/延后」以 [`../LEARNING-PLAN.md`](../LEARNING-PLAN.md) 为准。
> 下方清单是**本分类素材目录**；未列入主计划的篇默认不读。需要做小验证时，优先做主计划点名的 `NN-*-*.md`。

## 🌐 公共部分

| 主题 | 公共文档 |
|------|----------|
| 测试金字塔 / TDD / 覆盖率 / AAA / 性能与安全测试 | [`_common/18-testing`](../../_common/18-testing/) |

## 前置依赖

- `01-fundamentals` 全部
- `02-backend` 的分层架构

## 模块 9.1 测试基础理论（公共）

- [ ] [1.1 测试金字塔：单元 / 集成 / E2E](../../_common/18-testing/01-testing-pyramid.md)
- [ ] [1.2 TDD：红绿重构](../../_common/18-testing/02-tdd.md)
- [ ] [1.3 测试覆盖率：行覆盖 / 分支覆盖 / 路径覆盖](../../_common/18-testing/03-coverage.md)
- [ ] [1.4 Arrange-Act-Assert 测试结构](../../_common/18-testing/04-aaa-pattern.md)

## 模块 9.2 pytest 实战

- [ ] [2.1 pytest 基础：`test_` 函数与断言](./01-pytest-basics.md)
- [ ] [2.2 pytest Fixture：`@pytest.fixture` 与作用域](./02-pytest-fixture.md)
- [ ] [2.3 pytest 参数化：`@pytest.mark.parametrize`](./03-pytest-parametrize.md)
- [ ] [2.4 pytest Mock：`monkeypatch` / `unittest.mock`](./04-pytest-mock.md)
- [ ] [2.5 pytest 插件：`pytest-cov` / `pytest-asyncio`](./05-pytest-plugins.md)
- [ ] [2.6 dify 的测试目录结构与规范](./06-pytest-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [07-*-pytest-core: pytest 核心与 dify 测试布局](./07-*-pytest-core.md)
  - 覆盖：01-pytest-basics.md, 02-pytest-fixture.md, 03-pytest-parametrize.md, 04-pytest-mock.md, 05-pytest-plugins.md, 06-pytest-in-dify.md


## 模块 9.3 集成测试与端到端测试

- [ ] [3.1 集成测试：数据库与外部服务](./08-integration-test.md)
- [ ] [3.2 测试数据库：事务回滚与 fixture](./09-test-database.md)
- [ ] [3.3 E2E 测试：Playwright / Cypress](./10-e2e-test.md)
- [ ] [3.4 dify 的 E2E 测试配置](./11-e2e-in-dify.md)

## 模块 9.4 测试专项

- [ ] [4.1 性能测试：Locust / k6 / JMeter](../../_common/18-testing/05-performance-test.md)
- [ ] [4.2 压力测试与基准测试](../../_common/18-testing/06-stress-test.md)
- [ ] [4.3 安全测试：OWASP ZAP / Bandit](../../_common/18-testing/07-security-test.md)
- [ ] [4.4 LLM 应用测试：响应质量评估](./12-llm-test.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [13-*-integration-e2e-llm: 集成 / E2E / LLM 测试](./13-*-integration-e2e-llm.md)
  - 覆盖：08-integration-test.md, 09-test-database.md, 10-e2e-test.md, 11-e2e-in-dify.md, 12-llm-test.md


## 模块 9.5 代码质量

- [ ] [5.1 Lint 工具：Ruff / Flake8 / Black](./14-lint-tools.md)
- [ ] [5.2 类型检查：mypy / pyright](./15-type-check.md)
- [ ] [5.3 Pre-commit Hook](./16-pre-commit.md)
- [ ] [5.4 dify 的 lint / type-check / test 三件套](./17-quality-in-dify.md)

### ✅ 小验证（学完以上内容后做）
- [ ] [18-*-quality-tooling: Lint · 类型检查 · pre-commit · dify 质量三件套](./18-*-quality-tooling.md)
  - 覆盖：14-lint-tools.md, 15-type-check.md, 16-pre-commit.md, 17-quality-in-dify.md


## 🎯 dify 仓库对应位置

- 后端测试：`/Users/xu/code/github/dify/api/tests/`
- pytest 配置：`/Users/xu/code/github/dify/api/pyproject.toml`
- Makefile：`/Users/xu/code/github/dify/api/Makefile`
- E2E 测试：`/Users/xu/code/github/dify/api/tests/integration_tests/`
- CI 中的测试：`/Users/xu/code/github/dify/.github/workflows/`
