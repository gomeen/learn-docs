# 4.1 CI/CD 概念与流水线设计

> 理解 CI（持续集成）/ CD（持续交付 / 持续部署）的核心概念，能设计完整流水线。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 CI / CD（持续交付）/ CD（持续部署）的差异
- 理解流水线（Pipeline）的关键阶段：build / test / publish / deploy
- 了解 dify 仓库 `.github/workflows/` 下的工作流设计

## 📚 前置知识

- Git 基础（`branch`、`commit`、`merge`）
- `08-devops/01-docker-concepts.md`

## 1. 核心概念

### 1.1 CI/CD 是什么？

- **CI（Continuous Integration，持续集成）**：开发人员频繁合并代码到主干，每次合并触发自动化构建和测试
- **CD（Continuous Delivery，持续交付）**：CI 的基础上，**自动**准备发布产物（镜像、二进制包），但**人工决定**何时部署到生产
- **CD（Continuous Deployment，持续部署）**：进一步自动化，**自动**部署到生产环境

```
开发 → CI（构建+测试）→ CD（交付）→ 人工审批 → CD（部署）→ 生产
```

### 1.2 关键收益

| 维度 | 收益 |
|------|------|
| **质量** | 每次提交都测试，问题早发现 |
| **速度** | 自动化取代手工操作，部署从小时级降到分钟级 |
| **风险** | 小批量频繁发布，单次变更小，回滚快 |
| **可观测** | 流水线状态可视化，问题定位快 |

### 1.3 流水线关键阶段

```
┌────────┐  ┌──────┐  ┌─────────┐  ┌────────┐  ┌───────┐
│ 检出   │→│ 安装 │→│ 静态检查 │→│ 单元测试 │→│ 构建  │
│ (Checkout) │ (Setup) │ (Lint)   │ (Test)  │ (Build) │
└────────┘  └──────┘  └─────────┘  └────────┘  └───────┘
                                                       │
                                                       ▼
                                            ┌──────────┐
                                            │ 发布镜像  │
                                            │ (Publish)│
                                            └──────────┘
                                                       │
                                                       ▼
                                            ┌──────────┐
                                            │ 部署     │
                                            │ (Deploy) │
                                            └──────────┘
```

### 1.4 常见工具

- **GitHub Actions**（dify 用的）
- **GitLab CI**
- **Jenkins**（自托管，功能最强）
- **CircleCI / Travis CI**（SaaS）
- **Drone**（轻量级）

## 2. 代码示例

### 2.1 最小 GitHub Actions 流水线

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -r requirements.txt
      - run: pytest
```

### 2.2 多阶段流水线

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest

  build:
    needs: test                       # 等待 test 通过
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t myapp:${{ github.sha }} .

  deploy-staging:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - run: kubectl apply -f k8s/staging/

  deploy-prod:
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production           # 关联环境（审批）
    steps:
      - run: kubectl apply -f k8s/prod/
```

### 2.3 流水线即代码（Pipeline as Code）

把流水线定义**写在仓库里**（YAML 文件），好处：
- 版本化：流水线变更可追溯
- 复用：模板化组织内所有项目
- 审查：流水线变更走 PR 流程

### 2.4 常见错误：缺少并发控制

```yaml
# ❌ 错误：每次 push 都触发，浪费资源
on: push
# 同一分支多次 push 会排队执行

# ✅ 正确：用 concurrency 取消旧运行
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

## 3. dify 仓库源码解读

### 3.1 dify 的工作流文件清单

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/`

**核心文件**（按职责分类）：

| 文件 | 职责 |
|------|------|
| `main-ci.yml` | 主 CI 流水线（按改动路径分派任务） |
| `api-tests.yml` | API 单元/集成测试 |
| `docker-build.yml` | Docker 镜像构建（PR 时） |
| `build-push.yml` | Docker 镜像构建+推送（合并后） |
| `deploy-dev.yml` / `deploy-saas.yml` / `deploy-enterprise.yml` | 多环境部署 |
| `style.yml` | 代码风格检查 |
| `labeler.yml` | 自动打 PR 标签 |
| `autofix.yml` | 自动修复（black/isort） |
| `cli-tests.yml` / `cli-e2e.yml` / `cli-smoke.yml` | CLI 测试 |
| `semantic-pull-request.yml` | PR 标题语义化检查 |
| `stale.yml` | 自动关闭长期未维护 Issue |

