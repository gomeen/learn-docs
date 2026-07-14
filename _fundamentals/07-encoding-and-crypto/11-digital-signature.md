# 3.4 数字签名与数字证书

> 数字签名保证消息的**完整性和不可抵赖性**。数字证书绑定身份和公钥。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解数字签名的原理（私钥签、公钥验）
- 区分签名 vs 加密
- 掌握数字证书（CA 颁发）
- 在 HTTPS、API 签名中识别应用

## 📚 前置知识

- 10-asymmetric.md
- 12-tls.md（关联）

## 1. 核心概念

### 1.1 数字签名的核心思想

```
签名：
  1. 对消息计算哈希（SHA-256）
  2. 用私钥加密哈希 → 签名
  3. 把消息 + 签名一起发送

验证：
  1. 收到消息和签名
  2. 用公钥解签 → 哈希1
  3. 对消息计算哈希 → 哈希2
  4. 哈希1 == 哈希2 → 签名有效
```

### 1.2 签名的 3 个性质

- **真实性**：私钥签的，只有持有私钥的人能签
- **完整性**：消息被篡改，签名验证失败
- **不可抵赖性**：签名后不能否认

### 1.3 签名 vs 加密

| 维度 | 签名 | 加密 |
|------|------|------|
| 目的 | 验证身份 | 保护机密 |
| 用谁的密钥 | 私钥签名 | 对方公钥加密 |
| 谁可以验证 | 任何有公钥的人 | 只有收件人能解 |

### 1.4 数字证书（Digital Certificate）

证书 = 身份信息 + 公钥 + CA 签名

```
证书内容：
  主体：example.com
  公钥：04:5e:...
  颁发者：DigiCert
  有效期：2024-01-01 ~ 2025-01-01
  签名：CA 用自己的私钥对证书签名
```

**CA（Certificate Authority）**：可信第三方，颁发证书。

## 2. 代码示例

### 2.1 Python 数字签名（RSA）

```python
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

# 生成密钥对
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

# 签名
message = b"Transfer 100 to Alice"
signature = private_key.sign(
    message,
    padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH,
    ),
    hashes.SHA256(),
)
print(f"Signature: {signature[:32].hex()}...")

# 验签
try:
    public_key.verify(
        signature,
        message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    print("Signature valid!")
except Exception:
    print("Signature INVALID")
```

### 2.2 篡改检测

```python
# 篡改消息
tampered = message + b" and 1000 to Bob"
try:
    public_key.verify(
        signature,
        tampered,  # 用原签名验证新消息
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
except Exception as e:
    print(f"Tampering detected: {e}")
```

### 2.3 签名 vs 加密（联合使用）

```python
# 场景：A 给 B 发消息（既保密又签名）

# 1. A 用私钥签名（保证完整性和身份）
signature = a_private_key.sign(message, padding.PSS(...), hashes.SHA256())

# 2. A 用 B 的公钥加密（保证机密性）
encrypted = b_public_key.encrypt(message + signature, padding.OAEP(...))

# 3. 发送密文

# 4. B 解密（用自己的私钥）
plaintext_with_sig = b_private_key.decrypt(encrypted, padding.OAEP(...))

# 5. B 验签（用 A 的公钥）
message, sig = plaintext_with_sig[:-256], plaintext_with_sig[-256:]
a_public_key.verify(sig, message, padding.PSS(...), hashes.SHA256())
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的 API 签名

**位置**：`/Users/xu/code/github/dify/api/controllers/console/`
**核心代码**：

```python
import hmac
import hashlib

def sign_request(secret: str, method: str, path: str, body: str) -> str:
    """API 签名——HMAC（不是 RSA，但思想类似）"""
    message = f"{method}\n{path}\n{body}"
    return hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_request(secret: str, method: str, path: str, body: str, signature: str) -> bool:
    """验证签名"""
    expected = sign_request(secret, method, path, body)
    return hmac.compare_digest(expected, signature)
```

**解读**：
- dify 用 HMAC（对称签名）——更轻量
- 比 RSA 签名快
- **设计意图**：内部 API 用 HMAC，对外签名才用 RSA

### 3.2 ruoyi 的 JWT 签名

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`
**核心代码**：

```java
@Component
public class JwtTokenProvider {
    private final SecretKey jwtSecret;  // HMAC-SHA256 密钥
    private final long expirationMs;

    public String generateToken(LoginUser user) {
        return Jwts.builder()
            .setSubject(user.getUsername())
            .setIssuedAt(new Date())
            .setExpiration(new Date(System.currentTimeMillis() + expirationMs))
            .signWith(SignatureAlgorithm.HS256, jwtSecret)  // HMAC 签名
            .compact();
    }

    public boolean validateToken(String token) {
        try {
            Jwts.parser().setSigningKey(jwtSecret).parseClaimsJws(token);
            return true;
        } catch (Exception e) {
            return false;
        }
    }
}
```

**解读**：
- ruoyi 用 HMAC-SHA256（HS256）签名 JWT
- 比 RSA（RS256）快
- **整体设计**：对称密钥 + JWT 是分布式系统常用认证方案

## 4. 关键要点总结

- 数字签名 = 私钥签、公钥验
- 提供完整性、真实性、不可抵赖性
- 数字证书 = 身份 + 公钥 + CA 签名
- dify 用 HMAC（内部 API）
- ruoyi 用 HS256 JWT（认证）

## 5. 练习题

### 练习 1：基础
实现消息签名：发送方签名，接收方验证，并测试篡改检测。

### 练习 2：进阶
用 Python 的 `cryptography` 库生成自签名证书，并用 OpenSSL 验证。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/controllers/console/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`
- 《密码学工程》第 2 章：对称加密

---

**文档版本**：v1.0
**最后更新**：2026-07-13