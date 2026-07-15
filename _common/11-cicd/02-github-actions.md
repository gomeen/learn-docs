# 11.2 GitHub Actions 实战

> 深入 GitHub Actions 的核心机制：workflow / job / step / action，能读懂并编写复杂的流水线。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 GitHub Actions 的核心对象（workflow / job / step / action）
- 使用 `matrix`、`needs`、`if`、`secrets`、`paths` 等关键字段
- 看懂 dify 的多架构（amd64 / arm64）Docker 构建
- 比较 GitHub Actions 与 Jenkinsfile 的写法差异

## 📚 前置知识

- [11.1 CI/CD 概念与流水线设计](./01-concepts.md)
- YAML 基础语法
- [Docker 基础](../09-containerization/01-concepts.md)

## 1. 核心概念

### 1.1 GitHub Actions 的 4 个核心对象

```
workflow（一个 YAML 文件）        .github/workflows/ci.yml
  └─ job（一个 CI 阶段）         api-tests / docker-build
       └─ step（一个步骤）       checkout / setup-python / pytest
            └─ action（可复用单元）  官方或社区 action
```

| 对象 | 类比 | 作用域 |
|------|------|--------|
| workflow | Jenkinsfile | 一个文件 / 一个工作流 |
| job | stage | 一个 runner 上的工作单元 |
| step | 命令 | 一个 step = 一条 shell 或一个 action |
| action | 函数调用 | 复用单元（`uses: actions/checkout@v4`） |

### 1.2 关键语法

```yaml
on:                          # 触发器
  pull_request:               # PR 触发
    branches: [main]
    paths: ['api/**']         # 只 PR 改 api/ 才跑

jobs:                        # jobs map
  job-name:
    runs-on: ubuntu-latest   # runner 类型
    needs: [other-job]       # 依赖
    if: ${{ github.event.action == 'opened' }}   # 条件
    strategy:                 # 矩阵
      matrix:
        python: ['3.11', '3.12']
    steps:
      - uses: actions/checkout@v4     # action
      - name: Run tests               # name
        env:                          # 环境变量
          FOO: bar
        run: pytest                   # 命令
        shell: bash
        timeout-minutes: 10
```

### 1.3 矩阵构建（Matrix）

```yaml
strategy:
  matrix:
    python-version: [3.10, 3.11, 3.12]
    os: [ubuntu-latest, macos-latest]
runs-on: ${{ matrix.os }}
```

GitHub 会自动跑 `2 × 3 = 6` 个 job，每个组合一次。

### 1.4 产物传递（artifacts）

```yaml
- name: Build
  run: pytest --junitxml=results.xml

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: results.xml
```

后续步骤或下游 workflow 可以用 `actions/download-artifact@v4` 拉取。

### 1.5 Secrets 安全管理

```yaml
steps:
  - name: Login to DockerHub
    uses: docker/login-action@v3
    with:
      username: ${{ secrets.DOCKERHUB_USERNAME }}
      password: ${{ secrets.DOCKERHUB_TOKEN }}
```

secrets 在 GitHub 仓库 Settings → Secrets 注入，**绝不**用明文。

## 2. 代码示例

### 2.1 完整 Python CI 流水线

```yaml
name: Python CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip  # 关键：缓存 pip
          cache-dependency-path: requirements.txt

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Lint with ruff
        run: ruff check .

      - name: Format check
        run: ruff format --check .

      - name: Type check
        run: mypy .

      - name: Run tests
        run: pytest --cov=src --cov-report=xml

      - name: Upload coverage
        if: matrix.python-version == '3.12'
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

### 2.2 缓存策略

```yaml
- name: Cache
  uses: actions/cache@v4
  with:
    path: |
      ~/.cache/pip
      ~/.cache/pre-commit
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

`key` 含 hashFiles('requirements.txt')，requirements 改了缓存就失效。

### 2.3 常见错误：未设置 timeout

```yaml
# ❌ 错误：测试卡住会卡到 6 小时（GitHub 默认最长）
steps:
  - run: pytest

# ✅ 正确：显式设置超时
steps:
  - name: Run tests with timeout
    timeout-minutes: 10
    run: pytest
```

### 2.4 常见错误：用 latest action

