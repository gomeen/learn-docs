# 5.5.4 dify 的 API Key 体系分析

> 端到端解析 dify 的 API Key 体系：生成、存储、缓存、验证、撤销全链路。

## 🎯 学习目标

完成本文档后，你将能够：
- 完整画出 dify API Key 的生命周期
- 理解 ApiTokenCache（Redis 缓存）的设计意图
- 掌握删除 Key 时的缓存清理流程
- 能在 dify 中追溯一次 API Key 调用的完整路径

## 📚 前置知识

- API Key 设计原则（详见 [API Key 与 Secret 管理](./06-api-key.md)）
- 缓存策略（详见 [缓存策略](../../_common/03-cache-patterns/01-strategies.md)；dify Redis 场景见 [Redis in dify](../04-cache-and-queue/01-redis-in-dify.md)）
- 租户隔离（详见 [资源所有权与租户隔离](./01-resource-ownership.md)）

## 1. 核心概念

### 1.1 API Key 生命周期

```
1. 用户在控制台创建 Key
   ↓
2. 服务端生成（prefix + 24字符随机）+ 写入 DB（api_tokens 表）
   ↓
3. 返回明文 Key 给用户（仅一次！之后无法查看）
   ↓
4. 用户保存 Key，调用 dify API 时携带
   ↓
5. 服务端从 Redis 缓存查（命中）/ 从 DB 查（未命中）
   ↓
6. 验证 Key + tenant_id + 资源匹配
   ↓
7. 更新 last_used_at（审计）
   ↓
8. 用户在控制台删除 Key → 缓存清理 + DB 删除
```

### 1.2 dify 的双层 Key 设计

dify 区分两类 API Key：

| 类型 | 存储位置 | 缓存策略 | 撤销 |
|------|---------|---------|------|
| 应用 API Key（`ApiToken`） | DB 明文 + Redis 缓存 | DB-first + Redis 二级缓存 | 删 DB + 清缓存 |
| 数据源 API Key | DB 加密 + 不缓存 | 直接查 DB | 删 DB |

> 数据源 Key 的「加密存储」依赖对称加密与密钥管理（详见 [对称加密](../../_common/06-encryption/01-symmetric.md)、[密钥管理](../../_common/06-encryption/05-key-management.md)）。

### 1.3 ApiTokenCache 的设计

```
请求进来 → Redis 查 Key → 命中：直接放行
                          → 未命中：DB 查 + 写 Redis

删除 Key → DB 删 + Redis 清（先清缓存后删 DB，避免 stale cache）
```

> 先清缓存再删 DB 是为了降低缓存与库不一致窗口；缓存三大问题背景见 [缓存三大问题](../../_common/03-cache-patterns/02-three-problems.md)。

## 2. 代码示例

### 2.1 简化的 ApiTokenCache

```python
class ApiTokenCache:
    """Redis 缓存层，DB 是 source of truth。"""

    def __init__(self, redis_client, ttl_seconds: int = 300):
        self.redis = redis_client
        self.ttl = ttl_seconds

    def _make_key(self, token: str, scope: str | None) -> str:
        return f"api_token:{scope or 'any'}:{token}"

    def get(self, token: str, scope: str | None) -> dict | None:
        """查缓存，未命中返回 None。"""
        data = self.redis.get(self._make_key(token, scope))
        return json.loads(data) if data else None

    def set(self, token: str, scope: str | None, payload: dict) -> None:
        """写缓存，TTL 防止长期堆积。"""
        self.redis.setex(
            self._make_key(token, scope),
            self.ttl,
            json.dumps(payload),
        )

    def delete(self, token: str, scope: str | None) -> None:
        """删缓存（删除 Key 时调用）。"""
        self.redis.delete(self._make_key(token, scope))


# 使用
cache = ApiTokenCache(redis_client)

# 校验 Key
payload = cache.get(token, scope="app")
if payload is None:
    payload = db.session.scalar(select(ApiToken).where(ApiToken.token == token))
    if payload:
        cache.set(token, scope="app", payload=payload.to_dict())
if payload is None:
    raise Unauthorized()
```

### 2.2 常见错误：先删 DB 再清缓存

```python
# ❌ 错误：先删 DB 再清缓存（中间窗口期有 stale cache）
db.session.delete(api_token)
db.session.commit()
cache.delete(token, scope)  # 缓存可能已被新请求回填

# ✅ 正确：先清缓存再删 DB
cache.delete(token, scope)
db.session.delete(api_token)
db.session.commit()
```

## 3. 关键要点总结

- dify API Key = **应用 Key（明文存 DB + Redis 缓存）** + **数据源 Key（加密存 DB）**
- **生成**：前缀 + 24 字符随机 + DB 唯一约束
- **存储**：DB 主存储 + Redis 二级缓存（5 分钟 TTL）
- **查询**：缓存命中走缓存，未命中走 DB + 回填缓存
- **删除**：**先清缓存再删 DB**（关键顺序，避免 stale cache）
- **租户隔离**：所有查询都通过 `_get_resource` 带 tenant_id 过滤
- **限额**：每个 resource 最多 10 个 Key

---

**文档版本**：v1.0
**最后更新**：2026-07-13
