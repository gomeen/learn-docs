# 10.3 HTTPS 配置：TLS 证书与 Let's Encrypt

> 从零搭建生产级 HTTPS：TLS 握手、TLS 证书、Let's Encrypt 自动签发，以及如何在 dify 中启用。

## 🎯 学习目标

完成本文档后，你将能够：
- 解释 TLS 握手过程与对称加密 / 非对称加密分工
- 区分自签证书 / CA 签发证书 / Let's Encrypt 自动证书
- 配置 Nginx 启用 HTTPS / 强制 HTTP→HTTPS 重定向
- 看懂 dify 通过 Certbot 容器自动签发证书的实现

## 📚 前置知识

- 10.2 反向代理（Nginx 反代概念）
- SSL/TLS 协议基本原理（不需要深入握手细节）
- DNS 与域名解析（要签 HTTPS 必须有域名）

## 1. 核心概念

### 1.1 TLS 握手：客户端 / 服务器协商加密通道

```
1. ClientHello       → 客户端：支持的 TLS 版本 + 加密套件
2. ServerHello       → 服务器：选定版本 + 套件 + 服务器证书
3. 客户端：用 CA 公钥验证证书
4. 客户端：用服务器公钥加密 "pre-master secret" 发送
5. 双方：用 pre-master secret 派生 "会话密钥"
6. 切换到对称加密通信
```

**关键概念**：
- **证书**：CA 机构证明"这个域名是你的"的数字签名
- **非对称加密**：用于交换密钥（慢，安全）
- **对称加密**：用于数据传输（快）

### 1.2 证书类型与申请方式

| 类型 | 用途 | 申请 |
|------|------|------|
| **自签证书** | 开发 / 内网 | 自己签，无第三方信任 |
| **CA 签发证书** | 生产（传统） | 向 DigiCert / GlobalSign 等申请 |
| **Let's Encrypt** | 生产（免费） | 用 acme.sh / Certbot 自动 90 天续签 |

### 1.3 Let's Encrypt 自动续签原理

```
  ┌─────────┐    1. 域名验证 (HTTP-01)   ┌──────────────┐
  │ Certbot ├──────────────────────────►│ 你的 Nginx   │
  │         │    :80/.well-known/.../..  │ :80         │
  │         │                            └──────────────┘
  │         │    2. 验证通过 → 颁发证书      Let's Encrypt
  │         │    3. 写入 /etc/letsencrypt
  └─────────┘    4. 定期重新签发
```

### 1.4 Nginx HTTPS 配置三要素

```nginx
server {
    listen 443 ssl;

    # 1. 证书 + 私钥
    ssl_certificate     /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;

    # 2. 协议版本 + 加密套件（安全硬基线）
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 3. 会话缓存（性能优化）
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    location / { root /var/www/html; }
}

# 强制 HTTP → HTTPS 重定向
server {
    listen 80;
    return 301 https://$host$request_uri;
}
```

## 2. 代码示例

### 2.1 自签证书（开发环境）

```bash
# 1. 生成私钥
openssl genrsa -out server.key 2048

# 2. 生成自签证书（365 天）
openssl req -new -x509 -key server.key -out server.crt -days 365 \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=Dev/CN=localhost"

# 3. Nginx 引用
```

```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/ssl/server.crt;
    ssl_certificate_key /etc/ssl/server.key;
    location / { ... }
}
```

浏览器会显示"此连接不安全"，但加密正常工作。

### 2.2 Let's Encrypt 申请（使用 acme.sh）

```bash
# 安装 acme.sh
curl https://get.acme.sh | sh

# 申请并安装证书（HTTP-01 验证）
~/.acme.sh/acme.sh --issue -d example.com --nginx

# 复制到 Nginx 目录
~/.acme.sh/acme.sh --install-cert -d example.com \
    --key-file /etc/nginx/ssl/example.com.key \
    --fullchain-file /etc/nginx/ssl/example.com.crt

# 同时配置 cron 自动续签（默认 60 天后会重新签）
```

### 2.3 常见错误：协议版本过低

```nginx
# ❌ 错误：允许 SSLv3 等不安全协议
ssl_protocols SSLv3 TLSv1;     # 浏览器会拒绝访问

# ✅ 正确：只允许 TLS 1.2+
ssl_protocols TLSv1.2 TLSv1.3;

# 或者用 Mozilla 提供的 SSL 配置生成器：
# https://ssl-config.mozilla.org/
```

## 3. dify 源码解读

### 3.1 dify：HTTPS 配置块模板

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/https.conf.template`
**核心代码**（行 1-9）：

```nginx
# Please do not directly edit this file. Instead, modify the .env variables related to NGINX configuration.

listen ${NGINX_SSL_PORT} ssl;
ssl_certificate ${SSL_CERTIFICATE_PATH};
ssl_certificate_key ${SSL_CERTIFICATE_KEY_PATH};
ssl_protocols ${NGINX_SSL_PROTOCOLS};
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
```

**解读**：
- **第 1 行注释**：依然是变量化—— 通过 `.env` 配置 `NGINX_SSL_PORT` / `SSL_CERTIFICATE_PATH` 等
- **第 3 行**：`ssl_certificate` 路径由环境变量决定，可能指向：
  - 本地证书：`/etc/nginx/ssl/...crt`（手动放置）
  - Let's Encrypt 证书：`/etc/letsencrypt/live/<domain>/fullchain.pem`
- **第 6 行**：`ssl_prefer_server_ciphers on`——服务端选定的加密套件优先（增强安全性）
- **第 7-8 行**：共享 SSL 会话缓存，所有 worker 共享（提升 HTTPS 握手性能 10 倍）

### 3.2 dify：如何在 conf.d 中加载 HTTPS

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/conf.d/default.conf.template`
**核心代码**（行 1, 68-72）：

