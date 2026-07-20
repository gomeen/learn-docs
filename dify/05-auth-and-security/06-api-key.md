# 5.5.3 API Key 与 Secret 管理

> 理解 API Key 的设计原则，掌握 dify 的 API Key 体系。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 API Key 的核心设计原则（前缀 + 随机串）
- 理解 API Key 与 OAuth Token 的差异
- 能看懂 dify 中 API Key 的生成、存储、缓存机制
- 理解 API Key 与租户隔离的协同

## 📚 前置知识

- 密钥管理（详见 [密钥管理](../../_common/06-encryption/05-key-management.md)）
- 租户隔离（详见 [资源所有权与租户隔离](./01-resource-ownership.md)）
- JWT / OAuth 对比背景（详见 [JWT](../../_common/07-authentication/03-jwt.md)、[OAuth 2.0](../../_common/07-authentication/05-oauth2.md)）

## 1. 核心概念

### 1.1 API Key vs OAuth Token vs JWT

| 维度 | API Key | OAuth Token | JWT |
|------|---------|-------------|-----|
| 形态 | 随机字符串 | 不透明字符串 | 自包含 JSON |
| 用途 | 服务对服务 | 授权第三方 | 用户身份 |
| 撤销 | 删记录即可 | 删记录即可 | 等 exp |
| 寿命 | 长（可永久） | 中等 | 短 |
| 携带 | Header / Query | Header | Header |

> 📌 **Sighting**：Bearer / HTTP 认证头语义见 [HTTP 认证基础](../../_common/07-authentication/01-http-auth.md)；JWT 结构与无状态见 [JWT](../../_common/07-authentication/03-jwt.md)。

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

应用 API Key 由 dify 自己签发，数据源 API Key 由用户手动填入（dify 加密存储；哈希与对称加密详见 [哈希算法](../../_common/06-encryption/03-hash.md)、[对称加密](../../_common/06-encryption/01-symmetric.md)）。

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

## 3. 关键要点总结

- API Key 设计：**可识别前缀 + 高熵随机 + DB 唯一约束**
- dify 应用 Key 格式：`app-` / `ds-` 前缀 + 24 字符随机串
- 每个 app 最多 **10 个 Key**，超出 400
- 三层索引：`app_id` / `token` / `tenant_id` 复合索引
- 第三方 Key **加密存 DB**（按 tenant 派生密钥）
- API Key 应通过 `Authorization: Bearer` 传递，不要进 URL

---

**文档版本**：v1.0
**最后更新**：2026-07-13
