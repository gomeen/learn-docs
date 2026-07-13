# 5.4.5 密钥管理：Vault / KMS / 环境变量

> 理解密钥管理的核心原则，掌握 dify 的密钥存储与轮换策略。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解密钥管理的核心原则（不硬编码、不提交到 git）
- 掌握三种密钥管理方案：环境变量 / Vault / KMS
- 理解密钥轮换的实现方式
- 能用 Python 实现一个简化版密钥管理

## 📚 前置知识

- 21-symmetric-encryption.md
- 23-hashing.md
- DevOps 基础（Docker / K8s）

## 1. 核心概念

### 1.1 密钥管理的三条铁律

1. **不硬编码**：源代码里永远不出现明文密钥
2. **不提交到 git**：用 `.env` 文件 + `.gitignore`
3. **定期轮换**：泄露时影响窗口有限

### 1.2 三种密钥管理方案

| 方案 | 适用 | 优点 | 缺点 |
|------|------|------|------|
| **环境变量** | 单机/小团队 | 简单 | 多机管理麻烦 |
| **Vault** | 中大型 | 集中管理、自动轮换 | 部署运维成本 |
| **KMS** | 云上 | 硬件级保护 | 绑定云厂商 |

### 1.3 dify 的密钥管理策略

dify 主要用**环境变量**（`dify_config.py` 从环境变量读），高级场景用 **KMS / Vault**（通过插件）。

**典型密钥**：
- `SECRET_KEY`：JWT 签名密钥
- `DB_PASSWORD`：数据库密码
- `ENCRYPT_KEY`：对称加密主密钥
- 各 provider 的 API Key

### 1.4 密钥轮换

```python
# 多版本密钥同时存在（key rotation）
keys = {
    "v1": "old-secret-xxx",  # 仅用于验证旧 token
    "v2": "new-secret-yyy",  # 用于签名新 token
}
active_kid = "v2"
```

这样轮换密钥时**无需停服**，旧 token 还能验证，新 token 用新密钥签。

## 2. 代码示例

### 2.1 从环境变量读密钥

```python
import os

class Settings:
    @property
    def secret_key(self) -> str:
        key = os.environ.get("DIFY_SECRET_KEY")
        if not key:
            raise RuntimeError("DIFY_SECRET_KEY is required")
        return key

    @property
    def db_password(self) -> str:
        # 支持从文件读取（K8s Secret mount）
        password_file = os.environ.get("DB_PASSWORD_FILE")
        if password_file:
            return open(password_file).read().strip()
        return os.environ.get("DB_PASSWORD", "")
```

### 2.2 密钥轮换：JWT KeySet

```python
from datetime import datetime, timedelta
import jwt

class RotatingKeys:
    def __init__(self):
        # 当前 + 上一代密钥（用于验证未过期的旧 token）
        self.keys = {
            "v2": "current-secret-yyy",
            "v1": "previous-secret-xxx",
        }
        self.active_kid = "v2"

    def sign(self, payload: dict) -> str:
        return jwt.encode(
            payload,
            self.keys[self.active_kid],
            algorithm="HS256",
            headers={"kid": self.active_kid},
        )

    def verify(self, token: str) -> dict:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if kid not in self.keys:
            raise ValueError(f"Unknown kid: {kid}")
        return jwt.decode(token, self.keys[kid], algorithms=["HS256"])

    def rotate(self, new_secret: str) -> None:
        """轮换：把当前密钥降级为 v(n-1)，新密钥设为 active。"""
        # 找到当前 active 的 kid 编号
        old_active = self.active_kid
        old_version = int(old_active.lstrip("v"))
        new_kid = f"v{old_version + 1}"

        # 删除最老的密钥（保留 N 个版本）
        oldest_kid = f"v{max(1, old_version - 1)}"
        self.keys.pop(oldest_kid, None)

        # 添加新密钥
        self.keys[new_kid] = new_secret
        self.active_kid = new_kid
```

### 2.3 常见错误：硬编码密钥到 git

```python
# ❌ 错误：硬编码到源码
SECRET_KEY = "super-secret-abc123"

# ✅ 正确：从环境变量读
SECRET_KEY = os.environ["DIFY_SECRET_KEY"]

# ✅ 更安全：从 secret 文件读（K8s Secret mount）
SECRET_KEY = open("/run/secrets/dify_secret").read().strip()
```

## 3. dify 仓库源码解读

### 3.1 KeySet：密钥轮换的核心

**文件位置**：`/Users/xu/code/github/dify/api/libs/jws.py`
**核心代码**（行 25-50）：