```yaml
# ❌ 错误：action 不固定版本，容易被破坏
- uses: actions/checkout@main

# ✅ 正确：固定到 SHA 或带版本号
- uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0
```

## 3. dify 与 ruoyi 源码解读

### 3.1 dify：多架构 Docker 镜像构建矩阵

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/docker-build.yml`
**核心代码**（行 28-63）：

```yaml
    strategy:
      matrix:
        include:
          - service_name: "api-amd64"
            platform: linux/amd64
            runs_on: depot-ubuntu-24.04-4
            context: "{{defaultContext}}"
            file: "api/Dockerfile"
          - service_name: "api-arm64"
            platform: linux/amd64
            runs_on: depot-ubuntu-24.04-4
            context: "{{defaultContext}}"
            file: "api/Dockerfile"
          - service_name: "web-amd64"
            platform: linux/amd64
            runs_on: depot-ubuntu-24.04-4
            context: "{{defaultContext}}"
            file: "web/Dockerfile"
          - service_name: "web-arm64"
            platform: linux/amd64
            runs_on: depot-ubuntu-24.04-4
            context: "{{defaultContext}}"
            file: "web/Dockerfile"
    steps:
      - name: Set up Depot CLI
        uses: depot/setup-action@15c09a5f77a0840ad4bce955686522a257853461 # v1.7.1

      - name: Build Docker Image
        uses: depot/build-push-action@98e78adca7817480b8185f474a400b451d74e287 # v1.18.0
