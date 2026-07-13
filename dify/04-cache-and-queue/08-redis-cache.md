# 4.2.1 Redis 作为缓存：缓存策略与失效

> Redis 最常见的用途是缓存——但如何保证缓存与数据库的一致性是核心难点。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Cache-Aside、Read-Through、Write-Through 三种缓存策略
- 掌握缓存失效的几种模式（TTL、主动失效、延迟双删）
- 在 dify 中识别缓存的使用位置
- 解决缓存与数据库不一致问题

## 📚 前置知识

- Redis 基础
- 关系数据库事务
- 01-redis-data-structures.md、07-redis-py.md

## 1. 核心概念

### 1.1 为什么需要缓存？

数据库查询通常 10-100ms，Redis 查询通常 < 1ms。**缓存把热数据放在内存**，减少数据库压力。

### 1.2 Cache-Aside（旁路缓存，最常用）

```
读流程：
1. 先查 Redis
2. 命中 → 返回
3. 未命中 → 查数据库 → 写 Redis → 返回

写流程：
1. 写数据库
2. 删除 Redis 缓存（不是更新！）
```

**为什么是"删除"而不是"更新"**：
- 更新缓存可能引入并发问题（A 写缓存、B 读旧值再覆盖）
- "先更新 DB 再删缓存"是最简单的实现，失效留给下次读

### 1.3 Read-Through / Write-Through

缓存服务作为代理，**应用层不直接操作数据库**：

```
读：App → Cache → (miss) → DB → Cache → App
写：App → Cache → DB
```

**优点**：对应用透明。**缺点**：实现复杂。

### 1.4 Write-Behind（异步写回）

```
写：App → Cache → (异步) → DB
```

**优点**：写性能极高。**缺点**：可能丢数据（Cache 挂了 DB 还没写）。

### 1.5 缓存失效模式

| 模式 | 说明 |
|------|------|
| TTL 过期 | `SETEX k 60 v`，60 秒后自动失效 |
| 主动删除 | 写 DB 时同步删缓存 |
| 延迟双删 | 写 DB → 删缓存 → 延时 500ms → 再删一次 |
| 异步失效 | 消息队列通知其他节点删缓存 |
| 版本号 | 缓存带版本，写时版本+1，读时判断 |

### 1.6 缓存预热

服务启动时**主动加载热数据**到缓存，避免冷启动时数据库被打爆。

```python
def warm_up():
    hot_keys = ["config:site", "config:pricing", "feature:flags"]
    for key in hot_keys:
        cache.set(key, db.get(key), ttl=3600)
```

## 2. 代码示例

### 2.1 Cache-Aside 模式

```python
import redis
import json

r = redis.Redis(decode_responses=True)

def get_user(user_id: int) -> dict:
    cache_key = f"user:{user_id}"

    # 1. 先查缓存
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)

    # 2. 缓存未命中，查数据库
    user = db.query("SELECT * FROM users WHERE id = %s", user_id)

    # 3. 写缓存（设置 TTL）
    r.setex(cache_key, 300, json.dumps(user))
    return user

def update_user(user_id: int, data: dict):
    db.execute("UPDATE users SET ... WHERE id = %s", user_id, data)
    # 删缓存（不是更新！）
    r.delete(f"user:{user_id}")
```

### 2.2 延迟双删（解决主从同步延迟）

```python
import time

def update_user_safe(user_id: int, data: dict):
    # 第一次删除
    r.delete(f"user:{user_id}")

    # 写数据库
    db.execute("UPDATE users SET ... WHERE id = %s", user_id, data)

    # 延迟再删一次（等待主从同步）
    time.sleep(0.5)
    r.delete(f"user:{user_id}")
```

### 2.3 批量预热

```python
def warm_up_cache():
    """服务启动时预热热数据"""
    hot_data = db.query("SELECT * FROM config WHERE hot = 1")
    pipe = r.pipeline()
    for row in hot_data:
        key = f"config:{row.key}"
        pipe.setex(key, 3600, json.dumps(row.value))
    pipe.execute()
    print(f"Warmed up {len(hot_data)} keys")
```

### 2.4 常见错误：缓存击穿（热点 key 失效）

```python
# ❌ 错误：热点 key 失效瞬间，大量请求穿透到 DB
def get_hot_item():
    item = r.get("hot:item:1")
    if not item:
        # 1000 个并发请求同时查 DB
        item = db.query("SELECT * FROM items WHERE id = 1")
        r.setex("hot:item:1", 60, json.dumps(item))
    return item

# ✅ 正确：分布式锁防止击穿
def get_hot_item_safe():
    item = r.get("hot:item:1")
    if not item:
        lock = r.lock("lock:hot:item:1", timeout=10)
        if lock.acquire(blocking=False):
            try:
                item = db.query("SELECT * FROM items WHERE id = 1")
                r.setex("hot:item:1", 60, json.dumps(item))
            finally:
                lock.release()
        else:
            # 没抢到锁，等一会重试
            time.sleep(0.1)
            return get_hot_item_safe()
    return item
```

