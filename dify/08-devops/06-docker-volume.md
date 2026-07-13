# 1.6 Docker 卷与数据持久化

> 理解 Docker 卷的两种形式（bind mount / named volume），能正确处理 dify 中的数据持久化场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 bind mount 和 named volume 的使用场景
- 写出正确的数据持久化配置
- 能读懂 dify 中 `volumes/app/storage`、`volumes/db/data` 等挂载点的作用

## 📚 前置知识

- `08-devops/01-docker-concepts.md`
- `08-devops/04-docker-compose.md`

## 1. 核心概念

### 1.1 容器数据的生命周期问题

**容器的文件系统是临时的**：
- 容器删除后，**容器层**的所有数据丢失
- 容器重启不会丢失数据（容器层持久），但重建容器会丢

**需要持久化的数据**：
- 数据库文件（PostgreSQL data、MySQL data）
- 用户上传的文件（dify 的 storage 目录）
- 配置/证书（nginx SSL 证书、certbot 证书）

### 1.2 两种挂载方式

| 类型 | 语法 | 管理方 | 性能 | 迁移性 |
|------|------|--------|------|--------|
| **bind mount** | `./host/path:/container/path` | 用户 | 取决于主机文件系统 | 差（依赖主机路径） |
| **named volume** | `volume_name:/container/path` | Docker | 较稳定 | 好（Docker 自动管理） |

### 1.3 Bind Mount 详解

```yaml
volumes:
  - ./volumes/db/data:/var/lib/postgresql/data
```

- `./volumes/db/data` 是**宿主机路径**（相对 compose 文件）
- `/var/lib/postgresql/data` 是**容器内路径**
- 文件直接由主机文件系统管理，**Docker 不知道也不关心**内容
- 容器删除后，**主机上的数据还在**
- 适合：开发环境、需要直接查看/编辑文件的场景

### 1.4 Named Volume 详解

```yaml
volumes:
  data:    # 声明在顶层 volumes

services:
  db:
    volumes:
      - data:/var/lib/postgresql/data   # 引用
```

- `data` 由 Docker 管理，存储在 `/var/lib/docker/volumes/`
- Docker 提供高级特性（备份、跨平台驱动）
- 适合：生产环境、跨主机部署

### 1.5 readonly 挂载

```yaml
volumes:
  - ./nginx/nginx.conf.template:/etc/nginx/nginx.conf.template:ro
```

- `:ro` 表示**只读**，容器内无法修改
- 适合：配置文件、证书等不应被容器修改的资产

## 2. 代码示例

### 2.1 数据库持久化

```yaml
services:
  postgres:
    image: postgres:15
    volumes:
      - db-data:/var/lib/postgresql/data   # named volume
    environment:
      POSTGRES_PASSWORD: secret

volumes:
  db-data:    # Docker 自动创建
```

**好处**：
- `docker compose down` 不删除数据（`down -v` 才删）
- 数据存储路径与主机文件系统解耦
- 备份简单：`docker run --rm -v db-data:/data -v $(pwd):/backup alpine tar czf /backup/data.tar.gz /data`

### 2.2 Bind Mount：开发环境

```yaml
services:
  api:
    volumes:
      - ./src:/app/src        # 主机源码改动，容器立即可见
      - ./config:/etc/app:ro  # 配置文件只读
```

**注意**：生产环境**不建议**用 bind mount 部署数据，容易出权限问题。

### 2.3 常见错误：没挂载导致数据丢失

```yaml
# ❌ 错误：数据库数据在容器内，删除容器后数据全丢
services:
  postgres:
    image: postgres:15
    # 没有 volumes

# ✅ 正确：挂载 named volume 或 bind mount
services:
  postgres:
    image: postgres:15
    volumes:
      - db-data:/var/lib/postgresql/data
```

### 2.4 权限问题：UID 不匹配

```yaml
# 容器内进程以 UID 1001 运行，但主机目录属主是 root
volumes:
  - ./data:/app/data    # 容器启动报错：Permission denied
```

