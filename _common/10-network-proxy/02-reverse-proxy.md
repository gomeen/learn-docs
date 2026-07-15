# 10.2 Nginx 反向代理与负载均衡

> 掌握 Nginx 的 `proxy_pass` / `upstream` / 负载均衡算法，能看懂 dify 和 ruoyi 的反向代理配置。

## 🎯 学习目标

完成本文档后，你将能够：
- 配置 `proxy_pass` 反向代理
- 用 `upstream` 定义负载均衡池和多种调度算法
- 配置 WebSocket 升级（dify /socket.io 反向代理）
- 解释负载均衡与反向代理在架构中的位置

## 📚 前置知识

- [10.1 Nginx 基础](./01-nginx-basics.md)（server / location 块）
- HTTP 协议（请求方法、Header、状态码）
- WebSocket 协议基础（Upgrade / Connection）

## 1. 核心概念

### 1.1 反向代理 vs 正向代理

```
正向代理 ──── 用户配置代理上网，代理隐藏"客户端"
  客户端 ──[代理]──→ 互联网

反向代理 ──── 服务端反向暴露，代理隐藏"服务端"
  客户端 ──→ [反向代理] ──→ 后端 N 个实例
```

**反向代理的核心能力**：
1. **负载均衡**：多后端实例间分配流量
2. **SSL 终结**：在代理处统一处理 HTTPS（配置见 [03-https](./03-https.md)）
3. **缓存**：静态文件 / API 响应缓存
4. **限流 / WAF**：在网关层做防御（限流算法见 [04-rate-limiting](../03-cache-patterns/04-rate-limiting.md)）
5. **动静分离**：静态资源直接由 Nginx 返回，动态请求转发

### 1.2 proxy_pass：反向代理核心指令

```nginx
location /api {
    proxy_pass http://api-server:5001;     # 注意末尾斜杠
}

# 末尾没有 /：把 /api/users -> http://api-server:5001/api/users
# 末尾有 /：把 /api/users -> http://api-server:5001/users（保留路径替换）
```

### 1.3 upstream：负载均衡池

```nginx
upstream backend {
    ip_hash;                                # 算法：会话保持
    server 10.0.0.1:5001 weight=3;          # 权重 3
    server 10.0.0.2:5001 weight=1;
    server 10.0.0.3:5001 backup;            # 仅当主都挂了才参与
    keepalive 32;                           # Nginx 到 upstream 的 keepalive 连接池
}

server {
    location / {
        proxy_pass http://backend;
    }
}
```

**5 种负载均衡算法**：
1. `round-robin`（默认）：轮询
2. `weight=`：加权轮询
3. `ip_hash`：同 IP 路由到同一后端（会话保持）
4. `least_conn`：最少连接优先
5. `random`：随机（2 个后端时最简单）

### 1.4 WebSocket 反向代理（特殊协议升级）

WebSocket 协议是 HTTP 升级（Upgrade），需要特殊处理：

```nginx
location /socket.io/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;        # 关键：把客户端的 Upgrade: websocket 传下去
    proxy_set_header Connection "upgrade";         # 关键：把 Connection: upgrade 传下去
    proxy_read_timeout 86400;                      # 长连接超时不能太短
}
```

## 2. 代码示例

### 2.1 完整负载均衡示例

```nginx
upstream api_cluster {
    least_conn;                                  # 最少连接优先
    server 10.0.0.1:5001 max_fails=3 fail_timeout=30s;
    server 10.0.0.2:5001 max_fails=3 fail_timeout=30s;
    server 10.0.0.3:5001 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 80;

    location /api {
        proxy_pass http://api_cluster;

        # 真实客户端信息传递给后端
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # 超时设置
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # 失败重试
        proxy_next_upstream error timeout http_502;
        proxy_next_upstream_tries 2;
    }
}
```

### 2.2 缓存配置（核心片段）

```nginx
proxy_cache_path /tmp/nginx_cache levels=1:2 keys_zone=api_cache:10m max_size=1g;

location /api/v1/static-list {
    proxy_pass http://backend;
    proxy_cache api_cache;
    proxy_cache_valid 200 10m;       # 200 响应缓存 10 分钟
    proxy_cache_key "$scheme$host$request_uri";
    add_header X-Cache-Status $upstream_cache_status;  # HIT/MISS 调试
}
```

### 2.3 常见错误：未保留 Host 头

```nginx
# ❌ 错误：默认 proxy_set_header Host 是 $proxy_host（后端服务名）
# 多域名应用路由会乱
location / { proxy_pass http://backend; }

# ✅ 正确：显式保留 Host（dify 的做法）
location / { 
    proxy_pass http://backend;
    proxy_set_header Host $host;
}
```

## 3. dify 与 ruoyi 源码解读

### 3.1 dify：9 条 location 反代到 3 类后端

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/conf.d/default.conf.template`
**核心代码**（行 7-66）：

```nginx
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
```

**解读**：

**A. 服务名解析**（与 Compose 网络对应）：
- `http://api:5001`：反代到 Compose 服务 `api`（Flask 后端）
- `http://web:3000`：反代到 Compose 服务 `web`（Next.js 前端）
- `http://plugin_daemon:5002`：反代到 Compose 服务 `plugin_daemon`

