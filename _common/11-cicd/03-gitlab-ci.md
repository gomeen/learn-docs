# 11.3 GitLab CI 实战

> 学会用 `.gitlab-ci.yml` 编写 GitLab CI 流水线，能与 GitHub Actions 写法互通。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 GitLab CI 的核心对象（stage / job / script / artifact）
- 编写一份 `.gitlab-ci.yml`，覆盖 build / test / deploy
- 理解 GitLab Runner 的工作原理
- 在 GitHub Actions 与 GitLab CI 之间迁移配置

## 📚 前置知识

- 11.1 - 11.2 节 CI/CD 概念
- GitLab / GitHub 平台的基本使用
- /Users/xu/code/gomeen/learn-docs/_common/11-cicd/02-github-actions.md

## 1. 核心概念

### 1.1 GitLab CI 与 GitHub Actions 的术语对照

| 概念 | GitLab CI | GitHub Actions |
|------|-----------|----------------|
| 配置文件 | `.gitlab-ci.yml` | `.github/workflows/*.yml` |
| 平台 runner | GitLab Runner（自托管） | GitHub-hosted runner |
| 阶段 | `stages:` | `jobs:` |
| 任务 | `job_name:` | `job_name:` |
| 步骤 | `script:` | `steps.run` |
| 自定义动作 | `extends:` / 镜像 | `uses: action@version` |
| 缓存 | `cache:` | `actions/cache@v4` |
| 产物 | `artifacts:` | `actions/upload-artifact@v4` |
| 变量 | `variables:` / `CI_*` | `env:` / `secrets.*` |
| 触发器 | `rules:` | `on:` |

### 1.2 核心对象：stage 与 job

```yaml
stages:                      # 阶段顺序
  - test
  - build
  - deploy

variables:                   # 全局变量
  PYTHON_VERSION: "3.12"

# 每个 job 都会跑
job_name:
  stage: test                # 属于哪个 stage
  image: python:3.12-slim    # runner 用什么镜像
  before_script:             # 阶段前置
    - pip install -r requirements.txt
  script:                    # 主逻辑（必须）
    - pytest
  after_script:              # 阶段后置
    - echo "done"
  artifacts:                 # 产物
    paths:
      - dist/
  only:                      # 触发条件（旧语法）
    - main
```

### 1.3 rules 是 GitLab CI 的核心触发器语法

```yaml
job_name:
  stage: deploy
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
      when: manual           # 手动触发
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
      when: never            # MR 上不跑
```

**rules** 比 `only/except` 更灵活，支持复杂条件。

### 1.4 GitLab Runner 原理

```
┌───────────────────────┐         ┌─────────────────────┐
│  GitLab CI Server     │  任务推送 │   GitLab Runner     │
│  (gitlab.com / 自托管) │────────►│  (执行容器/VM)       │
└───────────────────────┘        └─────────────────────┘
                                          │ docker run
                                          ↓
                                  ┌─────────────────────┐
                                  │  容器：debian-slim  │
                                  │  + 脚本            │
                                  └─────────────────────┘
```

Runner 是一个 daemon 进程，轮询 GitLab Server 拿任务，并用 Docker 执行 job（job 镜像由 `image:` 指定）。

## 2. 代码示例

### 2.1 完整 Python CI（GitLab CI）

```yaml
# 文件：.gitlab-ci.yml

image: python:3.12-slim

stages:
  - lint
  - test
  - build
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

# 共享：每个 job 都用
default:
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - .cache/pip

lint:
  stage: lint
  script:
    - pip install ruff
    - ruff check .
    - ruff format --check .

test:
  stage: test
  image: python:3.12-slim
  parallel: 3                  # 并行 3 个 job
  script:
    - pip install -r requirements.txt
    - pytest tests/ --cov=src

build:
  stage: build
  script:
    - pip install build
    - python -m build
  artifacts:
    paths:
      - dist/*.whl
    expire_in: 1 week

deploy-prod:
  stage: deploy
  rules:
    - if: '$CI_COMMIT_TAG =~ /^v[0-9]+\.[0-9]+\.[0-9]+$/'
  script:
    - ./scripts/deploy.sh production
  environment:
    name: production
    url: https://example.com
```

