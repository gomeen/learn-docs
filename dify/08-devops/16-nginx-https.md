# 3.3 HTTPS 配置：TLS 证书与 Let's Encrypt

> 学会用 Nginx 配置 HTTPS，能用 Let's Encrypt 自动签发证书。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 HTTPS / TLS 的工作原理
- 用 Let's Encrypt 申请免费证书
- 配置 Nginx HTTPS server 块
- 理解 dify 的 certbot 自动续期方案

## 📚 前置知识

- `08-devops/14-nginx-basics.md`
- `08-devops/15-nginx-proxy.md`

## 1. 核心概念

### 1.1 HTTPS 是什么？

HTTPS = HTTP + TLS（Transport Layer Security）。通过 TLS 握手建立加密通道：

```
客户端                    Nginx（服务器）
  │ ─── ClientHello ───→  │   1. 客户端发起握手
  │ ←── ServerHello ────  │   2. 服务器返回证书
  │     + Certificate     │
  │ ─── Key Exchange ──→  │   3. 客户端验证证书
  │ ←── Finished ───────  │   4. 协商出对称密钥
  │ ─── Encrypted Data ─→ │   5. 开始加密通信
```

### 1.2 关键概念

- **证书（Certificate）**：证明服务器身份的电子文档（由 CA 签发）
- **CA（Certificate Authority）**：证书颁发机构（Let's Encrypt 是免费 CA）
- **私钥（Private Key）**：服务器保管，绝不公开
- **TLS 握手**：建立加密通道的过程
- **SNI（Server Name Indication）**：单 IP 托管多域名证书

### 1.3 Let's Encrypt 与 ACME 协议

- Let's Encrypt 提供**免费、自动**的 TLS 证书
- 通过 **ACME 协议**自动验证域名所有权
- 验证方式：
  - **HTTP-01**：在 `http://yourdomain/.well-known/acme-challenge/xxx` 放特定文件
  - **DNS-01**：在 DNS 添加特定 TXT 记录（支持通配符证书）
- 证书有效期 90 天，**必须自动续期**

### 1.4 dify 的 HTTPS 方案

dify 用 `certbot`（Let's Encrypt 官方客户端）做证书自动签发和续期：

1. 启动时 entrypoint 检查证书是否存在
2. 不存在则通过 HTTP-01 挑战签发
3. 证书存到 `/etc/letsencrypt/live/`
4. Nginx 重新加载配置

## 2. 代码示例

### 2.1 手动配置 HTTPS

```nginx
server {
    listen 443 ssl;
    server_name example.com;

    ssl_certificate     /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://backend;
    }
}

# HTTP 自动跳转 HTTPS
server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
}
```

### 2.2 用 certbot 申请证书

```bash
# 安装
apt install certbot

# 申请证书（standalone 模式需要先停掉 80 端口）
certbot certonly --standalone -d example.com

# 申请证书（webroot 模式，Nginx 继续运行）
certbot certonly --webroot -w /var/www/html -d example.com

# 查看证书
ls /etc/letsencrypt/live/example.com/
# cert.pem  chain.pem  fullchain.pem  privkey.pem
```

### 2.3 自动续期

```bash
# 测试续期（不实际执行）
certbot renew --dry-run

# 实际续期（证书 < 30 天到期才续）
certbot renew

# 用 crontab 自动续期
0 0 1 * * certbot renew --quiet && nginx -s reload
```

### 2.4 常见错误：证书链不完整

```bash
# 错误：客户端报"unable to get local issuer certificate"
# 原因：用了 cert.pem 而不是 fullchain.pem

# 错误：用
ssl_certificate /etc/letsencrypt/live/example.com/cert.pem;

# 正确：用（包含完整证书链）
ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
```

## 3. dify 仓库源码解读

