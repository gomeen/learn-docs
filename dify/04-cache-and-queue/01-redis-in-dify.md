# 4.2.6 dify 中 Redis 的使用场景分析

> Redis 在 dify 中扮演多重角色：缓存、限流、Session、Pub/Sub、分布式锁……理解这些场景是掌握 dify 后端的关键。

## 🎯 学习目标

完成本文档后，你将能够：
- 全面了解 dify 中 Redis 的所有使用场景
- 通过 `grep` 工具自行发现 Redis 使用点
- 理解 dify 如何设计 Redis key 命名空间
- 区分"必须 Redis"和"可选 Redis"的场景

## 📚 前置知识

- Redis 基础（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）
- 缓存策略（详见 [缓存策略](../../_common/03-cache-patterns/01-strategies.md)）
- dify 整体架构
- [Celery 架构](./05-celery-architecture.md)（Broker / Backend 角色）

## 1. 核心概念

### 1.1 dify 中 Redis 的角色

dify 后端的 Redis **不是单一用途**，它承担：

```
                  ┌── Celery Broker（任务队列）
                  │
                  ├── Celery Result Backend（任务结果）
                  │
Redis in dify ────┼── 业务缓存（配置、token、限流计数）
                  │
                  ├── Session / Token 存储
                  │
                  ├── Pub/Sub（实时事件）
                  │
                  └── 分布式锁 / 协调
```

> 📌 **Sighting**（本篇只列场景，不展开原理）：
> - 限流计数 → [限流算法](../../_common/03-cache-patterns/04-rate-limiting.md)
> - Session / Token 存储 → [分布式 Session](../../_common/03-cache-patterns/05-distributed-session.md)、[Session 与 Cookie](../../_common/07-authentication/02-session-cookie.md)
> - Pub/Sub → [Redis Pub/Sub 与 Stream](../../_common/01-redis/06-pubsub-stream.md)
> - 分布式锁 → [Redis 分布式锁](../../_common/04-distributed-locks/02-redis-redlock.md)

### 1.2 Redis 不可用时的降级

dify 的策略是**业务可用性优先**：
- Redis 故障 → 业务降级运行（不崩溃）
- DB 故障 → 严重错误（数据源丢失）
- **设计哲学**：Redis 是"加速器"，DB 是"真相"

### 1.3 关键 key 命名规范

dify 用 `REDIS_KEY_PREFIX` 统一前缀，格式：
```
{REDIS_KEY_PREFIX}:{业务}:{实体}:{ID}

例：
dify:login_error_rate_limit:alice@example.com
dify:account_refresh_token:user-123
dify:stream:workflow_events
```

## 2. dify 仓库 Redis 使用全景

### 2.1 核心扩展模块

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`

这是 dify 的 Redis **唯一初始化入口**，所有 Redis 客户端都从这里拿：

```python
redis_client: RedisClientWrapper = RedisClientWrapper()

# 业务代码统一这样用：
from extensions.ext_redis import redis_client
redis_client.set("foo", "bar")
```

### 2.2 Session / Token 存储（高频使用）

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`

| key 模式 | 用途 | TTL |
|---------|------|-----|
| `refresh_token:{token}` | Refresh Token → 用户 ID | `REFRESH_TOKEN_EXPIRY` |
| `account_refresh_token:{user_id}` | 用户 ID → Refresh Token | `REFRESH_TOKEN_EXPIRY` |
| `account_last_active_refresh:{user_id}` | 活跃时间防抖 | 60 秒 |
| `login_error_rate_limit:{email}` | 登录失败计数 | `LOGIN_LOCKOUT_DURATION` |
| `forgot_password_error_rate_limit:{email}` | 忘记密码失败 | `FORGOT_PASSWORD_LOCKOUT_DURATION` |
| `email_register_error_rate_limit:{email}` | 注册失败 | `EMAIL_REGISTER_LOCKOUT_DURATION` |
| `account_frozen:{email}` | 账户冻结标志 | 60 分钟 |
| `account_hour_limit:{email}` | 每小时计数 | 10 分钟 |

