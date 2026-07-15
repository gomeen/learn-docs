# 2.3 K8s 网络：Service / Ingress / NetworkPolicy

> 理解 K8s 的三层网络模型：Service 内部访问、Ingress 外部访问、NetworkPolicy 访问控制。

> ⚠️ **dify 中暂未直接使用 Kubernetes**。本文档基于通用 K8s 概念讲解。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 ClusterIP / NodePort / LoadBalancer / Ingress 四种暴露方式
- 编写 Ingress 把 HTTP 流量路由到 Service
- 用 NetworkPolicy 限制 Pod 间网络访问

## 📚 前置知识

- `08-devops/08-k8s-concepts.md`
- `08-devops/09-k8s-workloads.md`

## 1. 核心概念

### 1.1 K8s 网络的四层模型

```
┌──────────────────────────────────────────────────┐
│ Ingress (七层)                                    │
│  - 基于域名/路径路由                              │
│  - TLS 终止                                      │
└──────────────────┬───────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────┐
│ Service (四层)                                    │
│  - ClusterIP（集群内）                            │
│  - NodePort（节点端口）                           │
│  - LoadBalancer（云厂商 LB）                      │
└──────────────────┬───────────────────────────────┘
                   ▼
┌──────────────────────────────────────────────────┐
│ NetworkPolicy (L3/L4 访问控制)                    │
│  - 允许/拒绝 Pod 间通信                           │
│  - 类似 K8s 的"网络防火墙"                        │
└──────────────────┬───────────────────────────────┘
                   ▼
                  Pod
```

### 1.2 Service 的三种类型

| 类型 | 暴露方式 | 访问范围 | 场景 |
|------|----------|----------|------|
| **ClusterIP**（默认） | 集群内虚拟 IP | 集群内 | 微服务间调用 |
| **NodePort** | 每个 Node 暴露固定端口 | 集群外（IP:NodePort） | 开发测试 |
| **LoadBalancer** | 云厂商 LB | 公网 | 生产环境 |

### 1.3 Ingress：七层路由

Ingress 是**七层（L7）反向代理**，基于 HTTP 主机名/路径路由（反向代理概念详见 [Nginx 反向代理与负载均衡](../../_common/10-network-proxy/02-reverse-proxy.md)）：

```yaml
# example.com/api → api-svc
# example.com/web → web-svc
```

需要 Ingress Controller（Nginx、Traefik、HAProxy 等）配合（Nginx 配置详见 [Nginx 基础](../../_common/10-network-proxy/01-nginx-basics.md)）。

### 1.4 NetworkPolicy：网络隔离

默认 K8s 集群内**所有 Pod 可互相访问**。NetworkPolicy 用来限制：

```yaml
# 允许 api 访问 db，但禁止 db 主动访问 api
```

dify 的 SSRF 防护思想在 K8s 中可用 NetworkPolicy 实现：禁止 `api` Pod 直接访问外网，只能通过 `ssrf-proxy`。

## 2. 代码示例

### 2.1 ClusterIP Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: dify-api
spec:
  type: ClusterIP
  selector:
    app: dify-api
  ports:
    - name: http
      port: 5001
      targetPort: 5001
```

集群内其他 Pod 通过 `dify-api:5001` 访问。

### 2.2 Ingress 路由

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dify-ingress
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - dify.example.com
      secretName: dify-tls
  rules:
    - host: dify.example.com
      http:
        paths:
          - path: /v1
            pathType: Prefix
            backend:
              service:
                name: dify-api
                port:
                  number: 5001
          - path: /
            pathType: Prefix
            backend:
              service:
                name: dify-web
                port:
                  number: 3000
```

### 2.3 NetworkPolicy：API 只能访问 DB 和 SSRF 代理

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-egress
spec:
  podSelector:
    matchLabels:
      app: dify-api
  policyTypes:
    - Egress
  egress:
    # 允许 DNS
    - to:
        - namespaceSelector: {}
      ports:
        - port: 53
          protocol: UDP
    # 允许访问 db
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - port: 5432
    # 允许访问 ssrf-proxy
    - to:
        - podSelector:
            matchLabels:
              app: ssrf-proxy
      ports:
        - port: 3128
    # 禁止其他所有出站（默认 deny）
```

### 2.4 常见错误：Ingress 路径冲突

```yaml
# ❌ 错误：两条规则都匹配 /
- path: /
  backend: {service: dify-api}
- path: /
  backend: {service: dify-web}    # 冲突，K8s 报错

# ✅ 正确：按优先级匹配
- path: /v1
  pathType: Prefix
  backend: {service: dify-api}
- path: /
  pathType: Prefix
  backend: {service: dify-web}    # 最后兜底
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Nginx 入口配置（K8s 化的对照）

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/nginx.conf.template`
**核心代码**（行 1-34）：

```nginx
user  nginx;
worker_processes  ${NGINX_WORKER_PROCESSES};

