# 1.1 Redis 数据结构：String / Hash / List / Set / Sorted Set

> 掌握 Redis 五大基础数据结构的底层实现与典型使用场景。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Redis 五种基础数据结构的适用场景
- 理解各结构的底层编码（SDS / dict / listpack / skiplist 等）
- 用 redis-py 正确操作这些结构
- 能在 dify 中找到对应的实战用法

## 📚 前置知识

- Redis 基本概念（Key-Value 数据库、内存存储）
- Python 字典、列表、集合的基本操作
- dify 仓库整体结构（`/Users/xu/code/github/dify/api/`）

## 1. 核心概念

### 1.1 为什么 Redis 数据结构如此重要？

Redis 与 Memcached 的最大区别是**数据结构丰富**。同一个 key 可以是字符串、哈希、列表等，开发者能直接表达业务语义，而不必把所有东西都序列化成 JSON 字符串。

### 1.2 五大基础结构总览

| 结构 | 命令示例 | 底层实现 | 典型场景 |
|------|---------|----------|---------|
| String | `SET` / `GET` / `INCR` | SDS（简单动态字符串） | 缓存值、计数器、分布式锁 |
| Hash | `HSET` / `HGETALL` | listpack + dict | 对象属性、会话信息 |
| List | `LPUSH` / `RPOP` | quicklist（双向链表） | 消息队列、最新列表 |
| Set | `SADD` / `SMEMBERS` | intset + dict | 标签、共同好友、去重 |
| Sorted Set (ZSet) | `ZADD` / `ZRANGE` | skiplist + dict + listpack | 排行榜、带权重的队列 |

### 1.3 String（字符串）

最简单也最常用的结构。**value 不仅是字符串，也可以是整数 / 浮点数**，此时 Redis 提供原子自增（`INCR` / `DECR`）能力，常用于：
- 计数器（文章阅读数、API 调用次数）
- 分布式 ID（`INCR` + 业务前缀）
- 分布式锁的占位符

```redis
SET user:1001:name "alice"
INCR article:2001:views
GET article:2001:views   # 返回 1（整数）
```

### 1.4 Hash（哈希）

**对象型数据**的理想选择。相比把整个对象 JSON 化后塞进 String，Hash 允许单独读写某个字段，节省网络流量和序列化成本。

```redis
HSET user:1001 name "alice" age 30 city "Beijing"
HGET user:1001 name      # "alice"
HGETALL user:1001        # {name, age, city}
HINCRBY user:1001 age 1  # 原子 +1
```

### 1.5 List（列表）

**有序、可重复**的字符串序列。底层是双向链表（quicklist），两端 O(1) 插入删除，中间 O(N)。典型用法：
- 消息队列（`LPUSH` 生产 + `BRPOP` 消费）
- 最新 N 条记录（`LPUSH` + `LTRIM 0 99` 保留最近 100 条）

```redis
LPUSH news:latest "article-1"
LPUSH news:latest "article-2"
LRANGE news:latest 0 9   # 取最近 10 条
LTRIM news:latest 0 99  # 裁剪到只保留 100 条
```

### 1.6 Set（集合）

**无序、不可重复**。支持集合运算（交集、并集、差集），适合：
- 标签、共同关注、好友推荐
- 去重（用 `SADD` 配合 `SISMEMBER` 做唯一性判断）

```redis
SADD user:1001:tags "python" "redis" "k8s"
SISMEMBER user:1001:tags "python"   # 1
SUNION user:1001:tags user:1002:tags
```

### 1.7 Sorted Set（有序集合 / ZSet）

每个成员关联一个 **score**，按 score 排序。底层是 **skiplist（跳跃表） + hash 表**，使范围查询达到 O(log N)。典型场景：
- 排行榜（`ZADD score member`，`ZREVRANGE 0 9` 取 Top 10）
- 延时队列（score = 执行时间戳，定时 `ZRANGEBYSCORE` 取到期任务）
- 滑动窗口限流（score = 请求时间戳）

```redis
ZADD leaderboard 95 "alice" 87 "bob" 99 "carol"
ZREVRANGE leaderboard 0 2 WITHSCORES   # Top 3
ZRANGEBYSCORE leaderboard 90 100       # 90~100 分的人
```

## 2. 代码示例

### 2.1 用 redis-py 操作五种结构

```python
# 文件：example_data_structures.py
import redis

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# 1. String：计数器
r.set("counter:api", 0)
r.incr("counter:api")            # 1
r.incrby("counter:api", 10)      # 11

# 2. Hash：用户对象
r.hset("user:1001", mapping={"name": "alice", "age": 30, "city": "BJ"})
print(r.hget("user:1001", "name"))    # "alice"
r.hincrby("user:1001", "age", 1)      # age=31

# 3. List：最新动态
r.delete("news:latest")
r.lpush("news:latest", "a", "b", "c")
print(r.lrange("news:latest", 0, -1)) # ['c', 'b', 'a']

# 4. Set：用户标签
r.sadd("user:1001:tags", "python", "redis")
print(r.smembers("user:1001:tags"))   # {'python', 'redis'}

# 5. Sorted Set：排行榜
r.delete("game:rank")
r.zadd("game:rank", {"alice": 95, "bob": 87, "carol": 99})
print(r.zrevrange("game:rank", 0, 2, withscores=True))
```

