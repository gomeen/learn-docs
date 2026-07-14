# 4.1 GitHub Actions 实战

> 理解 GitHub Actions 的工作原理，掌握为 ruoyi 编写 CI/CD 工作流。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 GitHub Actions 的核心概念（workflow、job、step、action）
- 掌握 workflow YAML 的编写
- 能为 ruoyi 编写"代码提交 → 编译 → 部署"自动化
- 掌握 secrets 配置与缓存优化

## 📚 前置知识

- Git 基础
- Maven 命令
- `01-maven-build.md`

## 1. 核心概念

### 1.1 什么是 GitHub Actions？

GitHub 内置的 CI/CD 平台：
- 触发条件：push / pull_request / schedule
- 工作流：`.github/workflows/*.yml`
- 执行环境：GitHub 提供的 runner（Ubuntu / macOS / Windows）

### 1.2 核心概念

| 概念 | 说明 |
|------|------|
| **Workflow** | 一个 YAML 文件，定义自动化流程 |
| **Job** | 一个执行单元（默认串行，可并行） |
| **Step** | Job 内的一个步骤（命令或 action） |
| **Action** | 复用的步骤（如 `actions/checkout@v4`） |
| **Runner** | 执行 Job 的虚拟机 |

### 1.3 触发器

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨 2 点
  workflow_dispatch:      # 手动触发
```

## 2. 代码示例

### 2.1 最小 workflow

```yaml
# 文件：.github/workflows/build.yml
name: Build

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: 检出代码
        uses: actions/checkout@v4

      - name: 设置 JDK
        uses: actions/setup-java@v4
        with:
          java-version: '8'
          distribution: 'temurin'

      - name: 编译
        run: mvn clean package -pl yudao-server -am -DskipTests

      - name: 上传制品
        uses: actions/upload-artifact@v4
        with:
          name: yudao-server-jar
          path: yudao-server/target/yudao-server.jar
```

**说明**：
- `actions/checkout@v4` — 检出代码
- `actions/setup-java@v4` — 安装 JDK
- `actions/upload-artifact@v4` — 上传构建产物
- 触发：push 到 main 分支

### 2.2 缓存 Maven 依赖

```yaml
- name: 缓存 Maven 依赖
  uses: actions/cache@v4
  with:
    path: ~/.m2/repository
    key: ${{ runner.os }}-m2-${{ hashFiles('**/pom.xml') }}
    restore-keys: |
      ${{ runner.os }}-m2-
```

**说明**：用 `hashFiles('**/pom.xml')` 作为缓存 key，pom 变化时缓存失效。

### 2.3 配置 Secrets

```bash
# 在 GitHub 仓库 Settings → Secrets and variables → Actions 添加：
DEPLOY_HOST=192.168.1.10
DEPLOY_USER=root
DEPLOY_SSH_KEY=-----BEGIN OPENSSH PRIVATE KEY-----...
```

在 workflow 中引用：

```yaml
- name: 部署到服务器
  uses: appleboy/scp-action@v0.1.7
  with:
    host: ${{ secrets.DEPLOY_HOST }}
    username: ${{ secrets.DEPLOY_USER }}
    key: ${{ secrets.DEPLOY_SSH_KEY }}
    source: "yudao-server/target/yudao-server.jar"
    target: "/work/projects/yudao-server/build/"
```

## 3. ruoyi 仓库源码解读

**注**：ruoyi 仓库**没有 `.github/workflows/`**（CI 主要用 Jenkins）。

**基于 ruoyi 的 GitHub Actions 配置**（建议）：

```yaml
# 文件：.github/workflows/ci.yml
name: yudao-ci

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]
  workflow_dispatch:

env:
  MAVEN_OPTS: -Xmx2g -XX:MaxRAMPercentage=75.0

jobs:
  build:
    name: 构建
    runs-on: ubuntu-latest

    steps:
      - name: 检出代码
        uses: actions/checkout@v4

      - name: 设置 JDK 8
        uses: actions/setup-java@v4
        with:
          java-version: '8'
          distribution: 'temurin'

      - name: 缓存 Maven 依赖
        uses: actions/cache@v4
        with:
          path: ~/.m2/repository
          key: ${{ runner.os }}-m2-${{ hashFiles('**/pom.xml') }}

      - name: 编译（跳过测试）
        run: mvn clean package -pl yudao-server -am -DskipTests -B

      - name: 上传 jar 到制品
        uses: actions/upload-artifact@v4
        with:
          name: yudao-server-jar
          path: yudao-server/target/yudao-server.jar
          retention-days: 30

  deploy:
    name: 部署
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'

    steps:
      - name: 下载 jar
        uses: actions/download-artifact@v4
        with:
          name: yudao-server-jar
          path: target/

      - name: 部署到服务器
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            cd /work/projects/yudao-server
            cp target/yudao-server.jar build/
            cp script/shell/deploy.sh .
            bash deploy.sh
```

**解读**：
- 第 10 行：env 设置 `MAVEN_OPTS`（JVM 内存）
- 第 17-21 行：build job（编译 + 上传制品）
- 第 45-65 行：deploy job（仅 main 分支的 push 触发）
  - `needs: build` — 依赖 build 完成
  - 远程执行 `deploy.sh`（详见 `09-ruoyi-deploy.md`）

## 4. 关键要点总结

- Workflow 文件放在 `.github/workflows/*.yml`
- `actions/checkout`、`actions/setup-java` 是最常用的 action
- 用 `actions/cache` 缓存 Maven 依赖，加速 CI
- `secrets.*` 安全地管理敏感信息
- `needs` 关键字定义 job 依赖
- `if` 条件判断决定是否运行

## 5. 练习题

### 练习 1：基础（必做）

为 ruoyi 创建 `.github/workflows/ci.yml`，配置 push 触发 → 编译 yudao-server → 上传 jar 制品。

### 练习 2：进阶

添加缓存步骤：缓存 `~/.m2/repository`，观察第二次构建的速度提升。

### 练习 3：挑战（选做）

为 workflow 添加**多 JDK 矩阵测试**（JDK 8 / JDK 11 / JDK 17），用 `strategy.matrix` 并行执行。

## 6. 参考资料

- [GitHub Actions 官方文档](https://docs.github.com/en/actions)
- [awesome-actions 列表](https://github.com/sdras/awesome-actions)
- [Spring Boot GitHub Actions 模板](https://github.com/spring-projects/spring-boot/tree/main/.github/workflows)
- ruoyi 部署文档：https://doc.iocoder.cn/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
