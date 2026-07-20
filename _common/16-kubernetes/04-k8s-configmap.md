# 2.4 ConfigMap 与 Secret

> 学习 K8s 中两种配置管理资源：ConfigMap（明文配置）和 Secret（敏感数据）。

> ⚠️ **dify 中暂未直接使用 Kubernetes**。本文档基于通用 K8s 概念讲解。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 ConfigMap 和 Secret 的使用场景
- 把 dify 的 `.env` 配置迁移到 ConfigMap/Secret
- 理解 K8s 配置热更新机制

## 📚 前置知识

- `01-k8s-concepts.md`
- 环境变量与 12-Factor（详见 [环境变量](../17-config/02-env-vars.md)）

## 1. 核心概念

### 1.1 ConfigMap 与 Secret 对比

| 资源 | 用途 | 存储 | 编码 |
|------|------|------|------|
| **ConfigMap** | 非敏感配置 | 明文 | - |
| **Secret** | 敏感数据（密码、token） | Base64 | 默认 Base64（非加密） |

### 1.2 三种使用方式

```yaml
# 1. 环境变量
env:
  - name: DB_HOST
    valueFrom:
      configMapKeyRef:
        name: app-config
        key: db.host

# 2. 整个 ConfigMap 作为环境变量
envFrom:
  - configMapRef:
      name: app-config

# 3. 挂载为文件
volumes:
  - name: config
    configMap:
      name: app-config
volumeMounts:
  - name: config
    mountPath: /etc/config
```

### 1.3 Secret 的特殊处理

- **Base64 不是加密**——只是编码，敏感数据应启用 K8s 加密（etcd encryption at rest）
- 真实生产环境用 **External Secrets**（AWS Secrets Manager / HashiCorp Vault）
- 替代方案：**Sealed Secrets**（公钥加密，存储在 Git）

### 1.4 热更新

- **环境变量**：ConfigMap 更新**不会**自动同步到运行中 Pod（需要重启）
- **挂载文件**：ConfigMap 更新**会自动**同步到文件（kubelet 定期刷新，约 60-90 秒）

## 2. 代码示例

### 2.1 ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dify-api-config
data:
  MODE: api
  CONSOLE_API_URL: http://127.0.0.1:5001
  CONSOLE_WEB_URL: http://127.0.0.1:3000
  LOG_LEVEL: INFO
  PLUGIN_MAX_PACKAGE_SIZE: "52428800"
  NGINX_CLIENT_MAX_BODY_SIZE: 100M
```

### 2.2 Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: dify-api-secret
type: Opaque
stringData:           # stringData 会自动 Base64
  DB_PASSWORD: difyai123456
  REDIS_PASSWORD: difyai123456
  SECRET_KEY: a-long-random-string
```

### 2.3 在 Pod 中使用

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: api
spec:
  containers:
    - name: api
      image: langgenius/dify-api:1.16.0-rc1
      envFrom:
        - configMapRef:
            name: dify-api-config
        - secretRef:
            name: dify-api-secret
      volumeMounts:
        - name: config-volume
          mountPath: /etc/config
  volumes:
    - name: config-volume
      configMap:
        name: dify-api-config
```

### 2.4 常见错误：ConfigMap 改名后 Pod 起不来

```bash
# ❌ 错误：ConfigMap 改名，envFrom 引用旧名字
# Pod 状态：CreateContainerConfigError
kubectl describe pod api
# Events: Error: configmap "dify-api-config" not found

