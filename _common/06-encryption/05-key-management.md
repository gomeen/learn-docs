# 6.5 密钥管理：Vault / KMS / 环境变量

> 理解密钥管理的核心原则，掌握企业级密钥管理方案。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解密钥管理的"分层防护"原则
- 掌握环境变量、Vault、KMS 等主流方案的适用场景
- 在 dify 和 ruoyi 项目中找到密钥加载位置
- 避免常见的密钥泄露陷阱

## 📚 前置知识

- [6.1 对称加密](./01-symmetric.md)、[6.2 非对称加密](./02-asymmetric.md)、[6.3 哈希](./03-hash.md)
- Docker / 容器化基础（见 [09-containerization](../09-containerization/01-concepts.md)）
- Linux 环境变量

## 1. 核心概念

### 1.1 密钥管理的"金字塔"

```
                    ▲
                   ╱ ╲
                  ╱   ╲              ← KMS（云厂商托管）
                 ╱ HSM ╲             ← 硬件安全模块（最高安全）
                ╱───────╲
               ╱  Vault  ╲           ← HashiCorp Vault（自建）
              ╱───────────╲
             ╱ 配置中心      ╲       ← Nacos / Consul / Apollo
            ╱─────────────────╲
           ╱ 加密的环境变量     ╲     ← .env 文件 + 加密
          ╱─────────────────────╲
         ╱ 源代码（绝对禁止！）  ╲   ← ❌ 永远不要把密钥写进代码
        ╱_________________________╲
```

### 1.2 密钥管理的核心原则

1. **永不硬编码**：密钥不能在源码、注释、commit 历史中
2. **最小权限**：每个密钥只能访问必要的资源
3. **定期轮换**：密钥有过期时间，定期更换
4. **分级管理**：主密钥（KEK）保护数据密钥（DEK）
5. **审计日志**：所有密钥使用都要记录
6. **不在日志中**：密钥、Token、密码都不能写日志

### 1.3 主流方案对比

| 方案 | 安全等级 | 适用场景 | 成本 |
|------|---------|---------|------|
| **硬编码** | ❌ 零 | 永远禁止 | — |
| **环境变量** | 低 | 本地开发、CI | 免费 |
| **.env 文件** | 低 | 本地开发 | 免费 |
| **配置文件** | 低 | 自托管 | 免费 |
| **配置中心** | 中 | 微服务集群 | 低 |
| **HashiCorp Vault** | 高 | 中大型企业 | 中 |
| **云 KMS** | 极高 | 云原生应用 | 按调用付费 |
| **HSM** | **最高** | 金融、政企 | 极高 |

### 1.4 KEK / DEK 模式（信封加密）

```
主密钥 KEK（存于 Vault/KMS）
   ↓ 加密
数据密钥 DEK（用于加密业务数据）
   ↓ 加密
业务数据
```

**优势**：
- KEK 极少使用（只在轮换时使用），可以放在硬件中
- DEK 可以和密文一起存储，丢失不影响安全
- 轮换 KEK 不需要重新加密所有数据

### 1.5 dify 和 ruoyi 的密钥加载方式

| 项目 | 密钥加载方式 | 位置 |
|------|------------|------|
| **dify** | 环境变量 + `.env` 文件 | `api/.env` / `docker/.env` |
| **dify** | Secrets（Docker / K8s） | `docker-compose.yaml` |
| **ruoyi** | Nacos 配置中心 | `application-{profile}.yml` |
| **ruoyi** | Jasypt 加密配置 | `ENC(...)` 格式 |

## 2. 代码示例

### 2.1 反面教材：硬编码密钥

```python
# ❌ 反面教材：硬编码密钥
# 文件: app.py
SECRET_KEY = "sk-prod-abc123xyz"  # ❌ 永远不要这样做！
DATABASE_URL = "postgresql://admin:password123@db/app"  # ❌
API_KEY = "AIzaSyB-1234567890"  # ❌

# 即使是"开发用"的密钥也不能硬编码：
# - GitHub 公开仓库会被爬虫 30 秒内发现
# - 离职员工的 commit 历史能查到
# - Docker 镜像层会保留密钥
```

### 2.2 正确做法：环境变量 + .env

```python
# 文件: app.py
# ✅ 从环境变量加载
import os
from pathlib import Path

def load_env_file(env_path: str = ".env"):
    """手动加载 .env 文件（不依赖 python-dotenv）"""
    env_file = Path(env_path)
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

load_env_file()

# 读取
SECRET_KEY = os.environ["SECRET_KEY"]  # 缺失时抛 KeyError
DATABASE_URL = os.environ["DATABASE_URL"]
API_KEY = os.environ["OPENAI_API_KEY"]

# 提供默认值（仅限非敏感配置）
DEBUG = os.getenv("DEBUG", "0") == "1"
```

