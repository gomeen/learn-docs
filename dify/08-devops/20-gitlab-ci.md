# 4.3 GitLab CI 入门

> 学会用 GitLab CI 编写 `.gitlab-ci.yml`，能与 GitHub Actions 对照学习。

> ⚠️ **dify 主仓库使用 GitHub Actions，未直接使用 GitLab CI**。本文档基于通用 GitLab CI 概念讲解。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 GitLab CI 的核心概念：pipeline / stage / job
- 编写 `.gitlab-ci.yml` 多阶段流水线
- 比较 GitLab CI 与 GitHub Actions 的差异

## 📚 前置知识

- `08-devops/18-cicd-concepts.md`
- `08-devops/19-github-actions.md`

## 1. 核心概念

### 1.1 GitLab CI 是什么？

GitLab CI 是 GitLab 内置的 CI/CD 平台。配置文件为 `.gitlab-ci.yml`（在仓库根目录）。

### 1.2 核心概念

- **Pipeline**：一次完整的流水线执行（对应一次 push/PR）
- **Stage**：阶段（一组 job，串行执行）
- **Job**：任务（同一 stage 内并行执行）
- **Runner**：执行 Job 的 agent
- **Artifact**：构建产物（供后续 job 下载）

### 1.3 Pipeline 结构

```
Pipeline
├── Stage: test
│   ├── Job: lint
│   └── Job: unit-test
├── Stage: build
│   └── Job: docker-build
└── Stage: deploy
    └── Job: deploy-staging
    └── Job: deploy-prod (manual)
```

- 同一 stage 的 job **并行**执行
- 跨 stage **串行**执行（必须前一阶段所有 job 成功）

### 1.4 GitLab CI vs GitHub Actions

| 维度 | GitLab CI | GitHub Actions |
|------|-----------|----------------|
| 配置文件 | `.gitlab-ci.yml` | `.github/workflows/*.yml` |
| 阶段模型 | 显式 `stages` | 隐式（用 `needs` 表达） |
| Runner | GitLab Runner（自托管/SaaS） | GitHub Runner（托管） |
| 缓存 | `cache:` 关键字 | `actions/cache` action |
| 制品 | `artifacts:` 关键字 | `actions/upload-artifact` |
| 触发 | `rules:` / `only:` | `on:` |
| 手动审批 | `when: manual` | `environment` + 审批规则 |

## 2. 代码示例

### 2.1 最小流水线

```yaml
# .gitlab-ci.yml
stages:
  - test
  - deploy

test:
  stage: test
  image: python:3.12
  script:
    - pip install -r requirements.txt
    - pytest

deploy:
  stage: deploy
  script:
    - echo "Deploying..."
  only:
    - main
```

### 2.2 多阶段流水线

```yaml
stages:
  - lint
  - test
  - build
  - deploy

lint:
  stage: lint
  image: python:3.12
  script:
    - pip install ruff
    - ruff check .

test:
  stage: test
  image: python:3.12
  script:
    - pip install -r requirements.txt
    - pytest
  coverage: '/(?i)total.*? (100(?:\.0+)?\%|[1-9]?\d(?:\.\d+)?\%)$/'

build:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  script:
    - docker build -t myapp:$CI_COMMIT_SHA .
    - docker push myapp:$CI_COMMIT_SHA

deploy-staging:
  stage: deploy
  script:
    - kubectl apply -f k8s/staging/
  environment:
    name: staging
  only:
    - main

deploy-prod:
  stage: deploy
  script:
    - kubectl apply -f k8s/prod/
  environment:
    name: production
  when: manual           # 手动触发
  only:
    - main
```

### 2.3 缓存与制品

```yaml
test:
  stage: test
  image: python:3.12
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - .cache/pip
  script:
    - pip install -r requirements.txt
    - pytest
  artifacts:
    paths:
      - coverage/
    expire_in: 7 days
```

### 2.4 常见错误：stage 顺序错乱

```yaml
# ❌ 错误：未声明 stages，所有 job 都在同一 stage（并行）
script:
  - pytest
script:
  - deploy

# ✅ 正确：声明 stages
stages:
  - test
  - deploy
```

## 3. dify 仓库源码解读

### 3.1 dify 主仓库的 CI 工具

