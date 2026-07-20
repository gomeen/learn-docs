# 13 E2E 测试：Playwright / Cypress

> 理解端到端测试（E2E）的目标和工具栈，能用 Playwright/Cypress 测试完整的 Web 用户流程。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 E2E 测试与单元测试、集成测试的区别
- 掌握 Playwright 和 Cypress 的基本用法
- 知道 dify E2E 测试的选型（cucumber + playwright）
- 应用：能为 dify Web 应用编写 E2E 测试

## 📚 前置知识

- ../../_common/18-testing/01-testing-pyramid.md
- Web 前端基础（HTTP 详见 [HTTP 协议](../../_common/14-api-protocols/01-http-protocol.md)、DOM）

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

## 3. 关键要点总结

- E2E 测试模拟真实用户操作，验证整个应用栈
- Playwright（跨浏览器、快）和 Cypress（调试好）是最流行的工具
- Cucumber + Gherkin 让业务人员能读懂测试
- dify E2E 用 Cucumber + Playwright，输出 HTML/JSON 报告
- E2E 默认 `parallel: 1`，避免浏览器实例冲突
- 默认排除 `@external-model` 等需要真实 API key 的场景

---

**文档版本**：v1.0
**最后更新**：2026-07-13
