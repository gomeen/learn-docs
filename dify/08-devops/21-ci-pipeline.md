# 4.4 自动化测试与构建流水线

> 学习如何设计完整的 CI 流水线（lint + test + build + publish），能读懂 dify 的实际工作流。

## 🎯 学习目标

完成本文档后，你将能够：
- 设计涵盖 lint / test / build / publish 的完整流水线
- 理解并发控制、缓存、矩阵构建等优化手段
- 区分 PR 阶段（验证）和 main 阶段（发布）的不同策略

## 📚 前置知识

- `08-devops/18-cicd-concepts.md`
- `08-devops/19-github-actions.md`

## 1. 核心概念

### 1.1 完整 CI 流水线的阶段

```
┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────────┐
│ 检出 │→│ 安装 │→│ Lint │→│ Test │→│ Build │→│ Publish │
└──────┘  └──────┘  └──────┘  └──────┘  └──────┘  └──────────┘
```

| 阶段 | 目的 | 失败时的影响 |
|------|------|---------------|
| Lint | 代码风格 / 类型检查 | 阻止合并 |
| Test | 单元 / 集成 / E2E 测试 | 阻止合并 |
| Build | 构建产物（镜像 / 包） | 阻止合并 |
| Publish | 发布到仓库（仅 main） | 通知，不阻止 |

### 1.2 PR 阶段 vs main 阶段

- **PR 阶段**：快速验证，**不推送**到生产仓库
  - 跑 lint + test + build（验证可构建）
  - 失败立即阻止合并
- **main 阶段**：完整发布流程
  - 全量测试 + 构建 + 推送镜像 + 打 tag
  - 失败触发告警

### 1.3 关键优化

- **路径过滤**（paths-filter）：只跑相关测试
- **缓存依赖**：pip/uv/npm 缓存加速
- **矩阵构建**：多版本并行
- **并发控制**：取消旧运行
- **复用工作流**（workflow_call）：抽公共步骤
- **专用 Runner**：自托管 / Depot 加速

## 2. 代码示例

### 2.1 完整 CI 流水线

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install ruff
      - run: ruff check .

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
          cache: pip
      - run: pip install -r requirements.txt
      - run: pytest --cov

  build:
    needs: [lint, test]            # 等待前面都通过
    runs-on: ubuntu-latest
    if: github.event_name == 'push' # 只在 push 时构建
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t myapp:${{ github.sha }} .

  publish:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    permissions:
      packages: write
    steps:
      - uses: actions/checkout@v4
      - run: docker login -u ${{ secrets.REGISTRY_USER }} -p ${{ secrets.REGISTRY_TOKEN }}
      - run: docker push myapp:${{ github.sha }}
      - run: docker tag myapp:${{ github.sha }} myapp:latest
      - run: docker push myapp:latest
```

### 2.2 缓存与制品

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
    cache: "pip"

- uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: ${{ runner.os }}-uv-${{ hashFiles('**/uv.lock') }}

- uses: actions/upload-artifact@v4
  with:
    name: dist
    path: dist/
    retention-days: 7
```

### 2.3 常见错误：缺少权限声明

```yaml
# ❌ 错误：push 镜像时 GITHUB_TOKEN 权限不足
- run: docker push ghcr.io/myorg/myapp

# ✅ 正确：显式声明 packages: write
permissions:
  packages: write
```

## 3. dify 仓库源码解读

### 3.1 dify 的多阶段测试工作流

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/api-tests.yml`
**核心代码**（行 16-100）：

```yaml
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
          # Controller tests register Flask routes at import time, so keep them out of xdist.
          uv run --project api pytest \
            --timeout "${PYTEST_TIMEOUT:-20}" \
            --cov-append \
            api/tests/unit_tests/controllers

      - name: Upload unit coverage data
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: api-coverage-unit
          path: coverage-unit
          retention-days: 1
```

**解读**：

测试设计（分层）：
- 第 50-51 行：**配置一致性测试**（`test_env_consistency.py`）—— 防止 `.env` 与代码不一致
- 第 54-62 行：单元测试用 `pytest-xdist` 的 `-n auto` 多核并行
- 第 63-67 行：**Controller 测试单独跑**（不并行）—— 注释解释：Controller 在 import 时注册 Flask 路由，xdist 会冲突
- 第 70-74 行：上传 coverage 数据（1 天保留期）

关键优化：
- 第 14-17 行：自定义 `depot-ubuntu-24.04` Runner 加速
- 第 38-42 行：`uv` 缓存（`cache-dependency-glob`）
- 第 45 行：`uv lock --check` 验证 lock 文件一致（防止 PR 改了依赖但没 lock）

### 3.2 dify 的镜像构建流水线

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/docker-build.yml`
**核心代码**（行 22-60）：

```yaml
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

矩阵设计：
- 4 个并行构建：api × {amd64, arm64} + web × {amd64, arm64}
- 总耗时 ≈ 单个构建时间（不是 4 倍）

PR 阶段策略：
- 第 23 行：`if` 条件只对**非 fork 内部 PR**运行（fork PR 无 secrets）
- 第 59 行：`push: false` PR 阶段不推送镜像，只验证构建
- 主分支合并后才由 `build-push.yml` 真正推送

性能优化：
- 用 **Depot**（`depot.dev`）替代原生 Docker Buildx，构建速度提升 10-40 倍
- 通过远程 BuildKit 缓存（共享 layer 缓存）

### 3.3 dify 的 lint / style 检查

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/style.yml`（参考）

典型内容（dify 的实际内容可能略有不同）：

```yaml
name: Code Style

on:
  pull_request:
    branches: [main]

jobs:
  ruff:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v8
      - run: uv sync --project api --dev
      - run: uv run --project api ruff check api/
      - run: uv run --project api ruff format --check api/
```

**解读**：
- 用 `ruff`（极快的 Python linter，比 flake8 快 10-100 倍）
- 同时检查 `check`（语法）和 `format`（格式）

## 4. 关键要点总结

- 完整 CI 流水线：lint → test → build → publish
- **PR 阶段不推送**，main 阶段才推送
- 关键优化：**路径过滤**、**缓存依赖**、**矩阵构建**、**专用 Runner**
- dify 用 **Depot** 加速 Docker 构建（4 镜像并行，跨 amd64+arm64）
- dify 用 `uv` 加速 Python 依赖安装
- Controller 测试因 Flask 路由注册冲突，**必须单独跑**（不能 xdist 并行）

## 5. 练习题

### 练习 1：基础（必做）

为你的 Python 项目写一个完整 CI：lint（ruff）+ test（pytest）+ build（docker），配置缓存和并发控制。

### 练习 2：进阶

阅读 dify `api-tests.yml` 全文，统计一共有多少个 job、它们之间的依赖关系。理解 `api-integration` 和 `api-unit` 的区别。

### 练习 3：挑战（选做）

把 dify 的 PR 阶段工作流改造成"PR 阶段跑快速测试，main 阶段跑全量测试 + 推送镜像"。用 `if: github.event_name == 'pull_request'` 实现。

## 6. 参考资料

- `/Users/xu/code/github/dify/.github/workflows/api-tests.yml`
- `/Users/xu/code/github/dify/.github/workflows/docker-build.yml`
- `/Users/xu/code/github/dify/.github/workflows/main-ci.yml`
- `/Users/xu/code/github/dify/.github/workflows/style.yml`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
