# 4.6 dify 的 CI/CD 配置分析（`.github/workflows/`）

> 深入解读 dify 仓库的完整 CI/CD 配置，理解开源项目如何搭建多工作流协作。

## 🎯 学习目标

完成本文档后，你将能够：
- 读懂 dify 仓库所有 GitHub Actions 工作流的职责
- 理解 `main-ci.yml` 用 `check-changes` 智能分派任务的设计
- 知道 dify 部署到不同环境的策略（dev / saas / enterprise）

## 📚 前置知识

- CI/CD 概念与流水线（详见 [CI/CD 概念](../../_common/11-cicd/01-concepts.md)）
- GitHub Actions 工作流机制（详见 [GitHub Actions 实战](../../_common/11-cicd/02-github-actions.md)）
- 部署策略：蓝绿 / 金丝雀 / 滚动（详见 [蓝绿部署](../../_common/12-deploy-strategies/01-blue-green.md)、[灰度发布](../../_common/12-deploy-strategies/02-canary.md)、[滚动发布](../../_common/12-deploy-strategies/03-rolling-and-ab.md)）

## 1. 核心概念

### 1.1 dify 工作流全景

dify 维护 20+ 个 GitHub Actions 工作流，按职责分为 4 类：

| 类别 | 文件 | 职责 |
|------|------|------|
| **核心 CI** | `main-ci.yml` | PR 触发的智能分派测试 |
| **专项测试** | `api-tests.yml` / `cli-tests.yml` / `vdb-tests.yml` / `db-migration-test.yml` | 各类测试 |
| **构建** | `docker-build.yml` / `build-push.yml` | Docker 镜像构建和推送（Dockerfile 详见 [Dockerfile 编写](../../_common/09-containerization/02-dockerfile.md)） |
| **部署** | `deploy-dev.yml` / `deploy-saas.yml` / `deploy-enterprise.yml` | 多环境部署 |
| **自动化** | `style.yml` / `autofix.yml` / `labeler.yml` / `translate-i18n-claude.yml` | 代码质量自动化 |
| **运维** | `stale.yml` / `post-merge.yml` / `hotfix-cherry-pick.yml` | 仓库运维 |

### 1.2 触发器分类

- **pull_request**：PR 创建/更新时
- **push**：直接 push 到 main
- **workflow_run**：另一个工作流完成后
- **schedule**：定时任务（如 `stale.yml`）
- **workflow_dispatch**：手动触发

### 1.3 关键设计模式

dify 用了多个企业级 CI 模式：

1. **路径过滤**（paths-filter）：只跑相关测试
2. **复用工作流**（workflow_call）：共享测试步骤
3. **Depot 加速构建**：4 倍速 Docker 构建
4. **多环境部署**：dev / saas / enterprise 独立
5. **自动修复**（autofix）：black/isort 自动提交
6. **i18n 自动化**（claude 翻译）：自动同步多语言

## 2. 代码示例

### 2.1 智能分派测试（paths-filter）

```yaml
check-changes:
  runs-on: depot-ubuntu-24.04
  outputs:
    api-changed: ${{ steps.changes.outputs.api }}
    web-changed: ${{ steps.changes.outputs.web }}
  steps:
    - uses: dorny/paths-filter@v4
      id: changes
      with:
        filters: |
          api:
            - 'api/**'
          web:
            - 'web/**'
```

后续 job 用 `if: needs.check-changes.outputs.api-changed == 'true'` 判断是否运行。

### 2.2 复用工作流（workflow_call）

```yaml
# api-tests.yml 顶部
on:
  workflow_call:                # 关键：可被其他 workflow 调用
```

```yaml
# 在 main-ci.yml 中调用
api-tests:
  uses: ./.github/workflows/api-tests.yml
  with:
    python-version: "3.12"
  secrets: inherit
```

### 2.3 跨工作流触发（workflow_run）

```yaml
on:
  workflow_run:
    workflows: ["Build and Push API & Web"]   # 等待此 workflow 完成
    types: [completed]
```

## 3. dify 仓库源码解读

