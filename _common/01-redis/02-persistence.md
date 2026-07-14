# 1.2 Redis 持久化：RDB / AOF

> 理解 Redis 两种持久化机制的原理、优缺点与生产配置建议。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 RDB 快照和 AOF 日志的差异
- 理解两种持久化的触发时机和恢复流程
- 为不同业务场景选择合适的持久化策略
- 能在 dify 配置中找到持久化相关参数

## 📚 前置知识

- Redis 基本概念（内存数据库）
- Linux 文件 I/O 基础
- `01-redis/01-data-structures.md`（推荐）

## 1. 核心概念

### 1.1 为什么需要持久化？

Redis 是**内存数据库**，进程重启或机器宕机会丢失所有数据。持久化机制把内存数据保存到磁盘，重启时再加载恢复。

### 1.2 RDB（Redis Database）

**全量快照**——把某一时刻的所有数据序列化保存为 `.rdb` 文件。

**触发方式**：
- 手动：`SAVE`（阻塞主线程）/ `BGSAVE`（fork 子进程异步）
- 自动：在 `redis.conf` 配置 `save <seconds> <changes>` 规则，如 `save 900 1` 表示 900 秒内有至少 1 个 key 变更就触发

**优点**：
- 单个压缩文件，便于备份和迁移
- 恢复大数据集比 AOF 快
- `BGSAVE` 用 fork 子进程，对主线程影响小

**缺点**：
- 丢失最后一次快照后的所有数据（可能几分钟）
- `fork()` 大数据集时可能阻塞（虽然子进程处理，主线程仍需复制页表）

### 1.3 AOF（Append Only File）

**增量日志**——把每条写命令以 `RESP` 协议追加到 `.aof` 文件。

**fsync 策略**（`appendfsync` 配置）：
- `always`：每条命令都 fsync，最安全但最慢
- `everysec`（默认）：每秒 fsync 一次，丢失最多 1 秒数据，**推荐**
- `no`：交给 OS 控制，最快但不安全

**AOF 重写（Rewrite）**：随着写命令累积，AOF 文件会膨胀。`BGREWRITEAOF` 会 fork 子进程，基于当前内存数据生成最简命令集（如多次 `INCR` 合并为 `SET key N`）。

**优点**：
- 数据安全性高（最多丢 1 秒）
- AOF 文件可读，便于分析

**缺点**：
- 文件体积通常比 RDB 大
- 恢复速度比 RDB 慢（需重放每条命令）

### 1.4 混合持久化（Redis 4.0+）

RDB 全量 + AOF 增量结合。`aof-use-rdb-preamble yes`：
- AOF 文件前半段是 RDB 格式的全量快照
- 后半段是 AOF 格式的增量命令
- **结合了两者优点**：恢复快 + 数据全

### 1.5 如何选择？

| 场景 | 推荐方案 |
|------|---------|
| 缓存（可丢数据） | RDB 或关闭持久化 |
| 数据库（不能丢） | AOF `everysec` |
| 大数据集 + 数据重要 | 混合持久化 |
| 主从架构 | Master 开 AOF，Slave 开 RDB |

## 2. 代码示例

### 2.1 redis.conf 关键配置

```conf
# RDB 配置
save 900 1           # 900 秒内至少 1 个 key 变更
save 300 10          # 300 秒内至少 10 个 key 变更
save 60 10000        # 60 秒内至少 10000 个 key 变更
dbfilename dump.rdb
dir /var/lib/redis

# AOF 配置
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec
no-appendfsync-on-rewrite yes   # 重写期间不 fsync，避免阻塞

# 混合持久化
aof-use-rdb-preamble yes
```

### 2.2 手动触发持久化

```python
# 文件：example_persistence.py
import redis

r = redis.Redis(host="localhost", port=6379)

# 触发 RDB 快照（异步 fork 子进程）
last_save = r.bgsave()
print(f"BGSAVE 返回: {last_save}")  # True 表示已启动

# 触发 AOF 重写
r.bgrewriteaof()

# 查看上次 RDB 保存时间（UNIX 时间戳）
last_save_time = r.lastsave()
print(f"上次保存: {last_save_time}")
```

### 2.3 常见错误：误用 SAVE 阻塞主线程

