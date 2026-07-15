# 2.5 K8s 持久化存储：PV / PVC

> 理解 K8s 存储模型：PV（PersistentVolume）/ PVC（PersistentVolumeClaim）/ StorageClass。

> ⚠️ **dify 中暂未直接使用 Kubernetes**。本文档基于通用 K8s 概念讲解。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 PV / PVC / StorageClass 的角色
- 理解动态供给（Dynamic Provisioning）的工作机制
- 为 dify 的 PostgreSQL 设计 K8s 存储方案

## 📚 前置知识

- Docker 卷与 bind mount（详见 [Docker 网络与卷](../../_common/09-containerization/05-network-volume.md)）
- `08-devops/09-k8s-workloads.md`（StatefulSet）

## 1. 核心概念

### 1.1 K8s 存储三层模型

```
┌────────────────────────────────────┐
│ Pod                                │
│   ↓ volumeMount                    │
│ PVC (PersistentVolumeClaim)        │  ← Pod 视角的"存储请求"
│   ↓ binding                       │
│ PV (PersistentVolume)              │  ← 集群视角的"实际存储"
│   ↓ driver                        │
│ NFS / iSCSI / 云盘 EBS / Ceph      │  ← 真实存储后端
└────────────────────────────────────┘
```

### 1.2 关键术语

- **PV（PersistentVolume）**：集群级别的**存储资源**，由管理员预创建或动态生成
- **PVC（PersistentVolumeClaim）**：Pod 对存储的**请求**（容量、访问模式）
- **StorageClass**：存储的**类别**（如"快速 SSD"、"慢速 HDD"），支持动态供给
- **动态供给（Dynamic Provisioning）**：PVC 申请时自动创建 PV，无需管理员预创建

### 1.3 访问模式

| 模式 | 缩写 | 含义 |
|------|------|------|
| **ReadWriteOnce** | RWO | 单节点读写 |
| **ReadOnlyMany** | ROX | 多节点只读 |
| **ReadWriteMany** | RWX | 多节点读写（需要 NFS / CephFS） |

数据库通常用 RWO（单机读写），共享文件系统用 RWX。

### 1.4 StatefulSet 自动创建 PVC

```yaml
volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

StatefulSet 会**自动**为每个 Pod 创建一个独立 PVC：
- `postgres-0` → PVC `data-postgres-0`
- `postgres-1` → PVC `data-postgres-1`

## 2. 代码示例

### 2.1 静态 PV + PVC

```yaml
# 1. 管理员预创建 PV
apiVersion: v1
kind: PersistentVolume
metadata:
  name: pg-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain   # Pod 删除后保留数据
  hostPath:                                # 本地路径（生产用云盘）
    path: /data/pg
---
# 2. Pod 申请 PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pg-pvc
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 10Gi
```

### 2.2 动态供给（推荐）

```yaml
# 1. StorageClass
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: kubernetes.io/aws-ebs    # AWS EBS
parameters:
  type: gp3
  fsType: ext4
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
---
# 2. PVC（无需预创建 PV）
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: pg-data
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: fast-ssd
  resources:
    requests:
      storage: 10Gi
```

### 2.3 StatefulSet 完整示例

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres
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
                  name: pg-secret
                  key: password
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: fast-ssd
        resources:
          requests:
            storage: 10Gi
```

### 2.4 常见错误：PVC Pending 状态

```bash
# Pod 一直 Pending，PVC 一直 Pending
# 通常原因：
# 1. 没有匹配的 StorageClass
# 2. 集群资源不足
# 3. accessModes 不支持（如 RWO 存储被其他 PVC 占用）
kubectl describe pvc pg-data
# Events: FailedBinding ... no persistent volumes available
```

## 3. dify 仓库源码解读

### 3.1 dify 的 bind mount 数据目录

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（行 435-436）：

```yaml
    volumes:
      - ./volumes/db/data:/var/lib/postgresql/data
```

**解读**：
- dify 用 **bind mount** 把数据库数据存到主机目录
- 这种方式在 K8s 中**不适用**（K8s Pod 漂移到其他节点会找不到数据）
- K8s 化时需要**改用 PVC**（绑定云盘或 NFS）

### 3.2 dify 的存储目录结构

**文件位置**：`/Users/xu/code/github/dify/docker/volumes/`
**核心结构**（参考）：

```
volumes/
├── app/storage/        # 用户上传文件
├── db/data/            # PostgreSQL 数据
├── redis/data/         # Redis 数据
├── sandbox/conf/       # sandbox 配置
├── sandbox/dependencies/  # sandbox 依赖
├── certbot/conf/       # 证书（HTTPS 签发详见 [HTTPS / Let's Encrypt](../../_common/10-network-proxy/03-https.md)）
└── certbot/www/        # HTTP-01 验证
```

**K8s 化映射**：

| 目录 | K8s 资源 | 存储大小 |
|------|----------|----------|
| `db/data` | StatefulSet volumeClaimTemplate | 10-100Gi |
| `app/storage` | Deployment volumeMount (RWX) | 100Gi+ |
| `redis/data` | StatefulSet volumeClaimTemplate | 5Gi |
| `certbot/conf` | Job/CronJob volumeMount | 1Gi |

### 3.3 dify 的 init_permissions 容器的 K8s 化

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（行 207-224）：

```yaml
  # Init container to fix permissions
  init_permissions:
    image: busybox:latest
    command:
      - sh
      - -c
      - |
        FLAG_FILE="/app/api/storage/.init_permissions"
        if [ -f "$${FLAG_FILE}" ]; then
          echo "Permissions already initialized. Exiting."
          exit 0
        fi
        echo "Initializing permissions for /app/api/storage"
        chown -R 1001:1001 /app/api/storage && touch "$${FLAG_FILE}"
        echo "Permissions initialized. Exiting."
    volumes:
      - ./volumes/app/storage:/app/api/storage
    restart: "no"
```

**K8s 化对照**：
- K8s 的 **Init Container** 完全对应这种场景
- 用 `securityContext.fsGroup: 1001` 更优雅——K8s 自动修改挂载卷的属主

```yaml
spec:
  template:
    spec:
      securityContext:
        fsGroup: 1001    # 自动 chown 挂载卷到 1001
      containers:
        - name: api
          ...
```

## 4. 关键要点总结

- **PV** = 实际存储，**PVC** = 存储请求，**StorageClass** = 存储类别
- **动态供给** 是云原生时代的主流：PVC → 自动创建 PV
- **StatefulSet** 用 `volumeClaimTemplates` 自动给每个 Pod 独立 PVC
- dify 的 bind mount 在 K8s 中改用 PVC（云盘或 NFS）
- `securityContext.fsGroup` 是 K8s 优雅处理权限问题的方式

## 5. 练习题

### 练习 1：基础（必做）

用 minikube 创建一个 StorageClass（`standard`）+ PVC（5Gi）+ Pod，挂载 `/data`，写入文件验证持久化。

### 练习 2：进阶

阅读 dify `docker/volumes/` 目录结构，为每个子目录设计 K8s PVC 方案：哪些用 StatefulSet、哪些用 Deployment volumeMount、是否需要 RWX 共享？

### 练习 3：挑战（选做）

为 dify 的 PostgreSQL 设计生产级 K8s 清单：StatefulSet（1 副本）+ 10Gi PVC（fast-ssd）+ 每日 CronJob 备份（pg_dump 到 S3）。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/docker-compose.yaml`
- `/Users/xu/code/github/dify/docker/volumes/`
- K8s 存储官方文档：https://kubernetes.io/docs/concepts/storage/persistent-volumes/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
