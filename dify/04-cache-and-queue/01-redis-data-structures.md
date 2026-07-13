# 4.1.1 Redis 数据结构：String / Hash / List / Set / Sorted Set

> Redis 不只是 key-value 缓存，它支持五种核心数据结构，是 dify 缓存、限流、Pub/Sub 的基础。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Redis 的 5 种核心数据结构及其适用场景
- 理解每种数据结构的底层实现（SDS / quicklist / skiplist）
- 能用 `redis-py` 客户端操作这些结构
- 在 dify 中识别每种结构的使用位置（缓存用 Hash，限流用 Sorted Set 等）

## 📚 前置知识

- Python 基础语法
- 命令行操作基础
- Redis 安装与启动（本地或 Docker）

## 1. 核心概念

### 1.1 为什么 Redis 这么快？

Redis 是**内存数据库**，所有数据驻留在内存中。但它不仅仅是一个 `dict`，它针对不同场景设计了**专用数据结构**：

| 数据结构 | 底层实现 | 典型场景 |
|---------|---------|---------|
| String | SDS（简单动态字符串）| 缓存、计数器、分布式锁 |
| Hash | listpack + hashtable | 对象存储（如用户配置）|
| List | quicklist（双向链表 + ziplist）| 消息队列、最新列表 |
| Set | hashtable + intset | 标签、共同好友、去重 |
| Sorted Set | skiplist + hashtable | 排行榜、滑动窗口限流 |

### 1.2 String（字符串）

最基础的数据结构。可以存字符串、整数、浮点数、二进制（最大 512MB）。

```bash
# 设置值
SET user:1:name "Alice"
SET counter 100

# 获取值
GET user:1:name

# 自增（原子操作）
INCR counter      # 101
INCRBY counter 5  # 106

# 设置过期时间
SETEX lock:order 30 "owner-token"
```

底层实现：**SDS（Simple Dynamic String）**，类似 Go 的 `string`，包含 `len`（已用长度）、`free`（剩余空间）、`buf`（字符数组）。优势是 O(1) 取长度、预分配减少内存碎片、二进制安全。

### 1.3 Hash（哈希）

键值对集合，适合存"对象"。每个 Hash 可存 2^32 - 1 个字段。

```bash
# 设置字段
HSET user:1 name "Alice" age 30 email "alice@example.com"

# 获取单个字段
HGET user:1 name

# 获取全部
HGETALL user:1

# 自增
HINCRBY user:1 age 1
```

**适用场景**：用户配置、应用配置、会话信息。dify 用 Hash 存储数据集元信息。

### 1.4 List（列表）

有序字符串列表，按插入顺序排序。底层是 **quicklist**（多个 ziplist 用双向链表串起来）。

```bash
# 左侧推入（LPUSH = Left Push）
LPUSH tasks "task1"
LPUSH tasks "task2"

# 右侧弹出（BRPOP = Blocking Right Pop）
BRPOP tasks 0  # 阻塞等待

# 取范围
LRANGE tasks 0 -1
```

**适用场景**：消息队列、最新 N 条、关注列表。Celery 早期版本就是用 Redis List 做 Broker。

### 1.5 Set（集合）

无序且元素唯一的集合，支持交、并、差运算。

```bash
# 添加
SADD tags:article:1 "python" "redis" "cache"

# 交集：两个用户共同关注的人
SINTER user:1:follows user:2:follows

# 并集
SUNION set1 set2

# 成员判断（O(1)）
SISMEMBER tags:article:1 "python"
```

**适用场景**：标签、共同好友、去重（抽奖）、黑白名单。

### 1.6 Sorted Set（有序集合）

每个元素关联一个 **score**，按 score 自动排序。底层是 **skiplist（跳跃表）+ hashtable**。

```bash
# 添加带分数的成员
ZADD leaderboard 100 "alice" 85 "bob" 92 "charlie"

# 排行榜前 3
ZREVRANGE leaderboard 0 2 WITHSCORES

# 按分数范围
ZRANGEBYSCORE leaderboard 80 100

# 增加分数
ZINCRBY leaderboard 10 "alice"  # alice -> 110
```

**适用场景**：排行榜、滑动窗口限流、延迟队列（score = 执行时间戳）。

## 2. 代码示例

### 2.1 用 redis-py 操作五种结构

```python
import redis

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# 1. String
r.set("user:1:name", "Alice")
r.incr("page:views")  # 自增计数器

# 2. Hash
r.hset("user:1", mapping={"name": "Alice", "age": 30})
print(r.hgetall("user:1"))  # {'name': 'Alice', 'age': '30'}

# 3. List（消息队列）
r.lpush("queue:tasks", json.dumps({"id": 1}))
task = r.brpop("queue:tasks", timeout=5)  # 阻塞 5 秒

# 4. Set（标签去重）
r.sadd("article:1:tags", "python", "redis")
print(r.smembers("article:1:tags"))

# 5. Sorted Set（排行榜）
r.zadd("game:leaderboard", {"alice": 100, "bob": 85})
top3 = r.zrevrange("game:leaderboard", 0, 2, withscores=True)
```

### 2.2 常见错误：误用 String 存对象

