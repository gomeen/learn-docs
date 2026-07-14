# 3.1 Nginx 反向代理

> 理解 Nginx 反向代理的原理，掌握用 Nginx 代理 Spring Boot 应用的最佳实践。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解反向代理 vs 正向代理的区别
- 掌握 Nginx `proxy_pass`、`upstream` 关键指令
- 能为 Spring Boot 应用编写 Nginx 配置
- 解决 WebSocket、长连接等高级场景的代理问题

## 📚 前置知识

- HTTP 协议基础
- Linux 基础命令
- `05-java-docker.md`

## 1. 核心概念

### 1.1 什么是反向代理？

| 类型 | 代理对象 | 典型场景 |
|------|---------|---------|
| **正向代理** | 代理**客户端** | 翻墙、内网访问 |
| **反向代理** | 代理**服务端** | Nginx → 后端服务 |

**反向代理的作用**：
- **隐藏真实服务**：客户端只知道 Nginx 不知道后端
- **负载均衡**：把请求分发到多台后端
- **SSL 终止**：Nginx 处理 HTTPS，后端只处理 HTTP
- **静态资源缓存**：Nginx 直接返回静态文件

### 1.2 Nginx 核心指令

```nginx
location /api/ {
    proxy_pass http://backend;       # 代理到后端
    proxy_set_header Host $host;     # 透传 Host
    proxy_set_header X-Real-IP $remote_addr;  # 透传真实 IP
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_connect_timeout 60s;       # 连接超时
    proxy_read_timeout 60s;          # 读取超时
}
```

### 1.3 upstream 负载均衡池

```nginx
upstream backend {
    server 192.168.1.10:8080;
    server 192.168.1.11:8080;
    server 192.168.1.12:8080;
}
```

Nginx 默认**轮询**（round-robin）分发请求。

## 2. 代码示例

### 2.1 最小反向代理配置

```nginx
# 文件：/etc/nginx/conf.d/yudao.conf
server {
    listen 80;
    server_name api.example.com;

    # 前端静态文件
    location / {
        root /opt/yudao-ui-admin;
        try_files $uri $uri/ /index.html;  # SPA 路由
    }

    # 后端 API
    location /admin-api/ {
        proxy_pass http://127.0.0.1:48080/admin-api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**说明**：
- `try_files $uri $uri/ /index.html` — Vue/React SPA 路由 fallback
- `proxy_set_header` — 透传客户端真实信息到后端
- `X-Forwarded-For` — 多级代理时累加客户端 IP

### 2.2 WebSocket 代理

```nginx
location /infra/ws {
    proxy_pass http://127.0.0.1:48080/infra/ws;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;     # 必须
    proxy_set_header Connection "upgrade";     # 必须
    proxy_read_timeout 86400s;                 # 保持长连接
}
```

**说明**：
- 缺 `Upgrade`/`Connection` 头会导致 WebSocket 升级失败
- `proxy_read_timeout` 要设大（默认 60 秒会断）

## 3. ruoyi 仓库源码解读

**说明**：ruoyi 没有内置完整的 Nginx 配置文件（部署文档在 `doc.iocoder.cn`）。

**推荐的反向代理配置**（基于 ruoyi 的特点）：

```nginx
# 文件：/etc/nginx/conf.d/yudao.conf
upstream yudao-server {
    server 127.0.0.1:48080 weight=1;
    # 多实例时添加：
    # server 192.168.1.11:48080 weight=1;
}

server {
    listen 80;
    server_name api.example.com;

    # 上传文件大小（与 Spring Boot multipart 配置一致）
    client_max_body_size 32M;

    # WebSocket 代理（ruoyi 的 websocket 端点）
    location /infra/ws {
        proxy_pass http://yudao-server;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }

    # 后端 API
    location /admin-api/ {
        proxy_pass http://yudao-server/admin-api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 前端 admin UI
    location / {
        root /opt/yudao-ui-admin;
        try_files $uri $uri/ /index.html;
        index index.html;
    }
}
```

**关键点**：
- ruoyi 的 API 前缀是 `/admin-api/`
- ruoyi 的 WebSocket 端点是 `/infra/ws`（见 `application.yaml` 第 282-284 行）
- 上传文件限制 32M（与 `application.yaml` 的 `max-request-size` 一致）
- **使用 `upstream` 块**：方便后续加多实例实现负载均衡

## 4. 关键要点总结

- Nginx 反向代理 = 客户端 → Nginx → 后端
- `proxy_set_header` 透传 Host / X-Real-IP / X-Forwarded-For
- WebSocket 代理必须设置 `Upgrade` 和 `Connection: upgrade`
- SPA 前端用 `try_files $uri $uri/ /index.html` 实现路由 fallback
- `upstream` 块定义后端池，支持多实例负载均衡

## 5. 练习题

### 练习 1：基础（必做）

本地启动 yudao-server（端口 48080），编写最小 Nginx 配置（监听 80，反代到 48080），通过 `curl http://localhost/admin-api/system/user/get` 验证。

### 练习 2：进阶

为 Nginx 配置**静态资源代理**：把 `/opt/yudao-ui-admin`（构建产物）放在 Nginx 后端，访问 `http://localhost/` 返回 `index.html`，并把 `/admin-api/` 反代到后端。

### 练习 3：挑战（选做）

用 Nginx 部署 2 个 yudao-server 实例（48080、48081），配置 `upstream` + `weight=1`，用 `wrk` 或 `ab` 压测，观察两个实例的请求分布。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`（含 `nginx` 替代方案）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application.yaml`（websocket 路径）
- [Nginx 官方文档 - 反向代理](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [Nginx WebSocket 代理配置](https://nginx.org/en/docs/http/websocket.html)
- ruoyi 部署文档：https://doc.iocoder.cn/deployment/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
