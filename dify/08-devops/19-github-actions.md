# 4.2 GitHub Actions 实战

> 学会用 GitHub Actions 编写工作流，能读懂 dify 的 `.github/workflows/` 配置。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 GitHub Actions 的核心语法：workflow / job / step / action
- 用常用 actions（checkout、setup-python、upload-artifact）
- 编写矩阵构建和依赖传递

## 📚 前置知识

- `08-devops/18-cicd-concepts.md`
- YAML 基础

## 1. 核心概念

### 1.1 GitHub Actions 是什么？

GitHub Actions 是 GitHub 内置的 CI/CD 平台。工作流文件放在 `.github/workflows/*.yml`，PR/Push 时自动触发。

### 1.2 核心概念

- **Workflow**：一个 YAML 文件，定义完整流水线
- **Job**：工作流中的一个执行单元（可并行/串行）
- **Step**：Job 中的一条命令或 action
- **Action**：可复用的步骤（marketplace 或自建）
- **Runner**：执行 Job 的机器（GitHub 托管或自托管）
- **Event**：触发工作流的事件（push、PR、schedule 等）

### 1.3 关键特性

- **矩阵构建（matrix）**：一次运行多种组合（多 OS / 多版本）
- **依赖（needs）**：Job 间的串行依赖
- **输出（outputs）**：Job 间传递数据
- **环境（environment）**：关联部署环境（用于审批）
- **密钥（secrets）**：存放敏感数据
- **缓存（cache）**：加速依赖安装

## 2. 代码示例

### 2.1 最小工作流

```yaml
# .github/workflows/hello.yml
name: Hello World

on: push

jobs:
  greet:
    runs-on: ubuntu-latest
    steps:
      - run: echo "Hello GitHub Actions"
```

### 2.2 检出代码 + 设置 Python

```yaml
name: Python CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4              # 检出代码

      - uses: actions/setup-python@v5          # 设置 Python
        with:
          python-version: "3.12"
          cache: "pip"                          # 自动缓存 pip 依赖

      - run: pip install -r requirements.txt
      - run: pytest
```

