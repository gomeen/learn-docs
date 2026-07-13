# 5.5.3 API Key 与 Secret 管理

> 理解 API Key 的设计原则，掌握 dify 的 API Key 体系。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 API Key 的核心设计原则（前缀 + 随机串）
- 理解 API Key 与 OAuth Token 的差异
- 能看懂 dify 中 API Key 的生成、存储、缓存机制
- 理解 API Key 与租户隔离的协同

## 📚 前置知识

- 25-key-management.md
- 11-resource-ownership.md
- 03-jwt-auth.md

## 1. 核心概念

### 1.1 API Key vs OAuth Token vs JWT

| 维度 | API Key | OAuth Token | JWT |
|------|---------|-------------|-----|
| 形态 | 随机字符串 | 不透明字符串 | 自包含 JSON |
| 用途 | 服务对服务 | 授权第三方 | 用户身份 |
| 撤销 | 删记录即可 | 删记录即可 | 等 exp |
| 寿命 | 长（可永久） | 中等 | 短 |
| 携带 | Header / Query | Header | Header |

### 1.2 API Key 设计原则

1. **可识别前缀**：区分用途（如 `app-`、`sk-`、`pk-`）
2. **足够随机**：至少 24 字节（128 位），防暴力
3. **不携带信息**：纯随机串，泄露即换
4. **租户绑定**：每条 Key 都属于某个 tenant

### 1.3 dify 的 API Key 体系

dify 区分两种 API Key：

| 类型 | 前缀 | 用途 |
|------|------|------|
| 应用 API Key | `app-` | 调用 dify 应用（开发者） |
| 数据源 API Key | 内部存 | 第三方平台（Notion 等） |

应用 API Key 由 dify 自己签发，数据源 API Key 由用户手动填入（dify 加密存储）。

## 2. 代码示例

### 2.1 API Key 生成（带前缀）

```python
import secrets
import string

def generate_api_key(prefix: str = "app", length: int = 24) -> str:
    """生成带前缀的 API Key。

    格式：{prefix}-{base62 随机串}
    例：app-X7bK2p9mQwRtYvN3jL5fH8cG
    """
    alphabet = string.ascii_letters + string.digits  # a-zA-Z0-9
    random_part = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}-{random_part}"


# 使用
print(generate_api_key("app"))  # app-X7bK2p9mQwRtYvN3jL5fH8cG
print(generate_api_key("sk"))   # sk-A2bC3dE4fG5hI6jK7lM8nO9p
```

### 2.2 API Key 校验（防时序攻击）

```python
import hmac

def verify_api_key(provided: str, stored_hash: bytes) -> bool:
    """恒定时间比较 API Key。"""
    expected_hash = hash_api_key(stored_hash)
    return hmac.compare_digest(provided.encode(), expected_hash)


def hash_api_key(key: str) -> bytes:
    """对 API Key 做哈希存 DB（避免明文存储）。"""
    import hashlib
    return hashlib.sha256(key.encode()).digest()
```

### 2.3 常见错误：API Key 泄露到 URL

```python
# ❌ 错误：API Key 放在 URL（会进日志）
requests.get(f"https://api.example.com/data?api_key={API_KEY}")

# ✅ 正确：API Key 放在 Header
requests.get("https://api.example.com/data",
             headers={"Authorization": f"Bearer {API_KEY}"})
```

## 3. dify 仓库源码解读

### 3.1 API Key 模型定义

**文件位置**：`/Users/xu/code/github/dify/api/models/model.py`
**核心代码**（行 2236-2259）：

```python
class ApiToken(Base):  # bug: this uses setattr so idk the field.
    __tablename__ = "api_tokens"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="api_token_pkey"),
        sa.Index("api_token_app_id_type_idx", "app_id", "type"),
        sa.Index("api_token_token_idx", "token", "type"),
        sa.Index("api_token_tenant_idx", "tenant_id", "type"),
    )

    id = mapped_column(StringUUID, default=lambda: str(uuid4()))
    app_id = mapped_column(StringUUID, nullable=True)
    tenant_id = mapped_column(StringUUID, nullable=True)
    type: Mapped[ApiTokenType] = mapped_column(EnumText(ApiTokenType, length=16), nullable=False)
    token: Mapped[str] = mapped_column(String(255), nullable=False)
    last_used_at = mapped_column(sa.Date, nullable=True)
    created_at = mapped_column(sa.DateTime, nullable=False, server_default=func.current_timestamp())

    @staticmethod
    def generate_api_key(prefix: str, n: int) -> str:
        while True:
            result = prefix + generate_string(n)
            if db.session.scalar(select(exists().where(ApiToken.token == result))):
                continue
            return result
```