```

**解读**：

**A. 矩阵 4 个组合**：
- `api-amd64` + `api-arm64`（后端 2 个架构）
- `web-amd64` + `web-arm64`（前端 2 个架构）

**B. `include` 字段**：
- 标准 `matrix` 只能定义笛卡尔积，但 dify 用 `include` 给每个组合附加配置
- 例如 `runs_on: depot-ubuntu-24.04-4` 这个字段无法在标准 `matrix` 里出现

**C. `service_name` 作为命名约定**：
- 矩阵每一项必须有名字，会显示在 GitHub UI 上
- `api-arm64` 这种命名让 PR reviewer 一眼看出构建了哪些组合

**D. `{{defaultContext}}`**：
- 仓库根目录作为 Docker 构建上下文
- 相比 `./api`，它能让 `Dockerfile` 用到根目录的 `dify-agent/` 等共享文件

**E. Depot 替代原生 Docker Buildx**：
- Depot 是一家构建加速服务（专门为多架构 Docker 镜像设计）
- 用本地缓存 + 远程编译，比 GitHub 原生快 5-10 倍
- 步骤：`depot/setup-action` 装 CLI → `depot/build-push-action` 调用构建

**F. Action 固定到 SHA**：
```yaml
- uses: depot/setup-action@15c09a5f77a0840ad4bce955686522a257853461 # v1.7.1
```
SHA + 版本注释——这是 GitHub 官方推荐的安全实践（避免上游被劫持）。

### 3.2 dify：PR 触发器 + 路径过滤

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/docker-build.yml`
**核心代码**（行 1-25）：

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
```

**解读**：
- **第 2-15 行 `on:` 触发器**：
  - `pull_request.branches: [main]`：只对 main 分支的 PR 触发
  - `paths:`：**只有 Docker 相关文件改了才触发**——避免改 docs / readme 也跑 docker build
  - `api/uv.lock` 列在 paths 里——依赖文件改了必须重新构建镜像，否则缓存失效

- **第 17-19 行 `concurrency`**：
  - `group: docker-build-${head_ref}`——同一 PR 的多次提交用同一组
  - `cancel-in-progress: true`——**关键**：新的 commit 自动取消旧 run，节省 CI 资源
  - 这是 GitHub Actions 的杀手锏，配合 push-friend 自动 cancel

### 3.3 dify：deploy-dev 触发器（基于 build 完成事件）

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

**A. `workflow_run` 触发器**：
- 不直接由 PR 触发，而是由 **另一个 workflow 的 `completed` 事件触发**
- 这里由 "Build and Push API & Web" workflow 完成（成功）后触发部署
- 这是 GitHub Actions 的解耦设计：构建 → 部署是串行两步

**B. `workflow_run.branches: [deploy/dev]`**：
- 只监听 `deploy/dev` 分支的 build 完成事件
- 这个分支通常是"开发环境"的发布线

**C. `if` 多行条件**：
- `conclusion == 'success'`：只有 build 成功才部署
- `head_branch == 'deploy/dev'`：必须是 `deploy/dev` 分支（避免其他分支误部署）

**D. `appleboy/ssh-action`**：
- 通过 SSH 连接到目标服务器执行脚本
- `vars.SSH_SCRIPT || secrets.SSH_SCRIPT`：先用仓库变量（明文）兜底，否则用密钥（密文）
- 这是**生产部署**的常见模式：构建在 CI 端，部署脚本在 CI 内但实际跑在生产服务器上

### 3.4 ruoyi：Jenkinsfile 与 GitHub Actions 等价对照

```groovy
// Jenkins 等价于：
stages {
    stage('检出') {
        steps {
            git url: "..."                 # actions/checkout
        }
    }

    stage('构建') {
        steps {
            sh 'mvn clean package -Dmaven.test.skip=true'  # run: mvn ...
        }
    }

    stage('部署') {
        steps {
            sh 'bash deploy.sh'            # run: bash deploy.sh
        }
    }
}
```

| 概念 | GitHub Actions | Jenkins |
|------|----------------|---------|
| 检出代码 | `uses: actions/checkout@v4` | `git url: '...'` |
| 缓存 | `actions/cache@v4` | `caching {}` 段 |
| 环境变量 | `env: {}` 局部 / `env:` workflow 全局 | `environment {}` |
| 矩阵 | `strategy.matrix` | `matrix {}` axis |
| if 条件 | `if: ${{ ... }}` | `when {}` |
| 产物 | `actions/upload-artifact@v4` | `archiveArtifacts` |
| 触发器 | `on:` 顶层 | `triggers {}` (cron/polling 等) |
| secrets | `secrets.X` | `credentials 'name'` |

## 4. 关键要点总结

- **4 对象层级**：workflow > job > step > action
- **`paths` 触发器**：避免无关改动触发 CI
- **`concurrency` + `cancel-in-progress`**：自动取消冗余 run
- **`matrix.include`**：矩阵里附加任意字段
- **`workflow_run`**：跨 workflow 事件触发，是 GitHub Actions 的解耦杀手锏
- **固定 action 到 SHA**：防止上游被劫持
- **SSH 部署**：`appleboy/ssh-action` 是主流方案

## 5. 练习题

### 练习 1：基础（必做）

写一份 GitHub Actions workflow：
1. 触发：PR 到 main 分支
2. 矩阵：`python 3.11 / 3.12`
3. 步骤：装依赖、ruff 检查、pytest
4. 上传覆盖率到 Codecov

**参考答案**：见 `solutions/01-github-actions-pytest.md`

### 练习 2：进阶

阅读 `dify/.github/workflows/main-ci.yml` 第 386-393 行：
```yaml
  style-check:
    name: Style Check
    needs: pre_job
    if: needs.pre_job.outputs.should_skip != 'true'
    uses: ./.github/workflows/style.yml
    with:
      base-rev: ${{ github.event.pull_request.base.sha || github.event.merge_group.base_sha }}
```

回答：
1. `uses: ./.github/workflows/style.yml` 是引用另一个 workflow，用 `with` 传参的原因是什么？
2. `base-rev` 的 fallback 表达式 `pull_request.base.sha || github.event.merge_group.base_sha` 处理了什么边界情况？

### 练习 3：挑战（选做）

为 dify `deploy-dev.yml` 添加 staging 环境：
1. workflow_run 监听 build 成功
2. `if` 增加 head_branch 判断（`deploy/staging`）
3. SSH 到 staging 服务器，调用 `docker compose pull && docker compose up -d`
4. 用 `timeout-minutes: 10` 限制最长执行时间

## 6. 参考资料

- `/Users/xu/code/github/dify/.github/workflows/docker-build.yml`
- `/Users/xu/code/github/dify/.github/workflows/main-ci.yml`
- `/Users/xu/code/github/dify/.github/workflows/deploy-dev.yml`
- GitHub Actions 官方文档：https://docs.github.com/en/actions
- `dorny/paths-filter`：https://github.com/dorny/paths-filter
- `appleboy/ssh-action`：https://github.com/appleboy/ssh-action

---

**文档版本**：v1.0
**最后更新**：2026-07-13
