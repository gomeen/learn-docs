# 13 E2E 测试：Playwright / Cypress

> 理解端到端测试（E2E）的目标和工具栈，能用 Playwright/Cypress 测试完整的 Web 用户流程。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 E2E 测试与单元测试、集成测试的区别
- 掌握 Playwright 和 Cypress 的基本用法
- 知道 dify E2E 测试的选型（cucumber + playwright）
- 应用：能为 dify Web 应用编写 E2E 测试

## 📚 前置知识

- 09-testing/01-testing-pyramid.md
- Web 前端基础（HTTP 详见 [HTTP 协议](../01-fundamentals/25-http-protocol.md)、DOM）

## 1. 核心概念

### 1.1 E2E 测试是什么

**端到端测试（E2E, End-to-End）** 模拟真实用户在浏览器中的操作，验证整个应用栈（前端、后端、数据库、外部服务）一起工作时的行为。

```
用户点击 "登录" → 浏览器发送 POST /api/login → 后端验证 → 写入 session
       ↑                                                           ↓
       └──────────── E2E 测试断言：成功跳转到首页 ←─────────────────┘
```

### 1.2 E2E 测试工具对比

| 工具 | 语言 | 浏览器支持 | 特点 |
|------|------|------------|------|
| Playwright | TypeScript / Python | Chromium, Firefox, WebKit | 微软出品，速度快，跨浏览器 |
| Cypress | JavaScript | Chromium 系（Edge、Chrome） | 调试体验好，实时 reload |
| Selenium | 多语言 | 全浏览器 | 老牌，慢，复杂 |
| Puppeteer | JavaScript | Chromium | 偏脚本化 |
| Cucumber + Playwright | Gherkin + TypeScript | 全浏览器 | BDD 风格，业务可读 |

### 1.3 dify 的 E2E 测试选型

dify 用 **Cucumber + Playwright**（见 `e2e/cucumber.config.ts`）：

- **Cucumber**：用自然语言（Gherkin）写测试用例
- **Playwright**：执行浏览器操作
- **好处**：业务人员能读懂测试，研发负责实现 step

## 2. 代码示例

### 2.1 Playwright Python 基础

```python
# 文件：test_e2e_login.py
from playwright.sync_api import sync_playwright


def test_login_flow():
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 访问登录页
        page.goto("http://localhost:3000/signin")

        # 填写表单
        page.fill('input[name="email"]', "alice@example.com")
        page.fill('input[name="password"]', "secret123")

        # 提交
        page.click('button[type="submit"]')

        # 等待跳转
        page.wait_for_url("**/apps")

        # 断言
        assert "My Apps" in page.content()

        browser.close()
```

### 2.2 Cypress 基础

```javascript
// 文件：cypress/e2e/login.cy.js
describe('Login Flow', () => {
  it('should login successfully', () => {
    cy.visit('/signin')
    cy.get('input[name="email"]').type('alice@example.com')
    cy.get('input[name="password"]').type('secret123')
    cy.get('button[type="submit"]').click()

    cy.url().should('include', '/apps')
    cy.contains('My Apps').should('be.visible')
  })
})
```

### 2.3 Cucumber + Gherkin 语法

```gherkin
# 文件：features/login.feature
Feature: User Login
  As a registered user
  I want to log in to the application
  So that I can access my apps

  Scenario: Successful login
    Given I am on the signin page
    When I fill in "alice@example.com" in the email field
    And I fill in "secret123" in the password field
    And I click the "Sign In" button
    Then I should be on the apps page
    And I should see "My Apps" in the header
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Cucumber 配置

**文件位置**：`/Users/xu/code/github/dify/e2e/cucumber.config.ts`
**核心代码**（行 1-26）：

```typescript
import type { IConfiguration } from '@cucumber/cucumber'
import './scripts/env-register'

const hasCliTags = process.argv.some(arg => arg === '--tags' || arg.startsWith('--tags='))
const defaultNonExternalTags = 'not @fresh and not @skip and not @preview and not @external-model and not @external-tool'
const defaultTags = process.env.E2E_CUCUMBER_TAGS
  || (hasCliTags ? undefined : defaultNonExternalTags)

