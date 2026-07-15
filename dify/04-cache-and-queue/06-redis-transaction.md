# 4.1.6 Redis 事务与 Lua 脚本

> Redis 事务（`MULTI/EXEC`）和 Lua 脚本是保证原子性的两种机制，Lua 更强大，能实现复杂业务逻辑。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Redis 事务的 ACID 特性（其实只支持部分）
- 掌握 `MULTI/EXEC` 和 Pipeline 的区别
- 用 Lua 脚本实现"读-改-写"原子操作
- 在 dify 中用 Lua 实现分布式限流等场景

## 📚 前置知识

- Redis 基础命令（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）

## 1. 核心概念

### 1.1 Redis 事务 vs 关系数据库事务

| 特性 | Redis 事务 | SQL 事务 |
|------|-----------|----------|
| 原子性 | ✅ 命令打包执行 | ✅ |
| 一致性 | ❌（不支持回滚）| ✅ |
| 隔离性 | ✅（串行执行）| ✅ |
| 持久性 | 取决于持久化策略（详见 [Redis 持久化](../../_common/01-redis/02-persistence.md)） | ✅ |
| 回滚 | ❌ 不支持 | ✅ |

**Redis 事务的"原子性"是"打包执行"而非"全部成功"**——如果中间命令失败，后续命令仍会执行。

### 1.2 MULTI/EXEC 命令

```bash
MULTI
SET key1 value1
INCR counter
SET key2 value2
EXEC  # 一次性执行所有命令
```

- **MULTI**：标记事务开始，返回 `OK`
- **EXEC**：执行队列中所有命令
- **DISCARD**：放弃事务
- **WATCH**：乐观锁（监控 key，被修改则事务失败）

### 1.3 Pipeline：批量发送

Pipeline 不是事务，只是把多条命令**一次发送、一次接收**，减少网络 RTT：

```python
pipe = r.pipeline(transaction=False)  # 不开启 MULTI/EXEC
pipe.set("k1", "v1")
pipe.get("k2")
results = pipe.execute()  # 批量发送
```

**Pipeline vs 事务**：
- Pipeline：性能优化，**不保证原子**
- 事务：原子执行（但仍可能部分失败）

### 1.4 Lua 脚本：真正的原子性

Redis 4.0+ 提供 `EVAL` 和 `EVALSHA`，Lua 脚本在 Redis **单线程**内执行，整个脚本是一个原子操作。

```bash
EVAL "return redis.call('GET', KEYS[1])" 1 mykey
```

**优势**：
1. **原子性**：脚本执行期间不会有其他命令插入
2. **减少网络往返**：复杂逻辑在服务端完成
3. **可复用**：`EVALSHA` 用 SHA1 缓存脚本

### 1.5 Lua 脚本：限流示例

> 📌 **Sighting**：限流算法（固定窗口 / 滑动窗口 / 令牌桶）完整原理见 [限流算法](../../_common/03-cache-patterns/04-rate-limiting.md)；此处只演示用 Lua 保证「读-改-写」原子性。

```lua
-- KEYS[1] = 限流 key
-- ARGV[1] = 限制次数
-- ARGV[2] = 时间窗口（秒）
local current = redis.call("INCR", KEYS[1])
if current == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[2])
end
if current > tonumber(ARGV[1]) then
    return 0  -- 拒绝
end
return 1  -- 允许
```

调用：
```python
script = """
local current = redis.call("INCR", KEYS[1])
if current == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[2])
end
if current > tonumber(ARGV[1]) then
    return 0
end
return 1
"""
result = r.eval(script, 1, "rate:user:1", 10, 60)
```

## 2. 代码示例

### 2.1 基础事务

```python
import redis

r = redis.Redis(decode_responses=True)

# MULTI/EXEC 事务
pipe = r.pipeline(transaction=True)
pipe.set("user:1:name", "Alice")
pipe.set("user:1:age", 30)
pipe.incr("counter")
results = pipe.execute()  # [True, True, 1]
```

### 2.2 WATCH 实现乐观锁

```python
def transfer_money(r, from_user, to_user, amount):
    """转账：使用 WATCH 实现乐观锁"""
    with r.pipeline() as pipe:
        while True:
            try:
                pipe.watch(from_user)  # 监控余额 key
                balance = r.get(from_user)
                if int(balance) < amount:
                    pipe.unwatch()
                    return False

                pipe.multi()
                pipe.decrby(from_user, amount)
                pipe.incrby(to_user, amount)
                pipe.execute()
                return True
            except redis.WatchError:
                # 余额被其他客户端修改，重试
                continue
```

### 2.3 Lua 脚本实现滑动窗口限流

