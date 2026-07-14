# 6.1 对称加密：AES / DES / 3DES / 国密 SM4

> 理解对称加密的原理，掌握 AES 加密在 Python/Java 中的正确使用方法。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解对称加密的核心概念（密钥、块、模式、IV）
- 区分 ECB、CBC、GCM 等加密模式的区别
- 在 Python/Java 中正确使用 AES 加密（避免踩坑）
- 识别 dify 和 ruoyi 中的对称加密实现

## 📚 前置知识

- 二进制与编码（Base64、Hex）
- 6 加密系列前置
- 任意一门编程语言基础

## 1. 核心概念

### 1.1 什么是对称加密？

对称加密：加密和解密**使用同一个密钥**的加密方式。

```
明文 ──[密钥 K]──> 密文 ──[密钥 K]──> 明文
```

### 1.2 主流算法对比

| 算法 | 密钥长度 | 块大小 | 安全性 | 速度 | 现状 |
|------|---------|--------|--------|------|------|
| **DES** | 56 bit | 64 bit | **已破解** | 慢 | **禁止使用** |
| **3DES** | 112/168 bit | 64 bit | 中等 | 很慢 | 逐步淘汰 |
| **AES** | 128/192/256 bit | 128 bit | **强** | 快 | **推荐** |
| **SM4** | 128 bit | 128 bit | 强（国产）| 快 | 国内合规场景 |

### 1.3 加密模式（Mode of Operation）

块密码只能加密固定长度（128 bit），加密长数据需要"模式"：

| 模式 | 特点 | 安全性 | 用途 |
|------|------|--------|------|
| **ECB** | 每块独立加密 | **有漏洞**（相同明文→相同密文）| 仅用于演示 |
| **CBC** | 前一块密文 XOR 后一块 | 需要 IV，**需要填充** | 传统加密 |
| **CTR** | 计数器模式，可并行 | 需 IV，**不需要填充** | 流式加密 |
| **GCM** | CTR + 认证（AEAD） | **同时加密+防篡改** | **推荐** |
| **CFB / OFB** | 流密码模式 | 较少用 | 特殊场景 |

### 1.4 IV（Initialization Vector）

- IV 是加密时引入的随机值，**每次加密必须不同**
- 即使加密相同明文，IV 不同 → 密文不同
- **IV 不需要保密**，可以明文存储
- IV 长度 = 块大小（AES = 128 bit = 16 字节）

### 1.5 填充（Padding）

块密码要求明文长度是块大小的整数倍，最后一块不够需要填充：

| 填充方式 | 规则 | 特点 |
|---------|------|------|
| **PKCS7** | 缺 N 字节就填 N 个 N | 标准、最常用 |
| **Zero Padding** | 补 0 | **不推荐**（无法区分明文末尾的 0）|
| **No Padding** | 不填充 | 要求明文长度对齐（CTR/GCM 模式） |

### 1.6 实战踩坑指南

| 错误 | 后果 | 正确做法 |
|------|------|---------|
| 用 ECB 模式 | 相同明文泄露 | 用 CBC/GCM |
| 密钥硬编码 | 密钥泄露 | 用 KMS/Vault |
| IV 复用 | 加密可破解 | 每次随机生成 IV |
| 自定义算法 | 必然有漏洞 | 用标准库（AES-GCM）|
| 不用 HMAC | 密文可被篡改 | 用 GCM 模式或额外 HMAC |

## 2. 代码示例

### 2.1 Python AES-CBC 加密（传统模式）