```python
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
- 第 5-10 行：`KeySet` 接受 `entries: dict[kid -> secret]`，**支持多版本密钥共存**
- 第 11 行：所有密钥都转成 `bytes` 防止类型不一致
- 第 16-21 行：从 `dify_config.SECRET_KEY`（环境变量）读取主密钥
- **关键设计**：`from_entries` 是预留接口，将来支持从 Vault 动态加载多密钥
- **空密钥检查**：启动时如果 SECRET_KEY 为空直接抛错（fail-fast）

### 3.2 配置入口：dify_config

**文件位置**：`/Users/xu/code/github/dify/api/configs/dify_config.py`
**核心代码**（典型结构）：

```python
from typing import Any
from pydantic import Field
from pydantic_settings import BaseSettings

class DifyConfig(BaseSettings):
    """所有配置从环境变量读，前缀 DIFY_。"""

    SECRET_KEY: str = Field(default="")
    DB_USERNAME: str = Field(default="postgres")
    DB_PASSWORD: str = Field(default="")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)

    # ... 几十个密钥字段

    class Config:
        env_prefix = "DIFY_"
        env_file = ".env"
```

**解读**：
- 第 6-13 行：所有密钥字段用 `pydantic.BaseSettings`，自动从环境变量读
- 第 15-17 行：环境变量前缀 `DIFY_`（如 `DIFY_SECRET_KEY`）
- 第 16 行：自动从 `.env` 文件加载（本地开发）
- **关键设计**：所有密钥集中在 `dify_config`，**业务代码用 `dify_config.SECRET_KEY`** 而非 `os.environ["..."]`

### 3.3 Provider API Key 加密存储

**文件位置**：`/Users/xu/code/github/dify/api/services/auth/api_key_auth_service.py`
**核心代码**（行 22-35）：

```python
    @staticmethod
    def create_provider_auth(tenant_id: str, args: dict[str, Any], *, session: Session):
        auth_result = ApiKeyAuthFactory(args["provider"], args["credentials"]).validate_credentials()
        if auth_result:
            # Encrypt the api key
            api_key = encrypter.encrypt_token(tenant_id, args["credentials"]["config"]["api_key"])
            args["credentials"]["config"]["api_key"] = api_key

            data_source_api_key_binding = DataSourceApiKeyAuthBinding(
                tenant_id=tenant_id, category=args["category"], provider=args["provider"]
            )
            data_source_api_key_binding.credentials = json.dumps(args["credentials"], ensure_ascii=False)
            session.add(data_source_api_key_binding)
            session.commit()
```

**解读**：
- 第 4 行：先用 `ApiKeyAuthFactory.validate_credentials()` 验证 Key 有效
- 第 6 行：用 `encrypter.encrypt_token(tenant_id, api_key)` **加密后**再存 DB
- 第 9-10 行：加密后的 Key + 其他凭证一起存到 DB
- **设计意图**：即使 DB 泄露，攻击者拿不到明文 API Key
- **tenant_id 派生密钥**：不同 tenant 用不同加密密钥（KDF 派生），跨租户攻击成本极高

## 4. 关键要点总结

- 密钥管理三铁律：**不硬编码、不提交 git、定期轮换**
- 环境变量是 dify 的主流方式（`dify_config` + `DIFY_` 前缀）
- **多版本密钥共存**：dify 的 `KeySet` 支持 `kid` 标识，轮换无需停服
- **第三方 API Key 加密存储**：`encrypter.encrypt_token(tenant_id, key)` 派生租户级密钥
- **fail-fast**：启动时缺密钥直接报错，不带病运行
- Vault / KMS 是高安全需求的可选升级路径

## 5. 练习题

### 练习 1：基础（必做）

用 `pydantic_settings.BaseSettings` 实现一个简化配置类，要求所有密钥字段从环境变量读（带 `MYAPP_` 前缀），缺密钥时启动报错。

### 练习 2：进阶

阅读 `api/libs/jws.py:25-50` 的 `KeySet`，设计一个 `rotate(new_secret)` 方法，支持 30 天自动轮换且保留 90 天的旧密钥用于验证。

### 练习 3：挑战（选做）

实现 **KMS 集成**：用 `boto3` 调用 AWS KMS 加密 / 解密 API Key，把加密结果存到 DB，业务代码通过统一接口调用。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/libs/jws.py`
- `/Users/xu/code/github/dify/api/configs/dify_config.py`
- `/Users/xu/code/github/dify/api/services/auth/api_key_auth_service.py`
- OWASP 密钥管理：https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html
- HashiCorp Vault：https://www.vaultproject.io/

---

**文档版本**：v1.0
**最后更新**：2026-07-13