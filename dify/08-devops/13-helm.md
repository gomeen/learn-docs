# 2.6 Helm Chart 入门

> 学会用 Helm 把 K8s 清单模板化，能读懂社区提供的 dify Helm Chart。

> ⚠️ **dify 主仓库未直接维护 Helm Chart**（社区版本较多）。本文档基于通用 Helm 概念讲解。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Helm Chart 的结构和三大概念：Chart / Release / Repository
- 编写 `values.yaml` 参数化配置
- 用 `helm install` / `helm upgrade` 管理应用

## 📚 前置知识

- `08-devops/08-k8s-concepts.md` ~ `12-k8s-storage.md`

## 1. 核心概念

### 1.1 Helm 是什么？

Helm 是 **K8s 的包管理器**（类似 apt/yum），把 K8s 资源打包成可复用、可配置的 Chart。

### 1.2 核心概念

- **Chart**：应用的 K8s 资源模板包（一个目录）
- **Release**：Chart 的一次部署实例（同名 Chart 可部署多次）
- **Repository**：Chart 的仓库（类似 Docker Hub）
- **values.yaml**：Chart 的参数化配置
- **templates/**：K8s 资源模板（用 Go template 语法）

### 1.3 Chart 目录结构

```
my-chart/
├── Chart.yaml          # Chart 元信息
├── values.yaml         # 默认配置
├── templates/          # K8s 资源模板
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   └── _helpers.tpl    # 模板辅助函数
└── charts/             # 子 Chart 依赖
```

### 1.4 模板语法

```yaml
# templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Values.appName }}
spec:
  replicas: {{ .Values.replicaCount }}
  template:
    spec:
      containers:
        - name: api
          image: {{ .Values.image.repository }}:{{ .Values.image.tag }}
          resources:
            requests:
              cpu: {{ .Values.resources.requests.cpu }}
```

## 2. 代码示例

### 2.1 最小 Chart

```bash
# 创建 Chart 骨架
helm create my-app
```

```yaml
# Chart.yaml
apiVersion: v2
name: my-app
description: A simple web app
type: application
version: 0.1.0
appVersion: "1.0"
```

```yaml
# values.yaml
replicaCount: 3
image:
  repository: nginx
  tag: 1.27
service:
  type: ClusterIP
  port: 80
```

```bash
# 安装
helm install my-release ./my-app

# 升级（修改 values.yaml 后）
helm upgrade my-release ./my-app

# 查看状态
helm list
helm status my-release

# 卸载
helm uninstall my-release
```

### 2.2 模板条件渲染

```yaml
# templates/ingress.yaml
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ .Release.Name }}-ingress
spec:
  rules:
    - host: {{ .Values.ingress.host }}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ .Release.Name }}-web
                port:
                  number: 80
{{- end }}
```

### 2.3 模板辅助函数

```yaml
# templates/_helpers.tpl
{{- define "my-app.fullname" -}}
{{- .Release.Name }}-{{ .Chart.Name -}}
{{- end -}}

# 使用
metadata:
  name: {{ include "my-app.fullname" . }}
```

### 2.4 常见错误：values 修改后 Pod 没更新

```bash
# 错误：直接 edit deployment，没改 values
kubectl edit deployment api
# helm upgrade 时会被覆盖回 values 中的配置

# 正确：改 values.yaml，再 helm upgrade
helm upgrade my-release ./my-app --set replicaCount=5
```

## 3. dify 仓库源码解读

### 3.1 社区 dify Helm Chart 结构

社区 Chart（https://github.com/difychart/helm-chart）结构如下：

```
dify-helm/
├── Chart.yaml
├── values.yaml                          # 主配置
├── charts/                              # 子 Chart
│   ├── api/                             # dify-api
│   ├── worker/                          # dify-worker
│   ├── web/                             # dify-web
│   ├── postgres/                        # PostgreSQL
│   ├── redis/                           # Redis
│   ├── weaviate/                        # 向量库
│   └── sandbox/                         # sandbox
├── templates/                           # 顶层资源
│   ├── ingress.yaml
│   ├── configmap.yaml
│   └── secret.yaml
└── README.md
```

### 3.2 社区 values.yaml 片段

社区 Chart 的 `values.yaml` 通常包含：

```yaml
# API 服务配置
api:
  enabled: true
  replicaCount: 2
  image:
    repository: langgenius/dify-api
    tag: 1.16.0-rc1
  service:
    type: ClusterIP
    port: 5001
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: 2000m
      memory: 4Gi
  env:
    MODE: api
    LOG_LEVEL: INFO
    PLUGIN_MAX_PACKAGE_SIZE: 52428800

# PostgreSQL 配置
postgres:
  enabled: true
  persistence:
    size: 10Gi
    storageClass: fast-ssd
  auth:
    password: difyai123456
```

**解读**：
- 顶层 keys 对应 dify 的不同组件（api、worker、web、postgres、redis...）
- 每个组件可独立启用/禁用（类似 docker-compose 的 profile）
- `persistence` 子项配置 PVC

### 3.3 对照 dify docker-compose 的 env 配置

**文件位置**：`/Users/xu/code/github/dify/docker/envs/core-services/api.env`

**Helm values 化**：

```yaml
# values.yaml
api:
  env:
    MODE: api
    CONSOLE_API_URL: http://127.0.0.1:5001
    CONSOLE_WEB_URL: http://127.0.0.1:3000
    PLUGIN_MAX_PACKAGE_SIZE: "52428800"
    # ...
  secretEnv:
    DB_PASSWORD: difyai123456          # Secret 渲染
    REDIS_PASSWORD: difyai123456
    PLUGIN_DIFY_INNER_API_KEY: QaHbT...
```

**模板渲染**：

```yaml
# charts/api/templates/deployment.yaml
env:
  - name: MODE
    value: {{ .Values.api.env.MODE }}
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: {{ .Release.Name }}-api-secret
        key: DB_PASSWORD
```

## 4. 关键要点总结

- Helm = K8s 包管理器，**Chart 是模板，Release 是实例**
- `values.yaml` 参数化所有可调配置
- 模板用 **Go template 语法**（`{{ .Values.x }}`）
- 用 `helm install` / `helm upgrade` 管理生命周期
- 社区 dify Chart 把 25+ 服务拆成多个子 Chart
- 修改配置**始终改 values.yaml**，不要直接 edit 资源

## 5. 练习题

### 练习 1：基础（必做）

用 `helm create my-app` 创建一个 Chart，修改 `values.yaml` 把 replicaCount 改为 3，部署到 minikube 并验证。

```bash
helm create my-app
cd my-app
# 修改 values.yaml
helm install test ./my-app
kubectl get pods
```

### 练习 2：进阶

阅读社区 dify Helm Chart 的 `values.yaml`（https://github.com/difychart/helm-chart/blob/main/values.yaml），列出它支持的所有可调参数。

### 练习 3：挑战（选做）

为 dify 编写一个最小化 Helm Chart：包含 `api` 一个子 Chart，支持通过 `values.yaml` 配置镜像版本、副本数、环境变量。安装到 K8s 集群并访问 API。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/docker-compose.yaml`（dify 官方部署）
- 社区 dify Helm Chart：https://github.com/difychart/helm-chart
- Helm 官方文档：https://helm.sh/docs/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
