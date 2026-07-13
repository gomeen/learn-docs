# 4.5 蓝绿部署 / 灰度发布 / 金丝雀

> 学习常见的高级部署策略，能在生产中安全发布新版本。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分蓝绿部署、灰度发布（金丝雀）、滚动更新的差异
- 为 dify 这种 LLM 应用选择合适的发布策略
- 理解发布策略的回滚机制

## 📚 前置知识

- `08-devops/04-docker-compose.md` 或 `08-devops/09-k8s-workloads.md`
- 负载均衡基础

## 1. 核心概念

### 1.1 三种发布策略对比

| 策略 | 原理 | 风险 | 回滚速度 | 资源消耗 |
|------|------|------|----------|----------|
| **滚动更新** | 逐步替换旧 Pod | 中 | 中 | 1x |
| **蓝绿部署** | 切流量到新环境 | 低 | 即时 | 2x |
| **灰度发布** | 小比例流量到新版本 | 低 | 即时 | 1.x |

### 1.2 滚动更新（Rolling Update）

```
旧版本：■■■■■■
新版本：□
↓ 逐步替换
新版本：□□□□□□
旧版本：（无）
```

- K8s **Deployment** 默认策略
- 适合：常规发布、变更不大
- 缺点：回滚需要重新部署

### 1.3 蓝绿部署（Blue-Green）

```
阶段 1：
   ┌─ Blue (v1) ─┐  ← 100% 流量
   └──────────────┘
   ┌─ Green (v2)─┐  ← 0% 流量（待命）
   └──────────────┘

阶段 2：
   ┌─ Blue (v1) ─┐  ← 0% 流量
   └──────────────┘
   ┌─ Green (v2)─┐  ← 100% 流量（一键切换）
   └──────────────┘
```

- **两套完整环境**，通过 LB 切换流量
- 优势：回滚**即时**（切回 Blue）
- 劣势：**资源 2x 成本**

### 1.4 灰度发布 / 金丝雀（Canary）

```
阶段 1：
   ┌─ v1 ─────┐ ← 95% 流量
   └──────────┘
   ┌─ v2 ─────┐ ← 5% 流量（金丝雀）
   └──────────┘

阶段 2（指标正常后）：
   ┌─ v1 ─────┐ ← 50% 流量
   └──────────┘
   ┌─ v2 ─────┐ ← 50% 流量
   └──────────┘

阶段 3（稳定后）：
   ┌─ v2 ─────┐ ← 100% 流量
   └──────────┘
```

- **小比例流量**先验证新版本
- 通过监控指标（错误率、延迟）决定是否继续
- 适合：核心业务、大版本发布

## 2. 代码示例

### 2.1 K8s 滚动更新

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dify-api
spec:
  replicas: 6
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 2          # 最多 2 个超量 Pod
      maxUnavailable: 0    # 始终保持所有 Pod 可用
  template:
    spec:
      containers:
        - name: api
          image: langgenius/dify-api:1.16.0-rc2   # 升级镜像
```

### 2.2 K8s 金丝雀发布（用两个 Deployment）

```yaml
# v1 稳定版
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dify-api-v1
spec:
  replicas: 9
  selector:
    matchLabels:
      app: dify-api
      version: v1
  template:
    metadata:
      labels:
        app: dify-api
        version: v1
    spec:
      containers:
        - name: api
          image: langgenius/dify-api:1.16.0-rc1
---
# v2 金丝雀（10% 流量）
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dify-api-v2
spec:
  replicas: 1
  selector:
    matchLabels:
      app: dify-api
      version: v2
  template:
    metadata:
      labels:
        app: dify-api
        version: v2
    spec:
      containers:
        - name: api
          image: langgenius/dify-api:1.16.0-rc2
---
# Service 通过标签选择所有版本
apiVersion: v1
kind: Service
metadata:
  name: dify-api
spec:
  selector:
    app: dify-api         # 匹配 v1 + v2
  ports:
    - port: 5001
```

流量比例 = 副本数比例（9:1 = 90%:10%）

### 2.3 K8s 蓝绿部署（用 Service 切换）

```yaml
# Blue (v1)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dify-api-blue
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dify-api
      track: blue
  template:
    metadata:
      labels:
        app: dify-api
        track: blue
    spec:
      containers:
        - name: api
          image: langgenius/dify-api:1.16.0-rc1
