# 4.3 密钥管理：Vault / KMS

> 密钥管理是企业级安全的核心。生产环境应该用专业的密钥管理服务。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解密钥管理的挑战
- 掌握 HashiCorp Vault 和云 KMS
- 在 dify/ruoyi 中集成密钥管理
- 避免常见的密钥泄露风险

## 📚 前置知识

- 10-asymmetric.md
- 13-password-storage.md

## 1. 核心概念

### 1.1 密钥管理的挑战

- **存储**：不能明文写在代码或配置文件
- **轮换**：定期更换密钥
- **权限**：谁能访问什么密钥
- **审计**：所有密钥使用都有记录
- **恢复**：密钥丢失怎么办

### 1.2 主流方案对比

| 方案 | 类型 | 特点 |
|------|------|------|
| HashiCorp Vault | 开源 | 自托管、灵活 |
| AWS KMS | 云服务 | 与 AWS 深度集成 |
| Azure Key Vault | 云服务 | Azure 集成 |
| Google Cloud KMS | 云服务 | GCP 集成 |
| 阿里云 KMS | 云服务 | 阿里云集成 |
| 环境变量 | 简易 | 仅适合开发 |

### 1.3 Vault 的核心概念

- **Secrets**：密钥、密码、API Token 等
- **Policies**：访问控制策略
- **Auth Methods**：认证方式（Token、AWS IAM、K8s）
- **Secret Engines**：后端存储（KV、数据库、PKI）
- **Transit Engine**：加解密即服务（不存储明文）

### 1.4 KMS 的核心操作

- **CreateKey**：创建密钥
- **Encrypt / Decrypt**：加解密（不暴露明文密钥）
- **GenerateDataKey**：生成数据密钥（用于本地加密）
- **Rotate**：轮换密钥

## 2. 代码示例

### 2.1 Vault KV 读取

```python
import hvac

# 连接 Vault
client = hvac.Client(
    url="https://vault.example.com",
    token="s.XXXXX",  # 实际应该用 IAM、Token 自动获取
)

# 读取密钥
secret = client.secrets.kv.v2.read_secret_version(
    path="myapp/database",
    mount_point="secret",
)
password = secret["data"]["data"]["password"]
print(f"Password: {password}")
```

### 2.2 AWS KMS 加解密

```python
import boto3

kms = boto3.client("kms", region_name="us-east-1")

# 加密（不需要本地持有密钥）
response = kms.encrypt(
    KeyId="arn:aws:kms:us-east-1:123456789012:key/abcd-1234",
    Plaintext=b"my secret data",
)
ciphertext = response["CiphertextBlob"]

# 解密
response = kms.decrypt(CiphertextBlob=ciphertext)
plaintext = response["Plaintext"]
print(f"Decrypted: {plaintext.decode()}")
```

### 2.3 阿里云 KMS

```python
from aliyunsdkcore.client import AcsClient
from aliyunsdkkms.request.v20160120 import EncryptRequest

client = AcsClient("<access_key_id>", "<access_key_secret>", "cn-hangzhou")

request = EncryptRequest.EncryptRequest()
request.set_KeyId("<key-id>")
request.set_Plaintext("my_secret_data")

response = client.do_action_with_exception(request)
```

## 3. dify / ruoyi 仓库源码解读

### 3.1 dify 的密钥管理（环境变量）

**位置**：`/Users/xu/code/github/dify/api/configs/`
**核心代码**：

```python
import os
from cryptography.fernet import Fernet

# 从环境变量读取密钥
SECRET_KEY = os.getenv("SECRET_KEY") or Fernet.generate_key()
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY is required")

# 用密钥加密敏感字段
def encrypt_credential(value: str) -> str:
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.encrypt(value.encode()).decode()
```

**解读**：
- dify 用环境变量管理密钥（Docker/K8s 标准做法）
- 密钥从 secrets 注入，不在代码或镜像中
- **生产环境建议**：用 Vault / AWS Secrets Manager

### 3.2 ruoyi 的密钥管理

**位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/`
**核心代码**：

```java
// ruoyi 用 Spring Cloud Config + Vault
// application.yml
spring:
  cloud:
    vault:
      host: vault.example.com
      port: 8200
      authentication: TOKEN
      token: ${VAULT_TOKEN}
```

**解读**：
- ruoyi 可集成 Spring Cloud Vault
- 密钥从 Vault 读取，不在配置文件中
- **整体设计**：生产级密钥管理方案

### 3.3 简单的密钥轮换

```python
class KeyManager:
    """简单的密钥轮换（生产环境建议用 Vault）"""

    def __init__(self):
        # 多个密钥，支持轮换
        self.keys = [
            os.getenv("ENCRYPTION_KEY_V1"),
            os.getenv("ENCRYPTION_KEY_V2"),  # 最新
        ]
        self.current_version = 1

    def encrypt(self, plaintext: str) -> tuple[str, int]:
        """加密并标记密钥版本"""
        f = Fernet(self.keys[self.current_version].encode())
        return f.encrypt(plaintext.encode()).decode(), self.current_version

    def decrypt(self, ciphertext: str, version: int) -> str:
        """根据版本解密"""
        f = Fernet(self.keys[version].encode())
        return f.decrypt(ciphertext).decode()
```

## 4. 关键要点总结

- 密钥管理 = 安全存储 + 访问控制 + 轮换 + 审计
- 简单方案：环境变量（开发用）
- 企业方案：Vault / 云 KMS（生产用）
- dify 用环境变量，ruoyi 支持 Spring Cloud Vault
- 永远不要把密钥硬编码到代码或配置文件中

## 5. 练习题

### 练习 1：基础
用环境变量管理密钥，重构硬编码密钥的代码。

### 练习 2：进阶
部署一个 Vault 实例（开发模式），用 Python hvac 库读写密钥。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/configs/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/`
- HashiCorp Vault：https://www.vaultproject.io/
- AWS KMS：https://aws.amazon.com/kms/

---

**文档版本**：v1.0
**最后更新**：2026-07-13