**解读**：
- 第 4-7 行：**三个复合索引** —— 按 app_id、token、tenant_id 都能快速查询
- 第 11 行：`tenant_id` 字段必填（多租户隔离）
- 第 12 行：`type` 字段区分 APP / DATASET 等不同 Key 类型
- 第 13 行：`token` 字段最长 255 字符
- 第 14 行：`last_used_at` 用于监控和审计
- 第 19-25 行：生成 API Key 的核心逻辑
  - 第 20 行：`prefix + generate_string(n)` 拼成完整 Key
  - 第 21-22 行：**唯一性检查**：DB 查重，碰撞则重试
  - **设计意图**：高熵随机 + DB 唯一性约束，碰撞概率极低

### 3.2 API Key 创建流程

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/apikey.py`
**核心代码**（行 96-124）：

```python
    def _create_api_key(self, resource_id: str, current_tenant_id: str) -> ApiToken:
        assert self.resource_id_field is not None, "resource_id_field must be set"
        _get_resource(resource_id, current_tenant_id, self.resource_model)
        current_key_count: int = (
            db.session.scalar(
                select(func.count(ApiToken.id)).where(
                    ApiToken.type == self.resource_type, getattr(ApiToken, self.resource_id_field) == resource_id
                )
            )
            or 0
        )

        if current_key_count >= self.max_keys:
            flask_restx.abort(
                HTTPStatus.BAD_REQUEST,
                message=f"Cannot create more than {self.max_keys} API keys for this resource type.",
                custom="max_keys_exceeded",
            )

        key = ApiToken.generate_api_key(self.token_prefix or "", 24)
        assert self.resource_type is not None, "resource_type must be set"
        api_token = ApiToken()
        setattr(api_token, self.resource_id_field, resource_id)
        api_token.tenant_id = current_tenant_id
        api_token.token = key
        api_token.type = self.resource_type
        db.session.add(api_token)
        db.session.commit()
        return api_token
```

**解读**：
- 第 3 行：`_get_resource` 校验资源存在 + 租户隔离（带 tenant_id）
- 第 4-10 行：统计当前 Key 数量
- 第 12-17 行：**最多 10 个 Key 限制**（`max_keys = 10`），超出 400
- 第 19 行：`ApiToken.generate_api_key(prefix, 24)` 生成 Key
- 第 20-23 行：填充 ORM 对象的字段
- **关联**：父类 `BaseApiKeyListResource.max_keys = 10`，每个 app 最多 10 个 Key

### 3.3 数据源 API Key 加密存储

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
- 第 3 行：先**验证**第三方 Key 有效
- 第 5 行：用 `encrypter.encrypt_token(tenant_id, api_key)` **加密**（按 tenant 派生密钥）
- 第 6 行：替换明文为密文
- 第 8-10 行：构造 `DataSourceApiKeyAuthBinding` 对象（含 tenant_id）
- **设计意图**：第三方 Key 加密存 DB，按 tenant 隔离加密密钥

## 4. 关键要点总结

- API Key 设计：**可识别前缀 + 高熵随机 + DB 唯一约束**
- dify 应用 Key 格式：`app-` / `ds-` 前缀 + 24 字符随机串
- 每个 app 最多 **10 个 Key**，超出 400
- 三层索引：`app_id` / `token` / `tenant_id` 复合索引
- 第三方 Key **加密存 DB**（按 tenant 派生密钥）
- API Key 应通过 `Authorization: Bearer` 传递，不要进 URL

## 5. 练习题

### 练习 1：基础（必做）

写一个 `generate_api_key(prefix, length)` 函数，前缀 + 24 位 base62 随机串；用 DB 唯一约束验证不会重复（模拟 100 万次生成）。

### 练习 2：进阶

阅读 `api/models/model.py:2236-2259`，解释 dify 的 API Key 为什么要带 `tenant_id` 字段？删除 Key 时是否需要连带处理 `last_used_at` 等审计字段？

### 练习 3：挑战（选做）

设计一个 **Key 轮换机制**：每 90 天自动作废旧 Key，提前 7 天通知用户新建 Key；过渡期 30 天内新旧 Key 都可用。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/models/model.py`
- `/Users/xu/code/github/dify/api/controllers/console/apikey.py`
- `/Users/xu/code/github/dify/api/services/auth/api_key_auth_service.py`
- Stripe API Key 设计：https://stripe.com/docs/keys
- GitHub PAT 设计：https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens

---

**文档版本**：v1.0
**最后更新**：2026-07-13