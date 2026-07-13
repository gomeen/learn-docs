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

dify 的 `docker-compose.yaml` 包含 25+ 个 service，按职责分为四类：

| 类别 | 核心服务 | 数量 |
|------|----------|------|
| **应用核心** | api、worker、worker_beat、web、api_websocket | 5 |
| **AI 引擎** | sandbox、plugin_daemon、agent_backend、local_sandbox | 4 |
| **数据存储** | db_postgres、db_mysql、redis、weaviate、qdrant、milvus、couchbase、pgvector、oceanbase、seekdb、tidb、iris、elasticsearch、opensearch、opengauss、myscale、matrixone、vastbase、oracle、pgvecto-rs、chroma | 20+ |
| **基础设施** | nginx、ssrf_proxy、certbot、unstructured | 4 |
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
                         │ reverse proxy
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
| `certbot` | HTTPS 证书自动签发 | `--profile certbot up` |
| `collaboration` | WebSocket 协同 | `--profile collaboration up` |

### 1.4 安全隔离三道防线

1. **ssrf_proxy_network（internal: true）**：API 容器无法直连外网
2. **ssrf_proxy（squid）**：所有外部 HTTP 请求走代理，dify 检查白名单
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

## 3. dify 仓库源码解读

### 3.1 入口容器：权限初始化

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

**解读**：
- 第 2 行：`busybox` 极简镜像（~1MB），只用来执行 shell 脚本
- 第 5-14 行：完整 shell 脚本——检查标记文件，避免重复 chown；用 `chown -R 1001:1001` 把目录属主改为 dify 用户
- 第 15 行：标记文件 `.init_permissions` 实现**幂等性**（多次执行只做一次）
- 第 16 行：`restart: "no"` 容器执行完即退出
- `$${FLAG_FILE}` 是 Compose 的转义（`$$` → `$`），避免 Compose 解析 `${}`
- **关键设计**：API 容器以 UID 1001 运行，但主机挂载目录默认属主是 root，需要预处理

### 3.2 Worker 服务的健康检查

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（行 333-342）：

```yaml
    healthcheck:
      test: ["CMD-SHELL", "celery -A celery_healthcheck.celery inspect ping"]
      interval: ${COMPOSE_WORKER_HEALTHCHECK_INTERVAL:-30s}
      timeout: ${COMPOSE_WORKER_HEALTHCHECK_TIMEOUT:-30s}
      retries: 3
      start_period: 60s
      disable: ${COMPOSE_WORKER_HEALTHCHECK_DISABLED:-true}
```

**解读**：
- 第 2 行：用 Celery 自带的 `inspect ping` 命令检查 worker 是否存活
- 第 3-4 行：健康检查间隔和超时通过 `.env` 文件可调
- 第 7 行：`start_period: 60s` 启动 60 秒内不检查（避免冷启动误报）
- 第 8 行：`disable: ${...:-true}` **默认禁用**健康检查，因为 Celery worker 在空闲时会无响应，导致不必要的重启

### 3.3 网络隔离（final 设计）

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
- `ssrf_proxy_network` 隔离所有外部 HTTP 流量
- `opensearch-net` 隔离 ES（ES 不需要外网）
- `milvus` 网络**不设** `internal`，因为 Milvus standalone 需要下载模型
- 顶层 `volumes` 声明的是 named volume（`oradata` for OceanBase、`dify_es01_data` for ES）

## 4. 关键要点总结

- dify 25+ 服务分为：应用核心、AI 引擎、数据存储、基础设施
- **Profile** 机制让 20+ 备选数据库按需启动，避免镜像臃肿
- **三道安全防线**：内网隔离 + ssrf_proxy 代理 + sandbox
- 入口容器 `init_permissions` 处理 UID 权限对齐
- Worker 健康检查**默认禁用**（避免 Celery 空闲态误重启）
- 启动命令：`docker compose --profile postgresql up -d`

## 5. 练习题

### 练习 1：基础（必做）

按官方文档在本地用 `docker compose --profile postgresql up -d` 启动 dify，访问 `http://localhost/install` 完成初始化，截图保存。

### 练习 2：进阶

阅读 dify `docker-compose.yaml` 全部内容，列出所有 Profile 及其对应的服务，画出依赖关系图。

### 练习 3：挑战（选做）

修改 dify 的启动配置：把 PostgreSQL 换成 MySQL（用 `--profile mysql`），同时启用 Weaviate 向量库（`--profile weaviate`），验证应用仍能正常工作。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/docker-compose.yaml`
- `/Users/xu/code/github/dify/docker/docker-compose-template.yaml`
- `/Users/xu/code/github/dify/docker/README.md`
- dify 官方安装文档：https://docs.dify.ai/getting-started/install-self-hosted/docker-compose

---

**文档版本**：v1.0
**最后更新**：2026-07-13