```bash
# 文件: .env（**必须加入 .gitignore**）
SECRET_KEY=sk-prod-abc123xyz
DATABASE_URL=postgresql://admin:password123@db/app
OPENAI_API_KEY=AIzaSyB-xxxxx

# 文件: .env.example（提交到 git，给开发者参考）
SECRET_KEY=
DATABASE_URL=
OPENAI_API_KEY=
```

```gitignore
# 文件: .gitignore
.env
*.pem
*.key
secrets/
```

### 2.3 进阶：HashiCorp Vault 集成

```python
# 文件: vault_integration.py
# ✅ 从 Vault 动态读取密钥
import hvac
from functools import lru_cache

class VaultClient:
    def __init__(self, url: str, token: str):
        self.client = hvac.Client(url=url, token=token)

    @lru_cache(maxsize=128)
    def get_secret(self, path: str, key: str) -> str:
        """读取密钥（带缓存）"""
        response = self.client.secrets.kv.read_secret_version(path=path)
        return response["data"]["data"][key]

    def get_dynamic_db_credential(self, role: str) -> dict:
        """获取动态数据库凭证（Vault 自动生成、定期轮换）"""
        response = self.client.secrets.database.generate_credentials(name=role)
        return {
            "username": response["data"]["username"],
            "password": response["data"]["password"],
        }

# 使用
vault = VaultClient(
    url=os.environ["VAULT_ADDR"],
    token=os.environ["VAULT_TOKEN"],
)
api_key = vault.get_secret("secret/data/openai", "api_key")
db_creds = vault.get_dynamic_db_credential("app-readwrite")
```

### 2.4 AWS KMS 集成（云原生）

```python
# 文件: kms_integration.py
# ✅ 用 AWS KMS 做信封加密
import boto3
import os

kms = boto3.client("kms")

def encrypt_with_kms(plaintext: bytes, key_id: str) -> bytes:
    """用 KMS 主密钥加密"""
    response = kms.encrypt(
        KeyId=key_id,
        Plaintext=plaintext,
    )
    return response["CiphertextBlob"]

def decrypt_with_kms(ciphertext_blob: bytes) -> bytes:
    """用 KMS 解密"""
    response = kms.decrypt(CiphertextBlob=ciphertext_blob)
    return response["Plaintext"]

# 应用：加密用户 API Key 后存储到数据库
def store_user_api_key(user_id: str, api_key: str):
    encrypted = encrypt_with_kms(api_key.encode(), os.environ["KMS_KEY_ID"])
    db.execute("UPDATE users SET api_key=%s WHERE id=%s", (encrypted, user_id))

def load_user_api_key(user_id: str) -> str:
    encrypted = db.execute("SELECT api_key FROM users WHERE id=%s", (user_id,)).scalar()
    return decrypt_with_kms(encrypted).decode()

# 优势：
# - KMS 主密钥永远不离开 AWS 硬件
# - 自动审计：所有加解密调用都记录到 CloudTrail
# - 自动轮换：可配置 KMS 主密钥每年自动轮换
```

## 3. dify 仓库源码解读

### 3.1 dify 的配置加载（环境变量优先）

**文件位置**：`/Users/xu/code/github/dify/api/configs/dify_config.py`（典型配置加载）
**核心代码**（典型实现）：

```python
"""
dify 配置加载器：从环境变量读取所有配置
"""
import os
from typing import Any

class DifyConfig:
    """集中管理所有配置"""

    def __init__(self):
        # 数据库
        self.DB_USERNAME = os.environ.get("DB_USERNAME", "postgres")
        self.DB_PASSWORD = os.environ["DB_PASSWORD"]  # 必填，缺失抛错
        self.DB_HOST = os.environ.get("DB_HOST", "db")
        self.DB_PORT = os.environ.get("DB_PORT", "5432")
        self.DB_DATABASE = os.environ.get("DB_DATABASE", "dify")

        # Redis
        self.REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
        self.REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")

        # 安全相关
        self.SECRET_KEY = os.environ["SECRET_KEY"]  # Flask Session 加密密钥
        self.PASSWORD_HASH_ITERATIONS = int(os.environ.get("PASSWORD_HASH_ITERATIONS", "10000"))

        # 加密相关（用于 provider API Key）
        self.SECRET_KEY_PROVIDER = os.environ.get("SECRET_KEY_PROVIDER", self.SECRET_KEY)

        # SSRF 代理
        self.SSRF_PROXY_HTTP_URL = os.environ.get("SSRF_PROXY_HTTP_URL", "")
        self.SSRF_PROXY_HTTPS_URL = os.environ.get("SSRF_PROXY_HTTPS_URL", "")

# 单例
dify_config = DifyConfig()
```

