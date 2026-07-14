# 3.2 对称加密：AES / DES / 3DES / SM4

> 对称加密用**同一把密钥**加密和解密，速度快，适合大量数据加密。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解对称加密的核心（同一密钥）
- 掌握 AES、DES、3DES 的差异
- 知道 SM4（国密）算法
- 在 Python/Java 中使用 AES

## 📚 前置知识

- 08-hash.md
- 加密学基础

## 1. 核心概念

### 1.1 对称加密原理

```
明文 + 密钥 → 加密算法 → 密文
密文 + 密钥 → 解密算法 → 明文
```

**特点**：加密和解密用同一把密钥（共享密钥）。

### 1.2 主流算法对比

| 算法 | 密钥长度 | 块大小 | 安全性 | 性能 |
|------|---------|--------|--------|------|
| DES | 56 位 | 64 位 | ❌ 已破解 | 慢 |
| 3DES | 168 位 | 64 位 | ⚠️ 不推荐 | 慢 |
| AES | 128/192/256 位 | 128 位 | ✅ 标准 | 快 |
| SM4 | 128 位 | 128 位 | ✅ 国密标准 | 快 |

### 1.3 加密模式

AES 加密需要选择**模式**（Mode）：

| 模式 | 全称 | 特点 |
|------|------|------|
| ECB | Electronic Codebook | ❌ 不安全（相同明文→相同密文） |
| CBC | Cipher Block Chaining | 需要 IV，安全性好 |
| GCM | Galois/Counter Mode | ✅ **认证加密**（推荐） |
| CTR | Counter | 流式加密 |

### 1.4 关键概念

- **IV（Initialization Vector）**：每次加密的随机值，确保相同明文产生不同密文
- **Padding**：明文长度不是块大小的倍数时填充（PKCS#7）

## 2. 代码示例

### 2.1 Python AES-GCM

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

# 加密
key = AESGCM.generate_key(bit_length=256)  # 32 字节密钥
aesgcm = AESGCM(key)
iv = os.urandom(12)  # 96 位 nonce（每次加密必须不同）
plaintext = b"Secret message"
ciphertext = aesgcm.encrypt(iv, plaintext, associated_data=None)

print(f"Ciphertext: {ciphertext.hex()}")

# 解密
decrypted = aesgcm.decrypt(iv, ciphertext, associated_data=None)
print(f"Decrypted: {decrypted.decode()}")
```

### 2.2 AES-CBC（兼容模式）

```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
import os

# 加密
key = os.urandom(32)  # AES-256
iv = os.urandom(16)   # AES 块大小
plaintext = b"Secret message"

# Padding
padder = padding.PKCS7(128).padder()
padded = padder.update(plaintext) + padder.finalize()

# 加密
cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
encryptor = cipher.encryptor()
ciphertext = encryptor.update(padded) + encryptor.finalize()

# 解密
cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
decryptor = cipher.decryptor()
padded = decryptor.update(ciphertext) + decryptor.finalize()
unpadder = padding.PKCS7(128).unpadder()
plaintext = unpadder.update(padded) + unpadder.finalize()
print(f"Decrypted: {plaintext.decode()}")
```

### 2.3 ECB 模式（不安全，仅教学）

```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

key = b"0123456789abcdef"  # 16 字节（AES-128）
cipher = Cipher(algorithms.AES(key), modes.ECB())
encryptor = cipher.encryptor()

# ❌ 相同明文产生相同密文
block1 = encryptor.update(b"AAAAAAAA") + encryptor.finalize()
print(block1.hex())  # 重复明文 → 重复密文

# ✅ 用 CBC/GCM 避免这个问题
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的字段加密（敏感数据）

**位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**：

```python
import base64
from cryptography.fernet import Fernet

# 用对称加密存储 API Key 等敏感数据
def encrypt_credential(value: str, key: bytes) -> str:
    """加密 API Key——Fernet（AES-128-CBC + HMAC）"""
    f = Fernet(key)
    encrypted = f.encrypt(value.encode())
    return base64.b64encode(encrypted).decode()


def decrypt_credential(encrypted: str, key: bytes) -> str:
    """解密"""
    f = Fernet(key)
    decrypted = f.decrypt(base64.b64decode(encrypted))
    return decrypted.decode()
```

**解读**：
- Fernet 是 cryptography 库的高级接口
- 内部用 AES-128-CBC + HMAC-SHA256
- 自动处理 IV 和认证

### 3.2 ruoyi 的密码字段加密

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`
**核心代码**：

```java
// Spring Security 默认用 BCrypt（密码哈希，不是加密）
// 但敏感字段（如 API Key）可用 AES 加密
public class FieldEncryptor {
    private static final String KEY = "your-256-bit-secret-key";  // 16/24/32 字节
    private static final String ALGO = "AES";

    public static String encrypt(String plain) throws Exception {
        SecretKeySpec key = new SecretKeySpec(KEY.getBytes(), ALGO);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key);
        return Base64.encode(cipher.doFinal(plain.getBytes()));
    }
}
```

**解读**：
- Java `Cipher` API
- ruoyi 用 AES/GCM/NoPadding（认证加密）

## 4. 关键要点总结

- 对称加密 = 同一密钥加解密
- AES 是当前标准（128/192/256 位）
- 推荐 AES-GCM 模式（认证加密）
- ECB 模式不安全，CBC 需要 IV
- dify 用 Fernet，ruoyi 用 AES-GCM

## 5. 练习题

### 练习 1：基础
用 AES-GCM 加密一段文本，再解密，对比密文和明文。

### 练习 2：进阶
实现文件加密工具：支持 AES-CBC 加密大文件（分块处理）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/account_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/`
- cryptography 库：https://cryptography.io/

---

**文档版本**：v1.0
**最后更新**：2026-07-13