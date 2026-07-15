# 5.5.4 dify 的 API Key 体系分析

> 端到端解析 dify 的 API Key 体系：生成、存储、缓存、验证、撤销全链路。

## 🎯 学习目标

完成本文档后，你将能够：
- 完整画出 dify API Key 的生命周期
- 理解 ApiTokenCache（Redis 缓存）的设计意图
- 掌握删除 Key 时的缓存清理流程
- 能在 dify 中追溯一次 API Key 调用的完整路径

## 📚 前置知识

- API Key 设计原则（详见 [API Key 与 Secret 管理](./28-api-key.md)）
- 缓存策略（详见 [缓存策略](../../_common/03-cache-patterns/01-strategies.md)；dify Redis 场景见 [Redis in dify](../04-cache-and-queue/13-redis-in-dify.md)）
- 租户隔离（详见 [资源所有权与租户隔离](./11-resource-ownership.md)）

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

## 3. dify 仓库源码解读

### 3.1 ApiTokenCache 完整实现

**文件位置**：`/Users/xu/code/github/dify/api/services/api_token_service.py`
**核心代码**（行 66-130）：

```python
class ApiTokenCache:
    """
    Redis cache wrapper for API tokens.
    Handles serialization, deserialization, and cache invalidation.
    """

    @staticmethod
    def make_active_key(token: str, scope: str | None = None) -> str:
        """Generate Redis key for recording token usage."""
        return f"{ACTIVE_TOKEN_KEY_PREFIX}{scope}:{token}"

    @staticmethod
    def _make_tenant_index_key(tenant_id: str) -> str:
        """Generate Redis key for tenant token index."""
        return f"tenant_tokens:{tenant_id}"

    @staticmethod
    def _make_cache_key(token: str, scope: str | None = None) -> str:
        """Generate cache key for the given token and scope."""
        scope_str = scope or "any"
        return f"{CACHE_KEY_PREFIX}:{scope_str}:{token}"

    @staticmethod
    def _serialize_token(api_token: Any) -> bytes:
        """Serialize ApiToken object to JSON bytes."""
        if isinstance(api_token, CachedApiToken):
            return api_token.model_dump_json().encode("utf-8")

        cached = CachedApiToken(
            id=str(api_token.id),
            app_id=str(api_token.app_id) if api_token.app_id else None,
            tenant_id=str(api_token.tenant_id) if api_token.tenant_id else None,
            type=api_token.type,
            token=api_token.token,
            last_used_at=api_token.last_used_at,
            created_at=api_token.created_at,
        )
        return cached.model_dump_json().encode("utf-8")

    @staticmethod
    @redis_fallback(default_return=None)
    def get(token: str, scope: str | None) -> Any | None:
        """Get API token from cache."""
        cache_key = ApiTokenCache._make_cache_key(token, scope)
        cached_data = redis_client.get(cache_key)

        if cached_data is None:
            logger.debug("Cache miss for token key: %s", cache_key)
            return None

        logger.debug("Cache hit for token key: %s", cache_key)
        return ApiTokenCache._deserialize_token(cached_data)
```

**解读**：
- 第 11-13 行：`_make_active_key` 用于记录 token 使用
- 第 15-17 行：`_make_tenant_index_key` 按租户建立索引，用于**批量失效**
- 第 19-22 行：`_make_cache_key` 按 token + scope 缓存
- 第 24-40 行：`_serialize_token` 把 ORM 对象转为 `CachedApiToken` Pydantic 模型，再 JSON 序列化
- 第 42-53 行：`get` 方法，先查缓存，未命中返 None，**`redis_fallback` 装饰器在 Redis 故障时降级**
- **设计意图**：缓存层有容错，Redis 挂了直接走 DB，不影响功能

