# 2.4 docker-compose 部署

> 理解 docker-compose 多容器编排，掌握 ruoyi 的 MySQL + Redis + Server + Admin 一键部署。

## 🎯 学习目标

完成本文档后，你将能够：
- 编写 docker-compose.yml 编排多个服务
- 掌握 services、volumes、networks、depends_on 关键指令
- 理解环境变量注入与默认值
- 能独立部署 ruoyi 全套服务

## 📚 前置知识

- Docker 基础
- `05-java-docker.md`

## 1. 核心概念

### 1.1 docker-compose 是什么？

**单 Docker 容器**只能跑一个进程。真实应用通常需要：
- 应用服务（Spring Boot）
- 数据库（MySQL/PostgreSQL）
- 缓存（Redis）
- 前端（Nginx）

**docker-compose** = 多容器编排工具，用一个 YAML 文件描述所有容器的关系。

### 1.2 核心概念

| 概念 | 含义 |
|------|------|
| `services` | 容器列表 |
| `image` / `build` | 拉取镜像 / 本地构建 |
| `ports` | 主机端口:容器端口 |
| `volumes` | 数据卷（持久化） |
| `environment` | 环境变量 |
| `depends_on` | 启动顺序（仅控制启动顺序，不等待就绪） |
| `networks` | 自定义网络（默认会创建 compose 内的网络） |

### 1.3 docker-compose 命令

```bash
# 启动
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f server

# 停止
docker-compose down

# 停止并删除数据卷
docker-compose down -v
```

## 2. 代码示例

### 2.1 最小可用的 compose 文件

```yaml
# 文件：docker-compose.yml
version: "3.4"

services:
  mysql:
    image: mysql:8
    environment:
      MYSQL_ROOT_PASSWORD: 123456
    volumes:
      - mysql-data:/var/lib/mysql
    ports:
      - "3306:3306"

  app:
    build: .
    depends_on:
      - mysql
    environment:
      SPRING_DATASOURCE_URL: jdbc:mysql://mysql:3306/test
    ports:
      - "8080:8080"

volumes:
  mysql-data:
```

**说明**：
- `depends_on: mysql` — app 容器先于 mysql 启动（但不等待 mysql 就绪）
- `volumes: mysql-data:/var/lib/mysql` — 数据持久化（避免容器删除后数据丢失）
- `mysql:3306` — 同 compose 内，service 名即 hostname

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的完整 compose 编排

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`
**核心代码**（行 1-30）：

```yaml
version: "3.4"

name: yudao-system

services:
  mysql:
    container_name: yudao-mysql
    image: mysql:8
    restart: unless-stopped
    tty: true
    ports:
      - "3306:3306"
    environment:
      MYSQL_DATABASE: ${MYSQL_DATABASE:-ruoyi-vue-pro}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-123456}
    volumes:
      - mysql:/var/lib/mysql/
      - ../../sql/mysql/ruoyi-vue-pro.sql:/docker-entrypoint-initdb.d/ruoyi-vue-pro.sql:ro

  redis:
    container_name: yudao-redis
    image: redis:6-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis:/data

  server:
    container_name: yudao-server
    build:
      context: ./yudao-server/
    image: yudao-server
    restart: unless-stopped
    ports:
      - "48080:48080"
    environment:
      SPRING_PROFILES_ACTIVE: local
      ...
```

**解读**：
- 第 1 行：`version: "3.4"` — compose 文件格式版本
- 第 3 行：`name: yudao-system` — 项目名（替代默认的目录名）
- 第 5 行：4 个 services（mysql、redis、server、admin）

### 3.2 MySQL 容器：初始化 SQL 自动加载

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`
**核心代码**（行 6-19）：

```yaml
  mysql:
    container_name: yudao-mysql
    image: mysql:8
    restart: unless-stopped
    tty: true
    ports:
      - "3306:3306"
    environment:
      MYSQL_DATABASE: ${MYSQL_DATABASE:-ruoyi-vue-pro}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-123456}
    volumes:
      - mysql:/var/lib/mysql/
      - ../../sql/mysql/ruoyi-vue-pro.sql:/docker-entrypoint-initdb.d/ruoyi-vue-pro.sql:ro
```

**解读**：
- 第 5 行：`tty: true` — 分配伪终端（避免某些镜像启动后立即退出）
- 第 7 行：`restart: unless-stopped` — 异常退出时自动重启
- 第 11-12 行：环境变量 + `${VAR:-default}` 默认值
- 第 14 行：`mysql:/var/lib/mysql/` — 命名卷（数据持久化）
- 第 15 行：**关键** — 把 `../../sql/mysql/ruoyi-vue-pro.sql` 挂载到 `/docker-entrypoint-initdb.d/`
  - MySQL 镜像启动时会**自动执行**该目录下的所有 `.sql` 文件
  - 实现"启动 MySQL → 自动建表 + 灌入初始数据"