## 3. dify 仓库源码解读

### 3.1 Redis 用作 Session 存储

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 269-274）：

```python
@staticmethod
def _store_refresh_token(refresh_token: str, account_id: str):
    redis_client.setex(AccountService._get_refresh_token_key(refresh_token), REFRESH_TOKEN_EXPIRY, account_id)
    redis_client.setex(
        AccountService._get_account_refresh_token_key(account_id), REFRESH_TOKEN_EXPIRY, refresh_token
    )
```

**解读**：
- dify 用 Redis 存 **refresh token**，而不是数据库
- **为什么用 Redis**：
  - token 生命周期短（`REFRESH_TOKEN_EXPIRY`，通常几天）
  - 需要快速读写（每个请求都查）
  - 过期自动清理（TTL 到期）
- **双向索引**：refresh_token → account_id，account_id → refresh_token（用于撤销）
- **失效模式**：登出时主动 `delete`，过期由 Redis 自动清理

### 3.2 Account 最后活跃时间缓存

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 239-249）：

```python
@staticmethod
@redis_fallback(default_return=True)
def _should_refresh_account_last_active(account_id: str) -> bool:
    return bool(
        redis_client.set(
            AccountService._get_account_last_active_refresh_key(account_id),
            1,
            ex=int(ACCOUNT_LAST_ACTIVE_REFRESH_INTERVAL.total_seconds()),
            nx=True,
        )
    )
```

**解读**：
- 用 `SET ... NX EX 60` 实现**分布式防抖**：每个账户的 `last_active_at` 60 秒内最多更新一次
- `NX=True`：仅当 key 不存在时设置（原子操作）
- `EX=60`：60 秒后自动过期
- **返回 True**：本次成功抢到锁，需要更新 DB
- **返回 False**：60 秒内已更新过，跳过
- **避免缓存一致性问题**：DB 是真实源，Redis 只用于"防抖"决策，不存数据

### 3.3 限流计数缓存

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 1052-1060）：

```python
@staticmethod
@redis_fallback(default_return=None)
def add_login_error_rate_limit(email: str):
    key = f"login_error_rate_limit:{email}"
    count = redis_client.get(key)
    if count is None:
        count = 0
    count = int(count) + 1
    redis_client.setex(key, dify_config.LOGIN_LOCKOUT_DURATION, count)
```

**解读**：
- 登录失败次数缓存在 Redis，TTL = `LOGIN_LOCKOUT_DURATION`（如 10 分钟）
- 这是典型的"**TTL 失效**"模式
- **缓存内容**：失败的**计数**（不是数据）
- **数据源**：失败次数本身（不需要其他存储）
- **一致性**：高，因为只有 Redis 计数，没数据库参考

## 4. 关键要点总结

- **Cache-Aside** 是最常用的缓存模式：读先查缓存，写 DB 后删缓存
- 缓存失效模式：TTL（自动）、主动删除（写后删）、延迟双删（解决主从延迟）
- 缓存预热避免冷启动击穿
- **热点 key** 需要分布式锁防击穿
- dify 用 Redis 存 **token**（TTL 短）、**防抖标志**（NX EX）、**限流计数**（TTL）
- `redis_fallback` 保证 Redis 故障时业务降级（读 DB、跳过限流等）

## 5. 练习题

### 练习 1：基础（必做）

用 Cache-Aside 模式实现一个商品缓存：
- 第一次查询查 DB 并缓存
- 更新商品时删缓存

```python
def get_product(product_id):
    # TODO
    pass

def update_product(product_id, data):
    # TODO
    pass
```

### 练习 2：进阶

用 `SETNX` 实现一个**分布式防抖器**：同一用户在 5 秒内多次调用某接口只执行一次。

### 练习 3：挑战（选做）

阅读 `services/account_service.py` 的登录限流实现，把 `GET + SETEX` 改为 **Lua 脚本** 实现原子操作。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/services/account_service.py`（第 239-274、1052-1060 行）
- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- Redis 缓存设计：https://redis.io/docs/manual/client-side-caching/
- 缓存模式经典论文：https://docs.microsoft.com/en-us/azure/architecture/patterns/cache-aside

---

**文档版本**：v1.0
**最后更新**：2026-07-13