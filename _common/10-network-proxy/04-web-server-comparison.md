# 10.4 Web 服务器对比：Nginx / Apache / Caddy

> 横向对比 4 款主流 Web 服务器的架构、配置、自动 HTTPS、性能、生态系统，并解释为什么 dify / ruoyi 都选 Nginx。

## 🎯 学习目标

完成本文档后，你将能够：
- 说出 Nginx、Apache、Caddy 的核心架构差异
- 理解 Caddy 的"自动 HTTPS"与 Let's Encrypt 集成
- 根据场景选择合适的 Web 服务器
- 解释为何 dify / ruoyi 在反向代理场景都使用 Nginx

## 📚 前置知识

- 10.1 - 10.3 节的 Nginx 概念
- HTTPS / TLS 基础知识
- 操作系统级进程 / 文件描述符概念

## 1. 核心概念

### 1.1 四款主流 Web 服务器纵览

| 服务器 | 架构 | 配置风格 | 自动 HTTPS | 使用规模 |
|--------|------|---------|-----------|---------|
| **Nginx** | 异步事件驱动 | 指令式 | 需手动 / Certbot | 33% 站点 |
| **Apache** | 多进程 / 多线程 | .htaccess 分布 | 需手动 | 24% 站点 |
| **Caddy** | 异步事件驱动 | 结构化 JSON | 内置 ACME | 新兴（<5%）|
| **Traefik** | 异步事件驱动 | YAML / TOML | 内置 ACME | 云原生场景 |

### 1.2 Nginx vs Apache：本质架构差异

**Nginx（异步事件驱动）**：
```
   ┌─ master ─┐
   │  ├─ worker (epoll 事件循环)
   │  ├─ worker
   │  └─ worker
   │
   └─ 单 worker 可处理 10000+ 并发
       内存占用：~几 MB / worker
```

**Apache（多进程 / 多线程）**：
```
   ┌─ prefork MPM ─┐         OR        ┌─ event MPM ─┐
   │  每个请求 1 进程                │  1 进程 N 线程
   │  进程数受限于内存                │  线程切换有 GIL-like 锁
   └─ 1000 并发 ≈ 1GB 内存          └─ 性能接近 Nginx
```

**核心差异**：Nginx 是"反向代理/网关"优先设计，Apache 是"传统 HTML 服务器"优先设计。

### 1.3 Caddy：自动 HTTPS 的现代化方案

Caddy 最大的特色是**默认开箱即用自动 HTTPS**，没有配置文件也能给网站套上 TLS：

```
# Caddyfile 示例：一行配置自动开 HTTPS
example.com {
    reverse_proxy localhost:5001
}
```

启动后 Caddy 自动检测域名 → 自动用 Let's Encrypt 申请证书 → 自动重载到内存 → 自动续签。

### 1.4 选择逻辑

| 场景 | 推荐 | 原因 |
|------|------|------|
| 反向代理、高并发 | Nginx | 成熟、性能好、生态完整 |
| 传统 PHP / .htaccess 项目 | Apache | 兼容性好（共享主机常用） |
| 个人博客、零运维 | Caddy | 自动 HTTPS、省心 |
| Kubernetes 服务网格 | Traefik / Istio | 自动发现服务、动态路由 |

## 2. 代码示例

### 2.1 Nginx 一份完整配置（对比示例）

```nginx
# 文件：nginx.conf
worker_processes auto;
events { worker_connections 4096; }

http {
    upstream backend {
        least_conn;
        server 10.0.0.1:5001;
        server 10.0.0.2:5001;
        keepalive 32;
    }

    server {
        listen 443 ssl http2;
        server_name example.com;
        ssl_certificate /etc/nginx/certs/fullchain.pem;
        ssl_certificate_key /etc/nginx/certs/privkey.pem;

        location / {
            proxy_pass http://backend;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
}
```

### 2.2 Caddy 一份完整配置（对比示例）

