# 6.4 限流、配额管理与用户余额

> 区分瞬时流量保护与长期额度控制，并理解 dify 的 Redis 滑动窗口和 quota 预留事务。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 rate limit、quota、balance、reserved 和 usage
- 使用 Redis ZSET 实现滑动窗口限流
- 解释 reserve、commit、release 的并发安全语义
- 看懂 dify `RateLimiter` 与 `BillingService` 的额度接口

## 📚 前置知识

- [Token 用量统计与计费](./36-token-tracking.md)
- Redis ZSET、TTL 和原子操作（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)；Lua 原子性见 [Redis 事务与 Lua](../04-cache-and-queue/02-redis-transaction.md)）
- 限流算法通识（详见 [限流算法](../../_common/03-cache-patterns/04-rate-limiting.md)）
- HTTP 429、幂等键与异常处理基础

## 1. 核心概念

### 1.1 限流、配额和余额

| 概念 | 回答的问题 | 常见周期 |
| --- | --- | --- |
| Rate limit | 现在请求得是否太快？ | 秒、分钟 |
| Quota | 本周期最多能使用多少？ | 日、月、订阅周期 |
| Usage | 已经实际消耗多少？ | 累计 |
| Reserved | 已冻结但尚未结算多少？ | 任务执行期间 |
| Available | 当前还能预留或消费多少？ | 实时 |

常见不变量是 `available + reserved + usage = quota`，但具体外部服务可能有赠送额度、多 bucket 或过期规则，必须以其契约为准。

### 1.2 滑动窗口限流

Redis ZSET 以请求时间作为 score：先删除窗口外记录，再数窗口内成员，达到阈值则拒绝，否则写入唯一成员。与固定窗口相比，它不会在分钟边界允许双倍突发。

严格并发场景下，“删除、计数、写入”应使用 Lua 脚本或 Redis 事务原子执行；分开的多个命令可能在并发竞争时短暂放过额外请求。

### 1.3 Quota 预留事务

长任务开始前不知道真实消耗，直接事后扣减可能让多个并发任务同时超额。三段式流程是：

1. `reserve(request_id, estimated_amount)`：原子冻结预计额度，返回 `reservation_id`。
2. `commit(reservation_id, actual_amount)`：按实际值结算，多余预留退回。
3. `release(reservation_id)`：任务失败或取消，归还全部冻结额度。

`request_id` 应具有幂等性，避免客户端重试导致重复预留。`commit` 与 `release` 也应能安全处理重复请求和终态冲突。

## 2. 代码示例

### 2.1 Redis 滑动窗口限流

```python
# 文件：sliding_window.py
import secrets
import time

from redis import Redis


class SlidingWindowLimiter:
    def __init__(self, redis: Redis, limit: int, window_seconds: int) -> None:
        self.redis = redis
        self.limit = limit
        self.window_seconds = window_seconds

    def allow(self, subject: str) -> bool:
        now = time.time()
        key = f"rate:{subject}"
        self.redis.zremrangebyscore(key, "-inf", now - self.window_seconds)
        if self.redis.zcard(key) >= self.limit:
            return False
        member = f"{now}:{secrets.token_urlsafe(8)}"
        self.redis.zadd(key, {member: now})
        self.redis.expire(key, self.window_seconds * 2)
        return True


limiter = SlidingWindowLimiter(Redis(decode_responses=True), 10, 60)
print(limiter.allow("tenant-123"))
```

**说明**：示例便于理解，但三个核心操作并非原子。生产版本应使用 Lua 脚本，并在拒绝响应中返回合理的 `Retry-After`。

### 2.2 用 `try/finally` 保证释放预留

```python
# 文件：quota_lifecycle.py
from typing import Protocol


class QuotaClient(Protocol):
    def reserve(self, request_id: str, amount: int) -> str: ...
    def commit(self, reservation_id: str, actual: int) -> None: ...
    def release(self, reservation_id: str) -> None: ...


def run_metered_task(client: QuotaClient, request_id: str, estimate: int) -> str:
    reservation_id = client.reserve(request_id, estimate)
    committed = False
    try:
        result = "generated answer"
        actual = len(result.encode("utf-8"))
        client.commit(reservation_id, actual)
        committed = True
        return result
    finally:
        if not committed:
            client.release(reservation_id)
```

**说明**：只有 commit 成功后才设置终态；模型调用、解析或提交失败都进入 release。真实服务还需定义 commit 结果未知时如何查询状态，避免误释放已结算额度。

## 3. 关键要点总结

- Rate limit 保护瞬时容量，quota 控制周期总量，balance 描述实时可用状态。
- 滑动窗口精确但多命令并发时需 Lua 保证原子性。
- `reserve → commit/release` 防止并发任务事后扣费超额。
- 每个额度操作都需要幂等键、终态定义和超时补偿。
- dify 的通用限流器基于 Redis ZSET，quota 则通过外部 Billing API 管理。

---

**文档版本**：v1.0  
**最后更新**：2026-07-13
