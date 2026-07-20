# 小验证：Celery 结果/幂等/重试与事件驱动

> 覆盖：
> - [19-celery-result](./11-celery-result.md)
> - [20-celery-idempotency](./12-celery-idempotency.md)
> - [21-celery-retry](./13-celery-retry.md)
> - [22-celery-in-dify](./14-celery-in-dify.md)
> - [27-event-driven](./15-event-driven.md)
>
> 预计：40～60 分钟 · 本地练习或改 dify 仓库

## 背景

可观测结果、幂等与重试决定「失败后用户看到什么」。事件驱动文强调解耦与最终一致性，不必上 Kafka。

## 需求

1. 选做改动（**其一即可**）：
   - 为某任务补充/收紧 `autoretry_for` 与 `retry_backoff`（或等价），或
   - 为任务增加基于业务 id 的幂等键检查（Redis `SETNX`），默认保持兼容，或
   - 本地独立 `mini_celery`（或纯函数模拟）：任务 + 重试 + 幂等骨架。
2. 说明结果如何查询/落库：Result Backend 或业务状态字段（对照 `22-celery-in-dify` 与仓库）。
3. 结合 [27-event-driven](./15-event-driven.md)：写 5～8 行——何时用「队列任务」vs「Pub/Sub 通知」，各举 1 个 dify 相关场景（可假设）。
4. `NOTES.md` 记：失败后用户侧可观察行为（结果查询/状态字段）。

## 提示

- `api/tasks/`、`api/extensions/ext_celery.py`
- 幂等键务必带业务 id + TTL 思路
- 事件驱动不必引入 Kafka；Redis Pub/Sub/Stream 足够

## 验收标准

- [ ] 有重试或幂等的可运行示例/改动说明
- [ ] 说清失败后用户侧可观察行为
- [ ] 队列任务 vs 事件通知的边界写清楚
- [ ] 不在 Web 进程默认执行长时间阻塞任务（有对照说明）

## 延伸（选做）

为幂等键设计失败路径：成功删键 vs TTL 过期，各写一句利弊。