### 3.3 Redis 容器

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`
**核心代码**（行 20-28）：

```yaml
  redis:
    container_name: yudao-redis
    image: redis:6-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis:/data
```

**解读**：
- `redis:6-alpine` — 使用 alpine 精简镜像（~10MB）
- `volumes: redis:/data` — 持久化 Redis 数据
- **未设置密码**（生产环境必须设置 `requirepass`）

### 3.4 后端服务容器：环境变量注入

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`
**核心代码**（行 46-56）：

```yaml
        --spring.datasource.dynamic.datasource.master.url=${MASTER_DATASOURCE_URL:-jdbc:mysql://yudao-mysql:3306/ruoyi-vue-pro?useSSL=false&serverTimezone=Asia/Shanghai&allowPublicKeyRetrieval=true&nullCatalogMeansCurrent=true}
        --spring.datasource.dynamic.datasource.master.username=${MASTER_DATASOURCE_USERNAME:-root}
        --spring.datasource.dynamic.datasource.master.password=${MASTER_DATASOURCE_PASSWORD:-123456}
        --spring.redis.host=${REDIS_HOST:-yudao-redis}
    depends_on:
      - mysql
      - redis
```

**解读**：
- `--spring.datasource.dynamic.datasource.master.*` — Spring Boot 接受 `--key=value` 形式覆盖配置
- `${VAR:-default}`：从 `.env` 文件或环境读取
- `yudao-mysql:3306` — 同 compose 内用 service 名访问
- `depends_on: mysql redis` — 控制启动顺序（但不等待 mysql ready！）

### 3.5 admin 前端容器

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`
**核心代码**（行 58-78）：

```yaml
  admin:
    container_name: yudao-admin
    build:
      context: ./yudao-ui-admin
      args:
        NODE_ENV:
          ENV=${NODE_ENV:-production}
          PUBLIC_PATH=${PUBLIC_PATH:-/}
          VUE_APP_TITLE=${VUE_APP_TITLE:-芋道管理系统}
          VUE_APP_BASE_API=${VUE_APP_BASE_API:-/prod-api}
    image: yudao-admin
    restart: unless-stopped
    ports:
      - "8080:80"
    depends_on:
      - server
```

**解读**：
- `build.args` — 构建参数（VUE_APP_* 是 Vue 编译时变量）
- `ports: "8080:80"` — admin 容器内 80 端口（nginx）映射到主机 8080
- `depends_on: server` — 等待 server 启动（虽然不真正"等待就绪"）

### 3.6 命名卷

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`
**核心代码**（行 80-85）：

```yaml
volumes:
  mysql:
    driver: local
  redis:
    driver: local
```

**解读**：
- 命名卷 `mysql` 和 `redis` 由 Docker 自动管理
- 容器删除后**数据保留**
- 完整清理：`docker-compose down -v`（会同时删除卷）

## 4. 关键要点总结

- `version: "3.4"` 是 compose 文件格式版本
- `depends_on` 只控制**启动顺序**，不等待服务**就绪**（生产环境用 healthcheck）
- `${VAR:-default}` 是 docker-compose 的变量插值（从 `.env` 文件或环境变量读取）
- MySQL 镜像支持把 `.sql` 挂载到 `/docker-entrypoint-initdb.d/` 自动执行
- 同一 compose 网络内，**service 名即 hostname**（如 `yudao-mysql:3306`）
- 命名卷 + `restart: unless-stopped` 保证数据和服务可用性

## 5. 练习题

### 练习 1：基础（必做）

在 `script/docker/` 目录下执行 `docker-compose up -d`，等待所有容器启动后访问 `http://localhost:48080` 验证后端，`http://localhost:8080` 验证前端。

### 练习 2：进阶

修改 `docker-compose.yml` 给 Redis 加密码：`--requirepass yourpassword`，在 yudao-server 的 ARGS 中添加 `--spring.redis.password=yourpassword`，重启验证。

### 练习 3：挑战（选做）

把 yudao-server 的启动方式从 `depends_on` 改为 `healthcheck`（`test: ["CMD", "curl", "-f", "http://localhost:48080/actuator/health"]`），实现真正的"等待就绪"。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`
- `/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker.env`
- [docker-compose 官方文档](https://docs.docker.com/compose/compose-file/)
- [MySQL Docker Hub - 初始化容器](https://hub.docker.com/_/mysql)

---

**文档版本**：v1.0
**最后更新**：2026-07-13