**解决**：在主机上 `chown 1001:1001 ./data` 或使用 `:uid` 选项（新版 Docker）。

## 3. dify 仓库源码解读

### 3.1 dify 的存储卷结构

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（行 222-224）：

```yaml
    volumes:
      - ./volumes/app/storage:/app/api/storage
    restart: "no"
```

**解读**：
- `init_permissions` 服务用 `busybox` 镜像专门做一次权限初始化
- `./volumes/app/storage` 是主机路径，绑定到 API 容器内的 `/app/api/storage`
- `restart: "no"` 表示这个 init 容器**只跑一次**就退出
- dify 的 storage 目录存放用户上传的文件、知识库内容

### 3.2 API 服务的存储挂载

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（行 260-262）：

```yaml
    volumes:
      # Mount the storage directory to the container, for storing user files.
      - ./volumes/app/storage:/app/api/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
```

**解读**：
- API 和 Worker 都需要访问 storage 目录（都挂载同一主机路径）
- 这是典型的**多容器共享数据**场景：API 处理上传，Worker 异步处理（向量化、索引）
- 注释明确说明用途：存储用户文件

### 3.3 数据库数据卷

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（行 435-436）：

```yaml
    volumes:
      - ./volumes/db/data:/var/lib/postgresql/data
    healthcheck:
      test:
        [
          "CMD",
          "pg_isready",
```

**解读**：
- PostgreSQL 数据存到 `./volumes/db/data`
- bind mount 让用户**可以方便地备份**：`tar czf db-backup.tar.gz volumes/db/data`
- 容器重建后数据不丢失
- dify 选择 bind mount 而非 named volume，因为是自托管部署，用户需要**直接访问数据**

### 3.4 Nginx 配置和证书挂载（readonly）

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（行 721-729）：

```yaml
    volumes:
      - ./nginx/nginx.conf.template:/etc/nginx/nginx.conf.template
      - ./nginx/proxy.conf.template:/etc/nginx/proxy.conf.template
      - ./nginx/https.conf.template:/etc/nginx/https.conf.template
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./nginx/docker-entrypoint.sh:/docker-entrypoint-mount.sh
      - ./nginx/ssl:/etc/ssl # cert dir (legacy)
      - ./volumes/certbot/conf/live:/etc/letsencrypt/live # cert dir (with certbot container)
      - ./volumes/certbot/conf:/etc/letsencrypt
      - ./volumes/certbot/www:/var/www/html
```

**解读**：
- 多个 bind mount 挂载**配置模板**和**SSL 证书**
- 模板挂载后由 `entrypoint.sh` 渲染（`envsubst` 替换环境变量）到 `/etc/nginx/conf.d/`
- 证书目录同时支持两种来源：
  - `./nginx/ssl`（legacy，手动放证书）
  - `./volumes/certbot/conf`（certbot 自动签发的证书）
- 配置未设为 `:ro`，因为 entrypoint 脚本要写入渲染后的配置文件

## 4. 关键要点总结

- **Bind mount**：主机路径，灵活但依赖主机文件系统
- **Named volume**：Docker 管理，跨平台、易备份
- 数据库、用户文件**必须挂载**，否则容器删除数据丢失
- 多容器共享数据用同一主机路径
- dify 用 bind mount 为主，方便用户直接备份 `volumes/` 目录

## 5. 练习题

### 练习 1：基础（必做）

写一个 `docker-compose.yaml` 启动 PostgreSQL，用 named volume `pgdata` 持久化数据到 `/var/lib/postgresql/data`。

### 练习 2：进阶

阅读 dify `docker-compose.yaml` 中 `api` 和 `worker` 的 volumes 配置，解释两者为什么都挂载 `./volumes/app/storage`？如果只挂一个会发生什么？

### 练习 3：挑战（选做）

把 dify 的 `./volumes/db/data` 数据从一台机器迁移到另一台：先停止服务，打包数据目录，启动新机器上的服务，验证数据完整。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/docker-compose.yaml`
- Docker 卷官方文档：https://docs.docker.com/storage/volumes/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
