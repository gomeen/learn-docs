# 4.4 国产密码算法：SM 系列

> SM（商密）系列是中国国家密码管理局发布的密码算法标准，包括 SM1-SM4 等。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 SM 系列的算法组成
- 掌握 SM2、SM3、SM4 的应用场景
- 知道国产化的合规要求
- 在 Java 中使用 SM 算法

## 📚 前置知识

- 08-hash.md
- 09-symmetric.md
- 10-asymmetric.md

## 1. 核心概念

### 1.1 SM 系列总览

| 算法 | 类型 | 对标国际 | 用途 |
|------|------|---------|------|
| SM1 | 对称 | AES | 硬件实现，不公开 |
| SM2 | 非对称 | RSA / ECC | 加密、签名、密钥交换 |
| SM3 | 哈希 | SHA-256 | 数据完整性 |
| SM4 | 对称 | AES | 数据加密（公开算法） |
| SM9 | 标识密码 | IBE | 基于身份的加密 |

### 1.2 国密合规要求

- **金融行业**：必须使用国密算法（央行规定）
- **政企领域**：等保 2.0 要求
- **密码模块**：GM/T 0028 认证
- **TLCP**：国密 TLS 协议（RFC 8998）

### 1.3 SM2 / SM3 / SM4 详解

**SM2（椭圆曲线，非对称）**：
- 密钥长度 256 位
- 比 RSA-2048 更快
- 支持加密、签名、密钥交换

**SM3（哈希）**：
- 输出 256 位
- 类似 SHA-256
- 用于数字签名、HMAC

**SM4（对称分组密码）**：
- 块大小 128 位，密钥 128 位
- 类似 AES-128
- 用于数据加密

## 2. 代码示例

### 2.1 Python SM3（哈希）

```python
from gmssl import sm3, func

# SM3 哈希
msg = b"hello world"
hash_hex = sm3.sm3_hash(func.bytes_to_list(msg))
print(f"SM3: {hash_hex}")
# 类似 SHA-256 的输出长度（256 位）

# SM3 HMAC
mac = sm3.sm3_kdf(msg, key=b"secret")
print(f"SM3 HMAC: {mac}")
```

### 2.2 Python SM4（对称加密）

```python
from gmssl import sm4, func

# 密钥必须是 16 字节（AES-128 等价）
key = b"1234567890abcdef"
plaintext = b"Hello, SM4! 中国"

# CBC 模式需要 16 字节 IV
iv = b"\x00" * 16

# 加密
crypt = sm4.CryptSM4()
crypt.set_key(key, sm4.SM4_ENCRYPT)
ciphertext = crypt.crypt_cbc(iv, plaintext)
print(f"Ciphertext: {ciphertext.hex()}")

# 解密
crypt.set_key(key, sm4.SM4_DECRYPT)
decrypted = crypt.crypt_cbc(iv, ciphertext)
print(f"Decrypted: {decrypted.decode()}")
```

### 2.3 Java SM2（需要 BouncyCastle）

```java
import org.bouncycastle.crypto.generators.ECKeyPairGenerator;
import org.bouncycastle.crypto.params.ECKeyGenerationParameters;
import org.bouncycastle.crypto.params.ECDomainParameters;
import org.bouncycastle.crypto.params.ECPrivateKeyParameters;
import org.bouncycastle.crypto.params.ECPublicKeyParameters;
import org.bouncycastle.jce.provider.BouncyCastleProvider;
import java.security.Security;

// 添加 BouncyCastle Provider
Security.addProvider(new BouncyCastleProvider());

// SM2 是基于特定椭圆曲线的 ECC 算法
// 实际开发通常用 hutool 或 BouncyCastle 封装
```

### 2.4 国密 TLS（TLCP）

```nginx
# Nginx 配置 TLCP（国密 TLS）
server {
    listen 443 ssl;
    ssl_protocols TLSv1.2 TLCP1.1;  # 同时支持 TLS 和 TLCP
    ssl_certificate gm_cert.pem;
    ssl_certificate_key gm_key.pem;
    ssl_ntls_protocols GMTLSv1.1;  # 国密协议
}
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 未集成国密（国际通用）

**位置**：`/Users/xu/code/github/dify/api/libs/password.py`
**核心代码**：

```python
import hashlib

def hash_password(password_str: str, salt_byte: bytes):
    """dify 用 SHA-256（PBKDF2）"""
    dk = hashlib.pbkdf2_hmac("sha256", password_str.encode("utf-8"), salt_byte, 10000)
    return binascii.hexlify(dk)
```

**解读**：
- dify 是国际化项目，使用国际通用算法
- 国密应用主要在国内政企/金融行业
- **dify/ruoyi 中无直接 SM 算法示例**

### 3.2 ruoyi 国密集成（可选）

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/`
**核心代码**：

```java
// ruoyi 框架预留扩展点，可以集成 hutool-crypto 或 BouncyCastle
// 启用国密需要引入额外依赖
```

**解读**：
- ruoyi 是国内开源项目，但默认仍是国际算法
- 用户可以基于 ruoyi 扩展国密支持

### 3.3 dify/ruoyi 中无直接示例

**dify 和 ruoyi 均无直接 SM 算法使用代码**。国密集成主要在：
- 政企定制开发
- 金融行业（银联、网联）
- 国产化替代项目

## 4. 关键要点总结

- SM 系列：SM1（不公开）、SM2（非对称）、SM3（哈希）、SM4（对称）
- SM2 比 RSA-2048 更快更安全
- 国密合规：金融、政企必须
- dify/ruoyi 中**无直接示例**——国际化项目默认国际算法
- 国产化替代需引入 hutool-crypto 或 BouncyCastle

## 5. 练习题

### 练习 1：基础
用 Python gmssl 库实现 SM3 哈希和 SM4 加解密。

### 练习 2：进阶
调研：在你的业务中是否需要国密合规？金融、政企、互联网公司的要求有何不同？

## 6. 参考资料

- 国家密码管理局：http://www.sca.gov.cn/
- SM 系列算法规范：GB/T 32907、GB/T 32918、GB/T 32905
- 商用密码检测中心：http://www.scctc.org.cn/
- **dify/ruoyi 中无直接示例**

---

**文档版本**：v1.0
**最后更新**：2026-07-13