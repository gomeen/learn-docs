# 14 dify 的 E2E 测试配置

> 深入了解 dify 的 E2E 测试基础设施、配置和执行流程。

## 🎯 学习目标

完成本文档后，你将能够：
- 熟悉 dify E2E 测试的目录结构和配置
- 理解 dify E2E 的 tags 分层策略
- 能本地运行 dify 的 E2E 测试
- 应用：能为 dify 新功能编写 E2E 测试用例

## 📚 前置知识

- 09-testing/13-e2e-test.md
- 02-backend/05-rest-api.md

## 1. 核心概念

### 1.1 dify E2E 测试栈

dify 的 E2E 测试由以下组件构成：

| 组件 | 作用 | 文件位置 |
|------|------|----------|
| **Cucumber** | 解析 Gherkin 场景 | `e2e/cucumber.config.ts` |
| **Playwright** | 浏览器自动化 | `e2e/support/` |
| **tsx** | TypeScript 执行 | `e2e/tsx-register.js` |
| **Web Server** | 被测对象 | `e2e/support/web-server.ts` |
| **API Client** | 数据准备 | `e2e/support/api.ts` |

### 1.2 dify E2E 的 Tags 分层

通过 Gherkin 的 tags，dify 把 E2E 测试分成多层：

```gherkin
@smoke               # 冒烟测试（最快，覆盖核心路径）
Feature: Login

@full                # 完整测试（慢，覆盖所有场景）
Feature: User Management

@external-model      # 需要真实 API key（默认排除）
Feature: GPT-4 Tests

@external-tool       # 需要真实第三方工具（默认排除）
Feature: Google Search Tests

@skip                # 已知问题，跳过
Feature: Bug Repro

@fresh               # 需要全新数据环境
Feature: Reset Tests
```

默认只跑"无 external 依赖"的测试，CI 完整跑时通过 `E2E_CUCUMBER_TAGS` 配置。

### 1.3 dify E2E 的 "API seed + UI 验证" 策略

dify E2E 测试不通过 UI 准备数据，而是**直接调 API** 创建测试数据，再用 UI 验证结果：

```typescript
// 1. 用 API 创建测试 app
const app = await api.createApp({ name: "Test App" })

// 2. 用 UI 验证 app 出现在列表里
await page.goto("/apps")
await expect(page.getByText("Test App")).toBeVisible()
```

**好处**：
- 测试数据准备快（避免 UI 操作的时间成本）
- 失败定位清晰：UI 失败 = 前端问题，API 失败 = 后端问题
- 减少重复测试逻辑

## 2. 代码示例

### 2.1 dify 的 E2E 项目结构

```
e2e/
├── cucumber.config.ts             # Cucumber 主配置
├── vite.config.ts                 # Vite 构建配置
├── test-env.ts                    # 环境变量定义
├── tsx-register.js                # TypeScript 运行时
├── scripts/                       # 脚本
│   └── env-register.ts
├── features/                      # Gherkin 特性文件
│   ├── login.feature
│   ├── app-management.feature
│   └── ...
├── tests/                         # TypeScript step definitions
│   ├── login.steps.ts
│   ├── app.steps.ts
│   └── ...
├── support/                       # 支持代码
│   ├── api.ts                     # 后端 API 客户端
│   ├── apps.ts                    # 应用管理 helpers
│   ├── datasets.ts                # 数据集 helpers
│   ├── process.ts                 # 进程管理
│   ├── seed.ts                    # 数据 seed
│   └── web-server.ts              # Web 服务器管理
└── cucumber-report/               # 生成的报告（git ignored）
    ├── report.html
    └── report.json
```

### 2.2 Gherkin 特性文件示例

