# 10.1 Nginx 基础：配置文件与虚拟主机

> 理解 Nginx 进程模型、配置文件结构、`server` 块（虚拟主机）与 `location` 路由匹配规则。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 Nginx 的 Master / Worker 进程模型
- 读懂 `nginx.conf` 的层级结构（`http` / `server` / `location`）
- 区分 `server_name` 虚拟主机、`listen` 端口、`location` 路径匹配
- 看懂 dify `/docker/nginx/nginx.conf.template` 的全局配置

## 📚 前置知识

- HTTP 协议基础（请求 / 响应 / 状态码）
- 容器网络可参考 [Docker 网络与卷](../09-containerization/05-network-volume.md)；反代见 [02-reverse-proxy](./02-reverse-proxy.md)

## 1. 核心概念

### 1.1 Nginx 进程模型

```
┌──────────────┐
│ master 进程  │  ← root 运行，负责读取配置 + fork worker
│ (pid 1)      │
└──────┬───────┘
       │ fork
       ↓
   ┌──────┐   ┌──────┐   ┌──────┐
   │worker│   │worker│   │worker│  ← 普通用户（nginx）
   │  1   │   │  2   │   │  N   │     处理实际请求
   └──────┘   └──────┘   └──────┘
```

- **Master**：只加载配置 + 管理 worker + 升级二进制时不中断服务
- **Worker**：单线程/单进程处理数千并发连接（基于 epoll 事件驱动）
- **配置热更新**：`nginx -s reload` 让 master 启动新 worker，关闭旧 worker，平滑切换

### 1.2 配置文件层级

```nginx
# 主配置：nginx.conf
main              # 顶层（user / worker_processes / events）
├── events {}     # 网络事件模型
└── http {}       # HTTP 模块
    ├── server {} # 虚拟主机（一个站点）
    │   ├── location /api {}   # 路径路由
    │   ├── location / {}
    │   └── listen 80
    ├── server {} # 另一个虚拟主机
    └── upstream {} # 负载均衡池
```

**关键点**：
- 一个 Nginx 可以托管多个站点（基于 `server_name` 和 `listen`）
- 每个 `server` 是一个虚拟主机
- 每个 `location` 是 URL 路径前缀匹配规则

### 1.3 四种 Location 匹配规则

| 前缀 | 含义 | 优先级 |
|------|------|--------|
| `=` | 精确匹配 URI | 1（最高） |
| `^~` | 前缀匹配，不检查正则 | 2 |
| `~` | 大小写敏感正则 | 3 |
| `~*` | 大小写不敏感正则 | 3（与 `~` 同级，但顺序加载）|
| 无前缀 | 普通前缀匹配 | 4（最低）|

```nginx
location = /favicon.ico { ... }           # 精确匹配
location ^~ /static/ { ... }              # 优先匹配静态文件
location ~ \.(gif|jpg)$ { ... }           # 匹配以 .gif / .jpg 结尾
location /api { ... }                     # 默认前缀匹配
```

## 2. 代码示例

### 2.1 最简 Nginx 配置

```nginx
# 文件：nginx.conf
user nginx;                       # worker 进程运行用户
worker_processes auto;            # worker 数量（auto = CPU 核数）
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;      # 每个 worker 最大并发连接
    use epoll;                    # Linux 高性能事件驱动
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    sendfile on;                  # 零拷贝提升静态文件传输
    keepalive_timeout 65;
    server_tokens off;            # 隐藏版本号（安全）

    include /etc/nginx/conf.d/*.conf;
}
```

### 2.2 多虚拟主机（同一 Nginx 托管 2 个域名）

```nginx
http {
    # 虚拟主机 1：example.com
    server {
        listen 80;
        server_name example.com www.example.com;
        root /var/www/example;
        index index.html;

        location /api {
            proxy_pass http://localhost:8080;
        }
    }

    # 虚拟主机 2：api.example.com
    server {
        listen 80;
        server_name api.example.com;
        location / {
            proxy_pass http://localhost:3000;
        }
    }
}
```

### 2.3 常见错误：缺少分号或花括号

```nginx
# ❌ 错误：user 指令没有分号
user nginx

# ✅ 正确
user nginx;

# ❌ 错误：location 块不闭合
location /api {
    proxy_pass http://localhost:8080
#   缺少 ; 或 }

# ✅ 正确
location /api {
    proxy_pass http://localhost:8080;
}
```

