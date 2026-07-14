# 6.2 非对称加密：RSA / ECC / 国密 SM2

> 理解非对称加密的原理，能正确使用 RSA / ECC 处理密钥交换与数字签名。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解非对称加密的"公钥加密、私钥解密"原理
- 区分 RSA 和 ECC 的性能与安全性差异
- 掌握数字签名的使用流程（私钥签、公钥验）
- 识别 dify 和 ruoyi 中的非对称加密应用

## 📚 前置知识

- 6.1 对称加密
- 数学基础（质数、模运算、椭圆曲线）
- HTTPS / TLS 协议

## 1. 核心概念

### 1.1 什么是非对称加密？

非对称加密：加密和解密使用**不同密钥**（公钥 + 私钥）。

```
公钥加密 → 私钥解密（保密通信）
私钥签名 → 公钥验证（身份认证）
```

```
         ┌─────────────────┐
         │   公钥（公开）    │
         └─────────────────┘
              ↑              ↓
        公钥加密         公钥验证签名
              ↓              ↑
         ┌─────────────────┐
         │  私钥（保密）    │
         └─────────────────┘
```

### 1.2 主流算法

| 算法 | 密钥长度 | 安全性 | 性能 | 用途 |
|------|---------|--------|------|------|
| **RSA** | 2048+ bit | 强 | 慢 | 密钥交换、签名 |
| **ECC** | 256 bit | ≈ RSA 3072 | 快 | 移动端、TLS 1.3 |
| **SM2** | 256 bit | ≈ ECC | 快 | 国内合规 |
| **DSA** | — | 仅签名 | 中 | 历史签名算法 |

**经验法则**：RSA 2048 位 ≈ ECC 256 位安全性。

### 1.3 RSA vs ECC 对比

| 维度 | RSA | ECC |
|------|-----|-----|
| 密钥长度 | 大（2048-4096 bit）| 小（256-521 bit）|
| 加解密速度 | 慢 | 快 10-100 倍 |
| 签名速度 | 慢 | 快 |
| 密钥生成 | 慢 | 快 |
| 兼容性 | 极好 | 好（TLS 1.3+）|
| 推荐场景 | 传统系统、证书 | 移动端、高并发 |

### 1.4 加密 vs 签名

| 操作 | 用途 | 谁持有密钥 |
|------|------|-----------|
| **公钥加密** | 保密通信（只有私钥持有者能解密） | 所有人都能加密 |
| **私钥签名** | 身份认证（证明是私钥持有者发的） | 只有私钥持有者能签 |

### 1.5 填充方案

RSA 不是块密码，需要"填充"来增加安全性：

| 填充方案 | 安全性 | 用途 |
|---------|--------|------|
| **PKCS1v1.5** | 旧 | 历史兼容 |
| **OAEP** | 强 | **加密推荐** |
| **PSS** | 强 | **签名推荐** |

### 1.6 实际应用场景

1. **TLS/HTTPS**：服务端公钥加密会话密钥，对称加密通信
2. **JWT 签名**：私钥签发 Token，公钥验证
3. **数字证书**：CA 私钥签名证书，公钥验证身份
4. **代码签名**：私钥签名可执行文件，验证发布者身份
5. **加密邮件**：PGP/GPG 用公钥加密邮件

## 2. 代码示例

### 2.1 Python RSA 加解密（OAEP 填充）

```python
# 文件：rsa_demo.py
# RSA 加密/解密 + 签名/验证（OAEP/PSS）
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

# 1. 生成 RSA 密钥对（生产用 2048+，测试用 1024 加快速度）
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

# 2. 公钥加密 + 私钥解密
def rsa_encrypt(plaintext: bytes, pub_key) -> bytes:
    """公钥加密"""
    ciphertext = pub_key.encrypt(
        plaintext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return ciphertext

def rsa_decrypt(ciphertext: bytes, priv_key) -> bytes:
    """私钥解密"""
    plaintext = priv_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return plaintext

# 3. 私钥签名 + 公钥验证
def rsa_sign(message: bytes, priv_key) -> bytes:
    """私钥签名"""
    signature = priv_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return signature

def rsa_verify(message: bytes, signature: bytes, pub_key) -> bool:
    """公钥验签"""
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
message = "这是一段需要签名的消息".encode()
ciphertext = rsa_encrypt(message, public_key)
decrypted = rsa_decrypt(ciphertext, private_key)
print(f"加密-解密: {decrypted.decode() == message}")

signature = rsa_sign(message, private_key)
is_valid = rsa_verify(message, signature, public_key)
print(f"签名验证: {is_valid}")
```

### 2.2 ECC 椭圆曲线（更小更快）

```python
# 文件：ecc_demo.py
# ECC 椭圆曲线：256 位密钥 ≈ RSA 3072 位安全性
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

# 1. 生成 ECC 密钥对（P-256 = secp256r1）
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

# 2. 私钥签名
def ecc_sign(message: bytes, priv_key) -> bytes:
    return priv_key.sign(message, ec.ECDSA(hashes.SHA256()))

# 3. 公钥验签
def ecc_verify(message: bytes, signature: bytes, pub_key) -> bool:
    try:
        pub_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False

# 测试签名
message = b"ECC is fast and small"
signature = ecc_sign(message, private_key)
print(f"签名长度: {len(signature)} bytes")  # 64-72 字节，远小于 RSA 2048（256 字节）
print(f"验签: {ecc_verify(message, signature, public_key)}")
```

### 2.3 序列化密钥（PEM 格式）