**说明**：dify 主仓库使用 **GitHub Actions**，仓库中**没有** `.gitlab-ci.yml`。

如果 dify 团队迁移到 GitLab CI，配置会类似：

```yaml
# 假想的 .gitlab-ci.yml（迁移版）
stages:
  - lint
  - test
  - build
  - deploy

variables:
  UV_VERSION: "0.8.9"
  PYTHON_VERSION: "3.12"

# 路径过滤
.api-changes: &api-changes
  changes:
    - api/**/*
    - docker/**/*
    - .github/workflows/api-tests.yml

api-lint:
  stage: lint
  image: python:3.12
  script:
    - pip install uv==$UV_VERSION
    - uv sync --project api --dev
    - uv run --project api ruff check api/
  rules:
    - <<: *api-changes

api-test:
  stage: test
  image: python:3.12
  script:
    - pip install uv==$UV_VERSION
    - uv sync --project api --dev
    - uv run --project api pytest api/tests/unit_tests
  coverage: '/(?i)total.*? (100(?:\.0+)?\%|[1-9]?\d(?:\.\d+)?\%)$/'
  artifacts:
    paths:
      - coverage/
  rules:
    - <<: *api-changes
```

### 3.2 dify 的 `.devcontainer`

**文件位置**：`/Users/xu/code/github/dify/.devcontainer/Dockerfile`（参考）

dify 的开发容器配置：

```dockerfile
FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

# Install uv
ENV UV_VERSION=0.8.9
RUN pip install --no-cache-dir uv==${UV_VERSION}

# Install Node.js for web frontend
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs
```

**解读**：
- `.devcontainer` 让开发者**一键启动**与 CI 完全一致的开发环境
- 包含 Python 3.12 + Node.js 22 + uv
- 这种容器化开发环境**可在 GitLab CI Runner 中复用**

### 3.3 dify 的部署流程（GitLab CI 化示例）

参考 `deploy-dev.yml`，迁移到 GitLab CI：

```yaml
# 假想的部署 stage
deploy-dev:
  stage: deploy
  image: alpine:3.20
  before_script:
    - apk add --no-cache openssh-client
  script:
    - eval $(ssh-agent -s)
    - echo "$SSH_PRIVATE_KEY" | tr -d '\r' | ssh-add -
    - ssh -o StrictHostKeyChecking=no $SSH_USER@$SSH_HOST
        "cd /opt/dify && docker compose pull && docker compose up -d"
  environment:
    name: development
    url: https://dev.dify.example.com
  rules:
    - if: $CI_COMMIT_BRANCH == "deploy/dev"
  when: manual
```

## 4. 关键要点总结

- GitLab CI 用 **`.gitlab-ci.yml`** 定义 pipeline
- 核心概念：**stage**（阶段，串行）+ **job**（任务，可并行）
- 用 `rules:` 替代 GitHub 的 `on:` 触发器
- 用 `artifacts:` 上传制品，用 `cache:` 缓存依赖
- `when: manual` 实现手动审批
- dify 暂未使用 GitLab CI，但配置模式与 GitHub Actions 类似
- **devcontainer** 让 CI 与开发环境一致

## 5. 练习题

### 练习 1：基础（必做）

用 GitLab.com 的公共仓库或本地 GitLab CE，编写一个 `.gitlab-ci.yml`：包含 `test` 和 `build` 两个 stage，分别运行 pytest 和 `docker build`。

### 练习 2：进阶

把 dify 的 `api-tests.yml`（GitHub Actions 版）改写成 GitLab CI 版，保留 `uv` 安装、pytest 矩阵、coverage 上传等关键步骤。

### 练习 3：挑战（选做）

用 GitLab CI 的 `include` 关键字抽取公共配置（lint、test）到模板项目，让多个项目复用同一套 CI 流程。

## 6. 参考资料

- `/Users/xu/code/github/dify/.github/workflows/api-tests.yml`（对照 GitHub Actions 版）
- `/Users/xu/code/github/dify/.github/workflows/deploy-dev.yml`
- `/Users/xu/code/github/dify/.devcontainer/Dockerfile`
- GitLab CI 官方文档：https://docs.gitlab.com/ee/ci/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