可用 `nginx -t` 校验语法是否正确。

## 3. dify 与 ruoyi 源码解读

### 3.1 dify Nginx 全局配置（变量化驱动）

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/nginx.conf.template`
**核心代码**（行 1-34）：

```nginx
# Please do not directly edit this file. Instead, modify the .env variables related to NGINX configuration.

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
- 第 1 行注释：**禁止手工修改**——文件由环境变量 `NGINX_*` 渲染（运行 `docker-entrypoint.sh` 时用 `envsubst` 替换）
- 第 4 行：`worker_processes ${NGINX_WORKER_PROCESSES}`——可通过 `.env` 调整
- 第 11 行：`worker_connections 1024`——每 worker 最大并发 1024（按 CPU 核数 ×1024 估算总并发）
- 第 19-21 行：`log_format main`——标准 combined log，附加 `$http_x_forwarded_for` 字段记录真实客户端 IP
- 第 25 行：`sendfile on`——sendfile 系统调用，零拷贝提升静态文件传输效率
- 第 28 行：`keepalive_timeout ${NGINX_KEEPALIVE_TIMEOUT}`——可调
- 第 31 行：`client_max_body_size ${NGINX_CLIENT_MAX_BODY_SIZE}`——**限制上传文件大小**（默认 1M，dify 大概改成 100MB 以支持上传大型文档）
- 第 33 行：`include /etc/nginx/conf.d/*.conf`——**关键的拆分**：把虚拟主机配置放在 conf.d 里

### 3.2 dify conf.d 虚拟主机配置

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/conf.d/default.conf`
**核心代码**（行 1-51）：

```nginx
# Please do not directly edit this file. Instead, modify the .env variables related to NGINX configuration.

server {
    listen 80;
    server_name _;

    location /console/api {
      proxy_pass http://api:5001;
      include proxy.conf;
    }

    location /api {
      proxy_pass http://api:5001;
      include proxy.conf;
    }

    location /v1 {
      proxy_pass http://api:5001;
      include proxy.conf;
    }

    location /files {
      proxy_pass http://api:5001;
      include proxy.conf;
    }

    location /explore {
      proxy_pass http://web:3000;
      include proxy.conf;
    }

    location /e/ {
      proxy_pass http://plugin_daemon:5002;
      proxy_set_header Dify-Hook-Url $scheme://$host$request_uri;
      include proxy.conf;
    }

    location / {
      proxy_pass http://web:3000;
      include proxy.conf;
    }
    location /mcp {
      proxy_pass http://api:5001;
      include proxy.conf;
    }
    # placeholder for acme challenge location


    # placeholder for https config defined in https.conf.template

}
```

**解读**：
- 第 4 行：`server_name _`——通配符，匹配任何域名（只有一个虚拟主机时常用）
- 第 7-15 行：`/console/api`、`/api`、`/v1`、`/files` 都转给 `api:5001`——dify 后端 Flask API
- 第 27-30 行：`/explore` 和 `/` 路径转给 `web:3000`——前端 Next.js
- 第 32-36 行：`/e/` 转给 `plugin_daemon:5002`——插件调试入口
- 第 34 行：`proxy_set_header Dify-Hook-Url $scheme://$host$request_uri`——插件回调 URL 注入
- 第 46-50 行：`# placeholder`——这些位置由容器启动时根据是否启用 HTTPS 渲染

**架构图**：

```
                  NginX (port 80)
                      │
   ┌──── /api ────────┼──── /v1 ────┐
   ├──── /console/api ┼──── /files ─┤
   └──── /mcp, /openapi ──────┐   │
                              ↓   ↓
                       api:5001 (Flask)
   ┌──── /explore ──────────┐   │
   └──── /                 ──┐   │
                              ↓
                       web:3000 (Next.js)
   /e/ ────────────────→ plugin_daemon:5002
```

### 3.3 proxy.conf：复用反向代理头配置

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/proxy.conf.template`
**核心代码**（行 1-12）：

```nginx
# Please do not directly edit this file. Instead, modify the .env variables related to NGINX configuration.

