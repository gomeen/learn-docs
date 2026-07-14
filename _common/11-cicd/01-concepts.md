# 11.1 CI/CD 概念与流水线设计

> 理解持续集成 / 持续交付 / 持续部署的本质区别，掌握流水线设计方法，对比 dify 与 ruoyi 的流水线架构。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 CI（持续集成）与 CD（持续交付 / 持续部署）
- 绘制标准 CI/CD 流水线（构建 → 测试 → 部署）
- 解释为什么 dify 用 GitHub Actions、ruoyi 用 Jenkins
- 理解**基于路径的变更检测**（dify 的做法）与 ruoyi 的"全量构建"差异

## 📚 前置知识

- Git 基本操作（分支 / 合并 / PR）
- Docker 镜像构建与推送
- 单元测试与集成测试基本概念
- /Users/xu/code/gomeen/learn-docs/_common/09-containerization/01-concepts.md

## 1. 核心概念

### 1.1 CI / CD / CD 三个"C"的含义

```
             持续集成(CI)         持续交付(CD)        持续部署(CD)
时间线 ────────────────────────────────────────────────────►
        │               │                  │
        ↓               ↓                  ↓
   合并代码时      自动化构建产物      自动部署到生产
   自动运行测试    生成可发布的       无人工干预
                 包/镜像             "按按钮"或全自动
```

| 缩写 | 全称 | 关键产出 | 是否自动化部署到生产 |
|------|------|---------|---------|
| **CI** | Continuous Integration | 测试通过 + 构建产物 | 否 |
| **交付** | Continuous Delivery | 可手动一键部署的产物 | 否（人工按按钮） |
| **部署** | Continuous Deployment | 自动部署到生产 | 是 |

### 1.2 标准流水线阶段

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 检出代码 │───►│ 安装依赖 │───►│ 静态检查 │───►│ 运行测试 │───►│ 构建发布 │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
   (git)        (npm/pip)     (lint/type)    (unit/e2e)     (image/jar)
                                                              ↓
                                                       ┌─────────────┐
                                                       │   部署      │
                                                       │ dev/staging │
                                                       │ /production │
                                                       └─────────────┘
