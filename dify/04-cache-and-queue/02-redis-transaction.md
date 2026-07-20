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

## 3. 关键要点总结

- Redis 事务 `MULTI/EXEC` 只保证"打包执行"，**不支持回滚**
- Pipeline 是性能优化（批量网络请求），不保证原子
- **Lua 脚本**才是真正的原子操作，适合限流、计数器等场景
- `EVALSHA` 缓存脚本减少网络传输
- dify 当前主要用 GET+SETEX 实现限流，可优化为 Lua 脚本

---

**文档版本**：v1.0
**最后更新**：2026-07-13
