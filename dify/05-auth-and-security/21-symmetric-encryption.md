# 5.4.1 对称加密：AES / DES

> 理解对称加密原理，掌握 AES 的两种主要模式（ECB / CBC / GCM）。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解对称加密的核心概念（密钥、加密、解密）
- 掌握 AES-128/192/256 的差异与适用场景
- 理解 ECB / CBC / GCM 三种模式的区别
- 能用 Python 的 `cryptography` 库实现 AES-GCM 加密

## 📚 前置知识

- Python 基础语法
- 01-fundamentals/04-typing-annotations.md

## 1. 核心概念

### 1.1 对称加密 vs 非对称加密

| 维度 | 对称加密 | 非对称加密 |
|------|---------|-----------|
| 密钥 | 同一把 | 公钥 + 私钥 |
| 速度 | 快 | 慢 100-1000 倍 |
| 用途 | 加密大量数据 | 密钥交换、数字签名 |
| 例 | AES、DES、ChaCha20 | RSA、ECC |

### 1.2 DES 与 AES

**DES**（Data Encryption Standard）：56 位密钥，**已被破解**（暴力破解只需几小时），**禁止使用**。

**AES**（Advanced Encryption Standard）：128/192/256 位密钥，当前标准。

| 算法 | 密钥长度 | 状态 |
|------|---------|------|
| DES | 56 位 | 不安全 |
| 3DES | 168 位 | 弃用 |
| AES-128 | 128 位 | 推荐 |
| AES-256 | 256 位 | 高安全需求 |

### 1.3 AES 的工作模式

**ECB（Electronic Codebook）**：
- 每块独立加密
- **危险**：相同明文块产生相同密文块，泄露模式

**CBC（Cipher Block Chaining）**：
- 每块与前一块密文 XOR 后再加密
- 需要 IV（初始向量）
- 需要 PKCS7 padding

**GCM（Galois/Counter Mode）**：
- **推荐**：自带认证（防篡改）+ 并行加密
- 不需要 padding
- 需要 12 字节 nonce

## 2. 代码示例

### 2.1 AES-GCM 加密（推荐）

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def encrypt(plaintext: bytes, key: bytes) -> bytes:
    """AES-256-GCM 加密。"""
    # 1. 生成 12 字节 nonce（每次必须唯一）
    nonce = os.urandom(12)
    # 2. 加密（返回 ciphertext + 16字节 tag）
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, associated_data=None)
    # 3. 拼成 nonce + ciphertext 返回
    return nonce + ciphertext


def decrypt(blob: bytes, key: bytes) -> bytes:
    """AES-256-GCM 解密。"""
    nonce = blob[:12]
    ciphertext = blob[12:]
    return AESGCM(key).decrypt(nonce, ciphertext, associated_data=None)


# 使用
key = os.urandom(32)  # AES-256
encrypted = encrypt(b"secret message", key)
decrypted = decrypt(encrypted, key)
print(decrypted)  # b"secret message"
```

### 2.2 常见错误：nonce 重用

```python
# ❌ 错误：固定 nonce（危险！）
nonce = b"\x00" * 12
ciphertext = AESGCM(key).encrypt(nonce, plaintext, ...)
# 攻击者可通过多次加密结果反推密钥

# ✅ 正确：每次随机 nonce
nonce = os.urandom(12)
ciphertext = AESGCM(key).encrypt(nonce, plaintext, ...)
```

### 2.3 AES-CBC（兼容老系统时用）

```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
import os

def encrypt_cbc(plaintext: bytes, key: bytes) -> bytes:
    """AES-CBC + PKCS7 padding。"""
    # 1. PKCS7 padding
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()

    # 2. 随机 IV
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return iv + ciphertext
```

## 3. dify 仓库源码解读

### 3.1 密码哈希（基于对称加密思想）

**文件位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**（行 19-26）：

```python
def hash_password(password_str: str, salt_byte: bytes):
    dk = hashlib.pbkdf2_hmac("sha256", password_str.encode("utf-8"), salt_byte, 10000)
    return binascii.hexlify(dk)


