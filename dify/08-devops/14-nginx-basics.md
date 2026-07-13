# 3.1 Nginx 基础：配置文件与虚拟主机

> 理解 Nginx 配置结构，能读懂 dify 的反向代理配置。

## 🎯 学习目标

完成本文档后，你将能够：
- 读懂 Nginx 配置的层级结构（main / events / http / server / location）
- 配置虚拟主机（基于域名/端口的多个站点）
- 理解 dify 的 `nginx.conf.template` 和 `proxy.conf.template` 的设计

## 📚 前置知识

- `01-fundamentals/18-config-file-format.md`（配置文件格式）
- Linux 基础

## 1. 核心概念

### 1.1 Nginx 是什么？

Nginx 是**高性能 HTTP 服务器 / 反向代理服务器**。dify 用它做：
- 静态资源服务（前端 Next.js 构建产物）
- 反向代理（API 转发）
- HTTPS 终止
- 限流、缓存（高级特性）

### 1.2 配置层级

```
main                          # 全局配置（user、worker_processes）
├── events                    # 连接模型
└── http                      # HTTP 协议配置
    ├── upstream              # 负载均衡池
    ├── server                # 虚拟主机
    │   ├── listen            # 监听端口
    │   ├── server_name       # 域名
    │   └── location          # URL 匹配规则
    │       ├── proxy_pass    # 反向代理
    │       └── root          # 静态文件
    └── ...
```

### 1.3 关键指令

| 指令 | 作用 | 示例 |
|------|------|------|
| `user` | 运行用户 | `user nginx;` |
| `worker_processes` | 工作进程数 | `worker_processes auto;` |
| `worker_connections` | 每进程最大连接 | `worker_connections 1024;` |
| `listen` | 监听端口 | `listen 80;` |
| `server_name` | 域名 | `server_name example.com;` |
| `location` | URL 匹配 | `location /api { ... }` |
| `proxy_pass` | 反向代理 | `proxy_pass http://backend;` |
| `root` | 静态文件根目录 | `root /usr/share/nginx/html;` |
| `try_files` | 文件查找 | `try_files $uri $uri/ /index.html;` |
| `client_max_body_size` | 上传体积限制 | `client_max_body_size 100M;` |

### 1.4 配置文件组织

- `nginx.conf`：主配置
- `conf.d/*.conf`：虚拟主机配置（include 引入）
- `*.template`：用环境变量渲染的模板（dify 用 `envsubst` 替换）

## 2. 代码示例

### 2.1 最小虚拟主机