```

### 1.3 GitHub Actions vs Jenkins：设计哲学对比

| 维度 | GitHub Actions | Jenkins |
|------|----------------|---------|
| 配置即代码 | `.github/workflows/*.yml` | `Jenkinsfile` |
| 宿主 | GitHub 托管（runner） | 自建 agent |
| 生态 | Marketplace 大 | Plugin 大 |
| 入门门槛 | 低（YAML 即一切） | 中（需装插件 + 管理 agent） |
| 自托管需求 | 可选（self-hosted runner）| 强制 |
| 适合场景 | 开源项目、创业公司 | 企业内部、复杂流水线 |

### 1.4 核心概念：路径过滤

dify 的流水线是**模块化、按需运行**的——只有 API 相关文件改了才跑 API 测试，否则跳过：

```yaml
filters: |
  api:
    - 'api/**'
    - 'docker/.env.example'
    - 'docker/docker-compose.yaml'
  cli:
    - 'cli/**'
  web:
    - 'web/**'
```

这种设计的优势：**节省 CI 时间**，避免每次 PR 都全量跑测试。ruoyi 的 Jenkins 没有这种过滤，每次都跑全部。

## 2. 代码示例

### 2.1 通用流水线伪代码

```yaml
# 概念性流水线
stages:
  - checkout       # git clone
  - install        # npm ci / pip install
  - lint           # eslint / ruff
  - typecheck      # tsc / mypy
  - test_unit      # pytest --cov
  - test_e2e       # playwright / cypress
  - build_image    # docker build
  - push_image     # docker push
  - deploy_dev     # kubectl apply / docker stack deploy
  - smoke_test     # curl /health
```

### 2.2 CI 流水线（最小可行版）

```yaml
# 文件：.github/workflows/ci.yml
name: CI

on:
  pull_request: { branches: [main] }
  push: { branches: [main] }

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Lint with ruff
        run: ruff check .

      - name: Type check with mypy
        run: mypy .

      - name: Run pytest
        run: pytest tests/ --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### 2.3 常见错误：所有改动跑全部 job

```yaml
# ❌ 错误：前端改了也跑后端测试（浪费 5 分钟）
on: pull_request
jobs:
  backend-test:    # 即使只改 web/ 也会跑
  frontend-test:
  e2e-test:

# ✅ 正确：用路径过滤或显式 if 条件
on:
  pull_request:
    paths:
      - 'api/**'
jobs:
  backend-test:
    if: contains(github.event.pull_request.changed_files, 'api/')
```

## 3. dify 与 ruoyi 源码解读

### 3.1 dify：基于变更路径的并行流水线

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/main-ci.yml`
**核心代码**（行 50-72）：

```yaml
      - uses: dorny/paths-filter@7b450fff21473bca461d4b92ce414b9d0420d706 # v4.0.2
        id: changes
        with:
          filters: |
            api:
              - 'api/**'
              - 'scripts/ast_grep_guard.py'
              - 'scripts/check_no_new_getattr.py'
              - 'scripts/check_no_new_controller_sqlalchemy.py'
              - 'scripts/lint_controller_sqlalchemy.py'
              - 'scripts/ast_grep_rules/no_new_getattr.yml'
              - 'scripts/ast_grep_rules/no_new_controller_sqlalchemy.yml'
              - '.github/workflows/style.yml'
              - '.github/workflows/main-ci.yml'
              - '.github/workflows/api-tests.yml'
              - 'docker/.env.example'
              - 'docker/envs/middleware.env.example'
              - 'docker/docker-compose.middleware.yaml'
              - 'docker/docker-compose-template.yaml'
              - 'docker/generate_docker_compose'
              - 'docker/ssrf_proxy/**'
              - 'docker/volumes/sandbox/conf/**'
            cli:
              - 'cli/**'
```

**解读**：
- 第 50 行：`dorny/paths-filter@v4.0.2`——GitHub Action 用来判断哪些路径被修改
- 第 51 行：输出 ID `changes` 供后续 job 用 `needs.check-changes.outputs.api-changed`
- 第 53-58 行：`api:` filter 包含 `api/**` 还有 CI 脚本、ASt_grep 规则——这些是 API 间接依赖
- 第 72 行：`cli:` filter 包含 `cli/**`——CLI 改动会触发 CLI 测试

**为什么把 `scripts/ast_grep_guard.py` 也算 api 改动？**
- 修改了一个公共脚本，理论上所有依赖它的人都需要测试
- dify 这种"主动权极强"的策略避免脚本改动时漏掉测试

### 3.2 dify：分层任务编排

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/main-ci.yml`
**核心代码**（行 145-205）：

```yaml
  # Run tests in parallel while always emitting stable required checks.
  api-tests-run:
    name: Run API Tests
    needs:
      - pre_job
      - check-changes
    if: needs.pre_job.outputs.should_skip != 'true' && needs.check-changes.outputs.api-changed == 'true'
    uses: ./.github/workflows/api-tests.yml
    secrets: inherit

  api-tests-skip:
    name: Skip API Tests
    needs:
      - pre_job
      - check-changes
    if: needs.pre_job.outputs.should_skip != 'true' && needs.check-changes.outputs.api-changed != 'true'
    runs-on: depot-ubuntu-24.04
    steps:
      - name: Report skipped API tests
        run: echo "No API-related changes detected; skipping API tests."

  api-tests:
    name: API Tests
    if: ${{ always() }}
    needs:
      - pre_job
      - check-changes
      - api-tests-run
      - api-tests-skip
    runs-on: depot-ubuntu-24.04
    steps:
      - name: Finalize API Tests status
        env:
          SHOULD_SKIP_WORKFLOW: ${{ needs.pre_job.outputs.should_skip }}
          TESTS_CHANGED: ${{ needs.check-changes.outputs.api-changed }}
          RUN_RESULT: ${{ needs.api-tests-run.result }}
          SKIP_RESULT: ${{ needs.api-tests-skip.result }}
        run: |
          if [[ "$SHOULD_SKIP_WORKFLOW" == 'true' ]]; then
            echo "API tests were skipped because this workflow run duplicated a successful or newer run."
            exit 0
          fi

          if [[ "$TESTS_CHANGED" == 'true' ]]; then
            if [[ "$RUN_RESULT" == 'success' ]]; then
              echo "API tests ran successfully."
              exit 0
            fi

            echo "API tests were required but finished with result: $RUN_RESULT" >&2
            exit 1
          fi
```

**解读**：

**A. 三 job 模式（run / skip / finalize）**：
- `api-tests-run`：实际跑测试（有 api 改动时）
- `api-tests-skip`：跳过（无改动时打印 "skipping"）
- `api-tests`：**finalizer**——根据前两者的结果判定最终状态

**B. 为什么需要 finalizer？**
- GitHub Branch Protection 要求"required check" 必须出现 success/failure
- 如果只跳过，会显示"无结果"，违反 branch protection 规则
- finalizer 始终输出 success 或 failure，确保 required check 总是有状态

**C. `if: ${{ always() }}` 关键**：finalizer 即使前者失败也要运行（用于汇总状态）

**D. `depot-ubuntu-24.04`**：dify 用 Depot 作为 runner（远程 Docker 构建服务），比原生 GitHub runner 快很多

### 3.3 ruoyi：极简但完整的 Jenkins 流水线

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/jenkins/Jenkinsfile`
**核心代码**（行 1-60）：

```groovy
#!groovy
pipeline {

    agent any

    parameters {
        string(name: 'TAG_NAME', defaultValue: '', description: '')
    }

    environment {
        // DockerHub 凭证 ID(登录您的 DockerHub)
        DOCKER_CREDENTIAL_ID = 'dockerhub-id'
        //  GitHub 凭证 ID (推送 tag 到 GitHub 仓库)
        GITHUB_CREDENTIAL_ID = 'github-id'
        // kubeconfig 凭证 ID (访问接入正在运行的 Kubernetes 集群)
        KUBECONFIG_CREDENTIAL_ID = 'demo-kubeconfig'
        // 镜像的推送
        REGISTRY = 'docker.io'
        //  DockerHub 账号名
        DOCKERHUB_NAMESPACE = 'docker_username'
        // GitHub 账号名
        GITHUB_ACCOUNT = 'https://gitee.com/zhijiantianya/ruoyi-vue-pro'
        // 应用名称
        APP_NAME = 'yudao-server'
        // 应用部署路径
        APP_DEPLOY_BASE_DIR = '/media/pi/KINGTON/data/work/projects/'
    }

    stages {
        stage('检出') {
            steps {
                git url: "https://gitee.com/will-we/ruoyi-vue-pro.git",
                        branch: "devops"
            }
        }

        stage('构建') {
            steps {
                // TODO 解决多环境链接、密码不同配置临时方案
                sh 'if [ ! -d "' + "${env.HOME}" + '/resources" ];then\n' +
                        '  echo "配置文件不存在无需修改"\n' +
                        'else\n' +
                        '  cp  -rf  ' + "${env.HOME}" + '/resources/*.yaml ' + "${env.APP_NAME}" + '/src/main/resources\n' +
                        '  echo "配置文件替换"\n' +
                        'fi'
                sh 'mvn clean package -Dmaven.test.skip=true'
            }
        }

        stage('部署') {
            steps {
                sh 'cp -f ' + ' bin/deploy.sh ' + "${env.APP_DEPLOY_BASE_DIR}" + "${env.APP_NAME}"
                sh 'cp -f ' + "${env.APP_NAME}" + '/target/*.jar ' + "${env.APP_DEPLOY_BASE_DIR}" + "${env.APP_NAME}" +'/build/'
                archiveArtifacts "${env.APP_NAME}" + '/target/*.jar'
                sh 'chmod +x ' + "${env.APP_DEPLOY_BASE_DIR}" + "${env.APP_NAME}" + '/deploy.sh'
                sh 'bash ' + "${env.APP_DEPLOY_BASE_DIR}" + "${env.APP_NAME}" + '/deploy.sh'
            }
        }
    }
}
```

**解读**：

**A. 流水线阶段（3 个 stage）**：
- `检出`：git clone（注意是 Gitee，fork 来源）
- `构建`：可选替换配置 → Maven 打 jar
- `部署`：复制 jar 到部署目录 → 调用 `deploy.sh`（详见 12 章）

**B. 大量"凭证 ID"声明**：Jenkins 的核心设计——所有外部依赖（DockerHub / GitHub / K8s）通过 Jenkins Credentials 管理
- 与 GitHub Actions 对比：GA 把凭证放在 `secrets.*` 上下文，Jenkins 全部靠 Credential Plugin

**C. 缺失的部分（对比 dify）**：
- ❌ **没有路径过滤**：任何 commit 都会跑全套 maven 编译（慢）
- ❌ **没有 lint / type-check**：JVM 项目这部分依赖 IDE
- ❌ **没有单元测试**：`mvn clean package -Dmaven.test.skip=true` —— **`-Dmaven.test.skip=true`** 直接跳过测试！

**关键观察**：
> ruoyi 的 Jenkinsfile **不是"完整 CI/CD"**，而是一个"打包 + 部署"流水线。它把所有质量门禁放在代码 review 和 IDE 层面，而 CI 只负责"打包 + 部署"。这是国内很多企业 Java 项目的典型模式。

**与 dify 对比**：
- dify 把所有检查放到 CI（lint / type-check / 单元测试 / DB migration test / VDB test / E2E test）
- ruoyi 假设这些都在 PR review 时人工确认，CI 只做"build + deploy"
- 两种模式都有效，但 dify 模式更"工业化"（GitHub 仓库可被全球贡献者 PR，必须严格 CI）

## 4. 关键要点总结

- **CI / 交付 / 部署**：3 个概念是递进关系，部署是最自动化的
- **流水线阶段**：检出 → 依赖 → 检查 → 测试 → 构建 → 部署 → 烟测
- **路径过滤**：dify 用 `paths-filter` 跳过不需要的 job，节省 CI 时间
- **finalizer trick**：让 GitHub Required Check 总有明确状态
- **GitHub Actions vs Jenkins**：GA 适合开源/云原生，Jenkins 适合企业内部复杂流水线
- **ruoyi 的"轻量 CI"**：只负责打包 + 部署，质量门禁放在 IDE/Review 层

## 5. 练习题

### 练习 1：基础（必做）

为一个简单的 Python 项目写一份 GitHub Actions CI 流水线：
1. PR 触发
2. 装依赖
3. 跑 ruff + mypy + pytest
4. 输出覆盖率报告

**参考答案**：见 `solutions/01-github-actions-ci.md`

### 练习 2：进阶

阅读 `dify/.github/workflows/main-ci.yml`，列出至少 5 处体现"最佳实践"的设计选择（提示：缓存、并行、超时控制、并发去重、finalizer 模式）。

### 练习 3：挑战（选做）

对比改造 ruoyi 的 `Jenkinsfile`：
1. 加入单元测试阶段（`mvn test` 而非 `-Dmaven.test.skip=true`）
2. 加入静态检查（spotbugs / checkstyle）
3. 设计灰度发布（详见 12 章）

## 6. 参考资料

- `/Users/xu/code/github/dify/.github/workflows/main-ci.yml`
- `/Users/xu/code/github/ruoyi-vue-pro/script/jenkins/Jenkinsfile`
- GitHub Actions 文档：https://docs.github.com/en/actions
- Jenkins 文档：https://www.jenkins.io/doc/
- Continuous Delivery 圣经：https://continuousdelivery.com/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