def compare_password(password_str, password_hashed_base64, salt_base64):
    # compare password for login
    return hash_password(password_str, base64.b64decode(salt_base64)) == base64.b64decode(password_hashed_base64)
```

**解读**：
- 第 2 行：`pbkdf2_hmac` 是**密钥派生函数**，**不是加密**——但基于同样的密钥学原理
- 第 3 行：HMAC-SHA256 + salt + 10000 轮迭代 = 慢哈希，防暴力破解
- 第 7 行：`compare_password` 用 `==` 直接比哈希值（**应该是恒定时间比较**才更安全）
- **关联**：对称加密用密钥做 AES，密码哈希用密码做密钥派生

### 3.2 dify 的字段"加密"（Base64 混淆）

**文件位置**：`/Users/xu/code/github/dify/api/libs/encryption.py`
**核心代码**（行 1-40）：

```python
"""
Field Encoding/Decoding Utilities

Provides Base64 decoding for sensitive fields (password, verification code)
received from the frontend.

Note: This uses Base64 encoding for obfuscation, not cryptographic encryption.
Real security relies on HTTPS for transport layer encryption.
"""

import base64
import logging

logger = logging.getLogger(__name__)


class FieldEncryption:
    """Handle decoding of sensitive fields during transmission"""

    @classmethod
    def decrypt_field(cls, encoded_text: str) -> str | None:
        """
        Decode Base64 encoded field from frontend.

        Args:
            encoded_text: Base64 encoded text from frontend

        Returns:
            Decoded plaintext, or None if decoding fails
        """
        try:
            # Decode base64
            decoded_bytes = base64.b64decode(encoded_text)
            decoded_text = decoded_bytes.decode("utf-8")
            logger.debug("Field decoding successful")
            return decoded_text

        except Exception:
            # Decoding failed - return None to trigger error in caller
            return None
```

**解读**：
- 第 7-9 行：**明确说明**这不是加密，只是编码混淆
- 第 33 行：`base64.b64decode` 不是加密算法，**任何人都能解码**
- **关键启示**：dify 在传输层"加密"用 Base64 + HTTPS；**真正的对称加密**用于存储敏感数据（如第三方 API Key）
- **设计意图**：传输用 HTTPS，存储用对称加密（`encrypter.encrypt_token`）

## 4. 关键要点总结

- 对称加密 = 加密解密用同一把密钥
- AES 是当前标准，DES 已不安全
- **AES-GCM 是推荐模式**：自带认证 + 并行加密
- **nonce 必须每次随机**（12 字节），不能重用
- dify 的密码哈希用 **PBKDF2-HMAC-SHA256**，10000 轮迭代
- 传输层"加密"用 Base64 + HTTPS，存储层用对称加密

## 5. 练习题

### 练习 1：基础（必做）

用 `cryptography` 库实现 AES-256-GCM 加解密函数 `encrypt(plain, key)` 和 `decrypt(blob, key)`，要求 nonce 随机且拼接到密文前。

### 练习 2：进阶

阅读 `api/libs/password.py`，解释为什么 dify 用 `pbkdf2_hmac` 而不是 `bcrypt` 或 `argon2`？10000 轮迭代是否足够？

### 练习 3：挑战（选做）

实现一个 **带 AAD（Additional Authenticated Data）的加密函数**：除了加密 message，还认证一个 metadata（如 user_id），解密时验证 metadata 是否匹配。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/password.py`
- `/Users/xu/code/github/dify/api/libs/encryption.py`
- cryptography 文档：https://cryptography.io/en/latest/hazmat/primitives/aead/
- NIST AES 标准：https://csrc.nist.gov/projects/block-cipher-techniques/aes
- 密码哈希对比：https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13