### 2.2 多语言混编（多阶段不同镜像）

```yaml
image: alpine:latest          # 默认镜像

build-frontend:
  stage: build
  image: node:20-alpine       # 覆盖默认镜像
  script:
    - cd web
    - npm ci
    - npm run build
  artifacts:
    paths:
      - web/dist

build-backend:
  stage: build
  image: python:3.12-slim     # 覆盖默认镜像
  script:
    - pip install .
    - python setup.py sdist
  artifacts:
    paths:
      - dist/*.tar.gz
```

### 2.3 常见错误：artifacts 跨 job 未传递

```yaml
# ❌ 错误：build job 没声明 artifact，downstream 拿不到
build:
  script: ./build.sh
deploy:
  script: ./deploy.sh         # 找不到编译产物

# ✅ 正确：声明 artifacts
build:
  script: ./build.sh
  artifacts:
    paths:
      - dist/
deploy:
  script: ./deploy.sh          # 此时 dist/ 可用
```

## 3. dify 与 ruoyi 源码解读

### 3.1 dify 仓库：没有 .gitlab-ci.yml

dify **完全使用 GitHub Actions**，没有 `.gitlab-ci.yml`。

但 GitLab 用户可以"导入" GitHub Actions 仓库，GitLab 会自动翻译 marketplace action（部分支持）。对于完全不想用 GitHub Actions 的场景，可以 fork 一个 `gitlab-ci.yml`。

**dify 的潜在 GitLab CI 等价改写**（用作团队参考）：

```yaml
# 文件：.gitlab-ci.yml （假如 dify 用 GitLab）
default:
  image: python:3.12-slim
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - api/.venv

stages:
  - lint
  - api-test
  - web-test
  - docker-build

# 对应 dify 的 'style.yml'
ruff:
  stage: lint
  before_script:
    - cd api
    - pip install ruff
  script:
    - ruff check .
    - ruff format --check .

# 对应 dify 的 'api-tests.yml'
api-tests:
  stage: api-test
  rules:
    - changes:
        paths:
          - api/**
          - docker/**
  before_script:
    - cd api
    - pip install uv
    - uv sync --frozen
  script:
    - uv run pytest tests/unit_tests/ -v
  artifacts:
    reports:
      junit: api/coverage.xml
```

### 3.2 ruoyi 仓库：实际部署常用 GitLab CI

许多使用 ruoyi 的团队在自建 GitLab 上托管代码，因为：
1. **代码保密性**：内部系统不能用 GitHub 公有云
2. **集成化平台**：GitLab 提供代码托管 + CI + CD 一站式
3. **国内团队偏好**：国内自建 GitLab 比例高（多年前 GitHub 慢）

**典型 ruoyi GitLab CI 示例**：

```yaml
# 文件：.gitlab-ci.yml
image: maven:3.9-eclipse-temurin-8

stages:
  - compile
  - deploy

variables:
  MAVEN_OPTS: "-Dmaven.repo.local=$CI_PROJECT_DIR/.m2/repository"
  MAVEN_CLI_OPTS: "--batch-mode --errors"

cache:
  paths:
    - .m2/repository

# 对应 ruoyi Jenkinsfile 的 '检出' 阶段
# (GitLab 自动 checkout，无需脚本)

# 对应 ruoyi Jenkinsfile 的 '构建' 阶段
compile:
  stage: compile
  script:
    - cd yudao-server
    - mvn clean package $MAVEN_CLI_OPTS -Dmaven.test.skip=true
  artifacts:
    paths:
      - yudao-server/target/*.jar
    expire_in: 7 days

# 对应 ruoyi Jenkinsfile 的 '部署' 阶段
deploy-dev:
  stage: deploy
  script:
    - cp yudao-server/target/yudao-server.jar /work/projects/build/
    - ssh deploy@dev-server "bash /work/projects/yudao-server/deploy.sh"
  only:
    - dev
  when: manual          # 需要手动触发部署
```

