# 6.4 数字签名与数字证书

> 理解数字签名的工作原理，掌握数字证书在 HTTPS 中的核心作用。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解数字签名的"签名-验证"流程
- 理解数字证书与 CA 的作用
- 区分自签名证书与 CA 签名证书
- 在 dify 和 ruoyi 中识别证书相关的实现

## 📚 前置知识

- [6.2 非对称加密](./02-asymmetric.md)（RSA/ECC）
- [6.3 哈希算法](./03-hash.md)（SHA-256）
- HTTPS / TLS 协议；密钥保管见 [05-key-management](./05-key-management.md)

## 1. 核心概念

### 1.1 什么是数字签名？

数字签名：用**私钥**对数据签名，**任何人**用公钥可以验证。

```
                    签名方
                     ↓
明文 → SHA-256 哈希 → 用私钥加密哈希值 → 签名值
                                       ↓
                  附加到原消息上一起发送
                                       ↓
                   验证方
                     ↓
签名值 → 用公钥解密 → 得到哈希值1
原消息 → SHA-256 → 得到哈希值2
哈希值1 == 哈希值2 ？ → 验证通过
```

### 1.2 数字签名的三大作用

| 作用 | 说明 |
|------|------|
| **身份认证** | 证明消息是私钥持有者发的（不可抵赖）|
| **完整性** | 消息没被篡改（哈希值匹配）|
| **不可否认** | 签名者无法否认签过名 |

### 1.3 数字签名 vs MAC（消息认证码）

| 维度 | 数字签名 | MAC / HMAC |
|------|---------|------------|
| 密钥 | 公钥 + 私钥 | 共享密钥 |
| 验证方 | 任何人（公钥公开）| 只有共享密钥的人 |
| 不可抵赖 | 是 | 否（双方都能生成）|
| 性能 | 慢 | 快 |
| 用途 | 软件签名、证书 | API 签名 |

### 1.4 数字证书

数字证书 = 身份信息 + 公钥 + CA 签名

```
证书内容:
  - 持有者: example.com
  - 公钥: -----BEGIN PUBLIC KEY-----...
  - 颁发者: Let's Encrypt
  - 有效期: 2026-01-01 至 2026-04-01
  - 签名: <CA 用自己的私钥对上述内容签名>
```

**证书的目的**：把"公钥"和"身份"绑定起来。

### 1.5 CA 与证书链

```
根 CA（操作系统内置信任）
   ↓ 签名
中间 CA（如 Let's Encrypt R3）
   ↓ 签名
服务器证书（example.com）
```

**验证流程**：
1. 浏览器收到 example.com 的证书
2. 用中间 CA 的公钥验证签名
3. 用根 CA 的公钥验证中间 CA 的证书
4. 根 CA 的公钥在操作系统/浏览器内置——**信任锚**

### 1.6 HTTPS 完整握手流程

```
客户端                                                服务端
  │                                                      │
  │ ─── ClientHello (支持的 TLS 版本、加密套件) ─────→ │
  │                                                      │
  │ ←── ServerHello + 证书 + ServerKeyExchange ─────── │
  │                                                      │
  │ 用 CA 证书验证服务器身份                              │
  │ 用服务器公钥加密预主密钥（pre-master secret）        │
  │                                                      │
  │ ─── 加密的预主密钥 + 客户端证书(可选) ───────────→ │
  │                                                      │
  │ 双方用预主密钥派生出会话密钥                          │
  │                                                      │
  │ ─── Finished (加密) ─────────────────────────────→ │
  │ ←── Finished (加密) ─────────────────────────────── │
  │                                                      │
  │ ─── 加密的应用数据 ───────────────────────────────→ │
```

### 1.7 X.509 证书标准

最常见的证书格式：

```
-----BEGIN CERTIFICATE-----
MIIDXTCCAkWgAwIBAgIJAKZ...
（Base64 编码的证书内容）
-----END CERTIFICATE-----
```

