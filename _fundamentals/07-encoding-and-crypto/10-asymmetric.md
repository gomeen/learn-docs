# 3.3 非对称加密：RSA / ECC / SM2

> 非对称加密用**公钥 + 私钥**对，公钥加密私钥解（或反之），解决密钥分发问题。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解非对称加密的核心（公钥 + 私钥）
- 掌握 RSA、ECC 的特点
- 知道 SM2 国密算法
- 在 HTTPS、签名场景中识别应用

## 📚 前置知识

- 09-symmetric.md
- 11-digital-signature.md（关联）

## 1. 核心概念

### 1.1 非对称加密原理

```
公钥（Public Key）  —— 可公开，用于加密
私钥（Private Key） —— 保密，用于解密

A 想给 B 发消息：
1. A 用 B 的公钥加密
2. B 用自己的私钥解密
```

### 1.2 主流算法对比

| 算法 | 密钥长度 | 速度 | 用途 |
|------|---------|------|------|
| RSA | 2048-4096 位 | 慢 | 加密、签名 |
| ECC | 256-521 位 | 快 | 加密、签名 |
| SM2 | 256 位 | 快 | 国密标准 |
| DSA | 1024-3072 位 | 中 | 仅签名 |

### 1.3 RSA vs ECC

| 维度 | RSA | ECC |
|------|-----|-----|
| 相同安全级别 | 3072 位 | 256 位 |
| 计算速度 | 慢 | 快 10x |
| 密钥体积 | 大 | 小 |
| 应用广泛度 | 极高 | 高 |

### 1.4 应用场景

- **加密传输**：HTTPS 握手（RSA 交换 AES 密钥）
- **数字签名**：私钥签名，公钥验证
- **身份认证**：证书（SSL/TLS）

## 2. 代码示例

### 2.1 Python RSA

```python
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

# 生成密钥对
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

# 加密（用公钥）
plaintext = b"Secret message"
ciphertext = public_key.encrypt(
    plaintext,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    ),
)
print(f"Ciphertext: {ciphertext[:32].hex()}...")

# 解密（用私钥）
decrypted = private_key.decrypt(
    ciphertext,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None,
    ),
)
print(f"Decrypted: {decrypted.decode()}")
```

### 2.2 Python ECC

```python
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

# 生成 ECC 密钥对
private_key = ec.generate_private_key(ec.SECP256R1())  # P-256 曲线
public_key = private_key.public_key()

# 签名（私钥）
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
message = b"Hello, World!"
signature = private_key.sign(
    message,
    ec.ECDSA(hashes.SHA256()),
)

# 验签（公钥）
public_key.verify(signature, message, ec.ECDSA(hashes.SHA256()))
print("Signature valid!")
```

### 2.3 密钥持久化

```python
# 保存私钥（PEM 格式）
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),  # 或 BestAvailableEncryption
)

with open("private_key.pem", "wb") as f:
    f.write(private_pem)

# 加载私钥
with open("private_key.pem", "rb") as f:
    loaded_private_key = serialization.load_pem_private_key(f.read(), password=None)
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的非对称加密（JWT 签名）

**位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**：

```python
import jwt
from cryptography.hazmat.primitives import serialization

# JWT 用 RSA/ECDSA 签名
def generate_jwt(payload: dict, private_key_pem: bytes) -> str:
    """用私钥签发 JWT"""
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)
    token = jwt.encode(payload, private_key, algorithm="RS256")
    return token

def verify_jwt(token: str, public_key_pem: bytes) -> dict:
    """用公钥验证 JWT"""
    public_key = serialization.load_pem_public_key(public_key_pem)
    payload = jwt.decode(token, public_key, algorithms=["RS256"])
    return payload
```

**解读**：
- JWT 用 RS256（RSA + SHA-256）签名
- 服务端持私钥签发，客户端持公钥验证

### 3.2 ruoyi 的 HTTPS 配置

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/`
**核心代码**（application.yml）：

```yaml
server:
  ssl:
    enabled: true
    key-store: classpath:keystore.p12  # 含 RSA 密钥对
    key-store-password: changeit
    key-store-type: PKCS12
    key-alias: tomcat
```

**解读**：
- HTTPS 用 RSA 非对称加密
- 客户端用服务器的公钥验证证书
- 之后用 AES 对称加密传输数据（混合加密）

### 3.3 实际应用：混合加密

```python
def hybrid_encrypt(plaintext: bytes, public_key) -> bytes:
    """混合加密：RSA 加密 AES 密钥 + AES 加密数据"""
    # 1. 生成随机 AES 密钥
    aes_key = os.urandom(32)
    iv = os.urandom(16)

    # 2. 用 AES 加密数据
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded(plaintext)) + encryptor.finalize()

    # 3. 用 RSA 加密 AES 密钥
    encrypted_key = public_key.encrypt(
        aes_key,
        padding.OAEP(...),
    )

    # 4. 返回：加密的密钥 + IV + 密文
    return encrypted_key + iv + ciphertext
```

## 4. 关键要点总结

- 非对称加密 = 公钥 + 私钥对
- RSA 主流（2048 位以上）
- ECC 更快（256 位足够）
- 应用：HTTPS 握手、数字签名
- 实际系统用混合加密（RSA + AES）
- dify 用 RS256 JWT，ruoyi 用 HTTPS

## 5. 练习题

### 练习 1：基础
生成一对 RSA 密钥，用公钥加密，私钥解密。

### 练习 2：进阶
实现混合加密：RSA 加密 AES 密钥 + AES 加密数据。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/account_service.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application.yml`
- 《密码学原理与实践》第 6 章：公钥加密

---

**文档版本**：v1.0
**最后更新**：2026-07-13