# 2.2 K8s 工作负载：Deployment / StatefulSet / DaemonSet

> 理解 K8s 三种主要工作负载资源的适用场景，能为 dify 各组件选择正确的工作负载。

> ⚠️ **dify 中暂未直接使用 Kubernetes**。本文档基于通用 K8s 概念讲解。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Deployment / StatefulSet / DaemonSet 的使用场景
- 理解有状态服务（数据库）的特殊处理
- 为 dify 的 API/Worker/PostgreSQL/Redis 各组件选择合适的工作负载

## 📚 前置知识

- `08-devops/08-k8s-concepts.md`

## 1. 核心概念

### 1.1 三种工作负载对比

| 资源 | 适用场景 | 标识 | 存储 |
|------|----------|------|------|
| **Deployment** | 无状态服务（API、前端） | Pod 名字随机 | 共享 |
| **StatefulSet** | 有状态服务（DB、MQ） | Pod 名字有序 | 独立 PVC |
| **DaemonSet** | 节点级服务（日志、监控） | 每个 Node 一个 | hostPath |

### 1.2 Deployment：无状态服务

- 适合：API 服务、前端、Nginx
- 特点：Pod 名字随机（`api-7d8f9c-b2x4y`），可任意替换
- 扩缩容：直接改 `replicas`
- 滚动更新：旧 Pod 逐步替换为新 Pod

### 1.3 StatefulSet：有状态服务

- 适合：PostgreSQL、Redis、MongoDB、Kafka
- 特点：Pod 名字稳定有序（`postgres-0`、`postgres-1`）
- 每个 Pod 独立 PVC（持久化存储）
- 扩缩容需要谨慎：缩容时**最后一个 Pod 先删除**
- 适合 dify 的 PostgreSQL / Redis（如果用 K8s 部署）

### 1.4 DaemonSet：节点级服务

- 适合：日志收集（Fluentd）、节点监控（Node Exporter）、网络插件
- 特点：每个 Node **保证有且仅有一个** Pod
- 新 Node 加入时自动部署
- 适合 dify 的日志收集器（如果用 K8s 部署）

### 1.5 任务型工作负载

- **Job**：跑一次就结束（数据迁移、批处理）
- **CronJob**：定时任务（备份、清理）

dify 的 Celery Beat 定时任务如果用 K8s 部署，可用 **CronJob** 替代。

## 2. 代码示例

### 2.1 Deployment 示例

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dify-api
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1            # 最多多 1 个 Pod
      maxUnavailable: 0      # 最少 0 个不可用
  selector:
    matchLabels:
      app: dify-api
  template:
    metadata:
      labels:
        app: dify-api
    spec:
      containers:
        - name: api
          image: langgenius/dify-api:1.16.0-rc1
          ports:
            - containerPort: 5001
```

### 2.2 StatefulSet 示例（PostgreSQL）

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres-headless
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:15-alpine
          env:
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: password
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:            # 每个 Pod 一个 PVC
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
```

### 2.3 DaemonSet 示例（日志收集）

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluentd
spec:
  selector:
    matchLabels:
      app: fluentd
  template:
    metadata:
      labels:
        app: fluentd
    spec:
      containers:
        - name: fluentd
          image: fluentd:1.16
          volumeMounts:
            - name: varlog
              mountPath: /var/log
      volumes:
        - name: varlog
          hostPath:
            path: /var/log
```

### 2.4 常见错误：用 Deployment 跑数据库

```yaml
# ❌ 错误：用 Deployment 跑 PostgreSQL
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
spec:
  template:
    spec:
      containers:
        - name: postgres
          image: postgres:15
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: shared-pvc    # 所有 Pod 共享一个 PVC！

# ✅ 正确：用 StatefulSet，每个 Pod 独立 PVC
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  volumeClaimTemplates:    # 自动为每个 Pod 创建独立 PVC
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
```

## 3. dify 仓库源码解读

### 3.1 dify 各组件的 K8s 工作负载选型

**说明**：dify 主仓库无 K8s 清单，但根据组件特性可推断推荐选型。

| dify 组件 | K8s 工作负载 | 理由 |
|-----------|--------------|------|
| `api` | Deployment | 无状态，水平扩容 |
| `worker` | Deployment | Celery worker 无状态 |
| `worker_beat` | Deployment (replicas=1) | 单点定时调度，多副本会冲突 |
| `web` | Deployment | 前端无状态 |
| `nginx` | Deployment + Service | 无状态 |
| `redis` | StatefulSet | 持久化数据 |
| `db_postgres` | StatefulSet | 持久化数据，名字稳定 |
| `sandbox` | Deployment | 无状态，可水平扩容 |
| `plugin_daemon` | Deployment | 无状态 |
| `agent_backend` | Deployment | 无状态 |
| `certbot` | CronJob | 定期续签证书 |
| 日志收集 | DaemonSet | 每节点一个 |

### 3.2 社区 dify-api Deployment 片段

社区 Helm Chart 中 dify-api 的典型定义：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dify-api
  labels:
    app.kubernetes.io/name: dify-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: dify-api
  template:
    metadata:
      labels:
        app.kubernetes.io/name: dify-api
    spec:
      containers:
        - name: api
          image: langgenius/dify-api:1.16.0-rc1
          ports:
            - name: http
              containerPort: 5001
          env:
            - name: MODE
              value: api
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 30
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 10
            periodSeconds: 10
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 2000m
              memory: 4Gi
```

**解读**：
- 第 7 行：`replicas: 2` 双副本保证高可用
- 第 25-29 行：`livenessProbe` 存活探针，失败则重启 Pod
- 第 30-34 行：`readinessProbe` 就绪探针，失败则从 Service 摘除流量
- 第 35-39 行：资源 requests / limits，**requests 用于调度，limits 防止资源滥用**

## 4. 关键要点总结

- **Deployment** = 无状态服务（API、前端）
- **StatefulSet** = 有状态服务（数据库），每个 Pod 独立 PVC
- **DaemonSet** = 节点级服务（每 Node 一个）
- **Job / CronJob** = 一次性或定时任务
- 数据库**绝不能用 Deployment**（共享 PVC 会导致数据损坏）
- dify 的 `worker_beat` 必须单副本，否则定时任务会重复执行

## 5. 练习题

### 练习 1：基础（必做）

用 minikube 部署一个 `postgres:15` 的 **StatefulSet**，验证 Pod 名字有序（`postgres-0`）并自动创建 PVC。

### 练习 2：进阶

阅读 dify `docker-compose.yaml`，列出每个服务并标注如果用 K8s 部署应该用哪种工作负载。考虑 `worker_beat` 应该如何处理？

### 练习 3：挑战（选做）

为 dify 设计一份 K8s 部署清单：Deployment（api/worker/web）+ StatefulSet（postgres/redis）+ CronJob（certbot），画出资源关系图。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/docker-compose.yaml`
- 社区 Helm Chart：https://github.com/difychart/helm-chart
- K8s 工作负载官方文档：https://kubernetes.io/docs/concepts/workloads/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