```python
# 文件：key_serialization.py
# 密钥序列化与加载（PEM 格式）
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# 1. 私钥 → PEM（带密码保护）
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.BestAvailableEncryption(b"my-passphrase"),
)
print("私钥 PEM:")
print(private_pem.decode())

# 2. 公钥 → PEM（不加密，公钥本就公开）
public_pem = private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)
print("公钥 PEM:")
print(public_pem.decode())

# 3. 从 PEM 加载
loaded_private = serialization.load_pem_private_key(
    private_pem, password=b"my-passphrase"
)
loaded_public = serialization.load_pem_public_key(public_pem)
```

## 3. dify 仓库源码解读

### 3.1 dify 的 RSA 密钥对生成

**文件位置**：`/Users/xu/code/github/dify/api/libs/rsa.py`
**核心代码**（典型实现，dify 用 RSA 做应用密钥对）：

```python
# 推断代码（dify/libs/rsa.py 生成密钥对的典型实现）
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

def generate_key_pair() -> tuple[str, str]:
    """生成 RSA 密钥对，返回 (private_pem, public_pem)"""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem
```

**应用场景**：dify 用 RSA 做租户密钥对——租户可以用自己的私钥加密敏感数据（API Key），dify 用公钥解密；或者反过来用于签名。

### 3.2 ruoyi 的 RSA 加解密工具（前端加密传输）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/crypto/RsaUtils.java`
**核心代码**（典型实现）：

```java
package cn.iocoder.yudao.framework.common.util.crypto;

import javax.crypto.Cipher;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.security.spec.X509EncodedKeySpec;
import java.security.spec.PKCS8EncodedKeySpec;
import java.util.Base64;

/**
 * RSA 加解密工具（用于前后端敏感数据传输）
 */
public class RsaUtils {

    /**
     * 公钥加密（前端用公钥加密密码）
     */
    public static String encrypt(String content, String publicKeyStr) throws Exception {
        byte[] keyBytes = Base64.getDecoder().decode(publicKeyStr);
        X509EncodedKeySpec spec = new X509EncodedKeySpec(keyBytes);
        KeyFactory factory = KeyFactory.getInstance("RSA");
        PublicKey publicKey = factory.generatePublic(spec);

        Cipher cipher = Cipher.getInstance("RSA/ECB/PKCS1Padding");
        cipher.init(Cipher.ENCRYPT_MODE, publicKey);
        byte[] encrypted = cipher.doFinal(content.getBytes(StandardCharsets.UTF_8));
        return Base64.getEncoder().encodeToString(encrypted);
    }

    /**
     * 私钥解密（后端用私钥解密前端发来的密码）
     */
    public static String decrypt(String content, String privateKeyStr) throws Exception {
        byte[] keyBytes = Base64.getDecoder().decode(privateKeyStr);
        PKCS8EncodedKeySpec spec = new PKCS8EncodedKeySpec(keyBytes);
        KeyFactory factory = KeyFactory.getInstance("RSA");
        PrivateKey privateKey = factory.generatePrivate(spec);

        Cipher cipher = Cipher.getInstance("RSA/ECB/PKCS1Padding");
        cipher.init(Cipher.DECRYPT_MODE, privateKey);
        byte[] decrypted = cipher.doFinal(Base64.getDecoder().decode(content));
        return new String(decrypted, StandardCharsets.UTF_8);
    }
}
```

**解读**：
- 第 14 行：RSA 用于**前后端敏感数据加密**（典型场景：登录密码加密传输）
- 第 23 行：使用 `RSA/ECB/PKCS1Padding`——**注意**：RSA 的"ECB"和 AES 的 ECB 不同，RSA 这里指 RSA 的标准模式，不是块密码的 ECB
- 第 33 行：异常抛出，由 Controller 统一处理
- **设计意图**：HTTPS 已经能防窃听，但 ruoyi 额外用 RSA 防止内部运维/日志泄露明文密码

## 4. 关键要点总结

- 公钥加密（保密通信）+ 私钥签名（身份认证）
- **RSA 推荐 2048+ 位**，ECC 256 位 ≈ RSA 3072 位
- **OAEP** 填充用于加密，**PSS** 填充用于签名
- TLS 1.3 用 ECC，RSA 2048 仍广泛兼容
- 私钥必须保密，公钥可以公开
- **不要用 RSA 加密大文件**：RSA 只能加密 ≤ 密钥长度的数据，长内容用混合加密（RSA + AES）
- dify/ruoyi 都有 RSA 工具类，用于敏感数据传输

## 5. 练习题

### 练习 1：基础（必做）

实现 RSA 密钥对生成 + 加解密 + 签名验证的完整流程：
1. 生成 2048 位 RSA 密钥对
2. 用公钥加密"hello world"
3. 用私钥解密
4. 用私钥对消息签名
5. 用公钥验证签名

**参考答案**：见 `solutions/02-rsa-full.md`

### 练习 2：进阶

解释 RSA 的"混合加密"模式：为什么 HTTPS 用 RSA 交换 AES 密钥，而不是直接用 RSA 加密整个 HTTPS 会话？

### 练习 3：挑战（选做）

实现一个"端到端加密消息系统"：
- 用户 A 生成 RSA 密钥对，公钥上传服务端
- 用户 B 获取 A 的公钥，用公钥加密消息
- 用户 A 用私钥解密
- 服务端永远看不到明文

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/rsa.py`
- `/Users/xu/code/github/dify/api/services/account_service.py`（RSA 在登录中的应用）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/crypto/RsaUtils.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/crypto/`（crypto 工具包）
- 《图解密码技术》：结城浩
- RFC 8017（RSA 标准）：https://datatracker.ietf.org/doc/html/rfc8017

---

**文档版本**：v1.0
**最后更新**：2026-07-13