```
# 文件：Caddyfile
example.com {
    reverse_proxy 10.0.0.1:5001 10.0.0.2:5001 {
        lb_policy least_conn
        header_up X-Forwarded-For {http.request.header.X-Forwarded-For}
        header_up Host {http.request.host}
    }
}

# 还可以这样配置：直接给所有 *.example.com 套自动 HTTPS
*.example.com {
    reverse_proxy localhost:5001
}
```

### 2.3 Apache 一份完整配置（对比示例）

```apache
# 文件：000-default.conf
<VirtualHost *:443>
    ServerName example.com
    SSLEngine on
    SSLCertificateFile /etc/apache2/certs/fullchain.pem
    SSLCertificateKeyFile /etc/apache2/certs/privkey.pem

    <Proxy balancer://mycluster>
        BalancerMember 10.0.0.1:5001
        BalancerMember 10.0.0.2:5001
    </Proxy>

    ProxyPass /api balancer://mycluster
    ProxyPassReverse /api balancer://mycluster
</VirtualHost>
```

## 3. dify 与 ruoyi 源码解读

### 3.1 dify：用 Nginx + Certbot 组合实现自动 HTTPS

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（行 716-735）：

```yaml
  # The nginx reverse proxy.
  # used for reverse proxying the API service and Web service.
  nginx:
    image: nginx:latest
    restart: always
    volumes:
      - ./nginx/nginx.conf.template:/etc/nginx/nginx.conf.template
      - ./nginx/proxy.conf.template:/etc/nginx/proxy.conf.template
      - ./nginx/https.conf.template:/etc/nginx/https.conf.template
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./nginx/docker-entrypoint.sh:/docker-entrypoint-mount.sh
      - ./nginx/ssl:/etc/ssl # cert dir (legacy)
      - ./volumes/certbot/conf/live:/etc/letsencrypt/live # cert dir (with certbot container)
      - ./volumes/certbot/conf:/etc/letsencrypt
```

**解读**：
- **第 720 行**：`nginx:latest`——dify 直接用官方镜像，不定制构建（最小依赖）
- **第 722-725 行**：把所有 `.conf.template` 挂进 `/etc/nginx/`，启动时由 docker-entrypoint.sh 用 envsubst 渲染
- **第 728-729 行**：把 certbot 签发的证书挂到 nginx 容器里，就实现了"Nginx + Certbot 解耦"——certbot 一开始签证书，然后退出；Nginx 只是读取证书文件

**为什么选 Nginx 而非 Caddy？**
- **生态成熟**：Nginx 文档 / 教程 / Stack Overflow 答案数量众多
- **性能可靠**：Nginx 经过 20+ 年实战检验
- **可控性高**：dify 需要精细化控制 `proxy_set_header` / 缓存 / WebSocket 升级，Caddy 这部分语法相对不那么灵活

### 3.2 dify 的 docker-entrypoint.sh：用 envsubst 渲染配置

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/docker-entrypoint.sh`（行号未列出，我们看核心逻辑）

环境变量 → 模板渲染，是 dify Nginx 配置系统的核心机制：

```bash
#!/bin/bash
# 用 envsubst 把 .template 文件中的 ${VAR} 替换为环境变量值

# 渲染 nginx.conf 主配置
envsubst '${NGINX_WORKER_PROCESSES} ${NGINX_KEEPALIVE_TIMEOUT} ...' \
    < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# 渲染 https 块（如果启用）
if [ "$NGINX_HTTPS_ENABLED" = "true" ]; then
    envsubst '$NGINX_SSL_PORT $SSL_CERTIFICATE_PATH ...' \
        < /etc/nginx/https.conf.template > /tmp/https.conf

    # 注入到 default.conf
    envsubst '$ACME_CHALLENGE_LOCATION' < /etc/nginx/conf.d/default.conf.template > /tmp/default.conf
    sed -i "s|\${HTTPS_CONFIG}|$(cat /tmp/https.conf)|" /tmp/default.conf
    cp /tmp/default.conf /etc/nginx/conf.d/default.conf
