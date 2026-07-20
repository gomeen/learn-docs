# 小验证：Redis 事务/客户端与 dify 用法

> 覆盖：
> - [06-redis-transaction](./02-redis-transaction.md)
> - [07-redis-py](./03-redis-py.md)
> - [13-redis-in-dify](./01-redis-in-dify.md)
>
> 预计：45～75 分钟 · 本地练习或改 dify 仓库

## 背景

dify 用 Redis 做缓存、限流、token、分布式协作。本组文件覆盖事务/Lua、redis-py 与项目内用法全景。

## 需求

1. 本地用 redis-py（或 fakeredis）实现：
   - 简易滑动窗口限流：`allow(key, limit, window_seconds) -> bool`
   - 用 pipeline 或 Lua 保证「读计数 + 递增」的原子性（二选一，注释权衡）
2. 在 `/Users/xu/code/github/dify` 阅读 `api/extensions/ext_redis.py` 与 `13` 文中的 key 模式，在 `NOTES.md` 列出 ≥5 个真实 key 前缀及用途。
3. （改仓库可选）给某次 Redis set 增加更清晰的 timeout 常量命名，或补充一处缺失的过期时间——**必须**说明不影响正确性。

## 提示

- 仓库：`api/extensions/ext_redis.py`、services 内 `redis_client` 用法
- 注意：练习勿连接生产 Redis；本地 docker redis 即可

## 验收标准

- [ ] 限流函数在窗口内第 limit+1 次返回 False
- [ ] 说明 pipeline/Lua 如何避免竞态
- [ ] `NOTES.md` 含真实 key 前缀与文件锚点
- [ ] 可选改动有过期策略意识，无密钥硬编码

## 延伸（选做）

实现一个带 token 的分布式锁（SET NX EX + 释放校验 value）。