```python
# ❌ 反例：在生产环境用 SAVE
r.save()    # 主线程被阻塞，期间无法处理任何请求！

# ✅ 正例：用 BGSAVE（异步 fork）
r.bgsave()  # 立即返回，后台生成快照
```

## 3. dify 仓库源码解读

### 3.1 dify 的 Redis 连接重试与健康检查

**文件位置**：`/Users/xu/code/github/dify/api/extensions/ext_redis.py`
**核心代码**（行 294-329）：

```python
def _get_retry_policy() -> Retry:
    """Build the shared retry policy for Redis connections."""
    return Retry(
        backoff=ExponentialWithJitterBackoff(
            base=dify_config.REDIS_RETRY_BACKOFF_BASE,
            cap=dify_config.REDIS_RETRY_BACKOFF_CAP,
        ),
        retries=dify_config.REDIS_RETRY_RETRIES,
    )


def _get_connection_health_params() -> RedisHealthParamsDict:
    """Get connection health and retry parameters for standalone and Sentinel Redis clients."""
    return RedisHealthParamsDict(
        retry=_get_retry_policy(),
        socket_timeout=dify_config.REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout=dify_config.REDIS_SOCKET_CONNECT_TIMEOUT,
        health_check_interval=dify_config.REDIS_HEALTH_CHECK_INTERVAL,
    )
```

**解读**：
- 第 2-7 行：使用 `ExponentialWithJitterBackoff`（指数退避 + 抖动）作为重试策略
- 第 14-19 行：配置 `socket_timeout` 和 `health_check_interval`，定期发送 `PING` 检测连接

**为什么这与持久化相关？** Redis 重启或 AOF 重写期间可能短暂不可用，连接超时和重试策略决定了客户端能否优雅恢复。生产环境的 Redis 必须开启 AOF `everysec`，否则重启会丢失缓存（业务可能感知不到，但已订阅的事件会丢失）。

### 3.2 ruoyi 的 Redis 健康检查（Java 类比）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
**核心代码**（简化）：

```java
// RedisHealthIndicator.java - Spring Boot Actuator 健康检查
@Component
public class RedisHealthIndicator implements HealthIndicator {
    @Resource
    private RedisTemplate<String, String> redisTemplate;

    @Override
    public Health health() {
        try {
            String pong = redisTemplate.execute(connection ->
                connection.ping());
            return "PONG".equals(pong) ? Health.up().build() : Health.down().build();
        } catch (Exception e) {
            return Health.down(e).build();
        }
    }
}
```

**解读**：
- 第 7-9 行：通过 `PING` 命令检测 Redis 可用性
- 第 11 行：异常时返回 `down` 状态，配合 K8s liveness probe 可自动重启 Pod

## 4. 关键要点总结

- **RDB**：全量快照，丢数据多但恢复快；**AOF**：增量日志，丢数据少但文件大
- 生产环境推荐 **AOF `everysec`**（最多丢 1 秒）
- 大数据集 + 高安全要求用 **混合持久化**
- 永不在生产用 `SAVE`（阻塞主线程）；用 `BGSAVE` / `BGREWRITEAOF`
- 重启恢复时优先加载 AOF（如果开启），否则加载 RDB

## 5. 练习题

### 练习 1：基础（必做）

写一个 Python 脚本，连接到本地 Redis，依次执行：
1. `SET foo bar`
2. `BGSAVE`
3. 等待 1 秒
4. 读取 `LASTSAVE` 时间戳

### 练习 2：进阶

阅读 `dify/api/extensions/ext_redis.py` 的 `_get_retry_policy()`，解释为什么重试需要 **指数退避 + 抖动**？如果只用固定间隔重试会怎样？

### 练习 3：挑战（选做）

设计一个方案：如何在 Redis 实例 AOF 文件损坏时（`redis-check-aof` 报错）尽可能恢复数据？

## 6. 参考资料

- `/Users/xu/code/github/dify/api/extensions/ext_redis.py`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/`
- Redis 持久化官方文档：https://redis.io/docs/management/persistence/
- Redis 混合持久化：https://redis.io/docs/management/persistence/#log-rewriting

---

**文档版本**：v1.0
**最后更新**：2026-07-14