### 3.2 删除 Key 时的缓存清理

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/apikey.py`
**核心代码**（行 140-172）：

```python
    def _delete_api_key(
        self,
        resource_id: str,
        api_key_id: str,
        current_tenant_id: str,
        current_user: Account,
    ) -> None:
        assert self.resource_id_field is not None, "resource_id_field must be set"
        _get_resource(resource_id, current_tenant_id, self.resource_model)

        if not dify_config.RBAC_ENABLED and not current_user.is_admin_or_owner:
            raise Forbidden()

        key = db.session.scalar(
            select(ApiToken)
            .where(
                getattr(ApiToken, self.resource_id_field) == resource_id,
                ApiToken.type == self.resource_type,
                ApiToken.id == api_key_id,
            )
            .limit(1)
        )

        if key is None:
            flask_restx.abort(HTTPStatus.NOT_FOUND, message="API key not found")

        # Invalidate cache before deleting from database
        # Type assertion: key is guaranteed to be non-None here because abort() raises
        assert key is not None  # nosec - for type checker only
        ApiTokenCache.delete(key.token, key.type)

        db.session.execute(delete(ApiToken).where(ApiToken.id == api_key_id))
        db.session.commit()
```

**解读**：
- 第 10-12 行：RBAC 未启用时，仅 admin/owner 能删除
- 第 14-21 行：DB 查询 Key（限定 resource + type + id）
- 第 23-24 行：Key 不存在 → 404
- 第 27 行：**关键**：`ApiTokenCache.delete(key.token, key.type)` —— **先清缓存再删 DB**
- 第 29-30 行：DB 删除
- **注释明确说明**："Invalidate cache before deleting from database"——避免删除窗口期有 stale cache

### 3.3 API Key 列表查询

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/apikey.py`
**核心代码**（行 81-90）：

```python
    def _get_api_key_list(self, resource_id: str, current_tenant_id: str) -> ApiKeyList:
        assert self.resource_id_field is not None, "resource_id_field must be set"

        _get_resource(resource_id, current_tenant_id, self.resource_model)
        keys = db.session.scalars(
            select(ApiToken).where(
                ApiToken.type == self.resource_type, getattr(ApiToken, self.resource_id_field) == resource_id
            )
        ).all()
        return ApiKeyList.model_validate({"data": keys}, from_attributes=True)
```

**解读**：
- 第 3 行：`_get_resource` 校验资源存在 + 租户隔离
- 第 4-9 行：查询当前 resource 下的所有 Key
- 第 10 行：转 Pydantic 模型返回
- **租户隔离**：通过 `_get_resource` 间接过滤，确保只看到当前租户的 Key

### 3.4 资源创建上限检查

**文件位置**：`/Users/xu/code/github/dify/api/controllers/console/apikey.py`
**核心代码**（行 108-114）：

```python
        if current_key_count >= self.max_keys:
            flask_restx.abort(
                HTTPStatus.BAD_REQUEST,
                message=f"Cannot create more than {self.max_keys} API keys for this resource type.",
                custom="max_keys_exceeded",
            )
```

**解读**：
- **max_keys = 10**：每个资源最多 10 个 Key
- 超限 → 400 + 自定义错误码 `max_keys_exceeded`
- **设计意图**：防滥用 + 简化管理（10 个 Key 足够）

## 4. 关键要点总结

- dify API Key = **应用 Key（明文存 DB + Redis 缓存）** + **数据源 Key（加密存 DB）**
- **生成**：前缀 + 24 字符随机 + DB 唯一约束
- **存储**：DB 主存储 + Redis 二级缓存（5 分钟 TTL）
- **查询**：缓存命中走缓存，未命中走 DB + 回填缓存
- **删除**：**先清缓存再删 DB**（关键顺序，避免 stale cache）
- **租户隔离**：所有查询都通过 `_get_resource` 带 tenant_id 过滤
- **限额**：每个 resource 最多 10 个 Key

## 5. 练习题

### 练习 1：基础（必做）

用 Redis 实现简化版 `ApiTokenCache`：支持 `get` / `set` / `delete` 方法，且 Redis 故障时降级到 None（不抛异常）。

### 练习 2：进阶

阅读 `api/controllers/console/apikey.py:140-172`，解释 dify 为什么"先清缓存再删 DB"？颠倒顺序会怎样？

### 练习 3：挑战（选做）

设计一个 **Key 使用监控**：每次 API 调用更新 `last_used_at`，并提供"近 30 天未使用的 Key 列表"接口（按 tenant 隔离）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/api_token_service.py`
- `/Users/xu/code/github/dify/api/controllers/console/apikey.py`
- `/Users/xu/code/github/dify/api/models/model.py`
- `/Users/xu/code/github/dify/api/services/auth/api_key_auth_service.py`
- Redis 缓存模式：https://redis.io/docs/manual/client-side-caching/

---

**文档版本**：v1.0
**最后更新**：2026-07-13