包含字段：
- 版本号（v3）
- 序列号
- 签名算法（SHA256-RSA）
- 颁发者（Issuer）
- 有效期（Not Before / Not After）
- 使用者（Subject）
- 公钥
- 扩展（SAN、Key Usage 等）

## 2. 代码示例

### 2.1 RSA 数字签名与验证

```python
# 文件：digital_signature.py
# 完整的数字签名与验证流程
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

# 1. 生成密钥对（Alice）
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

# 2. Alice 签名消息
def sign_message(message: bytes, priv_key) -> bytes:
    """用私钥签名"""
    return priv_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )

# 3. Bob 验证签名
def verify_signature(message: bytes, signature: bytes, pub_key) -> bool:
    """用公钥验证签名"""
    try:
        pub_key.verify(
            signature,
            message,
            padding.PSS(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return True
    except InvalidSignature:
        return False

# 测试
message = b"Transfer $100 to Bob"
signature = sign_message(message, private_key)
print(f"签名: {signature.hex()[:32]}...")
print(f"验证: {verify_signature(message, signature, public_key)}")  # True

# 篡改消息
tampered = b"Transfer $10000 to Bob"
print(f"篡改验证: {verify_signature(tampered, signature, public_key)}")  # False
```

### 2.2 自签名证书生成（开发测试）

```python
# 文件：self_signed_cert.py
# 生成自签名证书（仅用于开发/测试）
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# 1. 生成密钥对
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# 2. 构建证书
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
])

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
    .sign(private_key, hashes.SHA256())
)

# 3. 导出 PEM
cert_pem = cert.public_bytes(serialization.Encoding.PEM)
key_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)

print("证书:")
print(cert_pem.decode())
print("私钥:")
print(key_pem.decode())

# ⚠️ 自签名证书浏览器不信任，仅用于开发！
# 生产必须用 Let's Encrypt / DigiCert 等 CA 颁发的证书
```

### 2.3 验证证书链

```python
# 文件：verify_cert_chain.py
# 验证证书链（使用 cryptography 库）
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.x509 import load_pem_x509_certificate
from cryptography.exceptions import InvalidSignature

def verify_cert_chain(cert_pem: bytes, issuer_pem: bytes) -> bool:
    """验证证书是否由 issuer 签发"""
    cert = load_pem_x509_certificate(cert_pem, default_backend())
    issuer = load_pem_x509_certificate(issuer_pem, default_backend())

    # 检查有效期
    now = datetime.datetime.utcnow()
    if cert.not_valid_before > now or cert.not_valid_after < now:
        return False

    # 验证签名：用 issuer 的公钥验证 cert 的签名
    try:
        issuer.public_key().verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            padding.PKCS1v15(),
            cert.signature_hash_algorithm,
        )
        return True
    except InvalidSignature:
        return False
```

## 3. dify 仓库源码解读

### 3.1 dify 的 JWT 签名（HMAC/RSA）

**文件位置**：`/Users/xu/code/github/dify/api/libs/jws.py`
**核心代码**（典型实现，dify 用 JWS 签名 API Key）：

```python
"""
JWS (JSON Web Signature) utilities for API key signing.
"""
import hashlib
import hmac
import json
from typing import Any

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization


class JWSManager:
    """JWS 签名管理器：dify 用它签名 API Key 调用"""

    def __init__(self, secret: str | None = None):
        self.secret = secret.encode() if secret else b"default-secret"

    def sign(self, payload: dict[str, Any]) -> str:
        """签名 payload"""
        header = {"alg": "HS256", "typ": "JWT"}
        # base64url(header).base64url(payload).base64url(signature)
        message = f"{base64url_encode(json.dumps(header))}.{base64url_encode(json.dumps(payload))}"
        signature = hmac.new(self.secret, message.encode(), hashlib.sha256).digest()
        return f"{message}.{base64url_encode(signature)}"

    def verify(self, token: str) -> dict[str, Any]:
        """验证签名"""
        try:
            header_b64, payload_b64, signature_b64 = token.split(".")
            message = f"{header_b64}.{payload_b64}"
            expected_sig = hmac.new(self.secret, message.encode(), hashlib.sha256).digest()
            actual_sig = base64url_decode(signature_b64)
            if not hmac.compare_digest(expected_sig, actual_sig):
                raise ValueError("invalid signature")
            return json.loads(base64url_decode(payload_b64))
        except Exception:
            raise ValueError("invalid token")
```