proxy_set_header Host $host;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Port $server_port;
proxy_http_version 1.1;
proxy_set_header Connection "";
proxy_buffering off;
proxy_read_timeout ${NGINX_PROXY_READ_TIMEOUT};
proxy_send_timeout ${NGINX_PROXY_SEND_TIMEOUT};
```

**解读**：
- 第 3 行：`Host $host`——保留客户端原始域名（不是 `proxy_pass` 的服务名），应用层可正确处理多域名路由
- 第 4 行：`X-Forwarded-For $proxy_add_x_forwarded_for`——追加客户端 IP，否则后端日志全部是 Nginx IP
- 第 5 行：`X-Forwarded-Proto $scheme`——告诉后端原始协议（http / https），用于生成正确 URL
- 第 7 行：`proxy_http_version 1.1`——HTTP/1.1 支持 keepalive
- 第 8 行：`Connection ""`——禁用到上游的 keepalive 头来兼容 HTTP/1.0 后端
- 第 9 行：`proxy_buffering off`——流式响应不缓冲，配合 dify 的 SSE 流式输出
- 第 10 行：`proxy_read_timeout ${NGINX_PROXY_READ_TIMEOUT}`——读超时，避免流式响应被截断

**为什么单独文件？** 因为每个 `location` 块都引用 `include proxy.conf`，**一处定义，多处复用**——避免重复 9 段相同的代理头配置。

### 3.4 对比 ruoyi：缺少独立 Nginx 配置（关注点差异）

**事实**：在 `ruoyi-vue-pro/script/docker/` 目录里**没有 `nginx.conf` 或 `nginx.conf.template`**。

**为什么？** ruoyi 是 Spring Boot 后端 + yudao-ui 前端的"前后端分离"项目，其 Nginx 通常部署在**外层反向代理机器**（如云厂商 SLB / 单独 Nginx 节点），而不是容器化堆栈内。

**但生产实践常在容器外独立部署 Nginx**：

```nginx
# 典型部署在主机的 /etc/nginx/conf.d/yudao.conf
upstream yudao-backend {
    server 127.0.0.1:48080;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate     /etc/ssl/certs/example.crt;
    ssl_certificate_key /etc/ssl/private/example.key;

    client_max_body_size 100m;     # 后台上传大文件

    location / {
        proxy_pass http://yudao-backend;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

**对比要点**：
- dify 把 Nginx **也容器化**，统一由 docker-compose 管理（适合产品化交付）
- ruoyi 通常 Nginx 在**外层独立节点**（适合传统 IDC 部署）

## 4. 关键要点总结

- **进程模型**：1 master + N worker，平滑 reload 不中断
- **配置层级**：main → events / http → server → location
- **变量化驱动**：dify 把所有可调项都做成 `${VAR}` 形式，便于运营调整
- **`include` 复用**：长配置常用 `include conf.d/*.conf` 拆分，避免单文件巨型
- **`server_name _`**：匹配任意主机名
- **`proxy_*` 头设置**：Host / X-Forwarded-* 必须保留

## 5. 练习题

### 练习 1：基础（必做）

写一个最简 Nginx 配置：
- 监听 8080
- 域名 `test.local`
- `/` 返回静态页面 `/var/www/html/index.html`
- `/api/*` 反代到 `http://localhost:5001`

**参考答案**：见 `solutions/01-nginx-min.md`

### 练习 2：进阶

阅读 `dify/docker/nginx/conf.d/default.conf`：
1. `location /v1 { proxy_pass http://api:5001; }` 与 `location /v1/ { proxy_pass http://api:5001/; }` 有什么差异？
2. 为什么 `/explore` 不写成 `/explore/`？

### 练习 3：挑战（选做）

为 ruoyi `yudao-server` 编写一份**容器内可运行**的 Nginx 镜像（Dockerfile + nginx.conf）：
- 监听 80，反代 `yudao-server:48080`
- 加 HTTPS（用 self-signed 证书演示）
- 加日志格式输出 `$http_x_forwarded_for`

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/nginx/nginx.conf.template`
- `/Users/xu/code/github/dify/docker/nginx/conf.d/default.conf`
- `/Users/xu/code/github/dify/docker/nginx/proxy.conf.template`
- Nginx 官方文档：http://nginx.org/en/docs/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