---
# Green (v2)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dify-api-green
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dify-api
      track: green
  template:
    metadata:
      labels:
        app: dify-api
        track: green
    spec:
      containers:
        - name: api
          image: langgenius/dify-api:1.16.0-rc2
---
# Service 默认指向 Blue
apiVersion: v1
kind: Service
metadata:
  name: dify-api
spec:
  selector:
    app: dify-api
    track: blue         # 改成 green 即一键切流量
```

### 2.4 常见错误：滚动更新慢导致回滚慢

```yaml
# ❌ 错误：maxSurge=1, maxUnavailable=1（慢但稳）
# 升级 6 副本需要 3 分钟
# 出现严重 bug 时回滚同样慢

# ✅ 紧急情况：先切流量到旧版本，再调查
kubectl rollout undo deployment/dify-api
```

## 3. dify 仓库源码解读

### 3.1 dify 的镜像版本管理

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（行 227-229）：

```yaml
  # API service
  api:
    <<: *shared-api-worker-config
    image: langgenius/dify-api:1.16.0-rc1
```

**解读**：
- docker-compose 没有内置的滚动更新/蓝绿
- dify 自托管用户通过**修改 `image` 版本 + `docker compose up -d`** 升级
- 这是**手动更新**，无内置灰度
- K8s 用户需自行实现灰度（如上 2.2 示例）

### 3.2 dify 的滚动重启策略

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`

**核心内容**：

```yaml
  # API service
  api:
    image: langgenius/dify-api:1.16.0-rc1
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
```

**解读**：
- `restart: always`：容器退出自动重启
- `healthcheck`：30s 间隔检查 `/health` 端点
- **结合**就是简化版的"自愈"：容器崩溃 → 重启 → 健康检查失败 → 标记 unhealthy
- docker-compose 的 `up -d` 默认**滚动重启**（先创建新容器再停止旧的，但 K8s 比这精细）

### 3.3 dify 的部署工作流（GitHub Actions 视角）

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
- dify 用 `workflow_run` 串联：先构建+推送 → 完成后自动部署
- `deploy-dev` 是开发环境的自动部署
- `deploy-saas.yml` / `deploy-enterprise.yml` 是 SaaS 和企业版的部署
- **回滚策略**：通过回滚 `image` 版本 + 重新 `docker compose up -d`

### 3.4 LLM 应用的发布特殊性

**文件位置**：`/Users/xu/code/github/dify/.github/workflows/build-push.yml`（参考）

LLM 应用的发布需特别注意：
- **API 兼容性**：旧客户端能否调用新 API（response format 变化）
- **数据库迁移**：Schema 变更可能不可逆
- **模型版本**：不同模型的行为差异
- **Prompt 兼容**：新版本可能改变 prompt 模板

**建议的发布流程**：
1. 灰度 5% 流量到新版本
2. 观察关键指标（错误率、首 token 延迟、对话完成率）
3. 稳定后逐步扩大（25% → 50% → 100%）
4. 出问题时立即切回旧版本

## 4. 关键要点总结

- **滚动更新** = K8s 默认，适合常规发布
- **蓝绿部署** = 一键切换，回滚即时，资源 2x
- **灰度发布** = 小流量验证，逐步扩大
- LLM 应用发布需关注 API 兼容、DB 迁移、Prompt 变化
- 关键决策：变更风险 vs 资源成本
- dify docker-compose 部署是**手动更新**，K8s 部署可实现自动灰度

## 5. 练习题

### 练习 1：基础（必做）

设计一个简单的蓝绿部署：用 docker-compose 启动两套 dify（v1 和 v2），用 Nginx upstream 切换流量。

### 练习 2：进阶

为 dify 设计金丝雀发布方案：在 K8s 中同时运行 v1 和 v2 Deployment，通过副本数比例（9:1）实现 10% 灰度。

### 练习 3：挑战（选做）

为 dify 实现自动化灰度发布：监控错误率（Prometheus），错误率 > 5% 时自动切回旧版本；正常时按计划逐步扩大流量（5% → 25% → 50% → 100%）。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/docker-compose.yaml`
- `/Users/xu/code/github/dify/.github/workflows/deploy-dev.yml`
- `/Users/xu/code/github/dify/.github/workflows/build-push.yml`
- K8s 部署策略官方文档：https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#strategy

---

**文档版本**：v1.0
**最后更新**：2026-07-13
