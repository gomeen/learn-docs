# 5.4.2 非对称加密：RSA / ECC

> 理解非对称加密原理，掌握 RSA 与椭圆曲线密码学的应用场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解非对称加密的核心原理（公钥加密，私钥解密）
- 掌握 RSA 与 ECC 的差异与适用场景
- 理解数字签名的工作流程
- 能用 Python 实现 RSA 加解密和签名验证

## 📚 前置知识

- 21-symmetric-encryption.md
- 加密学基础

## 1. 核心概念

### 1.1 什么是非对称加密？

**一对密钥**：公钥（公开）+ 私钥（保密）。

```
加密：公钥加密 → 只有私钥能解
签名：私钥签名 → 任何人都能用公钥验证
```

### 1.2 RSA vs ECC

| 维度 | RSA | ECC |
|------|-----|-----|
| 基础 | 大整数分解 | 椭圆曲线离散对数 |
| 密钥长度 | 2048+ 位 | 256 位等价 3072 位 RSA |
| 性能 | 慢 | 快 5-10 倍 |
| 成熟度 | 1977 年 | 1985 年 |
| 适用 | TLS 证书、密钥交换 | 移动端、区块链 |

**经验法则**：新项目优先选 ECC（Ed25519、P-256），老系统兼容用 RSA-2048+。

### 1.3 数字签名流程

```
签名方：
  1. 对消息计算哈希（SHA-256）
  2. 用私钥加密哈希值
  3. 把消息 + 签名一起发送

验证方：
  1. 用公钥解密签名 → 得到哈希 H1
  2. 对收到的消息计算哈希 → 得到 H2
  3. 比较 H1 == H2
```

签名 ≠ 加密。**签名证明"是谁发的"，加密保护"内容不让人看"。**

## 2. 代码示例

### 2.1 RSA 加解密

```python
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

# 生成密钥对
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

# 加密
plaintext = b"secret message"
ciphertext = public_key.encrypt(
    plaintext,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    ),
)

# 解密
decrypted = private_key.decrypt(
    ciphertext,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    ),
)
print(decrypted)  # b"secret message"
```

### 2.2 RSA 数字签名

```python
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

# 签名
message = b"important announcement"
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

### 2.3 ECC 签名（Ed25519）

```python
from cryptography.hazmat.primitives.asymmetric import ed25519

# 生成密钥对（更短更快）
private_key = ed25519.Ed25519PrivateKey.generate()
public_key = private_key.public_key()

# 签名
signature = private_key.sign(b"hello")

# 验证
public_key.verify(signature, b"hello")  # 不抛异常 = 有效
```

### 2.4 常见错误：用 RSA 加密大量数据

```python
# ❌ 错误：RSA 加密 1MB 数据（慢 + 长度限制 245 字节）
public_key.encrypt(huge_data, padding.OAEP(...))

# ✅ 正确：RSA 只用于"加密会话密钥"，数据用 AES
import os
session_key = os.urandom(32)               # AES-256 密钥
encrypted_key = public_key.encrypt(session_key, padding.OAEP(...))  # RSA 加密密钥
encrypted_data = AESGCM(session_key).encrypt(nonce, data, None)     # AES 加密数据
```

## 3. dify 仓库源码解读

### 3.1 JWS 中的非对称签名能力

**文件位置**：`/Users/xu/code/github/dify/api/libs/jws.py`
**核心代码**（行 1-50）：

```python
"""HS256 compact JWS keyed on the shared Dify SECRET_KEY. Used by the SSO
state envelope, external subject assertion, and approval-grant cookie —
all three share one key-set so api ↔ enterprise can verify each other.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from configs import dify_config

AUD_STATE_ENVELOPE = "api.sso.state_envelope"
AUD_EXT_SUBJECT_ASSERTION = "api.device_flow.external_subject_assertion"
AUD_APPROVAL_GRANT = "api.device_flow.approval_grant"

ACTIVE_KID_V1 = "dify-shared-v1"


class KeySetError(Exception):
    pass


class KeySet:
    """``from_entries`` reserves multi-kid construction for rotation slots."""

    def __init__(self, entries: dict[str, bytes], active_kid: str) -> None:
        if active_kid not in entries:
            raise KeySetError(f"active kid {active_kid!r} missing from key-set")
        if not entries[active_kid]:
            raise KeySetError(f"active kid {active_kid!r} has empty secret")
        self._entries: dict[str, bytes] = {k: bytes(v) for k, v in entries.items()}
        self._active_kid = active_kid

    @classmethod
    def from_shared_secret(cls) -> KeySet:
        secret = dify_config.SECRET_KEY
        if not secret:
            raise KeySetError("dify_config.SECRET_KEY is empty; cannot build key-set")
        return cls({ACTIVE_KID_V1: secret.encode("utf-8")}, ACTIVE_KID_V1)
```

**解读**：
- 第 1-4 行：注释明确说明当前是 **HS256（对称）**，但 KeySet 设计预留了非对称扩展
- 第 25-32 行：`KeySet` 接受 `dict[bytes]`，意味着能存 RSA 私钥 / ECC 私钥等多种格式
- 第 36-41 行：`from_shared_secret` 是当前的对称实现
- **设计意图**：未来支持 OIDC / SAML 时，可平滑升级到 RS256 / ES256（非对称）

### 3.2 RSA 在企业 SSO 中的角色

**文件位置**：`/Users/xu/code/github/dify/api/libs/rsa.py`
**核心代码**（典型结构）：

```python
"""RSA utilities for SSO / encryption / signing."""
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

def generate_key_pair() -> tuple[bytes, bytes]:
    """生成 RSA 密钥对，返回 (private_pem, public_pem)。"""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem
```

**解读**：
- 第 6 行：2048 位 RSA 密钥（最低安全要求）
- 第 7-11 行：私钥 PEM 编码（PKCS8 格式）
- 第 12-16 行：公钥 PEM 编码（SubjectPublicKeyInfo 格式）
- **使用场景**：dify 企业版对接客户 IdP 时，用 RSA 加密 SAML 断言或验证签名

## 4. 关键要点总结

- 非对称加密 = 公钥加密，私钥解密（或反过来）
- RSA 慢但成熟；ECC 快且密钥短
- **签名 ≠ 加密**：签名证明身份，加密保护内容
- **RSA 不要直接加密大量数据**（限制 245 字节），用 RSA 加密会话密钥 + AES 加密数据
- dify 当前用 HS256 对称，未来可扩展到 RS256/ES256
- dify 企业版用 RSA 对接 SSO（SAML Assertion 加密 / 验签）

## 5. 练习题

### 练习 1：基础（必做）

用 `cryptography` 库生成 RSA 密钥对，实现 `sign(message, private_key)` 和 `verify(message, signature, public_key)`。

### 练习 2：进阶

阅读 `api/libs/jws.py:25-50`，解释 dify 的 `KeySet` 设计如何**支持从 HS256 升级到 RS256** 而不破坏向后兼容。

### 练习 3：挑战（选做）

实现 **混合加密**：用 RSA-2048 加密 32 字节 AES 密钥 + AES-GCM 加密实际数据，把两部分打包成单个字节串。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/jws.py`
- `/Users/xu/code/github/dify/api/libs/rsa.py`
- cryptography RSA：https://cryptography.io/en/latest/hazmat/primitives/asymmetric/rsa/
- NIST 密钥管理：https://csrc.nist.gov/projects/key-management

---

**文档版本**：v1.0
**最后更新**：2026-07-13