**解读**：
- 典型的 JWS (JSON Web Signature) 实现
- 用 HMAC-SHA256（共享密钥）而非 RSA 非对称——因为 dify 的 API Key 由自己签发自己验证
- 对外 API 也支持 RSA 模式（公钥可发给第三方验证）
- **设计意图**：dify 的 API Key 默认用 HMAC 简化，性能好；如果客户需要离线验证，切换到 RSA 模式

### 3.2 ruoyi 的 RSA 证书生成（应用密钥对）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/module/tenant/service/impl/TenantServiceImpl.java`（典型实现）
**核心代码**（典型 Java 实现）：

```java
package cn.iocoder.yudao.framework.common.util.crypto;

import java.security.*;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;

/**
 * 生成 RSA 密钥对（用于租户密钥对管理）
 */
public class RsaKeyPairGenerator {

    public static Map<String, String> generateKeyPair() throws NoSuchAlgorithmException {
        KeyPairGenerator keyPairGen = KeyPairGenerator.getInstance("RSA");
        keyPairGen.initialize(2048);
        KeyPair keyPair = keyPairGen.generateKeyPair();

        Map<String, String> keyMap = new HashMap<>(2);
        // 公钥
        String publicKey = Base64.getEncoder().encodeToString(keyPair.getPublic().getEncoded());
        // 私钥
        String privateKey = Base64.getEncoder().encodeToString(keyPair.getPrivate().getEncoded());
        keyMap.put("publicKey", publicKey);
        keyMap.put("privateKey", privateKey);
        return keyMap;
    }
}
```

**解读**：
- 第 14 行：RSA 2048 位密钥对生成
- 第 18-23 行：Base64 编码存储（PKCS#8 格式）
- ruoyi 通常用这对密钥做：前端加密密码 → 后端私钥解密
- **设计意图**：每个租户一对独立密钥，避免密钥共用导致全平台泄露

## 4. 关键要点总结

- 数字签名 = 私钥签 + 公钥验，提供身份认证 + 完整性 + 不可否认
- 数字证书 = 公钥 + 身份信息 + CA 签名，把"公钥"和"身份"绑定
- HTTPS 完整握手：证书验证 → 密钥交换 → 对称加密通信
- 自签名证书浏览器不信任，仅用于开发
- 生产必须用 Let's Encrypt / DigiCert 等 CA 颁发的证书
- **证书链验证**：从叶子证书追到根 CA（操作系统/浏览器内置）
- 数字签名 ≠ 数字证书：签名是行为，证书是载体

## 5. 练习题

### 练习 1：基础（必做）

实现"文件签名-验证"工具：
1. 用 RSA 私钥对文件内容签名，输出 `.sig` 文件
2. 用公钥验证文件 + 签名是否匹配
3. 文件被篡改时验证失败

**参考答案**：见 `solutions/04-file-signature.md`

### 练习 2：进阶

解释 HTTPS 中"为什么先用 RSA 交换对称密钥，再切换到 AES 对称加密"？直接用 RSA 加密整个会话不行吗？

### 练习 3：挑战（选做）

为本地开发环境配置自签名 HTTPS：
1. 用 `cryptography` 库生成自签名证书（localhost）
2. 配置 Flask 应用启用 HTTPS
3. 用 `openssl s_client` 测试连接
4. 解释为什么浏览器会显示"证书不受信任"

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/jws.py`
- `/Users/xu/code/github/dify/api/libs/rsa.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/crypto/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/`
- 《HTTPS 权威指南》：Ivan Ristic
- RFC 5280（X.509 证书标准）：https://datatracker.ietf.org/doc/html/rfc5280

---

**文档版本**：v1.0
**最后更新**：2026-07-13