```gherkin
# 文件：features/login.feature
@smoke
Feature: User Login
  As a registered user
  I want to log in to dify
  So that I can manage my apps

  Background:
    Given the system has a registered user "alice@example.com"

  Scenario: Successful login
    When I navigate to "/signin"
    And I fill in the login form
      | email                | password |
      | alice@example.com    | Test1234 |
    And I click the "Sign In" button
    Then I should be redirected to "/apps"
    And I should see "My Apps" in the header
```

## 3. dify 仓库源码解读

### 3.1 dify 的 E2E 配置文件

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
- 第 4 行：自动检测 CLI 是否传了 `--tags`，避免双重应用
- 第 5 行：默认排除的 5 个 tag —— fresh / skip / preview / external-model / external-tool
- 第 10-14 行：4 种输出格式（控制台进度 + 摘要 + HTML + JSON）
- 第 15 行：`import` 引入 tsx-register（支持 TypeScript）和 features 下的所有 step definitions
- 第 19 行：`timeout: 60_000` —— 每个 step 60 秒超时

### 3.2 dify 的 Web Server 管理

**文件位置**：`/Users/xu/code/github/dify/e2e/support/web-server.ts`

```typescript
// 摘要：dify 通过 web-server.ts 管理被测应用的生命周期
import { start, stop } from './process'

export async function startWebServer() {
  // 启动 dify API + Web 服务器
  await start()
}

export async function stopWebServer() {
  // 清理
  await stop()
}
```

**解读**：
- E2E 测试前需要先启动 dify 后端 + 前端 Web 服务器
- `process.ts` 负责启动/停止子进程
- **设计意图**：E2E 测试把"被测对象"也当作 fixture 管理

### 3.3 dify 的 CI E2E workflow

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/cli-e2e.yml`（CLI E2E 范例）

**核心代码**（摘要）：

```yaml
name: CLI E2E
on:
  workflow_call:

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: pnpm install
      - name: Run E2E tests
        env:
          E2E_CUCUMBER_TAGS: ${{ inputs.tags || '@smoke' }}
        run: pnpm e2e
      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-report
          path: e2e/cucumber-report/
```

**解读**：
- 默认跑 `@smoke`（冒烟测试），通过 `inputs.tags` 可覆盖
- `if: always()` 保证即使测试失败也上传报告
- E2E report 作为 CI artifact 保存，便于排查

## 4. 关键要点总结

- dify E2E 用 **Cucumber + Playwright + TypeScript** 组合
- 通过 tags 分层：`@smoke`（快）→ `@full`（完整）→ `@external-model`（默认排除）
- "API seed + UI 验证"策略：用 API 准备数据，UI 验证行为
- E2E 默认 60s/step 超时，`parallel: 1` 避免浏览器冲突
- 报告输出 HTML 和 JSON，CI artifact 保存

## 5. 练习题

### 练习 1：基础（必做）

阅读 `e2e/cucumber.config.ts`，用一句话解释：什么是 `not @external-model and not @external-tool`？为什么要排除这些 tag？

### 练习 2：进阶

本地 clone dify 仓库，参考 `e2e/features/` 下的某个 `.feature` 文件，写一个新的 Gherkin 场景：创建 Chatbot 类型应用、填写 Prompt、发布、对话验证。给它打上 `@smoke` tag。

### 练习 3：挑战（选做）

阅读 `e2e/support/api.ts`，找出 dify E2E 如何用 API 客户端登录获取 JWT，然后用 `page.setExtraHTTPHeaders({ Authorization: ... })` 让浏览器自动带上认证头，理解"绕过登录 UI 直接进入测试场景"的设计模式。

## 6. 参考资料

- `/Users/xu/code/github/dify/e2e/cucumber.config.ts`（Cucumber 配置）
- `/Users/xu/code/github/dify/e2e/support/`（E2E 支持代码）
- `/Users/xu/code/github/dify/.github/workflows/cli-e2e.yml`（CI E2E）
- Cucumber tags 文档：https://cucumber.io/docs/cucumber/api/

---

**文档版本**：v1.0
**最后更新**：2026-07-13