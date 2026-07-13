# 1.5 Docker 网络：bridge / host / overlay

> 理解 Docker 网络模型，能读懂 dify 中 `ssrf_proxy_network`（内网隔离）的设计意图。

## 🎯 学习目标

完成本文档后，你将能够：
- 说出 bridge / host / overlay / none 四种网络的区别
- 理解容器间通过服务名（DNS）通信的机制
- 理解 `internal: true` 网络的作用和安全意义
- 能解释 dify 的 `ssrf_proxy_network` 为何要设为 `internal: true`

## 📚 前置知识

- `08-devops/01-docker-concepts.md`
- `08-devops/04-docker-compose.md`

## 1. 核心概念

### 1.1 Docker 网络的四种模式

| 模式 | 作用范围 | 隔离性 | 性能 |
|------|----------|--------|------|
| `bridge` | 单机 | 容器间隔离 | 中（NAT） |
| `host` | 单机 | 与宿主机共享网络 | 高 |
| `overlay` | 跨主机（Swarm） | 跨节点互通 | 中 |
| `none` | 单机 | 完全无网络 | - |

### 1.2 bridge 网络（默认）

- 每个容器有自己的**虚拟网络接口**，通过 Docker 网桥与外界通信
- 同一 bridge 网络的容器可以通过**服务名**互相访问（Docker 内置 DNS）
- 不同 bridge 网络默认互相隔离
- 适合：单台主机上的多容器应用

### 1.3 host 网络

- 容器**直接使用宿主机网络栈**，没有网络隔离
- 没有端口映射（容器端口直接暴露到主机）
- 适合：高吞吐、低延迟的网络应用

### 1.4 internal 网络（关键安全特性）

```yaml
networks:
  ssrf_proxy_network:
    driver: bridge
    internal: true
```

- `internal: true` 的网络**没有网关**，容器**完全无法访问外网**
- 适合：需要严格限制出站流量的服务（如 SSRF 防护代理、数据库）
- dify 用它隔离 `api` 和 `ssrf_proxy`，**所有外部 HTTP 请求强制走代理**

### 1.5 容器间 DNS 解析

Docker 内置 DNS（127.0.0.11:53）会把**服务名**解析为该服务的容器 IP：

```
api 服务 → DNS 查询 "redis" → 10.0.0.5（redis 容器 IP）
```

所以 dify 的 API 容器可以用 `redis:6379` 而不是 IP 地址。

## 2. 代码示例

### 2.1 自定义 bridge 网络

```yaml
# 文件：docker-compose.yaml
services:
  api:
    image: my-api:1.0
    networks:
      - backend

  db:
    image: postgres:15
    networks:
      - backend

networks:
  backend:
    driver: bridge
```

```bash
# api 容器里执行
ping db      # 通过服务名访问，自动 DNS 解析
curl db:5432 # 直连
```

### 2.2 host 网络

```yaml
services:
  web:
    image: nginx
    network_mode: host   # 无端口映射，直接占用主机 80
```

### 2.3 internal 网络（出站隔离）

```yaml
services:
  ssrf_proxy:
    image: squid
    networks:
      - isolated      # 只能访问同网络的服务

  api:
    image: my-api
    networks:
      - isolated      # 只能访问同网络和 default 网络

networks:
  isolated:
    internal: true    # 关键：没有外网网关
  default:
    driver: bridge
```

**安全效果**：
- `api` 容器**无法直接访问公网**（如要拉取数据只能走 `ssrf_proxy`）
- 即使 `api` 被攻破，攻击者也无法用它直接打外网

### 2.4 常见错误：跨网络通信问题

```yaml
# ❌ 错误：两个服务在不同网络，无法互访
services:
  api:
    networks: [frontend]
  db:
    networks: [backend]

# ✅ 正确：加入同一网络
services:
  api:
    networks: [backend]
  db:
    networks: [backend]
```

## 3. dify 仓库源码解读

### 3.1 dify 的内网隔离设计

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（行 1246-1259）：

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

volumes:
  oradata:
  dify_es01_data:
```

**解读**：
- 第 1-4 行：`ssrf_proxy_network` 注释明确说明用途——"在 sandbox、api、ssrf_proxy 之间创建网络，**不能访问外部**"
- `internal: true` 关键作用：
  - API 容器**无法直接访问公网**
  - 任何外部 HTTP 请求**必须经过 ssrf_proxy 代理**
  - 即使 API 被攻破（SSRF 漏洞），攻击者也无法绕过代理直接打内网
- 第 5-6 行：`milvus` 网络**不设 internal**，因为 Milvus 需要下载模型/向量化数据
- 第 7-9 行：`opensearch-net` 同样是 `internal: true`，因为 ES 不需要外网

### 3.2 服务接入两个网络

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（行 269-271）：

```yaml
    networks:
      - ssrf_proxy_network
      - default
```

**解读**：
- API 服务同时接入 `ssrf_proxy_network`（内网隔离）和 `default`（普通网桥）
- 通过 `default` 网络可访问 db / redis / web（这些是常规服务）
- 通过 `ssrf_proxy_network` 访问 `ssrf_proxy` 容器（代理）
- **多网络接入**是 Compose 的关键能力：一个容器可以同时属于多个网络

### 3.3 Nginx 反向代理的端口暴露

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（行 758-760）：

```yaml
    ports:
      - "${EXPOSE_NGINX_PORT:-80}:${NGINX_PORT:-80}"
      - "${EXPOSE_NGINX_SSL_PORT:-443}:${NGINX_SSL_PORT:-443}"
```

**解读**：
- Nginx 是**唯一**对外暴露端口的容器（`80` 和 `443`）
- 其他服务（API、Worker、DB）**不暴露端口**，只通过内部网络访问
- 这是经典的"反向代理边缘化"模式：仅边缘服务暴露端口，内部服务隐藏在 Docker 网络中

## 4. 关键要点总结

- Docker 默认 `bridge` 网络，**同网络内通过服务名 DNS 解析**
- `internal: true` 禁止外网出站，**强化安全边界**
- 容器可同时加入**多个网络**，连接不同安全区域
- 反向代理（Nginx）是**唯一**对外暴露端口的服务
- dify 的 `ssrf_proxy_network` 通过内网隔离 + 强制代理，**防止 SSRF 攻击**

## 5. 练习题

### 练习 1：基础（必做）

写一个 `docker-compose.yaml`，包含 `api` 和 `db` 两个服务，加入同一个自定义 bridge 网络 `mynet`，让 `api` 能通过服务名 `db` 访问数据库。

### 练习 2：进阶

阅读 dify `docker-compose.yaml` 中 `ssrf_proxy` 服务的定义，解释为什么它需要同时接入 `ssrf_proxy_network` 和 `default`？如果只接入 `ssrf_proxy_network` 会发生什么？

### 练习 3：挑战（选做）

在本地用 `docker network ls` 查看 dify 创建的网络，用 `docker network inspect dify_ssrf_proxy_network` 查看哪些容器接入，分析其网络拓扑。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/docker-compose.yaml`
- Docker 网络官方文档：https://docs.docker.com/network/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
