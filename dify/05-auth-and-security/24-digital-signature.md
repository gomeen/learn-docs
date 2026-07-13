# 5.4.4 数字签名与证书

> 理解数字签名的工作机制，掌握 X.509 证书与 CA 链。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解数字签名的核心原理（私钥签，公钥验）
- 掌握 X.509 证书的结构与 CA 链
- 理解证书在 HTTPS 中的角色
- 能用 Python 生成自签名证书用于开发

## 📚 前置知识

- 22-asymmetric-encryption.md
- 23-hashing.md
- HTTP 协议基础

## 1. 核心概念

### 1.1 数字签名 vs 数字证书

| 概念 | 作用 |
|------|------|
| 数字签名 | 证明"消息是谁发的、没被篡改" |
| 数字证书 | 证明"某个公钥属于某个实体" |

**类比**：
- 数字签名 = 手写签名 + 防篡改信封
- 数字证书 = 身份证（证明"你就是你"）

### 1.2 数字签名流程

```
签名方：
  1. 计算消息哈希：h = SHA256(message)
  2. 用私钥加密 h：sig = RSA_SIGN(private_key, h)
  3. 发送 (message, sig)

验证方：
  1. 用公钥解密 sig：h1 = RSA_VERIFY(public_key, sig)
  2. 计算消息哈希：h2 = SHA256(message)
  3. 比较：h1 == h2？
```

### 1.3 X.509 证书结构

```
┌────────────────────────────┐
│ 版本（v3）                  │
│ 序列号                      │
│ 签名算法（SHA256-RSA）      │
│ 颁发者（Issuer）             │
│ 有效期（Not Before / After） │
│ 主体（Subject: CN=...）      │
│ 公钥（Public Key）           │
│ 扩展（SAN、用途等）         │
│ 颁发者签名（CA 的私钥签的）  │
└────────────────────────────┘
```

### 1.4 CA 信任链

```
根 CA（操作系统信任）
  ↓ 签发
中间 CA
  ↓ 签发
服务器证书（如 api.dify.ai）
```

浏览器验证：从服务器证书往上追溯，最终到达根 CA → 信任。

## 2. 代码示例

### 2.1 数字签名

```python
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

# 签名
message = b"transfer $100 to Alice"
signature = private_key.sign(
    message,
    padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
    hashes.SHA256(),
)

# 验证
try:
    public_key.verify(
        signature, message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    print("签名有效")
except Exception:
    print("签名无效")
```

### 2.2 生成自签名证书（开发用）

```python
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime

# 1. 生成密钥对
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# 2. 构造证书主体
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
])

# 3. 构建证书
cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(private_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.datetime.utcnow())
    .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
    .add_extension(
        x509.SubjectAlternativeName([x509.DNSName("localhost")]),
        critical=False,
    )
    .sign(private_key, hashes.SHA256())  # 自签名：用自己的私钥签
)

# 4. 导出 PEM
with open("cert.pem", "wb") as f:
    f.write(cert.public_bytes(serialization.Encoding.PEM))

with open("key.pem", "wb") as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))
```

### 2.3 常见错误：忽略证书验证

```python
# ❌ 错误：禁用证书验证（防 MITM 失效）
import httpx
httpx.get("https://api.example.com", verify=False)

# ✅ 正确：默认验证
httpx.get("https://api.example.com")  # verify=True 是默认
```

## 3. dify 仓库源码解读

### 3.1 JWT 中的签名（HS256）

**文件位置**：`/Users/xu/code/github/dify/api/libs/jws.py`
**核心代码**（行 55-80）：

```python
def sign(keyset: KeySet, payload: dict, aud: str, ttl_seconds: int) -> str:
    """``iat`` + ``exp`` are injected here; callers must not set them."""
    if "aud" in payload or "iat" in payload or "exp" in payload:
        raise ValueError("reserved claim present in payload (aud/iat/exp)")
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds must be positive")

    now = datetime.now(UTC)
    claims = {
        **payload,
        "aud": aud,
        "iat": now,
        "exp": now + timedelta(seconds=ttl_seconds),
    }
    return jwt.encode(
        claims,
        keyset.lookup(keyset.active_kid),
        algorithm="HS256",
        headers={"kid": keyset.active_kid},
    )
```

**解读**：
- 第 17-21 行：构造 claims（含 iat/exp/aud）
- 第 22 行：用 `keyset.lookup(active_kid)` 拿密钥（当前是 HS256 共享密钥）
- 第 23 行：算法硬编码为 `HS256`（HMAC-SHA256，**对称签名**）
- 第 24 行：JWT header 加 `kid` 标识密钥版本
- **HMAC 签名 = 哈希 + 密钥**：本质是 SHA256 哈希 + 共享密钥作为前缀，避免碰撞攻击

### 3.2 证书在 HTTPS / TLS 中的角色

**文件位置**：`/Users/xu/code/github/dify/docker/nginx/conf.d/`（部署配置）
**说明**（典型 Nginx 配置）：

```nginx
server {
    listen 443 ssl;
    server_name api.dify.ai;

    ssl_certificate     /etc/nginx/certs/api.dify.ai.crt;
    ssl_certificate_key /etc/nginx/certs/api.dify.ai.key;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
}
```

**解读**：
- `ssl_certificate` 服务端证书（公开）
- `ssl_certificate_key` 服务端私钥（保密）
- `ssl_protocols TLSv1.2 TLSv1.3` 强制 TLS 1.2+，禁用 SSLv3/TLSv1.0
- **证书在 TLS 握手时**：服务端用私钥签名，浏览器用证书里的公钥验证 + 验证证书链
- **设计意图**：dify 的所有 API 默认走 HTTPS（`is_secure(request)` 检测）

## 4. 关键要点总结

- 数字签名 = 私钥签哈希，公钥验哈希
- 数字证书 = 绑定"公钥 ↔ 实体"的身份证
- HTTPS = TLS 握手 + 证书验证 + 加密通信
- **自签名证书**：仅用于开发，生产用 CA 颁发的证书
- dify 的 JWT 用 HS256（HMAC），未来可升级到 RS256（非对称签名）
- 永远不要禁用证书验证（`verify=False`）

## 5. 练习题

### 练习 1：基础（必做）

用 `cryptography` 库生成 RSA 密钥对，实现 `sign_message(msg, private_key)` 和 `verify_signature(msg, sig, public_key)`。

### 练习 2：进阶

解释为什么 JWT 用 **HMAC（HS256）** 在 dify 内部足够，但跨组织场景（如 SSO）必须用 **RSA（RS256）**？

### 练习 3：挑战（选做）

实现一个简易 CA：签发证书、验证证书链、吊销证书（CRL），用 `cryptography` 库完整实现。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/jws.py`
- `/Users/xu/code/github/dify/docker/nginx/`（HTTPS 配置）
- HTTPS 工作原理：https://howhttps.works/
- X.509 详解：https://en.wikipedia.org/wiki/X.509
- cryptography X.509：https://cryptography.io/en/latest/x509/

---

**文档版本**：v1.0
**最后更新**：2026-07-13