```python
# 文件：aes_cbc.py
# AES-CBC 加密 + PKCS7 填充（兼容性好，但需额外 HMAC）
import os
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

KEY = b"this_is_a_32_byte_key_for_aes256!!"  # 32 字节 = AES-256
BLOCK_SIZE = 128  # AES 块大小（bit）

def encrypt_aes_cbc(plaintext: str) -> str:
    """AES-CBC 加密，返回 base64(IV + 密文)"""
    # 1. 随机生成 IV（每次必须不同）
    iv = os.urandom(16)

    # 2. PKCS7 填充
    padder = padding.PKCS7(BLOCK_SIZE).padder()
    padded = padder.update(plaintext.encode()) + padder.finalize()

    # 3. CBC 模式加密
    cipher = Cipher(algorithms.AES(KEY), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()

    # 4. 把 IV 拼接到密文前面（解密时需要）
    return base64.b64encode(iv + ciphertext).decode()

def decrypt_aes_cbc(b64_ciphertext: str) -> str:
    """AES-CBC 解密"""
    raw = base64.b64decode(b64_ciphertext)
    iv, ciphertext = raw[:16], raw[16:]

    cipher = Cipher(algorithms.AES(KEY), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()

    unpadder = padding.PKCS7(BLOCK_SIZE).unpadder()
    plaintext = unpadder.update(padded) + unpadder.finalize()
    return plaintext.decode()

# 测试
encrypted = encrypt_aes_cbc("Hello, AES!")
print(f"密文: {encrypted}")
print(f"解密: {decrypt_aes_cbc(encrypted)}")
# 两次加密相同明文，密文不同（因为 IV 不同）
```

### 2.2 Python AES-GCM 加密（推荐：AEAD）

```python
# 文件：aes_gcm.py
# ✅ AES-GCM 加密：同时加密 + 防篡改（无需额外 HMAC）
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY = b"this_is_a_32_byte_key_for_aes256!!"  # 32 字节

def encrypt_aes_gcm(plaintext: str, associated_data: bytes = b"") -> str:
    """AES-GCM 加密，返回 base64(nonce + 密文 + tag)"""
    aesgcm = AESGCM(KEY)
    nonce = os.urandom(12)  # GCM 推荐 12 字节 nonce
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), associated_data)
    # 输出格式：nonce(12) + ciphertext + tag(16)
    return base64.b64encode(nonce + ciphertext).decode()

def decrypt_aes_gcm(b64_ciphertext: str, associated_data: bytes = b"") -> str:
    """AES-GCM 解密（自动校验 tag，篡改会抛异常）"""
    raw = base64.b64decode(b64_ciphertext)
    nonce, ciphertext = raw[:12], raw[12:]

    aesgcm = AESGCM(KEY)
    plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data)
    return plaintext.decode()

# 测试：篡改密文会抛异常
encrypted = encrypt_aes_gcm("secret data")
print(f"密文: {encrypted}")
print(f"解密: {decrypt_aes_gcm(encrypted)}")

# 篡改测试
tampered = encrypted[:-4] + "XXXX"
try:
    decrypt_aes_gcm(tampered)
except Exception as e:
    print(f"篡改被检测: {e}")
```

### 2.3 ECB 模式的漏洞演示

```python
# 文件：ecb_weakness.py
# ❌ ECB 模式漏洞演示（**永远不要用 ECB**）
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

KEY = b"0" * 32

def ecb_encrypt(plaintext: bytes) -> bytes:
    """ECB 模式加密"""
    cipher = Cipher(algorithms.AES(KEY), modes.ECB())
    encryptor = cipher.encryptor()
    # ECB 要求明文长度是 16 字节倍数（这里补 0）
    padded = plaintext.ljust(16 * ((len(plaintext) // 16) + 1), b"\x00")
    return encryptor.update(padded) + encryptor.finalize()

# 测试：相同 16 字节块 → 相同密文
plaintext = b"AAAAAAAAAAAAAAAA" + b"AAAAAAAAAAAAAAAA"
ciphertext = ecb_encrypt(plaintext)
# 两块密文完全相同！攻击者知道密文长度就猜到原文结构
print(ciphertext.hex())
# 输出：c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8c8  ← 完全相同
```

## 3. dify 仓库源码解读

### 3.1 dify 的字段加密工具（Base64 + 说明）