```python
# ❌ 错误：用 String 存 JSON，反序列化开销大且无法局部更新
r.set("user:1", json.dumps({"name": "Alice", "age": 30}))
new_data = json.loads(r.get("user:1"))
new_data["age"] = 31
r.set("user:1", json.dumps(new_data))  # 整个对象重写

# ✅ 正确：用 Hash，支持局部更新
r.hset("user:1", "age", 31)  # 只更新 age 字段
print(r.hget("user:1", "age"))  # "31"
```

### 2.3 常见错误：List 当消息队列丢失数据

```python
# ❌ 错误：用 LPUSH + RPOP，消费者崩溃时数据丢失
r.lpush("tasks", "task1")
task = r.rpop("tasks")  # 拿到就删，消费者崩溃就丢

# ✅ 正确：用 BRPOPLPUSH 或 Stream 保证可靠性
r.brpoplpush("tasks", "tasks:processing", timeout=5)
# 处理完后从 tasks:processing 删除
```

## 3. dify 仓库源码解读

### 3.1 Redis 客户端的统一封装

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 79-115）：

```python
def get(self, name: str | bytes) -> Any:
    return self._require_client().get(_serialize_redis_name_arg(name, self._get_prefix()))

def set(
    self,
    name: str | bytes,
    value: Any,
    ex: int | None = None,
    px: int | None = None,
    nx: bool = False,
    xx: bool = False,
    keepttl: bool = False,
    get: bool = False,
    exat: int | None = None,
    pxat: int | None = None,
) -> Any:
    return self._require_client().set(
        _serialize_redis_name_arg(name, self._get_prefix()),
        value,
        ex=ex, px=px, nx=nx, xx=xx, keepttl=keepttl, get=get, exat=exat, pxat=pxat,
    )

def setex(self, name: str | bytes, time: int | timedelta, value: Any) -> Any:
    return self._require_client().setex(_serialize_redis_name_arg(name, self._get_prefix()), time, value)

def delete(self, *names: str | bytes) -> Any:
    return self._require_client().delete(*_serialize_redis_name_args(names, self._get_prefix()))
```

**解读**：
- 第 80 行：所有方法都通过 `_serialize_redis_name_arg` 自动加上**全局 key 前缀**（`REDIS_KEY_PREFIX`），这样多个 dify 实例共享 Redis 时不会 key 冲突
- 第 95 行：`set` 方法支持 `nx=True`（仅当 key 不存在时设置），这是实现分布式锁的关键
- 第 109 行：`setex` 把 value 和过期时间一起设，避免两条命令导致 key 永久存活
- 第 115 行：`delete` 用 `*names` 接收可变参数，支持一次删多个 key

### 3.2 Sorted Set 用于限流

**文件位置**：`/Users/xu/code/github/dify/api/services/account_service.py`
**核心代码**（行 1052-1073）：

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

@staticmethod
@redis_fallback(default_return=False)
def is_login_error_rate_limit(email: str) -> bool:
    key = f"login_error_rate_limit:{email}"
    count = redis_client.get(key)
    if count is None:
        return False

    count = int(count)
    if count > AccountService.LOGIN_MAX_ERROR_LIMITS:
        return True
    return False
```

**解读**：
- 第 1054-1060 行：登录失败计数用 **String + INCR**（其实 dify 用 `get` + `setex` 模拟），失败次数超过 `LOGIN_MAX_ERROR_LIMITS` 就触发限流
- 第 1063 行：`@redis_fallback` 装饰器保证 Redis 故障时返回默认值，**业务不被阻塞**
- 第 1071 行：超过阈值就拒绝登录，实现简单的"固定窗口"限流
- **改进方向**：更精确的限流应该用 Sorted Set 记录每次失败的时间戳，配合 `ZREMRANGEBYSCORE` 实现**滑动窗口**（详见 2.4 章节）

## 4. 关键要点总结

- Redis 支持 5 种核心数据结构：String / Hash / List / Set / Sorted Set
- String：缓存、计数器（`INCR` 是原子操作）
- Hash：对象存储，支持局部更新，比 JSON 序列化高效
- List：消息队列，但消费即删除有丢数据风险，建议用 Stream
- Set：去重、交集运算，用于标签、共同好友
- Sorted Set：排行榜、滑动窗口限流，底层是 skiplist
- dify 的 `redis_client` 封装统一加 key 前缀，支持集群/哨兵/SSL

## 5. 练习题

### 练习 1：基础（必做）

用 redis-py 实现一个**计数器限流器**：每分钟最多访问 10 次。提示：key 设置 60 秒过期。

```python
import redis
import time

r = redis.Redis(decode_responses=True)

def rate_limit(user_id: str, limit: int = 10) -> bool:
    # TODO: 用 INCR + EXPIRE 实现
    pass
```

### 练习 2：进阶

用 Sorted Set 实现**滑动窗口限流**（精确到秒级）。提示：score = 当前时间戳，每次请求删除 60 秒前的记录，再判断数量。

### 练习 3：挑战（选做）

阅读 `api/extensions/ext_redis.py`，理解 `redis_fallback` 装饰器的设计意图，并自己实现一个类似的降级装饰器（捕获 `ConnectionError`，返回默认缓存值）。

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- `/Users/xu/code/github/dify/api/extensions/redis_names.py`
- `/Users/xu/code/github/dify/api/services/account_service.py`
- Redis 官方文档：https://redis.io/docs/data-types/
- redis-py 文档：https://redis.readthedocs.io/en/stable/

---

**文档版本**：v1.0
**最后更新**：2026-07-13