```nginx
# Please do not directly edit this file. Instead, modify the .env variables related to NGINX configuration.

server {
    listen ${NGINX_PORT};
```

```nginx
    
    # placeholder for acme challenge location
    ${ACME_CHALLENGE_LOCATION}

    # placeholder for https config defined in https.conf.template
    ${HTTPS_CONFIG}
}
```

**解读**：
- **第 69 行**：`${ACME_CHALLENGE_LOCATION}`——通过 `envsubst` 渲染时，如果是签证书模式，加上一段：
  ```nginx
  location ^~ /.well-known/acme-challenge/ {
      default_type "text/plain";
      root /var/www/html;
  }
  ```
  这是 Let's Encrypt HTTP-01 验证路径，必须能访问。
- **第 72 行**：`${HTTPS_CONFIG}`——把整个 `https.conf.template` 内容插入到 server 块底部，自动启用 HTTPS

**dify 启用 HTTPS 的完整链路**：
1. `.env` 里设 `NGINX_HTTPS_ENABLED=true`
2. `docker-entrypoint.sh` 用 `envsubst` 渲染 `https.conf.template` 并注入到 `default.conf.template`
3. Certbot profile 负责签发 / 续签证书
4. 证书续签后 reload nginx 让其加载新证书

### 3.3 dify Certbot 服务

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
- **第 700 行**：`profiles: ["certbot"]`——默认不启动，仅在用户希望自动签证书时启用
- **第 702 行**：挂载 `./volumes/certbot/conf` 为 `/etc/letsencrypt`——证书存放目录
- **第 703 行**：挂载 `./volumes/certbot/www` 为 `/var/www/html`——ACME HTTP-01 验证文件目录
- **第 707 行**：`./certbot/docker-entrypoint.sh`——脚本负责执行 certbot 命令申请证书
- **第 714 行**：`tail -f /dev/null`——保持容器运行（init-run 类型任务用 `tail -f` 维持前台常驻）

**启用流程**：
```bash
# 1. 在 .env 配置：
CERTBOT_EMAIL=admin@example.com
CERTBOT_DOMAIN=example.com

# 2. 启动 Certbot profile（一次性申请证书）
docker compose --profile certbot up certbot

# 3. 容器内脚本自动 certbot certonly --webroot -w /var/www/html -d example.com
#    证书保存到 ./volumes/certbot/conf/live/example.com/

# 4. 重启 nginx 让证书生效
docker compose restart nginx

# 5. 配置 cron 每 60 天自动续签（容器外 / host cron）
0 0 * * * cd /path/to/dify/docker && \
    docker compose run --rm certbot certbot renew --quiet && \
    docker compose exec nginx nginx -s reload
```

### 3.4 ruoyi：传统 HTTPS 部署

ruoyi 部署惯例不在容器内启用 HTTPS，而是在**外层 SLB / Nginx 节点**统一处理：

```
   客户端 ──→ [云厂商 SLB / 外层 Nginx]
                  │ 终结 HTTPS（cloud cert / 手动 cert）
                  ↓ HTTP（内网）
              yudao-server:48080
```

**对比**：

| 对比点 | dify | ruoyi |
|--------|------|-------|
| 证书管理 | 容器内 Certbot | 外层 Nginx / 云厂商托管 |
| 自动续签 | 用 cron + certbot renew | 云厂商自动管理 |
| 配置复杂度 | 高（环境变量化）| 低（一次性 Nginx 配置） |
| 适用场景 | 自托管 / 离线环境 | 云上部署 / 传统 IDC |

## 4. 关键要点总结

- **TLS 握手**：非对称加密交换密钥，对称加密传输数据
- **证书类型**：自签（开发）/ CA（生产传统）/ Let's Encrypt（生产免费）
- **Nginx HTTPS 三要素**：协议版本 + 加密套件 + 证书路径
- **强制 HTTPS**：HTTP server 块用 `return 301 https://$host$request_uri`
- **ACME HTTP-01 挑战**：必须把 `/.well-known/acme-challenge/` 反代到 certbot www 目录
- **ssl_prefer_server_ciphers**：服务端选套件优先（安全）

## 5. 练习题

### 练习 1：基础（必做）

用 `openssl req` 生成自签证书，并写一份 Nginx 配置启用 HTTPS（监听 8443 端口）。

**参考答案**：见 `solutions/01-self-signed-https.md`

### 练习 2：进阶

阅读 `dify/docker/nginx/https.conf.template`，回答：
1. 为什么 `ssl_certificate_key` 必须限制权限（`chmod 600`）？如果泄露会怎样？
2. `ssl_session_cache shared:SSL:10m` 是为哪个场景优化？什么情况下**应当关闭**？

### 练习 3：挑战（选做）

设计一个"零停机"证书更新方案：
1. Certbot 用 staging 环境先验证
2. 验证通过后切换到生产环境
3. `nginx -s reload` 热加载证书
4. 自动回滚机制：如果 reload 后健康检查失败，回滚到上一次证书

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/nginx/https.conf.template`
- `/Users/xu/code/github/dify/docker/docker-compose.yaml`（Certbot 服务）
- Let's Encrypt 官方：https://letsencrypt.org/getting-started/
- Mozilla SSL 配置生成器：https://ssl-config.mozilla.org/
- acme.sh：https://github.com/acmesh-official/acme.sh

---

**文档版本**：v1.0
**最后更新**：2026-07-13