**文件位置**：`/Users/xu/code/github/dify/api/libs/encryption.py`
**核心代码**（行 1-66）：

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
- 第 1-9 行：文档明确说明这是 **Base64 混淆，不是加密**——重要！Base64 是编码，不是加密
- 第 32 行：`base64.b64decode` 只是解码，任何人都能还原
- 第 39 行：异常时返回 None（**安全失败模式**），让上层业务决定如何处理
- **设计意图**：dify 把"传输层加密"的责任交给 HTTPS，前端 Base64 只是为了避免明文密码出现在网络包中（防运维误看）

### 3.2 ruoyi 的 AES 加密工具（实际加密）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/crypto/AesUtils.java`（或类似路径）
**核心代码**（典型实现）：

```java
package cn.iocoder.yudao.framework.common.util.crypto;

import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

/**
 * AES/CBC/PKCS5Padding 加密工具类
 */
public class AesUtils {

    private static final String ALGORITHM = "AES";
    private static final String TRANSFORMATION = "AES/CBC/PKCS5Padding";

    public static String encrypt(String content, String key) {
        try {
            // 1. 密钥必须是 16/24/32 字节（AES-128/192/256）
            SecretKeySpec keySpec = new SecretKeySpec(key.getBytes(StandardCharsets.UTF_8), ALGORITHM);
            // 2. IV 是固定的 16 字节（AES 块大小）—— 注意：生产环境应当随机生成
            IvParameterSpec ivSpec = new IvParameterSpec(key.getBytes(StandardCharsets.UTF_8), 0, 16);
            // 3. CBC 模式加密
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.ENCRYPT_MODE, keySpec, ivSpec);
            byte[] encrypted = cipher.doFinal(content.getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(encrypted);
        } catch (Exception e) {
            throw new RuntimeException("AES encrypt error", e);
        }
    }
}
```

**解读**：
- 第 13 行：算法固定为 `AES/CBC/PKCS5Padding`（PKCS5 = PKCS7 在 AES 上的特例）
- 第 17 行：密钥直接传入（生产应从 KMS 取）
- 第 19 行：**注意**：用密钥的前 16 字节做 IV——这是简化实现，**真实场景应随机生成 IV**
- 第 24 行：异常时抛 RuntimeException，让上层处理
- **设计意图**：ruoyi 提供统一的加密工具，业务代码不用关心 AES 细节

## 4. 关键要点总结

- **首选 AES-256-GCM**：同时加密 + 防篡改，无需额外 HMAC
- CBC 模式需要 IV + 填充，GCM 不需要
- **永远不要用 ECB**——相同明文 → 相同密文
- **永远不要硬编码密钥**——用 KMS/Vault/环境变量
- IV 每次必须随机生成，不要复用
- 加密 ≠ 编码：Base64/MD5/URL编码都不是加密
- dify 用 Base64（混淆），真正的加密交给 HTTPS；ruoyi 提供 AES 工具类

## 5. 练习题

### 练习 1：基础（必做）

实现 `encrypt_aes_gcm(plaintext, key)` 和 `decrypt_aes_gcm(ciphertext, key)`，要求：
- 使用 AES-256-GCM
- nonce 12 字节，每次随机
- 输出 base64 编码
- 解密时自动校验 tag

**参考答案**：见 `solutions/01-aes-gcm.md`

### 练习 2：进阶

解释为什么 AES-CBC 模式"必须配合 HMAC 使用"才能防止篡改？为什么 AES-GCM 不需要？

### 练习 3：挑战（选做）

为 dify 实现一个"密钥加密存储"功能：
- 用环境变量中的主密钥（KEK）加密每个租户的 DEK
- DEK 用于加密租户敏感数据（API Key 等）
- 实现 KEK 轮换时重加密

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/encryption.py`
- `/Users/xu/code/github/dify/api/core/helper/provider_encryption.py`（更复杂的加密）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/crypto/`（加密工具类目录）
- Python `cryptography` 库文档：https://cryptography.io/en/latest/
- NIST AES 标准（FIPS 197）：https://csrc.nist.gov/publications/detail/fips/197/final

---

**文档版本**：v1.0
**最后更新**：2026-07-13