```python
# 滑动窗口限流（精确）
script = """
-- KEYS[1] = sorted set key
-- ARGV[1] = 当前时间戳（毫秒）
-- ARGV[2] = 窗口大小（毫秒）
-- ARGV[3] = 限制次数
-- ARGV[4] = 请求唯一 ID
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local request_id = ARGV[4]

-- 删除窗口外的旧记录
redis.call("ZREMRANGEBYSCORE", key, 0, now - window)

-- 统计当前窗口内的请求数
local count = redis.call("ZCARD", key)
if count >= limit then
    return 0  -- 拒绝
end

-- 添加当前请求
redis.call("ZADD", key, now, request_id)
redis.call("PEXPIRE", key, window)
return 1  -- 允许
"""

# 注册脚本（自动用 EVALSHA 优化）
limit_script = r.register_script(script)

for i in range(15):
    result = limit_script(
        keys=["rate:user:1"],
        args=[int(time.time() * 1000), 60000, 10, f"req-{i}"],
    )
    print(f"request {i}: {'allow' if result else 'deny'}")
```

### 2.4 常见错误：事务中用 SELECT 命令

```python
# ❌ 错误：SELECT 不能在 MULTI/EXEC 中执行
pipe = r.pipeline()
pipe.select(1)  # 错误！EXEC 时报错
pipe.set("key", "value")
pipe.execute()
```

## 3. dify 仓库源码解读

### 3.1 Redis Pipeline 在 dify 中的使用

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 214-215）：

```python
def pipeline(self, transaction: bool = True, shard_hint: str | None = None) -> Any:
    return self._require_client().pipeline(transaction=transaction, shard_hint=shard_hint)
```

**解读**：
- dify 的 `redis_client.pipeline()` 默认 `transaction=True`（开启 MULTI/EXEC）
- `shard_hint` 用于 Cluster 模式，提示 Pipeline 中的 key 都在同一节点，减少重定向
- 业务代码可以这样用：
  ```python
  with redis_client.pipeline() as pipe:
      pipe.hset("user:1", "name", "Alice")
      pipe.incr("counter")
      results = pipe.execute()
  ```

### 3.2 Lua 脚本未在 dify 中大量使用

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
- dify 的限流用 **GET + SETEX**，**非原子**（高并发下可能少计）
- **改进空间**：改用 Lua 脚本保证 `GET + INCR + EXPIRE` 原子性：
  ```lua
  local count = redis.call("INCR", KEYS[1])
  if count == 1 then
      redis.call("EXPIRE", KEYS[1], ARGV[1])
  end
  return count
  ```
- 这是一个**潜在优化点**，但当前实现简单可读，业务影响小

### 3.3 Redis 错误处理

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 488-494）：

```python
def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | T | None:
    try:
        return func(*args, **kwargs)
    except RedisError as e:
        func_name = getattr(func, "__name__", "Unknown")
        logger.warning("Redis operation failed in %s: %s", func_name, str(e), exc_info=True)
        return default_return
```

**解读**：
- `RedisError` 是基类，捕获所有 Redis 异常（包括连接错误、OOM、语法错误）
- **不区分错误类型**：所有错误一律降级返回默认值
- **缺点**：可能掩盖真实的 bug（如 Lua 脚本语法错误），建议生产环境加监控告警

## 4. 关键要点总结

- Redis 事务 `MULTI/EXEC` 只保证"打包执行"，**不支持回滚**
- Pipeline 是性能优化（批量网络请求），不保证原子
- **Lua 脚本**才是真正的原子操作，适合限流、计数器等场景
- `EVALSHA` 缓存脚本减少网络传输
- dify 当前主要用 GET+SETEX 实现限流，可优化为 Lua 脚本

## 5. 练习题

### 练习 1：基础（必做）

用 `r.pipeline()` 实现批量写入 1000 个 key，并对比 Pipeline vs 单独写入的性能差异。

### 练习 2：进阶

用 Lua 脚本实现一个**令牌桶限流器**：
- 每秒补充 N 个令牌
- 桶容量 M
- 请求消耗 1 个令牌

### 练习 3：挑战（选做）

阅读 `redis-py` 的 `register_script` 实现，理解它如何用 `EVALSHA` + 自动降级到 `EVAL` 保证脚本执行。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`（第 214-215、488-494 行）
- `/Users/xu/code/github/dify/api/services/account_service.py`（第 1052-1060 行）
- Redis 事务文档：https://redis.io/docs/interact/transactions/
- Redis Lua 文档：https://redis.io/docs/interact/programmability/eval-intro/

---

**文档版本**：v1.0
**最后更新**：2026-07-13