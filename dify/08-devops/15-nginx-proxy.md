# 3.2 Nginx 反向代理与负载均衡

> 学会用 Nginx 配置反向代理和负载均衡，能读懂 dify 的请求路由配置。

## 🎯 学习目标

完成本文档后，你将能够：
- 配置反向代理把请求转发到后端服务
- 用 `upstream` 配置负载均衡（轮询、权重、ip_hash）
- 读懂 dify 的 `default.conf.template` 路由规则设计

## 📚 前置知识

- `08-devops/14-nginx-basics.md`

## 1. 核心概念

### 1.1 反向代理 vs 正向代理

```
正向代理（代理客户端）：
   客户端 → 代理 → 目标服务器
   用途：翻墙、匿名访问

反向代理（代理服务器）：
   客户端 → 反代（Nginx）→ 后端服务（多个）
   用途：负载均衡、SSL 终止、隐藏真实 IP
```

### 1.2 反向代理关键指令

```nginx
location /api {
    proxy_pass http://backend:5001;        # 后端地址
    proxy_set_header Host $http_host;       # 传递原始 Host
    proxy_set_header X-Real-IP $remote_addr;# 真实客户端 IP
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### 1.3 负载均衡算法

- **轮询（round-robin，默认）**：请求均匀分配
- **权重（weight）**：按比例分配（性能不均的服务器）
- **ip_hash**：同一 IP 始终到同一后端（会话保持）
- **least_conn**：最少连接优先（长连接场景）
- **random**：随机

### 1.4 健康检查

- Nginx 开源版**不主动健康检查**（被动的：失败 N 次后临时摘除）
- Nginx Plus 和 `upstream_check_module` 支持主动健康检查
- K8s 用 **readinessProbe** 实现（更标准）

## 2. 代码示例

### 2.1 简单反向代理

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2.2 负载均衡

```nginx
upstream backend {
    # 轮询（默认）
    server 10.0.0.1:5001;
    server 10.0.0.2:5001;
    server 10.0.0.3:5001;

    # 权重（server 1 接收 3 倍流量）
    # server 10.0.0.1:5001 weight=3;
    # server 10.0.0.2:5001 weight=1;

    # 健康检查参数
    keepalive 32;                # 长连接池
    keepalive_timeout 60s;
}

server {
    listen 80;
    location / {
        proxy_pass http://backend;
    }
}
```

### 2.3 WebSocket 反向代理

```nginx
location /socket.io/ {
    proxy_pass http://backend:5001;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;       # 关键
    proxy_set_header Connection "upgrade";         # 关键
    proxy_read_timeout 3600s;                      # 长连接
}
```

### 2.4 常见错误：proxy_pass 末尾斜杠

```nginx
# 路径处理差异
location /api/ {                       # 带斜杠
    proxy_pass http://backend;          # /api/users → http://backend/users
}

location /api/ {
    proxy_pass http://backend/;         # /api/users → http://backend//users
}
```

## 3. dify 仓库源码解读

### 3.1 dify 的路由分发

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/conf.d/default.conf.template`
**核心代码**（行 1-73）：

```nginx
# Please do not directly edit this file. Instead, modify the .env variables related to NGINX configuration.

server {
    listen ${NGINX_PORT};
    server_name ${NGINX_SERVER_NAME};

    location /console/api {
      proxy_pass http://api:5001;
      include proxy.conf;
    }

    location /api {
      proxy_pass http://api:5001;
      include proxy.conf;
    }

    location /socket.io/ {
      resolver 127.0.0.11 valid=30s ipv6=off;
      set $socket_io_upstream ${NGINX_SOCKET_IO_UPSTREAM};
      proxy_pass http://$socket_io_upstream;
      include proxy.conf;
      proxy_set_header Upgrade $http_upgrade;
      proxy_set_header Connection "upgrade";
      proxy_cache_bypass $http_upgrade;
    }

    location /v1 {
      proxy_pass http://api:5001;
      include proxy.conf;
    }

    location /openapi {
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

    location /triggers {
      proxy_pass http://api:5001;
      include proxy.conf;
    }

    # placeholder for acme challenge location
    ${ACME_CHALLENGE_LOCATION}

    # placeholder for https config defined in https.conf.template
    ${HTTPS_CONFIG}
}
```

**解读**：

路径路由设计：
- `/console/api`、`/api`、`/v1`、`/openapi`、`/files`、`/mcp`、`/triggers` → **`api:5001`**（后端 API 服务）
- `/explore`、`/` → **`web:3000`**（Next.js 前端）
- `/e/` → **`plugin_daemon:5002`**（插件守护进程）
- `/socket.io/` → **`api_websocket:5001`**（WebSocket 服务，profile=collaboration）

关键设计点：
- 第 17-25 行：WebSocket 路由，需要 `Upgrade` / `Connection: upgrade` 头才能升级
- 第 18 行：`resolver 127.0.0.11` 使用 Docker 内置 DNS（避免硬编码 upstream IP）
- 第 19 行：`set $socket_io_upstream` 用变量动态指定 upstream
- 第 49 行：`Dify-Hook-Url` 告诉插件守护进程外部访问 URL（用于回调）
- 第 69-72 行：占位符由 entrypoint 脚本替换为 HTTPS 配置和 certbot 验证路径

### 3.2 dify 的 upstream 动态化

**核心代码片段**（行 17-20）：

```nginx
location /socket.io/ {
    resolver 127.0.0.11 valid=30s ipv6=off;
    set $socket_io_upstream ${NGINX_SOCKET_IO_UPSTREAM};
    proxy_pass http://$socket_io_upstream;
    include proxy.conf;
}
```

**解读**：
- 用环境变量 `${NGINX_SOCKET_IO_UPSTREAM}` 决定 WebSocket upstream
- 默认 `api_websocket:5001`（开启了 collaboration profile 时）
- 未开启时 fallback 到 `api:5001`
- `resolver 127.0.0.11` 是 **Docker 嵌入式 DNS**，每次请求都重新解析服务名

## 4. 关键要点总结

- 反向代理用 `proxy_pass` + `proxy_set_header` 传递真实客户端信息
- 负载均衡用 `upstream` 块，支持轮询、权重、ip_hash
- WebSocket 代理必须设置 `Upgrade` 和 `Connection: upgrade` 头
- `proxy_pass` 末尾斜杠**改变路径拼接**行为
- dify 的路由设计：API 类路径 → api:5001，页面类 → web:3000，插件 → plugin_daemon
- WebSocket 用变量 + Docker DNS 动态化 upstream

## 5. 练习题

### 练习 1：基础（必做）

启动两个后端服务（可用 `python -m http.server 8001` 和 `8002`），用 Nginx upstream 做负载均衡，访问 `http://localhost/` 看到请求在两个服务间切换。

### 练习 2：进阶

阅读 dify `default.conf.template`，画出请求路由表（路径 → 后端服务、端口）。为什么 `/console/api` 和 `/api` 都转发到 `api:5001`？它们有区别吗？

### 练习 3：挑战（选做）

修改 dify `default.conf.template`，加一个 `/api/v2` 路径，强制要求 header `X-API-Version: 2` 才转发，否则返回 403。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/nginx/conf.d/default.conf.template`
- `/Users/xu/code/github/dify/docker/nginx/proxy.conf.template`
- `/Users/xu/code/github/dify/docker/docker-compose.yaml`
- Nginx 反向代理官方文档：http://nginx.org/en/docs/http/ngx_http_proxy_module.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