**B. WebSocket 升级（行 17-25）**：
```nginx
location /socket.io/ {
    resolver 127.0.0.11 valid=30s ipv6=off;       # Docker 内置 DNS (127.0.0.11)
    set $socket_io_upstream ${NGINX_SOCKET_IO_UPSTREAM};
    proxy_pass http://$socket_io_upstream;
    include proxy.conf;
    proxy_set_header Upgrade $http_upgrade;       # WebSocket 握手关键
    proxy_set_header Connection "upgrade";
    proxy_cache_bypass $http_upgrade;             # WebSocket 不缓存
}
```

- 第 17 行：用 `127.0.0.11` 解析，是因为 `${NGINX_SOCKET_IO_UPSTREAM}` 是变量，proxy_pass 不能用变量直接拼域名
- 第 18-19 行：`set $socket_io_upstream`——把环境变量赋给变量
- 第 24 行：`proxy_cache_bypass $http_upgrade`——如果有 Upgrade 头，不读缓存

**C. 关键反代头（proxy.conf 复用）**：
- 第 16 行：`include proxy.conf`——把 `Host / X-Forwarded-For / Connection: ""` 等公用头一次性引入

**D. 末尾斜杠一致性**：
- `location /v1 { proxy_pass http://api:5001; }`——访问 `/v1/users` → 后端 `/v1/users`（路径不替换）
- `location /e/ { proxy_pass http://plugin_daemon:5002; }`——访问 `/e/foo` → 后端 `/foo`（带末尾 `/` 的会替换）

### 3.2 ruoyi：生产层独立 Nginx 反代（典型模式）

如 10.1 节所述，ruoyi 仓库本身不直接带 Nginx 配置文件，但其在生产环境的部署惯例是**在独立 NginX 节点上反代**：

```nginx
# 这是典型生产 ruoyi 部署的反向代理配置
# 文件：/etc/nginx/conf.d/yudao.conf

upstream yudao_backend {
    server 127.0.0.1:48080 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate     /etc/nginx/certs/example.com.crt;
    ssl_certificate_key /etc/nginx/certs/example.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 100m;     # 上传大文件（ruoyi 经常传 Excel）

    # 安全头
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-Content-Type-Options nosniff;

    location / {
        proxy_pass http://yudao_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 静态前端（前端 CDN）
    location / {
        root /var/www/yudao-ui;
        try_files $uri $uri/ /index.html;
    }
}
```

**对比 dify 与 ruoyi 反代**：

| 对比点 | dify | ruoyi |
|--------|------|-------|
| Nginx 部署位置 | 容器内（统一编排） | 容器外（独立节点） |
| upstream 池 | 单实例（无池） | 通常 1 个，但配 keepalive |
| WebSocket | 有（`/socket.io/` 路径） | 几乎无（管理后台用 HTTP） |
| 文件上传大小 | 较大（dify 默认 100MB+）| 适中（Excel 通常 100MB） |
| HTTPS | 通过 Certbot profile 自动签发 | 通常用自签 / 云厂商证书 |

**为什么 dify 不做 upstream 池？** 因为 docker-compose 默认单实例就够了，多实例需要 Swarm 或 K8s（dify 在 helm chart 中才有）。

## 4. 关键要点总结

- **proxy_pass** 是反代核心，注意末尾 `/` 的路径替换语义
- **upstream** 定义负载均衡池：`round-robin` / `weight` / `ip_hash` / `least_conn`
- **WebSocket**：必须传 `Upgrade` 和 `Connection: upgrade` 头
- **proxy_next_upstream**：自动重试其他后端
- **Host 头保留**：多域名路由必须显式 `proxy_set_header Host $host`
- **变量化的反代**：dify 用 `${NGINX_SOCKET_IO_UPSTREAM}` 是因为 `proxy_pass` 不支持变量直拼域名

## 5. 练习题

### 练习 1：基础（必做）

写一份 Nginx 配置：
- upstream `api_pool` 含 2 个后端（`10.0.0.1:5001` 和 `10.0.0.2:5001`）
- `least_conn` 算法
- `location /` 反代到 `api_pool`
- 保留 Host、X-Real-IP

**参考答案**：见 `solutions/01-upstream.md`

### 练习 2：进阶

阅读 `dify/docker/nginx/proxy.conf.template`，回答：
1. 第 8 行 `proxy_set_header Connection ""` 的含义是什么？为什么要清空而不是保持默认？
2. 第 9 行 `proxy_buffering off` 适用什么场景？为什么 dify 流式响应需要关掉？

### 练习 3：挑战（选做）

为 dify 设计一个**支持多实例 API 的反代配置**：
```nginx
upstream api_pool {
    server api:5001;
    server api:5002;          # 假设有双实例
    server api:5003;
}
```
考虑：会话保持（dify 用 JWT 不需要 IP hash）、健康检查、失败重试。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/nginx/conf.d/default.conf.template`
- `/Users/xu/code/github/dify/docker/nginx/proxy.conf.template`
- Nginx 反向代理官方文档：http://nginx.org/en/docs/http/ngx_http_proxy_module.html
- Nginx upstream：http://nginx.org/en/docs/http/ngx_http_upstream_module.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