**解读**：
- 第 11 行：DB 密码、SECRET_KEY 等用 `os.environ["..."]` 直接读取（**缺失即报错**，避免上线时才发现）
- 第 22 行：`SECRET_KEY` 是 Flask Session 加密密钥，必须保密
- 第 23 行：PBKDF2 迭代次数可配置（便于将来调整）
- 第 26-27 行：Provider 加密密钥可独立（生产建议与主密钥分离）
- **设计意图**：dify 把所有密钥集中到 `dify_config` 对象，方便审计和单元测试覆盖

### 3.2 ruoyi 的 Jasypt 加密配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/crypto/JasyptUtils.java`（典型实现）
**核心代码**（典型 Java 实现）：

```java
package cn.iocoder.yudao.framework.common.util.crypto;

import org.jasypt.encryption.pbe.StandardPBEStringEncryptor;
import org.jasypt.encryption.pbe.config.EnvironmentStringPBEConfig;

/**
 * Jasypt 配置加密工具
 *
 * 用法：在 application.yml 中写
 *   spring.datasource.password: ENC(加密后的密文)
 */
public class JasyptUtils {

    /**
     * 加密
     */
    public static String encrypt(String plaintext, String password) {
        StandardPBEStringEncryptor encryptor = new StandardPBEStringEncryptor();
        EnvironmentStringPBEConfig config = new EnvironmentStringPBEConfig();
        config.setPassword(password);  // 主密钥（从环境变量读取）
        config.setAlgorithm("PBEWithMD5AndDES");
        encryptor.setConfig(config);
        return encryptor.encrypt(plaintext);
    }

    /**
     * 解密
     */
    public static String decrypt(String ciphertext, String password) {
        StandardPBEStringEncryptor encryptor = new StandardPBEStringEncryptor();
        EnvironmentStringPBEConfig config = new EnvironmentStringPBEConfig();
        config.setPassword(password);
        config.setAlgorithm("PBEWithMD5AndDES");
        encryptor.setConfig(config);
        return encryptor.decrypt(ciphertext);
    }
}
```

**对应 application.yml**：
```yaml
# 文件：application-prod.yml
spring:
  datasource:
    password: ENC(Ah3xkP9c+SZObd4zF8...)  # ✅ 加密存储，git 中安全

# 启动时传入主密钥：
# java -Djasypt.encryptor.password=${MASTER_KEY} -jar app.jar
```

**解读**：
- 第 15 行：Jasypt 是 Java 生态的配置加密库
- 第 18 行：`PBEWithMD5AndDES` 是加密算法（**注意：MD5+DES 已陈旧，ruoyi 实际配置可能用了更强算法**）
- 第 33 行：解密用于运行时读取配置
- **设计意图**：让运维可以把加密后的配置 commit 到 git，**只有拿到主密钥才能解密**，避免明文泄露

## 4. 关键要点总结

- **永远不要硬编码密钥**——包括注释、commit 历史
- **.env 文件必须加入 .gitignore**
- 生产用 KMS/Vault/配置中心，本地开发用环境变量
- **轮换密钥**：KEK 每年轮换，DEK 每月轮换
- **信封加密**（KEK 加密 DEK）是大规模密钥管理的标准模式
- **最小权限**：每个密钥只授予必要的权限
- **审计日志**：所有密钥使用都要记录，便于溯源
- dify 用环境变量 + `.env` 文件
- ruoyi 用 Jasypt 加密配置 + Nacos 配置中心

## 5. 练习题

### 练习 1：基础（必做）

实现一个"配置加载器"：
1. 优先从环境变量读取
2. 环境变量缺失时回退到 `.env` 文件
3. 关键密钥缺失时抛错（fail fast）
4. 单元测试覆盖

**参考答案**：见 `solutions/05-config-loader.md`

### 练习 2：进阶

阅读 dify 的 `configs/dify_config.py` 和 `docker/.env.example`，列出至少 5 个"绝对不能泄露"的关键配置项，并说明每个的用途。

### 练习 3：挑战（选做）

实现 KEK/DEK 信封加密：
1. 启动时从环境变量读取 KEK
2. 为每条用户数据随机生成 DEK
3. 用 KEK 加密 DEK，用 DEK 加密数据
4. 数据库中存储 `encrypted_dek + encrypted_data`
5. KEK 轮换时只需要重新加密 DEK，无需重加密所有数据

## 6. 参考资料

- `/Users/xu/code/github/dify/api/configs/dify_config.py`
- `/Users/xu/code/github/dify/docker/.env.example`
- `/Users/xu/code/github/dify/docker/docker-compose.yaml`（看 secrets 配置）
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/crypto/`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/`（租户密钥管理）
- HashiCorp Vault 文档：https://www.vaultproject.io/docs
- AWS KMS 文档：https://docs.aws.amazon.com/kms/

---

**文档版本**：v1.0
**最后更新**：2026-07-13