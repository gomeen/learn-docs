# 9.5 Docker 网络与卷

> 理解容器间通信（bridge / host / overlay）与数据持久化（bind mount / named volume / tmpfs）。

## 🎯 学习目标

完成本文档后，你将能够：
- 选择合适的 Docker 网络驱动
- 解释 bind mount / volume / tmpfs 的区别和适用场景
- 看懂 dify `docker-compose.yaml` 中 `ssrf_proxy_network` 为何 `internal: true`
- 排查容器无法互相通信、容器重启后数据丢失等常见问题

## 📚 前置知识

- 9.4 Docker Compose（服务依赖与启动顺序）
- Linux 网络基础（接口、路由、DNS）
- /Users/xu/code/gomeen/learn-docs/_common/09-containerization/04-compose.md

## 1. 核心概念

### 1.1 三种挂载方式

| 类型 | 形式 | 主机位置 | 适合场景 |
|------|------|---------|---------|
| **Bind Mount** | `-v /host/path:/container/path` | 任意 | 开发期热加载源码 |
| **Named Volume** | `-v volname:/container/path` | Docker 管理 | 生产数据库数据 |
| **tmpfs** | `--tmpfs /container/path` | 内存 | 临时缓存、敏感文件 |

```bash
# Bind mount：开发期把源码挂进去改
docker run -v $(pwd)/src:/app/src myapp

# Named volume：数据库持久化（容器删了数据还在）
docker run -v pgdata:/var/lib/postgresql/data postgres

# tmpfs：临时文件，重启即清空
docker run --tmpfs /tmp myapp
```

### 1.2 五种网络驱动

| 驱动 | 范围 | 适用场景 |
|------|------|---------|
| **bridge**（默认） | 单机 | Compose 同一项目内服务互通 |
| **host** | 单机 | 网络性能极致要求（如 VoIP） |
| **none** | 单机 | 完全隔离，配合 ip 白名单 |
| **overlay** | 跨主机 | Swarm / K8s 跨节点 |
| **macvlan** | 单机 | 给容器真实局域网 IP |

**常用命令**：
```bash
docker network create my-net
docker network connect my-net container-name
docker network inspect my-net
```

### 1.3 内置 DNS 与容器名解析

Compose 把所有服务名、容器名注册到**内置 DNS**。这就是为什么 `http://api:5001` 能解析到 `api` 容器。

```bash
# 在容器内用 docker 内置 DNS 查询
docker exec api nslookup redis
# Server:    127.0.0.11
# Address 1: 127.0.0.11
# Name:      redis
# Address 1: 172.18.0.5
```

### 1.4 容器间通信的"超能力"：`internal: true`

```yaml
networks:
  internal-only:
    driver: bridge
    internal: true    # 关键：禁用对外路由
```

这个网络内的容器**互相能通，但访问不了外网**——是 SSRF 防护的标配。dify 正是用这个机制构建 SSRF 防护区。

## 2. 代码示例

### 2.1 容器网络通信示例

```bash
# 创建自定义网络
docker network create mynet

# 启动两个容器加入网络
docker run -d --name api --network mynet nginx
docker run -d --name client --network mynet alpine sleep 3600

# 测试连通性
docker exec client sh -c "wget -q -O- http://api/"
# 输出 nginx 默认页面 → 同网络可直接用容器名访问

# 默认 bridge 网络则必须用 IP
docker inspect api | grep IPAddress
```

### 2.2 持久化 volume 示例

```bash
# 1. 创建命名卷
docker volume create pgdata

# 2. 用卷启动 postgres
docker run -d --name db -v pgdata:/var/lib/postgresql/data postgres:15

# 3. 数据库里建表，插入数据
docker exec -it db psql -U postgres -c "CREATE TABLE t(id int); INSERT INTO t VALUES (1);"

# 4. 删除容器（数据卷保留！）
docker rm -f db

# 5. 重启容器验证数据还在
docker run -d --name db2 -v pgdata:/var/lib/postgresql/data postgres:15
docker exec db2 psql -U postgres -c "SELECT * FROM t;"
# id
#  1
```

### 2.3 常见错误：bind mount 误把主机路径写错

```bash
# ❌ 错误：容器内 /app 永远是空的（因为主机路径不存在）
docker run -v /does/not/exist:/app myapp

# ✅ 正确：用 pwd 或相对路径确认存在
ls ./src && docker run -v $(pwd)/src:/app/src myapp

# 看容器内实际挂了什么
docker exec myapp ls -la /app/src
```

## 3. dify 与 ruoyi 源码解读

### 3.1 dify：网络分段与 SSRF 防护

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（行 1246-1255，行 671-694）：

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

```yaml
  # ssrf_proxy server
  # for more information, please refer to
  # https://docs.dify.ai/learn-more/faq/install-faq#18-why-is-ssrf-proxy-needed%3F
  ssrf_proxy:
    image: ubuntu/squid:latest
    restart: always
    volumes:
      - ./ssrf_proxy/squid.conf.template:/etc/squid/squid.conf.template
      - ./ssrf_proxy/docker-entrypoint.sh:/docker-entrypoint-mount.sh
    entrypoint:
      [
        "sh",
        "-c",
        "cp /docker-entrypoint-mount.sh /docker-entrypoint.sh && sed -i 's/\r$$//' /docker-entrypoint.sh && chmod +x /docker-entrypoint.sh && /docker-entrypoint.sh",
      ]
    environment:
      # pls clearly modify the squid env vars to fit your network environment.
      HTTP_PORT: ${SSRF_HTTP_PORT:-3128}
      COREDUMP_DIR: ${SSRF_COREDUMP_DIR:-/var/spool/squid}
      SSRF_PROXY_ALLOW_PRIVATE_IPS: ${SSRF_PROXY_ALLOW_PRIVATE_IPS:-}
      SSRF_PROXY_ALLOW_PRIVATE_DOMAINS: ${SSRF_PROXY_ALLOW_PRIVATE_DOMAINS:-}
    networks:
      - ssrf_proxy_network
      - default
```