```nginx
# /etc/nginx/conf.d/my-site.conf
server {
    listen 80;
    server_name example.com;

    root /var/www/html;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

```bash
nginx -t           # 测试配置
nginx -s reload    # 重载配置
```

### 2.2 反向代理

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2.3 常见错误：location 优先级

```nginx
# /api/v1/users 匹配哪个？
location /api {                    # 前缀匹配（最长前缀优先）
    proxy_pass http://api;
}
location /api/v1 {                 # 比上面更具体，优先匹配
    proxy_pass http://api-v1;
}
location = /api/health {           # 精确匹配，最优先
    return 200 "OK";
}
```

**优先级**：`=` 精确 > `^~` 前缀 > `~` 正则 > 通用前缀

## 3. dify 仓库源码解读

### 3.1 dify 的 Nginx 主配置

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
- 第 1 行：注释明确说明这是**模板文件**，不要直接编辑
- 第 4 行：`worker_processes ${NGINX_WORKER_PROCESSES}` 用 envsubst 替换环境变量（默认 `auto`，=CPU 核心数）
- 第 10-12 行：`events` 块定义连接模型，1024 个连接/进程
- 第 15-33 行：`http` 块：mime types、log format、sendfile 优化
- 第 19-21 行：自定义 log 格式（main）记录客户端 IP、User-Agent、Referer
- 第 28 行：`keepalive_timeout 65` 保持连接 65 秒（HTTP/1.1 长连接）
- 第 31 行：`client_max_body_size 100M` 限制上传文件大小（dify 上传文档/图片）
- 第 33 行：`include /etc/nginx/conf.d/*.conf` 引入子配置（路由规则）

### 3.2 dify 的反代通用配置

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/proxy.conf.template`（参考结构）

**核心内容**：

```nginx
proxy_http_version 1.1;
proxy_set_header   Host              $http_host;
proxy_set_header   X-Real-IP         $remote_addr;
proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
proxy_set_header   X-Forwarded-Proto $scheme;
proxy_redirect     off;
proxy_buffering    off;
proxy_read_timeout ${NGINX_PROXY_READ_TIMEOUT};
proxy_send_timeout ${NGINX_PROXY_SEND_TIMEOUT};
```

**解读**：
- 第 1 行：使用 HTTP/1.1 协议（支持长连接）
- 第 2-5 行：传递客户端真实 IP 和协议（后端服务需要这些头做日志和鉴权）
- 第 7 行：`proxy_buffering off` 关闭缓冲，**流式响应**（dify 的 LLM 流式输出必需）
- 第 8-9 行：`proxy_read/send_timeout 3600s`（默认 1 小时），覆盖默认 60s
  - **关键**：LLM 生成可能持续数分钟，默认 60s 会断开连接
- 用 `include proxy.conf` 在每个 location 中复用

### 3.3 dify 的 https 配置模板

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/https.conf.template`（参考）

**核心内容**：

```nginx
# HTTPS server
server {
    listen ${NGINX_SSL_PORT} ssl;
    ssl_certificate     /etc/letsencrypt/live/${CERTBOT_DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${CERTBOT_DOMAIN}/privkey.pem;
    ssl_protocols       ${NGINX_SSL_PROTOCOLS};
    ssl_ciphers         HIGH:!aNULL:!MD5;

    location / {
        # 同 HTTP 配置
    }
}
```

**解读**：
- 第 3 行：`listen 443 ssl` 启用 HTTPS
- 第 4-5 行：证书路径指向 certbot 签发的位置
- 第 6 行：`ssl_protocols TLSv1.2 TLSv1.3`（默认禁用不安全的 SSLv3/TLSv1.0）
- 第 7 行：`ssl_ciphers` 加密套件优先级
- 通过 `NGINX_HTTPS_ENABLED=true` 启用 HTTPS server 块

## 4. 关键要点总结

- Nginx 配置分**全局 / events / http / server / location** 五层
- **虚拟主机**通过 `server_name` + `listen` 区分
- **反向代理**用 `proxy_pass` + `proxy_set_header`
- **关键配置**：`client_max_body_size`（上传）、`proxy_*_timeout`（长连接）、`proxy_buffering off`（流式）
- dify 的 `*.template` 用 `envsubst` 渲染环境变量
- dify 用 `proxy_read_timeout 3600s` 支持 LLM 长连接

## 5. 练习题

### 练习 1：基础（必做）

在本地启动一个 Nginx 容器，挂载一个 HTML 目录，访问 `http://localhost` 看到自己的页面。

```bash
docker run -d --name my-nginx -p 8080:80 -v ./html:/usr/share/nginx/html nginx:1.27
echo "<h1>Hello Nginx</h1>" > html/index.html
curl http://localhost:8080
```

### 练习 2：进阶

阅读 dify `docker/nginx/nginx.conf.template` 和 `docker/nginx/proxy.conf.template`，画出 dify Nginx 的配置层次和请求处理流程（用户 → 443 → proxy_pass → api）。

### 练习 3：挑战（选做）

为 dify 写一个自定义的 `dev.conf`，把 `/v1` 路径的请求转发到 `api:5001`，`/console` 路径转发到 `web:3000`，启用 `client_max_body_size 200M`。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/nginx/nginx.conf.template`
- `/Users/xu/code/github/dify/docker/nginx/proxy.conf.template`
- `/Users/xu/code/github/dify/docker/nginx/https.conf.template`
- Nginx 官方文档：https://nginx.org/en/docs/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