### 3.1 主 CI 流水线（智能分派）

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/main-ci.yml`
**核心代码**（行 35-160）：

```yaml
  # Check which paths were changed to determine which tests to run
  check-changes:
    name: Check Changed Files
    needs: pre_job
    if: needs.pre_job.outputs.should_skip != 'true'
    runs-on: depot-ubuntu-24.04
    outputs:
      api-changed: ${{ steps.changes.outputs.api }}
      cli-changed: ${{ steps.changes.outputs.cli }}
      e2e-changed: ${{ steps.changes.outputs.e2e }}
      web-changed: ${{ steps.changes.outputs.web }}
      vdb-changed: ${{ steps.changes.outputs.vdb }}
      migration-changed: ${{ steps.changes.outputs.migration }}
    steps:
      - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0
      - uses: dorny/paths-filter@7b450fff21473bca461d4b92ce414b9d0420d706 # v4.0.2
        id: changes
        with:
          filters: |
            api:
              - 'api/**'
              - 'scripts/ast_grep_guard.py'
              - 'scripts/check_no_new_getattr.py'
              - 'scripts/lint_controller_sqlalchemy.py'
              - '.github/workflows/style.yml'
              - '.github/workflows/main-ci.yml'
              - '.github/workflows/api-tests.yml'
              - 'docker/.env.example'
              - 'docker/envs/middleware.env.example'
              - 'docker/docker-compose.middleware.yaml'
              - 'docker/docker-compose-template.yaml'
              - 'docker/generate_docker_compose'
              - 'docker/ssrf_proxy/**'
            cli:
              - 'cli/**'
              - 'packages/**'
              - 'package.json'
              - 'pnpm-lock.yaml'
              - 'pnpm-workspace.yaml'
              - '.nvmrc'
            web:
              - 'web/**'
              - 'packages/**'
              - 'package.json'
              - 'pnpm-lock.yaml'
              - 'pnpm-workspace.yaml'
              - '.nvmrc'
              - '.github/workflows/web-tests.yml'
              - '.github/actions/setup-web/**'
            e2e:
              - 'api/**'
              - 'api/pyproject.toml'
              - 'e2e/**'
              - 'web/**'
              - 'docker/docker-compose.middleware.yaml'
            vdb:
              - 'api/core/rag/datasource/**'
              - 'api/tests/integration_tests/vdb/**'
              - 'api/conftest.py'
              - 'api/tests/pytest_dify.py'
              - 'api/providers/vdb/*/tests/**'
              - '.github/workflows/vdb-tests.yml'
              - 'docker/.env.example'
              - 'docker/envs/middleware.env.example'
              - 'docker/docker-compose.pytest.ports.yaml'
              - 'docker/docker-compose.yaml'
              - 'docker/docker-compose-template.yaml'
              - 'docker/generate_docker_compose'