### 2.3 Celery Broker（任务队列）

> Celery 四大组件与任务生命周期见 [Celery 架构](./05-celery-architecture.md)。

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_celery.py`

```python
celery_app = Celery(
    app.name,
    task_cls=FlaskTask,
    broker=dify_config.CELERY_BROKER_URL,      # redis://...
    backend=dify_config.CELERY_RESULT_BACKEND,  # redis://...
)
```

- 所有 `api/tasks/*.py` 里的任务用 `redis://` 作为 Broker
- Broker 存的是**待执行任务列表**，重启时不能丢

### 2.4 Pub/Sub（事件广播）

**文件位置**：`/Users/xu/code/github/dify/api/libs/broadcast_channel/`

```python
from libs.broadcast_channel.channel import BroadcastChannel

channel = BroadcastChannel(redis_client)
topic = channel.topic("workflow_events")
producer = topic.as_producer()
producer.publish(b"event payload")
```

**用途**：
- 工作流执行进度通知
- 多实例间的状态同步

支持三种实现：
- `pubsub_channel.py`：普通 Pub/Sub（Redis 6.0+）
- `sharded_channel.py`：Sharded Pub/Sub（Cluster 友好）
- `streams_channel.py`：Streams（更可靠）

### 2.5 任务重试标志

**文件位置**：`/Users/xu/code/github/dify/api/tasks/retry_document_indexing_task.py`

```python
retry_indexing_cache_key = f"document_{document_id}_is_retried"
# ...
redis_client.delete(retry_indexing_cache_key)
```

**用途**：防止同一文档被并发重试。

## 3. 代码示例

### 3.1 检索 dify 中所有 Redis key 模式

```bash
# 搜索 dify 代码中所有 redis_client.set/setex 的 key
grep -rn 'redis_client\.setex\|redis_client\.set(' \
    /Users/xu/code/github/dify/api/services/ \
    /Users/xu/code/github/dify/api/tasks/
```

### 3.2 用 redis-cli 监控 dify 的 key 命名空间

```bash
# 监控所有 key
redis-cli MONITOR

# 只看 dify 前缀
redis-cli --scan --pattern "dify:*" | head -20

# 看某个 key 的 TTL
redis-cli TTL "dify:login_error_rate_limit:alice@example.com"
```

### 3.3 模拟 Redis 故障测试降级

```bash
# 临时停 Redis
docker stop redis

# dify 业务继续运行（限流、token 验证会跳过）
# 观察日志：RedisError ... default_return

# 重启 Redis
docker start redis
```

## 4. 关键要点总结

- dify 的 Redis 承担 **5 种角色**：Broker、Backend、缓存、Session、Pub/Sub
- **统一前缀** `REDIS_KEY_PREFIX` 避免多实例冲突
- **`redis_fallback` 装饰器**是核心保护机制
- **Pub/Sub 可独立部署**，与业务 Redis 解耦
- 业务代码统一从 `extensions.ext_redis.redis_client` 取客户端

### 4.1 Redis key 速查表

| key 模式 | 类型 | 用途 | 失效策略 |
|---------|------|------|---------|
| `refresh_token:{token}` | String | Refresh Token | TTL |
| `account_refresh_token:{user_id}` | String | 反向索引 | TTL |
| `login_error_rate_limit:{email}` | String | 失败计数 | TTL |
| `account_frozen:{email}` | String | 冻结标志 | TTL 60min |
| `document_{id}_is_retried` | String | 重试标志 | 手动删 |
| `stream:{topic}` | Stream | 事件流 | TTL |
| `celery-task-meta-{id}` | Hash | 任务结果 | TTL |

---

**文档版本**：v1.0
**最后更新**：2026-07-13
