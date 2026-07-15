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
- [Celery 架构](./14-celery-architecture.md)（Broker / Backend 角色）

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

> Celery 四大组件与任务生命周期见 [Celery 架构](./14-celery-architecture.md)。

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

## 4. dify 仓库源码解读

### 4.1 redis_fallback：通用降级

> `@redis_fallback` 是装饰器写法（详见 [装饰器](../01-fundamentals/10-decorator.md)），此处只把它当作「包住 Redis 调用、失败时返回默认值」的保护层。

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 476-496）：

```python
def redis_fallback[T](default_return: T | None = None):  # type: ignore
    """
    decorator to handle Redis operation exceptions and return a default value when Redis is unavailable.
    """
    def decorator[**P, R](func: Callable[P, R]) -> Callable[P, R | T | None]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | T | None:
            try:
                return func(*args, **kwargs)
            except RedisError as e:
                func_name = getattr(func, "__name__", "Unknown")
                logger.warning("Redis operation failed in %s: %s", func_name, str(e), exc_info=True)
                return default_return

        return wrapper

    return decorator
```

**解读**：
- 这是 dify 中**用得最多的 Redis 保护机制**
- 几乎所有 `redis_client.get/set/setex/delete` 都有 `@redis_fallback`
- **默认返回值**根据业务设计：
  - `get` → `None`（缓存未命中）
  - 限流检查 → `False`（不限流）
  - Token 验证 → `None`（token 无效，但**注意可能误拒绝**）

### 4.2 客户端初始化与降级选择

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 438-461）：

```python
def init_app(app: DifyApp):
    """Initialize Redis client and attach it to the app."""
    global redis_client

    # Determine Redis mode and create appropriate client
    if dify_config.REDIS_USE_SENTINEL:
        redis_params = _get_base_redis_params()
        client = _create_sentinel_client(redis_params)
    elif dify_config.REDIS_USE_CLUSTERS:
        client = _create_cluster_client()
    else:
        redis_params = _get_base_redis_params()
        client = _create_standalone_client(redis_params)

    # Initialize the wrapper and attach to app
    redis_client.initialize(client)
    app.extensions["redis"] = redis_client

    global _pubsub_redis_client
    _pubsub_redis_client = client
    if dify_config.normalized_pubsub_redis_url:
        _pubsub_redis_client = _create_pubsub_client(
            dify_config.normalized_pubsub_redis_url, dify_config.PUBSUB_REDIS_USE_CLUSTERS
        )
```

**解读**：
- 三种部署模式：Standalone / Sentinel / Cluster
- **Pub/Sub 可以单独用 Redis**（通过 `normalized_pubsub_redis_url` 配置）
  - 业务 Redis 与 Pub/Sub Redis 解耦
  - Pub/Sub 用长连接，不影响业务 Redis 连接池

### 4.3 Celery 配置中的 Redis 角色

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_celery.py`
**核心代码**（行 109-128）：

```python
celery_app = Celery(
    app.name,
    task_cls=FlaskTask,
    broker=dify_config.CELERY_BROKER_URL,
    backend=dify_config.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    result_backend=dify_config.CELERY_RESULT_BACKEND,
    broker_transport_options=broker_transport_options,
    broker_connection_retry_on_startup=True,
    worker_log_format=dify_config.LOG_FORMAT,
    worker_task_log_format=dify_config.LOG_FORMAT,
    worker_hijack_root_logger=False,
    timezone=pytz.timezone(dify_config.LOG_TZ or "UTC"),
    task_ignore_result=True,
    task_annotations=dify_config.CELERY_TASK_ANNOTATIONS,
)
```

**解读**：
- `broker`：Celery Broker URL（Redis 存**待执行任务**）
- `backend`：Result Backend URL（Redis 存**任务结果**）
- `broker_connection_retry_on_startup=True`：启动时连接失败重试
- `task_ignore_result=True`：默认不存结果（节省 Redis 空间）

## 5. 关键要点总结

- dify 的 Redis 承担 **5 种角色**：Broker、Backend、缓存、Session、Pub/Sub
- **统一前缀** `REDIS_KEY_PREFIX` 避免多实例冲突
- **`redis_fallback` 装饰器**是核心保护机制
- **Pub/Sub 可独立部署**，与业务 Redis 解耦
- 业务代码统一从 `extensions.ext_redis.redis_client` 取客户端

## 6. Redis key 速查表

| key 模式 | 类型 | 用途 | 失效策略 |
|---------|------|------|---------|
| `refresh_token:{token}` | String | Refresh Token | TTL |
| `account_refresh_token:{user_id}` | String | 反向索引 | TTL |
| `login_error_rate_limit:{email}` | String | 失败计数 | TTL |
| `account_frozen:{email}` | String | 冻结标志 | TTL 60min |
| `document_{id}_is_retried` | String | 重试标志 | 手动删 |
| `stream:{topic}` | Stream | 事件流 | TTL |
| `celery-task-meta-{id}` | Hash | 任务结果 | TTL |

## 7. 练习题

### 练习 1：基础（必做）

用 `grep` 检索 `/Users/xu/code/github/dify/api/services/account_service.py` 里所有 `redis_client.setex` 的调用，列出它们的功能和 TTL。

### 练习 2：进阶

写一个脚本监控 dify 的 Redis key 数量和内存使用，统计每个 key pattern 的占比。

### 练习 3：挑战（选做）

阅读 `extensions/ext_redis.py` 完整代码，画出 dify Redis 客户端的初始化流程图（包括 Sentinel/Cluster/Standalone 三种分支）。

## 8. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- `/Users/xu/code/github/dify/api/extensions/ext_celery.py`
- `/Users/xu/code/github/dify/api/services/account_service.py`
- `/Users/xu/code/github/dify/api/libs/broadcast_channel/redis/`
- `/Users/xu/code/github/dify/api/extensions/redis_names.py`

---

**文档版本**：v1.0
**最后更新**：2026-07-13