```

**解读**：

智能分派设计：
- 第 5-7 行：6 个布尔输出（api/cli/e2e/web/vdb/migration）
- 第 12-15 行：dorny/paths-filter 把路径映射到布尔值
- 第 16-31 行：api-changed 包含 api 代码 + 相关脚本 + docker 配置 + 相关 workflow
- 第 31-39 行：cli-changed 包含 CLI + 共享 packages
- 第 39-46 行：web-changed 包含 web 前端
- 第 47-53 行：e2e-changed（端到端测试）几乎所有改动都触发

**关键设计**：
- 改 `api/**` 会触发 api + e2e + vdb 测试
- 改 `docker/**` 也会触发 api 测试（防止环境配置错误）
- 改 `web/**` 触发 web + e2e 测试
- **节省 CI 资源**：小改动不会触发全量测试

### 3.2 部署工作流

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/deploy-dev.yml`
**核心代码**（行 1-26）：

```yaml
name: Deploy Dev

on:
  workflow_run:
    workflows: ["Build and Push API & Web"]
    branches:
      - "deploy/dev"
    types:
      - completed

jobs:
  deploy:
    runs-on: depot-ubuntu-24.04
    if: |
      github.event.workflow_run.conclusion == 'success' &&
      github.event.workflow_run.head_branch == 'deploy/dev'
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@0ff4204d59e8e51228ff73bce53f80d53301dee2 # v1.2.5
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            ${{ vars.SSH_SCRIPT || secrets.SSH_SCRIPT }}
```

**解读**：
- 触发链：`push to deploy/dev` → `Build and Push API & Web` → `Deploy Dev`
- `if` 条件：上游成功 **且** 分支是 `deploy/dev`
- 用 SSH 远程执行部署脚本（vars 优先，secrets 兜底）
- **生产环境部署**（saas/enterprise）用类似工作流但有更严格的审批

### 3.3 Post-Merge 检查

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/post-merge.yml`
**核心代码**（行 1-55）：

```yaml
name: Post-Merge Checks

on:
  push:
    branches: ["main"]

permissions:
  contents: read

concurrency:
  group: post-merge-${{ github.sha }}
  cancel-in-progress: false

jobs:
  check-changes:
    name: Check Changed Files
    runs-on: depot-ubuntu-24.04
    outputs:
      external-e2e-changed: ${{ steps.changes.outputs.external_e2e }}
    steps:
      - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0
      - uses: dorny/paths-filter@7b450fff21473bca461d4b92ce414b9d0420d706 # v4.0.2
        id: changes
        with:
          filters: |
            external_e2e:
              - 'e2e/features/agent-v2/**'
              - 'e2e/scripts/**'
              - 'e2e/support/**'
              - '.github/workflows/post-merge.yml'
              - '.github/workflows/web-e2e.yml'
              - '.github/actions/setup-web/**'
              - 'dify-agent/**'
              - 'api/clients/agent_backend/**'
              - 'api/core/app/apps/agent_app/**'
              - 'api/core/workflow/nodes/agent_v2/**'
              - 'api/controllers/console/agent/**'
              - 'api/services/agent/**'
              - 'api/core/plugin/**'
              - 'api/services/plugin/**'
              - 'api/core/tools/**'
              - 'api/services/tools/**'
              - 'web/features/agent-v2/**'
              - 'web/app/(commonLayout)/roster/**'
              - 'web/app/components/workflow/nodes/agent-v2/**'

  external-e2e:
    name: External Runtime E2E
    needs: check-changes
    if: needs.check-changes.outputs.external-e2e-changed == 'true'
    uses: ./.github/workflows/web-e2e.yml
    with:
      run-external-runtime: true
    secrets: inherit
```

**解读**：
- **合并后**才跑（`on.push.branches: main`），不像 PR 阶段
- 关注"外部运行时 E2E"（external runtime）
- `external-e2e-changed` 包含 agent-v2、插件系统、工作流等关键模块
- 用 `cancel-in-progress: false` 防止漏跑（按 sha 串行）
- **关键设计**：把昂贵的测试**延后到合并后**，PR 阶段不跑，节省时间

### 3.4 dify 的 Docker 镜像推送

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/build-push.yml`（参考）

典型内容：

```yaml
name: Build and Push API & Web

on:
  push:
    branches: [main]
    tags: ['*']

jobs:
  build:
    runs-on: depot-ubuntu-24.04-4
    permissions:
      contents: read
      packages: write
    strategy:
      matrix:
        include:
          - service_name: "api-amd64"
            platform: linux/amd64
            file: "api/Dockerfile"
          - service_name: "web-amd64"
            platform: linux/amd64
            file: "web/Dockerfile"
    steps:
      - uses: actions/checkout@v4
      - name: Set up Depot
        uses: depot/setup-action@v1
      - name: Build and Push
        uses: depot/build-push-action@v1
        with:
          project: ${{ vars.DEPOT_PROJECT_ID }}
          push: true                       # 真正推送
          tags: |
            langgenius/dify-api:${{ github.sha }}
            langgenius/dify-api:latest
```

**解读**：
- 与 `docker-build.yml` 区别：**push: true**（真正推送）
- 触发器：`push to main` 或 **打 tag**
- 多平台并行构建（amd64、arm64）
- 镜像打两个 tag：commit SHA + latest

## 4. 关键要点总结

- dify 维护 20+ 工作流，按职责分类清晰
- **`main-ci.yml` 用 paths-filter 智能分派**，只跑相关测试
- **复用工作流**（workflow_call）让测试步骤可在多处调用
- **Post-merge** 把昂贵测试延后到合并后，PR 阶段不跑
- **多环境部署**：dev / saas / enterprise 独立
- **Depot** 加速 Docker 构建（10-40x）
- **手动审批**用 SSH 远程执行部署脚本

## 5. 练习题

### 练习 1：基础（必做）

列出 dify `.github/workflows/` 所有 yml 文件，按职责（CI / 测试 / 构建 / 部署 / 自动化）分类整理成表格。

### 练习 2：进阶

阅读 `main-ci.yml` 全文（510 行），理解每个 job 的作用，绘制完整依赖图（哪些 job 串行 / 哪些并行）。

### 练习 3：挑战（选做）

为你的项目设计一个类似 dify 的"智能分派"工作流：根据 PR 改动路径（api / web / db / docs）决定跑哪些测试，用 `paths-filter` 实现。

## 6. 参考资料

- `/Users/xu/code/github/dify/.github/workflows/main-ci.yml`
- `/Users/xu/code/github/dify/.github/workflows/api-tests.yml`
- `/Users/xu/code/github/dify/.github/workflows/docker-build.yml`
- `/Users/xu/code/github/dify/.github/workflows/build-push.yml`
- `/Users/xu/code/github/dify/.github/workflows/deploy-dev.yml`
- `/Users/xu/code/github/dify/.github/workflows/post-merge.yml`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