**vs ruoyi 的 Jenkinsfile（11.1 节）对比**：

| 阶段 | Jenkinsfile | GitLab CI |
|------|-------------|-----------|
| 检出 | `git url: ...` | 自动 |
| 凭证管理 | Jenkinsfile environment {} Credentials | GitLab CI/CD Variables（Settings 里配）|
| 条件判断 | `when {}` | `rules:` / `only:` |
| 触发 | 手动点 / webhook | 推送 / tag / schedule |
| 产物 | `archiveArtifacts` | `artifacts: paths:` |

**核心优势**：
- GitLab CI 不需要额外维护 Jenkins 实例
- GitLab 仓库的 `protected branches` 直接对接 CI/CD
- 改动仓库即部署（少一个人工环节）

### 3.3 三平台迁移难易度

```
GitHub Actions  ─── 强映射 ──►  GitLab CI
                ─── 强映射 ──►  Jenkins
```

| 概念 | GitHub Actions | GitLab CI | Jenkins |
|------|----------------|-----------|---------|
| 触发器 | `on:` | `rules:` / `only` | `triggers {}` |
| 步骤语法 | YAML 列表 | YAML 列表 | Groovy DSL |
| 学习曲线 | 平缓 | 中等 | 陡 |

**实际迁移成本**：
1. **GitHub Actions → GitLab CI**：~70% 自动翻译；自定义 action 需改写
2. **GitLab CI → GitHub Actions**：~50% 自动翻译；runner-specific script 需改写
3. **Jenkins → 其他**：需要重写 pipeline（完全不同语言）

## 4. 关键要点总结

- **核心层级**：stages > jobs > script，jobs 共享一个 stage
- **`rules` vs `only/except`**：rules 是新版，灵活；only 是旧版
- **artifacts 跨 job 传递**：必须显式声明 paths
- **cache 依赖哈希**：自动对 requirements.txt 之类做 hash
- **GitLab Runner 自托管**：可以弹性配置 docker executor
- **移植物色**：dify 单一 GitHub Actions，ruoyi 团队自定义灵活

## 5. 练习题

### 练习 1：基础（必做）

把 11.2 练习 1 的 GitHub Actions workflow 改写为 `.gitlab-ci.yml`。

**参考答案**：见 `solutions/01-gitlab-ci-pytest.md`

### 练习 2：进阶

设计一份 GitLab CI 多 project pipeline：
1. 项目 A：`library`（构建 jar 包）
2. 项目 B：`app`（依赖 library）

要求：
- B 等待 A 的 latest build 发布后再部署
- 用 GitLab 的 `trigger:` 多项目触发

### 练习 3：挑战（选做）

把 `ruoyi-vue-pro/script/jenkins/Jenkinsfile` 改写为 `.gitlab-ci.yml`：
- 加入 `cache:` 复用 `.m2/repository`
- 加入 `artifacts: paths:` 跨 stage 传递 jar
- 用 `environment:` 把 deploy-dev 标记为 GitLab Environment（带 URL）

## 6. 参考资料

- `/Users/xu/code/github/dify/.github/workflows/docker-build.yml`（GitHub Actions 模板）
- `/Users/xu/code/github/ruoyi-vue-pro/script/jenkins/Jenkinsfile`（Jenkins 模板）
- GitLab CI 官方文档：https://docs.gitlab.com/ee/ci/
- GitLab CI Lint 工具：https://gitlab.com/-/ci/lint（在线校验 .gitlab-ci.yml）
- GitLab vs GitHub Actions：https://about.gitlab.com/devops-tools/github-vs-gitlab/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