### 2.2 常见错误：错误地序列化为 JSON

```python
# ❌ 反例：把整个对象 JSON 化存进 String
import json
r.set("user:1001", json.dumps({"name": "alice", "age": 30}))

# 问题：
# 1. 修改一个字段要 GET -> 反序列化 -> 修改 -> 序列化 -> SET
# 2. 高并发下容易发生写覆盖（无 CAS）

# ✅ 正例：用 Hash
r.hset("user:1001", mapping={"name": "alice", "age": 30})
r.hincrby("user:1001", "age", 1)   # 原子更新单个字段
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Redis 客户端封装（Hash/List/ZSet 操作）

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 165-209）：

```python
def hset(self, name: str | bytes, *args: Any, **kwargs: Any) -> Any:
    return self._require_client().hset(_serialize_redis_name_arg(name, self._get_prefix()), *args, **kwargs)

def hgetall(self, name: str | bytes) -> Any:
    return self._require_client().hgetall(_serialize_redis_name_arg(name, self._get_prefix()), *args, **kwargs)

def zadd(
    self,
    name: str | bytes,
    mapping: dict[str | bytes | int | float, float | int | str | bytes],
    nx: bool = False,
    xx: bool = False,
    ch: bool = False,
    incr: bool = False,
    gt: bool = False,
    lt: bool = False,
) -> Any:
    return self._require_client().zadd(
        _serialize_redis_name_arg(name, self._get_prefix()),
        cast(Any, mapping),
        nx=nx, xx=xx, ch=ch, incr=incr, gt=gt, lt=lt,
    )

def zremrangebyscore(self, name: str | bytes, min: float | str, max: float | str) -> Any:
    return self._require_client().zremrangebyscore(_serialize_redis_name_arg(name, self._get_prefix()), min, max)
```

**解读**：
- 第 1-3 行：`hset` 接收可变参数，把 Redis 哈希的字段写入操作透明地加上 key 前缀
- 第 11-22 行：`zadd` 支持 `nx`（不存在才插入）、`ch`（返回变更数）、`incr`（自增 score）等高级选项——dify 用它实现限流和延时队列
- 第 26 行：`zremrangebyscore` 删除指定 score 区间成员，常配合 `ZADD` 实现滑动窗口

**整体设计意图**：`RedisClientWrapper` 把所有 key 都自动加上统一前缀，避免不同业务方 key 冲突，是生产环境的标准做法。

### 3.2 ruoyi 的 Redis 操作（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
**核心代码**（简化）：

```java
// RedisKeyUtils.java - 定义统一的 key 前缀
public class RedisKeyUtils {
    public static String format(String key) {
        return "ruoyi:" + key;
    }
}

// RedisUtils.java - Hash 操作示例
public static <T> void setHash(String key, String field, T value) {
    redisTemplate.opsForHash().put(RedisKeyUtils.format(key), field, value);
}

public static Map<Object, Object> getHash(String key) {
    return redisTemplate.opsForHash().entries(RedisKeyUtils.format(key));
}
```

**解读**：
- 第 1-4 行：`RedisKeyUtils.format()` 强制所有 key 加 `ruoyi:` 前缀，与 dify 的 `_serialize_redis_name_arg` 思想一致
- 第 7-9 行：通过 Spring 的 `redisTemplate.opsForHash()` 访问 Hash 结构，API 风格不同但语义一致

## 4. 关键要点总结

- **String** 适合简单 value 和原子计数器；**Hash** 适合对象字段；**List** 适合队列；**Set** 适合去重和集合运算；**Sorted Set** 适合排行榜和按 score 排序
- 不要把所有数据都 JSON 化后塞进 String，会丢失原子性优势
- 生产环境必须给 key 加统一前缀，避免多服务混用
- redis-py 的 `decode_responses=True` 让返回值为 `str` 而非 `bytes`，省去手动 decode

## 5. 练习题

### 练习 1：基础（必做）

用 redis-py 实现一个简单的访问计数器：每次调用 `incr_views(article_id)`，返回当前累计阅读数。

```python
def incr_views(article_id: str) -> int:
    # TODO: 用 INCR 实现
    pass
```

### 练习 2：进阶

实现一个 `top_n(items: dict[str, int], n: int)` 函数，把字典写入 ZSet 并返回分数最高的 N 个成员（用 `ZADD` + `ZREVRANGE`）。

### 练习 3：挑战（选做）

阅读 `dify/api/extensions/ext_redis.py` 的 `RedisClientWrapper`，分析它**没有**直接暴露哪些 Redis 命令（如 `HSCAN` / `ZPOPMIN`），这些命令在 dify 中通过什么方式被调用？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
- Redis 官方文档：https://redis.io/docs/data-types/
- redis-py 文档：https://redis-py.readthedocs.io/

---

**文档版本**：v1.0
**最后更新**：2026-07-14