### 3.1 dify 的 HTTPS 配置模板

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/https.conf.template`（参考）

**核心内容**：

```nginx
# HTTPS server
server {
    listen ${NGINX_SSL_PORT} ssl;
    server_name ${NGINX_SERVER_NAME};

    ssl_certificate     /etc/letsencrypt/live/${CERTBOT_DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${CERTBOT_DOMAIN}/privkey.pem;
    ssl_protocols       ${NGINX_SSL_PROTOCOLS};
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # 与 HTTP 相同的 location 块
    location /api {
        proxy_pass http://api:5001;
    }
    location / {
        proxy_pass http://web:3000;
    }
}
```

**解读**：
- 第 5-6 行：证书路径指向 certbot 签发的位置
- 第 7 行：`ssl_protocols TLSv1.2 TLSv1.3`（默认禁用不安全的 SSLv3/TLSv1.0/1.1）
- 第 8 行：加密套件优先级
- 通过 `NGINX_HTTPS_ENABLED=true` 启用 HTTPS server 块

### 3.2 dify 的 certbot 服务

**文件位置**：`/Users/xu/code/github/dify/docker/docker-compose.yaml`
**核心代码**（行 696-714）：

```yaml
  # Certbot service
  # use `docker-compose --profile certbot up` to start the certbot service.
  certbot:
    image: certbot/certbot
    profiles:
      - certbot
    volumes:
      - ./volumes/certbot/conf:/etc/letsencrypt
      - ./volumes/certbot/www:/var/www/html
      - ./volumes/certbot/logs:/var/log/letsencrypt
      - ./volumes/certbot/conf/live:/etc/letsencrypt/live
      - ./certbot/update-cert.template.txt:/update-cert.template.txt
      - ./certbot/docker-entrypoint.sh:/docker-entrypoint.sh
    environment:
      - CERTBOT_EMAIL=${CERTBOT_EMAIL:-}
      - CERTBOT_DOMAIN=${CERTBOT_DOMAIN:-}
      - CERTBOT_OPTIONS=${CERTBOT_OPTIONS:-}
    entrypoint: ["/docker-entrypoint.sh"]
    command: ["tail", "-f", "/dev/null"]
```

**解读**：
- 第 3-4 行：`profiles: [certbot]` 默认不启动，需要时 `docker compose --profile certbot up`
- 第 6-10 行：挂载 certbot 的标准目录结构（conf、www、logs、live）
- 第 12 行：`CERTBOT_EMAIL` 证书通知邮箱（必须填）
- 第 13 行：`CERTBOT_DOMAIN` 要签发证书的域名
- 第 15 行：自定义 entrypoint 脚本（执行证书签发/续期）
- 第 16 行：`tail -f /dev/null` 容器**保持运行**（方便后续手动触发续期）

### 3.3 dify 的 nginx 挂载证书

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
- 同时支持两种证书来源：
  - `./nginx/ssl`（legacy，手动放置证书）
  - `./volumes/certbot/conf`（certbot 自动签发）
- **`/etc/letsencrypt/live`** 是 certbot 的软链接目录，存放当前生效的证书
- entrypoint 脚本会执行 `envsubst` 渲染模板并 reload Nginx

## 4. 关键要点总结

- HTTPS = HTTP + TLS，用证书加密通信
- **Let's Encrypt** 提供免费 90 天证书，**必须自动续期**
- HTTP-01 验证需要把验证文件放在 `/.well-known/acme-challenge/`
- Nginx HTTPS 配置：`listen 443 ssl` + `ssl_certificate` + `ssl_certificate_key`
- 启用 `ssl_protocols TLSv1.2 TLSv1.3`，禁用老旧协议
- 用 `fullchain.pem` 而非 `cert.pem`（包含完整证书链）
- dify 的 certbot 用 profile 模式可选启动，自动续期

## 5. 练习题

### 练习 1：基础（必做）

用 certbot + Nginx 申请一个测试域名的证书（可以用 `example.com` 的子域名），验证浏览器访问 `https://` 看到锁图标。

### 练习 2：进阶

阅读 dify `docker/certbot/docker-entrypoint.sh`（如果存在），解释它如何实现自动续期：续期成功后如何触发 Nginx reload？

### 练习 3：挑战（选做）

在 dify 本地部署中启用 HTTPS：用 `mkcert` 生成本地证书（绕过 Let's Encrypt 验证），配置 Nginx 用 `ssl_certificate` 指向本地证书，访问 `https://localhost` 看到加密连接。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/nginx/https.conf.template`
- `/Users/xu/code/github/dify/docker/docker-compose.yaml`
- `/Users/xu/code/github/dify/docker/certbot/`（certbot 配置目录）
- Let's Encrypt 官方文档：https://letsencrypt.org/docs/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
