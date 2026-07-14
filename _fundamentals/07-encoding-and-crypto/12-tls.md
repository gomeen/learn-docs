# 3.5 SSL/TLS 握手详解

> SSL/TLS 是 HTTPS 的基石，通过握手建立安全通道。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 TLS 握手的完整流程
- 区分 SSL 与 TLS 的关系
- 知道证书验证的作用
- 在 dify/ruoyi 中配置 HTTPS

## 📚 前置知识

- 10-asymmetric.md
- 11-digital-signature.md

## 1. 核心概念

### 1.1 SSL vs TLS

| 版本 | 状态 |
|------|------|
| SSL 1.0 | ❌ 未发布 |
| SSL 2.0 | ❌ 已弃用 |
| SSL 3.0 | ❌ 已弃用（POODLE 漏洞） |
| TLS 1.0 | ⚠️ 弃用中 |
| TLS 1.1 | ⚠️ 弃用中 |
| TLS 1.2 | ✅ 主流 |
| TLS 1.3 | ✅ 最新（更快更安全） |

### 1.2 TLS 1.2 握手流程（11 步）

```
客户端                                服务器
  │                                     │
  │ ──── ClientHello ─────────────────> │  1. 客户端发送支持的加密套件
  │                                     │
  │ <─── ServerHello ────────────────── │  2. 服务器选择加密套件
  │ <─── Certificate ────────────────── │  3. 服务器发送证书（含公钥）
  │ <─── ServerKeyExchange ──────────── │  4. （可选）密钥交换参数
  │ <─── ServerHelloDone ────────────── │  5. 服务器阶段完成
  │                                     │
  │ ──── ClientKeyExchange ───────────> │  6. 客户端发送预主密钥（用服务器公钥加密）
  │ ──── ChangeCipherSpec ────────────> │  7. 切换到加密通道
  │ ──── Finished ────────────────────> │  8. 握手验证
  │                                     │
  │ <─── ChangeCipherSpec ───────────── │  9. 服务器切换到加密通道
  │ <─── Finished ───────────────────── │ 10. 握手验证
  │                                     │
  │ ════ 加密的 HTTP 数据 ══════════════> │ 11. 加密通信开始
```

### 1.3 TLS 1.3 简化（1-RTT）

TLS 1.3 只需 **1 次往返**：
- 客户端发送 ClientHello + 猜测的密钥
- 服务器响应 + 真实密钥 + 证书

### 1.4 关键步骤详解

**证书验证**：
- 客户端验证服务器证书是否可信（CA 链）
- 验证域名是否匹配
- 验证是否过期

**密钥交换**：
- RSA：客户端生成预主密钥，用服务器公钥加密
- ECDHE：双方各自生成临时密钥对，通过 DH 协议共享

## 2. 代码示例

### 2.1 Python HTTPS 客户端

```python
import ssl
import urllib.request

# 默认 HTTPS（验证证书）
response = urllib.request.urlopen("https://api.example.com")

# 跳过证书验证（仅测试用）
ctx = ssl.create_unverified_context()
response = urllib.request.urlopen("https://self-signed.example.com", context=ctx)

# 指定 CA 证书
ctx = ssl.create_default_context(cafile="/path/to/ca-bundle.crt")
response = urllib.request.urlopen("https://api.example.com", context=ctx)
```

### 2.2 Python HTTPS 服务端（aiohttp）

```python
from aiohttp import web
import ssl

# 加载证书
ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain("cert.pem", "key.pem")

app = web.Application()

# HTTPS 服务
web.run_app(app, host="0.0.0.0", port=443, ssl_context=ssl_context)
```

### 2.3 用 OpenSSL 查看证书

```bash
# 查看证书详情
openssl x509 -in cert.pem -text -noout

# 测试 TLS 连接
openssl s_client -connect example.com:443

# 检查证书链
openssl s_client -connect example.com:443 -showcerts
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的 HTTPS 配置（Nginx 反向代理）

**位置**：`/Users/xu/code/github/dify/docker/`
**核心代码**（nginx.conf）：

```nginx
server {
    listen 443 ssl;
    server_name dify.example.com;

    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;  # 禁用旧版本

    location / {
        proxy_pass http://api:5001;  # 反向代理到 dify API
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**解读**：
- dify 用 Nginx 终结 TLS，反向代理到 Flask
- 强制 TLS 1.2+（安全最佳实践）

### 3.2 ruoyi 的 HTTPS（Spring Boot）

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/`
**核心代码**（application.yml）：

```yaml
server:
  port: 443
  ssl:
    enabled: true
    key-store: classpath:keystore.p12
    key-store-password: changeit
    key-store-type: PKCS12
    key-alias: tomcat
```

**解读**：
- Spring Boot 直接处理 HTTPS
- 加载 keystore.p12（含私钥 + 证书）

## 4. 关键要点总结

- TLS 1.2 主流，TLS 1.3 最快
- 握手过程：协商 → 验证身份 → 交换密钥
- 客户端验证服务器证书（CA 链）
- 实际数据传输用对称加密（AES）
- dify 用 Nginx 终结 TLS，ruoyi 用 Spring Boot

## 5. 练习题

### 练习 1：基础
用 OpenSSL 生成自签名证书，启动一个 HTTPS 服务。

### 练习 2：进阶
用 Wireshark 抓包分析 TLS 1.2 握手的完整过程。

## 6. 参考资料

- `/Users/xu/code/github/dify/docker/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/`
- TLS 1.3 RFC：https://tools.ietf.org/html/rfc8446

---

**文档版本**：v1.0
**最后更新**：2026-07-13