**解读**：
- 第 1248-1250 行：`internal: true`——**这个网段彻底不能访问外网**，连网关路由都没有
- 第 671-684 行：Squid 作为唯一的反向代理出口，强制走白名单
- 第 692-693 行：`networks` 同时挂在 `ssrf_proxy_network`（受限）和 `default`（通用）—— 通过 Squid 访问外网

**SSRF 防护原理图**：
```
   ┌──────────────────────────┐
   │   api / plugin_daemon    │
   │   (在 ssrf_proxy_network) │ ◄── 内网
   └──────────────┬───────────┘
                  ↓ HTTP
   ┌──────────────────────────┐
   │   ssrf_proxy (Squid)     │ ◄── 唯一出口
   │   - 域名/IP 白名单过滤    │
   │   - 在两个网络之间桥接    │
   └──────────────┬───────────┘
                  ↓ HTTP（外网）
              公网 LLM API
```

**为什么不在 api 容器里加 ACL 就好？** 容器的 IP 是动态的，且应用代码可能因为 bugs 走别的协议。强制走代理是"防御性纵深"，即使应用层出错也兜得住。

### 3.2 ruoyi：本地 bind mount + 简单 volume

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`
**核心代码**（行 31-37）：

```yaml
  server:
    container_name: yudao-server
    build:
      context: ./yudao-server/
    image: yudao-server
    restart: unless-stopped
    ports:
      - "48080:48080"
```

```yaml
volumes:
  mysql:
    driver: local
  redis:
    driver: local
```

**与 MySQL 段对照（结合上下文行 15-18）**：
```yaml
    volumes:
      - mysql:/var/lib/mysql/
      - ../../sql/mysql/ruoyi-vue-pro.sql:/docker-entrypoint-initdb.d/ruoyi-vue-pro.sql:ro
```

**解读**：
- **Bind mount**：`../../sql/mysql/ruoyi-vue-pro.sql:/docker-entrypoint-initdb.d/...:ro`——挂载 SQL 脚本到 MySQL 初始化目录
  - `:ro` = 只读（read-only），防止容器内意外修改脚本
  - 这种挂载主要用于"启动初始化"，脚本本身就是只读的
- **Named volume**：`mysql:/var/lib/mysql/`——数据库数据放命名卷，重建容器数据还在
- **volumes 段（最后）**：`volumes: { mysql, redis }`——顶层声明的命名卷，Dockers 自动创建 `yudao-system_mysql` 卷

**对比 dify**：ruoyi 没有自定义网络，全部用 Compose 默认 `bridge`——只有本地开发足够用。生产部署需要更严格的网络分段时，应参照 dify 增加 `internal: true` 防护区。

## 4. 关键要点总结

- **Bind mount** vs **Named volume**：前者由主机路径直接暴露，后者由 Docker 管理更安全
- **`internal: true`** = 完全无外网（SSRF 防护标配）
- **容器名解析**：同一网络内可用服务名解析，无需记 IP
- **Compose 默认网络**：项目名作为前缀，所有服务互通
- **多网络挂载**：通过 `networks: [a, b]` 让容器同时属于多网络段（如 Squid）
- **常见故障**：容器间 ping 不通 → 检查 `networks` 字段；数据丢失 → 检查 `volumes` 是否命名卷

## 5. 练习题

### 练习 1：基础（必做）

```bash
# 操作题：验证 volume 持久化
docker run -d --name pg -v mydata:/var/lib/postgresql/data postgres:15
docker exec pg psql -U postgres -c "CREATE TABLE t(id int)"
docker rm -f pg
docker run -d --name pg2 -v mydata:/var/lib/postgresql/data postgres:15
docker exec pg2 psql -U postgres -c "\dt"   # 应输出 t
```

### 练习 2：进阶

阅读 `dify/docker/docker-compose.yaml` 第 69-71 行：
```yaml
x-shared-api-worker-config: &shared-api-worker-config
  ...
  networks:
    - ssrf_proxy_network
    - default
```

回答：
1. 为什么 api / worker 同时挂 `ssrf_proxy_network` 和 `default` 两个网络？
2. 如果只挂 `ssrf_proxy_network`，会带来哪些副作用？

### 练习 3：挑战（选做）

为 `ruoyi-vue-pro/script/docker/docker-compose.yml` 增加：
- 一个**专用内部网络** `internal-net: { driver: bridge, internal: true }`
- 让 `server` 同时挂 `internal-net` 和默认网络
- 让 `mysql` / `redis` 都挂 `internal-net`
- 实现"db 不能直接出公网"的安全约束

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/docker-compose.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`
- Docker 网络：https://docs.docker.com/network/
- Docker 卷：https://docs.docker.com/storage/volumes/
- Squid SSRF Proxy 文档：https://docs.dify.ai/learn-more/faq/install-faq

---

**文档版本**：v1.0
**最后更新**：2026-07-13
