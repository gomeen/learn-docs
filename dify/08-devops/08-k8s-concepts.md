# 2.1 K8s 核心概念：Pod / Deployment / Service

> 理解 Kubernetes 的三大基础资源，能区分 K8s 编排与 docker-compose 的差异。

> ⚠️ **dify 中暂未直接使用 Kubernetes 编排**（dify 官方推荐 docker-compose 自托管）。本文档基于通用 K8s 概念讲解，方便读者理解部署差异。

## 🎯 学习目标

完成本文档后，你将能够：
- 说出 Pod、Deployment、Service 三个最常用 K8s 资源的作用
- 理解 K8s 的声明式 API 与控制循环
- 区分 K8s 与 docker-compose 在多容器编排上的差异
- 能读懂社区提供的 dify K8s 部署清单

## 📚 前置知识

- `08-devops/01-docker-concepts.md`
- `08-devops/04-docker-compose.md`

## 1. 核心概念

### 1.1 K8s 是什么？

Kubernetes（K8s）是**容器编排系统**，源自 Google Borg 项目，用于自动化部署、扩缩和管理容器化应用。

### 1.2 核心资源

```
┌────────────────────────────────────────────────┐
│ Cluster (集群)                                  │
│  ├─ Node 1 (工作节点)                          │
│  │   ├─ Pod A1                                 │
│  │   ├─ Pod A2                                 │
│  │   └─ Pod B1                                 │
│  └─ Node 2 (工作节点)                          │
│      ├─ Pod A3                                 │
│      └─ Pod C1                                 │
└────────────────────────────────────────────────┘
```

- **Pod**：K8s 最小调度单元，包含 1+ 个共享网络和存储的容器
- **Deployment**：管理 Pod 副本集（ReplicaSet）的声明
- **Service**：为 Pod 提供稳定访问入口（负载均衡 + 服务发现）
- **Node**：K8s 工作节点（物理机或虚拟机）
- **Cluster**：一组 Node 组成的集群

### 1.3 声明式 API

K8s 用**声明式**管理资源（与 Docker Compose 命令式不同）：

```bash
# 提交期望状态
kubectl apply -f deployment.yaml

# K8s 控制循环持续协调实际状态向期望状态靠拢
# - Pod 挂了？自动重启
# - 节点挂了？自动迁移到其他节点
# - 流量大了？自动扩容（如果配置了 HPA）
```

### 1.4 K8s vs Docker Compose

| 维度 | Docker Compose | Kubernetes |
|------|---------------|------------|
| 规模 | 单机 | 跨节点集群 |
| 自愈 | 弱（仅 restart） | 强（自动重启/迁移） |
| 扩缩容 | 手动 | 自动（HPA） |
| 滚动更新 | 不支持 | 内置（RollingUpdate） |
| 服务发现 | 容器名 DNS | Service + kube-dns |
| 配置管理 | .env 文件 | ConfigMap / Secret |
| 学习曲线 | 平缓 | 陡峭 |

## 2. 代码示例

### 2.1 第一个 Deployment

```yaml
# 文件：deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  labels:
    app: my-app
spec:
  replicas: 3                    # 副本数
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
        - name: my-app
          image: my-app:1.0
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
```

```bash
kubectl apply -f deployment.yaml
kubectl get pods -l app=my-app
kubectl scale deployment/my-app --replicas=5
```

### 2.2 Service：暴露应用

```yaml
# 文件：service.yaml
apiVersion: v1
kind: Service
metadata:
  name: my-app-svc
spec:
  type: ClusterIP               # 集群内访问
  selector:
    app: my-app                 # 匹配 Pod 标签
  ports:
    - port: 80                  # Service 端口
      targetPort: 8080          # 容器端口
```

```bash
# 集群内其他 Pod 可通过 my-app-svc:80 访问
curl http://my-app-svc:80
```

### 2.3 Pod：多容器协同

```yaml
# Pod 中跑两个共享网络的容器（边车模式）
apiVersion: v1
kind: Pod
metadata:
  name: app-with-sidecar
spec:
  containers:
    - name: app
      image: my-app:1.0
    - name: log-collector
      image: fluentd:1.16
      volumeMounts:
        - name: logs
          mountPath: /var/log/app
  volumes:
    - name: logs
      emptyDir: {}
```

## 3. dify 仓库源码解读

### 3.1 dify 中 K8s 部署资源

**说明**：dify 主仓库中**没有** K8s 部署清单（`deploy/` 目录为其他用途），但社区维护了 Helm Chart 和 Kustomize 模板。

**社区资源**：
- Helm Chart：https://github.com/difychart/helm-chart
- Kustomize：https://github.com/doubleZ0108/dify-kustomize

### 3.2 社区 Kustomize 示例（典型结构）

```yaml
# 文件结构（社区版 dify-kustomize）
kustomize/
├── base/
│   ├── kustomization.yaml
│   ├── api-deployment.yaml
│   ├── api-service.yaml
│   └── api-configmap.yaml
└── overlays/
    └── production/
        ├── kustomization.yaml
        └── replicas-patch.yaml
```

**说明**：
- `base/`：基础清单，定义 Deployment / Service
- `overlays/production/`：生产环境补丁（如副本数、资源限制）

### 3.3 dify 部署方式的演进

**文件位置**：`/Users/xu/code/github/dify/docker/README.md`（参考）

**核心内容**：

```markdown
# dify 官方推荐部署方式：docker-compose
# 适合：单机、中小规模、自托管
# 不推荐：直接在 K8s 上跑 docker-compose（缺少 K8s 优势）
```

**解读**：
- dify 官方定位是**轻量化、自托管**，docker-compose 已能满足 90% 场景
- K8s 部署通常用于：大规模 SaaS、多租户、需要自动扩缩容
- **关键设计权衡**：docker-compose 部署简单，但 K8s 提供更强的弹性和可观测性

## 4. 关键要点总结

- K8s **声明式 API**：描述期望状态，K8s 自动协调
- 三大基础资源：**Pod**（最小单元）、**Deployment**（副本管理）、**Service**（访问入口）
- K8s vs Compose：K8s 适合大规模集群，Compose 适合单机
- dify 主仓库**未直接提供 K8s 清单**，但社区有 Helm/Kustomize 资源
- 控制循环是 K8s 的核心：实际状态 ↔ 期望状态

## 5. 练习题

### 练习 1：基础（必做）

用 minikube 或 kind 启动本地 K8s 集群，部署一个 `nginx:1.27` Deployment（3 副本），用 `kubectl get pods` 查看。

```bash
# 安装 minikube（macOS）
brew install minikube
minikube start

# 部署
kubectl create deployment nginx --image=nginx:1.27 --replicas=3
kubectl get pods
```

### 练习 2：进阶

参考社区的 dify K8s 部署清单，列出把 dify 从 docker-compose 迁移到 K8s 需要处理哪些差异（ConfigMap、Service、Ingress、PVC）。

### 练习 3：挑战（选做）

把 dify 的 `api` 服务用 Kustomize 部署到 K8s：定义 base（Deployment + Service + ConfigMap）和 overlay（生产环境 3 副本 + 资源限制），用 `kustomize build` 生成最终清单。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/docker-compose.yaml`（dify 官方部署方式）
- `/Users/xu/code/github/dify/docker/README.md`
- 社区 Helm Chart：https://github.com/difychart/helm-chart
- K8s 官方文档：https://kubernetes.io/docs/concepts/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