error_log  /var/log/nginx/error.log notice;
pid        /var/run/nginx.pid;


events {
    worker_connections  1024;
}


http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    sendfile        on;
    #tcp_nopush     on;

    keepalive_timeout  ${NGINX_KEEPALIVE_TIMEOUT};

    #gzip  on;
    client_max_body_size ${NGINX_CLIENT_MAX_BODY_SIZE};

    include /etc/nginx/conf.d/*.conf;
}
```

**解读**：
- 第 4 行：`worker_processes ${NGINX_WORKER_PROCESSES}` 用环境变量控制（默认 `auto`）
- 第 31 行：`client_max_body_size ${NGINX_CLIENT_MAX_BODY_SIZE}` 限制上传体积（默认 100M）
- 第 33 行：`include /etc/nginx/conf.d/*.conf` 引入子配置（dify 把路由规则放在这里）
- **K8s 对照**：这份 Nginx 配置 ≈ K8s **Ingress Controller**（Nginx Ingress）的功能

### 3.2 dify 的 proxy 配置（K8s Ingress 后端 Service）

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/proxy.conf.template`（参考）

**核心内容**：

```nginx
# 反向代理通用配置
proxy_http_version 1.1;
proxy_set_header   Host              $http_host;
proxy_set_header   X-Real-IP         $remote_addr;
proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
proxy_set_header   X-Forwarded-Proto $scheme;
proxy_read_timeout ${NGINX_PROXY_READ_TIMEOUT};
proxy_send_timeout ${NGINX_PROXY_SEND_TIMEOUT};
```

**解读**：
- 这就是 K8s **Ingress 默认行为**：Nginx Ingress 自动注入这些头
- `proxy_read_timeout 3600s` 重要：dify 的 LLM 长连接需要 1 小时超时
- dify 用环境变量 `${...}` 渲染配置，K8s 中可用 **ConfigMap** 替代

### 3.3 dify 的 docker-compose 网络（K8s Service 对照）

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`

**核心代码**（行 1246-1255）：

```yaml
networks:
  # create a network between sandbox, api and ssrf_proxy, and can not access outside.
  ssrf_proxy_network:
    driver: bridge
    internal: true
  milvus:
    driver: bridge
  opensearch-net:
    driver: bridge
    internal: true
```

**解读**：
- docker-compose 的 `internal: true` 网络（详见 [Docker 网络与卷](../../_common/09-containerization/05-network-volume.md)）≈ K8s 的 **NetworkPolicy**（拒绝所有出站）
- 三个网络对应 K8s 中三个 NetworkPolicy：
  - `api-egress`：限制 api 只能访问 db/redis/ssrf-proxy
  - `sandbox-egress`：限制 sandbox 只能访问特定网络
  - `opensearch-egress`：限制 opensearch 无外网访问

## 4. 关键要点总结

- **Service** 集群内访问（ClusterIP/NodePort/LoadBalancer）
- **Ingress** 集群外 HTTP 路由（七层）
- **NetworkPolicy** 限制 Pod 间网络（L3/L4 防火墙）
- dify 的 `internal: true` 网络 ≈ NetworkPolicy `policyTypes: [Egress]`
- 外部 HTTPS 终止通常用 Ingress + cert-manager（详见 [HTTPS / TLS / Let's Encrypt](../../_common/10-network-proxy/03-https.md)）
- Nginx Ingress 是最常见的 Ingress Controller

## 5. 练习题

### 练习 1：基础（必做）

部署一个简单的应用：Deployment（nginx）+ ClusterIP Service + Ingress，访问 `http://<ingress-ip>/` 看到 nginx 欢迎页。

```bash
kubectl create deployment web --image=nginx:1.27
kubectl expose deployment web --port=80
kubectl create ingress web --rule="/=web:80" --class=nginx
```

### 练习 2：进阶

阅读 dify 的 `docker/nginx/conf.d/dev.conf`（如果存在），分析 dify 的路由规则。然后用 Ingress 重写一份 K8s 版本。

### 练习 3：挑战（选做）

为 dify 设计 NetworkPolicy 集合：限制 `api` 只能访问 `postgres`/`redis`/`ssrf-proxy`，`worker_beat` 只能访问 `redis`，验证其他流量被拒绝。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/nginx/nginx.conf.template`
- `/Users/xu/code/github/dify/docker/nginx/proxy.conf.template`
- `/Users/xu/code/github/dify/docker/docker-compose.yaml`
- K8s Service 官方文档：https://kubernetes.io/docs/concepts/services-networking/service/
- K8s Ingress 官方文档：https://kubernetes.io/docs/concepts/services-networking/ingress/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