### 2.3 矩阵构建

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
        os: [ubuntu-latest, macos-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pytest
```

### 2.4 常用 Actions

| Action | 用途 |
|--------|------|
| `actions/checkout@v4` | 检出代码 |
| `actions/setup-python@v5` | 设置 Python |
| `actions/setup-node@v4` | 设置 Node.js |
| `actions/upload-artifact@v4` | 上传构建产物 |
| `actions/download-artifact@v4` | 下载构建产物 |
| `docker/build-push-action@v5` | 构建/推送 Docker |
| `appleboy/ssh-action@v1` | 远程 SSH 执行 |
| `dorny/paths-filter@v4` | 路径过滤 |
| `depot/build-push-action@v1` | Depot 加速构建 |

### 2.5 常见错误：checkout 权限

```yaml
# ❌ 错误：默认 token 在 PR 上限只读，无法 push
- uses: actions/checkout@v4

# ✅ 正确：PR 上 fetch depth=0（需要完整历史）
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
    persist-credentials: false
```

## 3. dify 仓库源码解读

### 3.1 dify 的 API 测试工作流

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/api-tests.yml`
**核心代码**（行 1-75）：

```yaml
name: Run Pytest

on:
  workflow_call:
    secrets:
      CODECOV_TOKEN:
        required: false

permissions:
  contents: read

concurrency:
  group: api-tests-${{ github.head_ref || github.run_id }}
  cancel-in-progress: true

jobs:
  api-unit:
    name: API Unit Tests
    runs-on: depot-ubuntu-24.04
    env:
      COVERAGE_FILE: coverage-unit
    defaults:
      run:
        shell: bash
    strategy:
      matrix:
        python-version:
          - "3.12"

    steps:
      - name: Checkout code
        uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0
        with:
          fetch-depth: 0
          persist-credentials: false

      - name: Setup UV and Python
        uses: astral-sh/setup-uv@d31148d669074a8d0a63714ba94f3201e7020bc3 # v8.3.0
        with:
          enable-cache: true
          python-version: ${{ matrix.python-version }}
          cache-dependency-glob: api/uv.lock

      - name: Check UV lockfile
        run: uv lock --project api --check

      - name: Install dependencies
        run: uv sync --project api --dev

      - name: Run dify config tests
        run: uv run --project api pytest api/tests/unit_tests/configs/test_env_consistency.py

      - name: Run Unit Tests
        run: |
          uv run --project api pytest \
            -p no:benchmark \
            --timeout "${PYTEST_TIMEOUT:-20}" \
            -n auto \
            api/tests/unit_tests \
            api/providers/vdb/*/tests/unit_tests \
            api/providers/trace/*/tests/unit_tests \
            --ignore=api/tests/unit_tests/controllers
```

**解读**：
- 第 3-7 行：`workflow_call` 触发器——这是**可复用工作流**，被其他 workflow 调用
- 第 14-15 行：自定义 Runner（`depot-ubuntu-24.04`，比 GitHub 官方 Runner 快 10-40 倍）
- 第 23-24 行：策略矩阵（多 Python 版本并行测试）
- 第 35-37 行：用 `uv`（现代 Python 包管理器）安装依赖，比 pip 快 10-100 倍
- 第 40 行：`cache-dependency-glob` 自动缓存 `api/uv.lock` 依赖
- 第 50-52 行：先跑配置一致性测试（防止环境配置错误）
- 第 54-62 行：跑单元测试，`-n auto` 启用多核并行（pytest-xdist）

### 3.2 dify 的 Docker 镜像构建工作流

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/docker-build.yml`
**核心代码**（行 1-50）：

```yaml
name: Build docker image

on:
  pull_request:
    branches:
      - "main"
    paths:
      - api/Dockerfile
      - api/Dockerfile.dockerignore
      - api/pyproject.toml
      - api/uv.lock
      - dify-agent/pyproject.toml
      - dify-agent/README.md
      - dify-agent/src/**
      - web/Dockerfile

concurrency:
  group: docker-build-${{ github.head_ref || github.run_id }}
  cancel-in-progress: true

jobs:
  build-docker:
    if: github.event.pull_request.head.repo.full_name == github.repository
    runs-on: ${{ matrix.runs_on }}
    permissions:
      contents: read
      id-token: write
    strategy:
      matrix:
        include:
          - service_name: "api-amd64"
            platform: linux/amd64
            runs_on: depot-ubuntu-24.04-4
            context: "{{defaultContext}}"
            file: "api/Dockerfile"
          - service_name: "api-arm64"
            platform: linux/arm64
            runs_on: depot-ubuntu-24.04-4
            context: "{{defaultContext}}"
            file: "api/Dockerfile"
          - service_name: "web-amd64"
            platform: linux/amd64
            runs_on: depot-ubuntu-24.04-4
            context: "{{defaultContext}}"
            file: "web/Dockerfile"
          - service_name: "web-arm64"
            platform: linux/arm64
            runs_on: depot-ubuntu-24.04-4
            context: "{{defaultContext}}"
            file: "web/Dockerfile"
    steps:
      - name: Set up Depot CLI
        uses: depot/setup-action@15c09a5f77a0840ad4bce955686522a257853461 # v1.7.1

      - name: Build Docker Image
        uses: depot/build-push-action@98e78adca7817480b8185f474a400b451d74e287 # v1.18.0
        with:
          project: ${{ vars.DEPOT_PROJECT_ID }}
          push: false
          context: ${{ matrix.context }}
          file: ${{ matrix.file }}
          platforms: ${{ matrix.platform }}
```

**解读**：
- 第 3-15 行：**路径过滤**——只在 Dockerfile / 依赖文件改动时构建，节省 CI 时间
- 第 17-19 行：并发控制（同 PR 取消旧构建）
- 第 22-23 行：`if` 条件只对**非 fork 的内部 PR**运行（fork PR 无 secrets 权限）
- 第 28-50 行：矩阵构建——amd64 + arm64 各两个服务（api / web），共 4 个并行 job
- 第 53-55 行：用 **Depot**（depot.dev）构建，比 Docker Buildx 快 10-40 倍
- 第 59 行：`push: false` PR 阶段不推送镜像，只验证构建成功

### 3.3 dify 的部署工作流

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
- 第 3-9 行：`workflow_run` 触发器——**当另一个工作流（"Build and Push API & Web"）完成时触发**
- 第 12-13 行：只在上游 workflow 成功时才部署
- 第 18-24 行：用 `appleboy/ssh-action` 远程 SSH 到服务器执行部署脚本
- **典型流程**：开发分支 deploy/dev → 构建镜像 → 推送 → SSH 拉取镜像 → 重启服务

## 4. 关键要点总结

- GitHub Actions 用 YAML 定义**事件驱动的流水线**
- 核心要素：workflow / job / step / action / runner / event
- **矩阵构建**：一次跑多组合（多 OS / 多版本）
- **复用工作流**（`workflow_call`）让多个 workflow 共享步骤
- **Depot** 加速 Docker 构建（dify 用的第三方服务）
- **路径过滤** + **并发控制** 是优化 CI 资源的关键
- dify 用了 20+ 个工作流，覆盖测试、构建、部署、自动化

## 5. 练习题

### 练习 1：基础（必做）

为你的项目创建 `.github/workflows/test.yml`：当 push 到 main 时运行 pytest，配置 `concurrency` 取消旧运行。

### 练习 2：进阶

阅读 dify `main-ci.yml` 中 `check-changes` job 的输出，理解 `api-changed` / `web-changed` 等布尔值如何被后续 job 用 `if` 条件引用。

### 练习 3：挑战（选做）

用 `appleboy/ssh-action` 写一个部署工作流：把 `main` 分支的构建产物（Docker 镜像）部署到一台测试服务器，包含健康检查和回滚机制。

## 6. 参考资料

- `/Users/xu/code/github/dify/.github/workflows/main-ci.yml`
- `/Users/xu/code/github/dify/.github/workflows/api-tests.yml`
- `/Users/xu/code/github/dify/.github/workflows/docker-build.yml`
- `/Users/xu/code/github/dify/.github/workflows/deploy-dev.yml`
- GitHub Actions 官方文档：https://docs.github.com/en/actions

---

**文档版本**：v1.0
**最后更新**：2026-07-13