# ✅ 解决：同步更新 Pod 的 envFrom
kubectl set env deployment/api --from=configmap/dify-api-config-new
```

## 3. dify 仓库源码解读

### 3.1 dify 的环境变量文件

**文件位置**：`/Users/xu/code/github/dify/docker/envs/core-services/api.env`（参考结构）

**核心内容**（典型形式）：

```bash
# dify API 服务的环境变量
MODE=api
CONSOLE_API_URL=http://127.0.0.1:5001
SERVICE_API_URL=http://api:5001
APP_WEB_URL=http://127.0.0.1:3000
PLUGIN_DAEMON_URL=http://plugin_daemon:5002
PLUGIN_MAX_PACKAGE_SIZE=52428800
PLUGIN_DIFY_INNER_API_KEY=QaHbTe77CtuXmsfyhR7+vRjI/+XbV1AaFy691iy+kGDv2Jvy0/eAh8Y1
LOG_LEVEL=INFO
```

**解读**：
- dify 把配置**按服务分类**到不同 `.env` 文件（api.env、worker.env、web.env、shared.env）
- 敏感数据（API Key、密码）也直接放在 `.env` 文件，**生产环境应改用 Secret 或 Vault**
- docker-compose 用 `env_file` 引用（详见 [Docker Compose](../../_common/09-containerization/04-compose.md)），K8s 中对应 `envFrom.configMapRef` / `envFrom.secretRef`

### 3.2 dify 的环境变量引用语法

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（行 423-426）：

```yaml
    environment:
      POSTGRES_USER: ${DB_USERNAME:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-difyai123456}
      POSTGRES_DB: ${DB_DATABASE:-dify}
      PGDATA: ${PGDATA:-/var/lib/postgresql/data/pgdata}
```

**解读**：
- `${DB_USERNAME:-postgres}` 是 **shell 变量替换**语法：取 `.env` 中的 `DB_USERNAME`，未设则用默认值 `postgres`
- docker-compose 启动时**不会**做变量替换，**容器启动时**由 entrypoint 脚本处理
- K8s 对照：K8s 不支持默认值语法，需要在 ConfigMap 中填好所有值，或用 **Kustomize** 补全

### 3.3 映射到 K8s ConfigMap

将上面的 dify API 配置转成 K8s ConfigMap：

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dify-api-config
data:
  MODE: "api"
  CONSOLE_API_URL: "http://127.0.0.1:5001"
  SERVICE_API_URL: "http://api:5001"
  APP_WEB_URL: "http://127.0.0.1:3000"
  PLUGIN_DAEMON_URL: "http://plugin_daemon:5002"
  PLUGIN_MAX_PACKAGE_SIZE: "52428800"
  LOG_LEVEL: "INFO"
---
apiVersion: v1
kind: Secret
metadata:
  name: dify-api-secret
type: Opaque
stringData:
  PLUGIN_DIFY_INNER_API_KEY: "QaHbTe77CtuXmsfyhR7+vRjI/+XbV1AaFy691iy+kGDv2Jvy0/eAh8Y1"
```

## 4. 关键要点总结

- **ConfigMap** 存非敏感配置，**Secret** 存敏感数据
- Secret 默认只是 Base64 编码，**不是加密**
- 两种使用方式：`envFrom`（环境变量）或 `volumeMount`（文件）
- **环境变量不会热更新**，文件挂载会自动同步（约 60-90s 延迟）
- dify 用 `.env` 文件组织配置，K8s 化时按 service 拆分 ConfigMap

## 5. 练习题

### 练习 1：基础（必做）

创建一个 ConfigMap `my-config`，包含两个 key：`LOG_LEVEL=INFO` 和 `DB_HOST=mysql`；在 Pod 中通过 `envFrom` 引用，验证环境变量正确注入。

### 练习 2：进阶

阅读 dify `docker/envs/core-services/` 目录下的所有 `.env` 文件，列出哪些应转为 ConfigMap、哪些应转为 Secret。区分标准是什么？

### 练习 3：挑战（选做）

把 dify 的 PostgreSQL 服务配置改造成 K8s ConfigMap + Secret，用 `volumeMount` 把 Secret 挂载为文件（`/run/secrets/db-password`），让 PostgreSQL 从文件读密码。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/envs/`（dify 环境变量文件目录）
- `/Users/xu/code/github/dify/docker/docker-compose.yaml`
- K8s ConfigMap 官方文档：https://kubernetes.io/docs/concepts/configuration/configmap/
- K8s Secret 官方文档：https://kubernetes.io/docs/concepts/configuration/secret/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
