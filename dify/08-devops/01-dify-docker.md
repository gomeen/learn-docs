# 1.7 dify 的 Docker Compose 全家桶分析

> 深入解读 dify 仓库的 Docker Compose 配置，理解其多服务架构、Profile 设计、安全隔离。

## 🎯 学习目标

完成本文档后，你将能够：
- 画出 dify 的服务依赖拓扑图
- 理解 dify 25+ 个 service 的分层（核心服务 / 中间件 / 基础设施）
- 掌握 Profile 按需启动可选服务的玩法
- 能根据 dify 文档本地启动整套服务

## 📚 前置知识

- `08-devops/01-docker-concepts.md` ~ `08-devops/06-docker-volume.md`

## 1. 核心概念

### 1.1 dify 的服务分层

dify 的 `docker-compose.yaml` 包含 25+ 个 service（Docker Compose 概念详见 [Docker Compose：本地多容器编排](../../_common/09-containerization/04-compose.md)），按职责分为四类：

| 类别 | 核心服务 | 数量 |
|------|----------|------|
| **应用核心** | api、worker、worker_beat、web、api_websocket | 5 |
| **AI 引擎** | sandbox、plugin_daemon、agent_backend、local_sandbox | 4 |
| **数据存储** | db_postgres、db_mysql、redis、weaviate、qdrant、milvus、couchbase、pgvector、oceanbase、seekdb、tidb、iris、elasticsearch、opensearch、opengauss、myscale、matrixone、vastbase、oracle、pgvecto-rs、chroma | 20+ |
| **基础设施** | nginx（详见 [Nginx 基础](../../_common/10-network-proxy/01-nginx-basics.md)）、ssrf_proxy、certbot、unstructured | 4 |
| **初始化** | init_permissions | 1 |

### 1.2 核心服务的依赖关系

```
                      ┌──────┐
                      │ web  │ (Next.js 前端)
                      └──┬───┘
                         │ HTTP
                         ▼
                      ┌──────┐         ┌────────────┐
                      │nginx │◄────────┤ certbot    │ (可选)
                      └──┬───┘         └────────────┘
                         │ reverse proxy（详见 [Nginx 反向代理](../../_common/10-network-proxy/02-reverse-proxy.md)）
              ┌──────────┼──────────┐
              ▼          ▼          ▼
          ┌──────┐   ┌──────┐  ┌──────────┐
          │ api  │   │ web  │  │ api_ws   │ (可选, profile=collaboration)
          └──┬───┘   └──────┘  └──────────┘
             │
    ┌────────┼────────┐
    ▼        ▼        ▼
┌──────┐ ┌──────┐ ┌─────────┐
│redis │ │ db_* │ │ agent_* │
└──────┘ └──────┘ └─────────┘
            ▲          ▲
            │          │
            └──────────┘
        ┌──────┐    ┌──────────┐
        │ ssrf │◄───┤ sandbox  │
        │ proxy│    └──────────┘
        └──────┘
```

### 1.3 Profile 设计

dify 把可选服务放进 `profiles`，用户按需启动：

| Profile | 作用 | 启动命令 |
|---------|------|----------|
| `postgresql` / `mysql` | 主数据库 | `--profile postgresql up` |
| `weaviate` / `qdrant` / `milvus` | 向量数据库 | `--profile weaviate up` |
| `elasticsearch` / `opensearch` | 全文检索 | `--profile elasticsearch up` |
| `certbot` | HTTPS 证书自动签发（详见 [HTTPS / Let's Encrypt](../../_common/10-network-proxy/03-https.md)） | `--profile certbot up` |
| `collaboration` | WebSocket 协同 | `--profile collaboration up` |

### 1.4 安全隔离三道防线

1. **ssrf_proxy_network（internal: true）**：API 容器无法直连外网
2. **ssrf_proxy（squid）**：所有外部 HTTP 请求走代理，dify 检查白名单（SSRF 防护详见 [SSRF](../../_common/05-web-security/06-ssrf.md)）
3. **sandbox**：执行用户自定义代码的隔离环境

## 2. 代码示例

### 2.1 启动完整 dify 栈

```bash
# 1. 克隆代码
git clone https://github.com/langgenius/dify.git
cd dify/docker

# 2. 复制环境变量
cp .env.example .env

# 3. 启动（postgresql 模式）
docker compose --profile postgresql up -d

# 4. 验证服务
docker compose ps
curl http://localhost/install
```

### 2.2 添加自定义向量库

```yaml
# docker-compose.override.yaml
services:
  api:
    environment:
      VECTOR_STORE: qdrant
  worker:
    environment:
      VECTOR_STORE: qdrant
```

```bash
docker compose --profile postgresql --profile qdrant up -d
```

### 2.3 自定义资源限制

```yaml
# 在 .env 文件中添加
COMPOSE_API_CPU_LIMIT=2
COMPOSE_API_MEMORY_LIMIT=4G
```

## 3. 关键要点总结

- dify 25+ 服务分为：应用核心、AI 引擎、数据存储、基础设施
- **Profile** 机制让 20+ 备选数据库按需启动，避免镜像臃肿
- **三道安全防线**：内网隔离 + ssrf_proxy 代理 + sandbox
- 入口容器 `init_permissions` 处理 UID 权限对齐
- Worker 健康检查**默认禁用**（避免 Celery 空闲态误重启）
- 启动命令：`docker compose --profile postgresql up -d`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
