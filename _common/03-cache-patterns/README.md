# 03 - 缓存模式

> 缓存是后端性能优化的核心，本分类讲解跨语言通用的缓存模式。

## 知识点

- [ ] [3.1 缓存策略：Cache-Aside / Read-Through / Write-Through / Write-Behind](./01-strategies.md)
- [ ] [3.2 缓存三大问题：穿透 / 击穿 / 雪崩](./02-three-problems.md)
- [ ] [3.3 缓存预热与更新](./03-warmup-and-refresh.md)
- [ ] [3.4 限流算法：固定窗口 / 滑动窗口 / 令牌桶 / 漏桶](./04-rate-limiting.md)
- [ ] [3.5 分布式 Session 设计](./05-distributed-session.md)
- [ ] [3.6 分布式 ID 生成：Snowflake / Leaf / UUID](./06-distributed-id.md)
- [ ] [3.7 全局唯一短 ID 生成方案](./07-short-id.md)

## 🔗 项目特定实现

- **dify（Python）**：[`../../dify/04-cache-and-queue/`](../../dify/04-cache-and-queue/)
- **ruoyi（Java）**：[`../../ruoyi-vue-pro/05-cache-and-mq/`](../../ruoyi-vue-pro/05-cache-and-mq/)