fi

# 启动 nginx（前台）
nginx -g "daemon off;"
```

**这种设计的优点**：
- 模板文件本身**完全版本化**（在仓库里）
- 运行时**根据环境变量**调整
- 不需要重新构建镜像

### 3.3 ruoyi：传统 Apache 兼容（项目特征）

ruoyi 项目的根目录自带 `ruoyi-vue-pro/ruoyi-admin/src/main/resources/application.yml`，没有 Nginx 配置文件。这反映了它的**部署灵活性**：

```yaml
# 内部 Tomcat 也可以直接做反向代理（Spring Boot 内嵌 Tomcat）
server:
    port: 48080
    servlet:
        context-path: /
```

**这意味着**：
1. ruoyi 默认可以直接暴露 48080 到外网（不推荐）
2. 生产部署会**在容器外**部署 Nginx / SLB
3. 用户社区常用 Apache / Nginx 做反代

**ruoyi 用户的典型 Apache 反代配置**：
```apache
<VirtualHost *:80>
    ServerName yudao.example.com
    ProxyPass / http://localhost:48080/
    ProxyPassReverse / http://localhost:48080/
</VirtualHost>
```

**为什么不用 Caddy？** ruoyi 目标用户（企业后台管理）通常已有运维惯例，Nginx 是被默认接受的。

### 3.4 三种选择背后的工程考量

| 场景 | dify | ruoyi | 推荐 |
|------|------|-------|------|
| 自带容器化 Nginx | 是 | 否（外置） | 自托管选 dify 模式，云上选 ruoyi 模式 |
| HTTPS 自动签发 | 是（Certbot profile） | 否（手动 / 云厂商） | 个人项目 Caddy，企业项目 Nginx + 商业证书 |
| 反向代理灵活性 | 10 个 location 精细路由 | 默认 1 个通配 | 不限定，看路由复杂度 |

## 4. 关键要点总结

- **Nginx**：异步事件驱动，反向代理工业标准，配置灵活但需手动管证书
- **Apache**：传统 htaccess，模块丰富，但内存占用大
- **Caddy**：自动 HTTPS（核心卖点），Go 单二进制，但生态较新
- **Traefik**：云原生服务发现，适合 K8s
- **dify 选 Nginx**：生态成熟 + 性能 + 可控性 + 模板化配置
- **ruoyi 不带 Nginx**：保留"外层独立部署"的灵活性

## 5. 练习题

### 练习 1：基础（必做）

为本地开发环境配置一款 Web 服务器反代 `http://localhost:5001`：
- Nginx / Apache / Caddy 任意选一种
- 用 `curl -I localhost:80` 验证反代是否生效

**参考答案**：见 `solutions/01-reverse-proxy-server.md`

### 练习 2：进阶

对比以下两种 `proxy_set_header` 设置的差异：
```nginx
# 设置 A（Nginx 默认）
proxy_set_header Host $proxy_host;       # 传给后端的 Host 是 upstream 的"主机名"

# 设置 B（dify 用）
proxy_set_header Host $host;             # 传给后端的 Host 是客户端访问的域名
```
思考：
1. 在多域名部署时哪个更合理？
2. 如果后端是 Spring Boot 的 `server.servlet.context-path=/api`，差异会导致什么 bug？

### 练习 3：挑战（选做）

为 dify 设计一份用 **Caddy 替代 Nginx** 的方案：
1. 用 Caddyfile 替换 `conf.d/default.conf.template`
2. 用 Caddy 内置 ACME 替代 Certbot 容器
3. 分析：这种替换能减少多少镜像体积和启动步骤？

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/nginx/docker-entrypoint.sh`
- `/Users/xu/code/github/dify/docker/docker-compose.yaml`
- Nginx 文档：http://nginx.org/en/docs/
- Caddy 文档：https://caddyserver.com/docs/
- Apache 文档：https://httpd.apache.org/docs/
- Web 服务器市场份额：https://news.netcraft.com/archives/category/web-server-survey/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