const config = {
  format: [
    'progress-bar',
    'summary',
    'html:./cucumber-report/report.html',
    'json:./cucumber-report/report.json',
  ],
  import: ['./tsx-register.js', 'features/**/*.ts'],
  parallel: 1,
  paths: ['features/**/*.feature'],
  ...(defaultTags ? { tags: defaultTags } : {}),
  timeout: 60_000,
} satisfies Partial<IConfiguration> & {
  timeout: number
}

export default config
```

**解读**：
- 第 5 行：`defaultNonExternalTags` 默认排除 `@fresh` / `@skip` / `@preview` / `@external-model` / `@external-tool` 等需要真实外部资源的标签
- 第 7 行：可通过环境变量 `E2E_CUCUMBER_TAGS` 覆盖默认 tags
- 第 10-13 行：输出 HTML 和 JSON 报告，便于可视化
- 第 15 行：`parallel: 1` —— E2E 默认串行执行（避免浏览器冲突）
- 第 20 行：`timeout: 60_000` —— 每个 step 60 秒超时

### 3.2 dify 的 E2E 目录结构

**文件位置**：`/Users/xu/code/github/dify/e2e/`

```
e2e/
├── cucumber.config.ts             # Cucumber 配置
├── vite.config.ts                 # Vite 配置
├── test-env.ts                    # 测试环境
├── features/                      # Gherkin 特性文件
│   └── ...
├── tests/                         # TypeScript 测试代码
│   ├── service-api-sse.test.ts
│   └── ...
└── support/                       # 支持代码（API、seed、apps、datasets）
    ├── api.ts
    ├── apps.ts
    ├── datasets.ts
    ├── process.ts
    ├── seed.ts
    └── web-server.ts
```

**解读**：
- `features/`：业务可读的 Gherkin 场景
- `tests/`：TypeScript 编写的 step definitions（实现层）
- `support/`：测试基础设施（启动 Web 服务器、初始化数据）
- **设计意图**：用 Cucumber 把"业务描述"和"技术实现"分层

### 3.3 dify 的 E2E 在 CI 中的执行

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/` 下的相关 workflow
**核心代码**（CLI-E2E workflow 摘要）：

```yaml
- name: Run E2E Tests
  env:
    E2E_CUCUMBER_TAGS: ${{ matrix.tags }}
  run: |
    pnpm install
    pnpm e2e
```

**解读**：
- E2E 测试通常单独跑一个 workflow（运行时间长）
- 通过 `E2E_CUCUMBER_TAGS` 控制跑哪些场景（如 `@smoke` 快速测试 vs `@full` 全部测试）
- E2E 需要 Web 服务器、API 服务、数据库都启动，CI 通过 docker-compose 编排

## 4. 关键要点总结

- E2E 测试模拟真实用户操作，验证整个应用栈
- Playwright（跨浏览器、快）和 Cypress（调试好）是最流行的工具
- Cucumber + Gherkin 让业务人员能读懂测试
- dify E2E 用 Cucumber + Playwright，输出 HTML/JSON 报告
- E2E 默认 `parallel: 1`，避免浏览器实例冲突
- 默认排除 `@external-model` 等需要真实 API key 的场景

## 5. 练习题

### 练习 1：基础（必做）

阅读 `e2e/cucumber.config.ts`，列出 5 个被默认排除的 tag，并解释为什么 E2E 测试需要排除它们。

### 练习 2：进阶

本地启动 dify，尝试用 Playwright 写一个简单的 E2E 测试：访问 `http://localhost:3000/install` → 填写管理员邮箱 → 提交 → 断言跳转到登录页。

### 练习 3：挑战（选做）

阅读 `e2e/support/api.ts` 和 `e2e/support/apps.ts`，理解 dify E2E 测试如何通过 API 准备数据（而不是通过 UI），并思考这种"API seed + UI 验证"的混合策略有什么好处。

## 6. 参考资料

- `/Users/xu/code/github/dify/e2e/cucumber.config.ts`（Cucumber 配置）
- `/Users/xu/code/github/dify/e2e/`（E2E 目录）
- Playwright 官方文档：https://playwright.dev/
- Cypress 官方文档：https://www.cypress.io/
- Cucumber 官方文档：https://cucumber.io/

---

**文档版本**：v1.0
**最后更新**：2026-07-13