### 3.2 dify 的主 CI 流水线（节选）

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/main-ci.yml`
**核心代码**（行 1-72）：

```yaml
name: Main CI Pipeline

on:
  pull_request:
    branches: ["main"]
  merge_group:
    branches: ["main"]
    types: [checks_requested]

permissions:
  actions: write
  contents: write
  pull-requests: write
  checks: write
  statuses: write

concurrency:
  group: main-ci-${{ github.head_ref || github.run_id }}
  cancel-in-progress: true

jobs:
  pre_job:
    name: Skip Duplicate Checks
    runs-on: depot-ubuntu-24.04
    outputs:
      should_skip: ${{ steps.skip_check.outputs.should_skip || 'false' }}
    steps:
      - id: skip_check
        continue-on-error: true
        uses: fkirc/skip-duplicate-actions@f75f66ce1886f00957d99748a42c724f4330bdcf # v5.3.1
        with:
          cancel_others: 'true'
          concurrent_skipping: same_content_newer

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
```

**解读**：
- 第 1-8 行：触发器（PR 到 main 分支）+ 完整权限声明
- 第 17-19 行：**concurrency 控制**——同一 PR 多次 push 时取消旧运行
- 第 22-34 行：`pre_job` 用 `fkirc/skip-duplicate-actions` 跳过内容相同的重复运行
- 第 36-71 行：`check-changes` 用 `dorny/paths-filter` 识别改动的路径，**只运行相关测试**
  - `api-changed` / `cli-changed` / `e2e-changed` 等作为后续 Job 的判断条件
  - 节省 CI 资源，只跑相关组件的测试

### 3.3 dify 的 Docker 镜像构建

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/docker-build.yml`
**核心代码**（行 1-30）：

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
```

**解读**：
- 第 3-15 行：**路径过滤**——只有 Dockerfile / 依赖文件改动时才构建
- 第 17-19 行：并发控制（同 PR 取消旧构建）
- 第 22-23 行：`if` 条件只对**内部 PR**（非 fork）运行完整构建
- 矩阵构建：amd64 + arm64 各编译一次

## 4. 关键要点总结

- **CI** 自动化构建和测试；**CD（交付）**自动出包；**CD（部署）**自动上线
- 流水线分阶段：build / test / publish / deploy
- **并发控制**节省 CI 资源（同分支取消旧运行）
- **路径过滤**只跑相关测试（`dorny/paths-filter`）
- dify 用 GitHub Actions，10+ 个工作流文件覆盖测试、构建、部署
- dify 的 `main-ci.yml` 用 `check-changes` 智能分派测试任务

## 5. 练习题

### 练习 1：基础（必做）

为你的个人项目写一个 `.github/workflows/ci.yml`：当 push 到 main 时运行 pytest，把状态显示在 README 徽章中。

### 练习 2：进阶

阅读 dify `main-ci.yml` 全文，列出所有 jobs 和它们之间的依赖关系（用 mermaid 画图）。理解 `check-changes` 输出的 `api-changed` 等变量如何被后续 job 使用。

### 练习 3：挑战（选做）

为 dify 设计一份"PR 时构建预览环境"工作流：当 PR 创建时，自动构建一个独立的 docker-compose 栈，部署到临时域名，PR 评论里附上访问链接。

## 6. 参考资料

- `/Users/xu/code/github/dify/.github/workflows/main-ci.yml`
- `/Users/xu/code/github/dify/.github/workflows/docker-build.yml`
- `/Users/xu/code/github/dify/.github/workflows/api-tests.yml`
- GitHub Actions 官方文档：https://docs.github.com/en/actions

---

**文档版本**：v1.0
**最后更新**：2026-07-13
