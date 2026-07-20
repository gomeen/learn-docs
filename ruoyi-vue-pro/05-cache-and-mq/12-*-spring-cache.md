# 小验证：Spring Cache 与 ruoyi 用法

> 覆盖：
- [Spring Cache 抽象](./08-spring-cache.md)
- [缓存注解](./09-cache-annotation.md)
- [Redis 后端](./10-spring-cache-redis.md)
- [ruoyi 缓存场景](./11-ruoyi-cache-usage.md)
>
> 预计：30～60 分钟 · 本地练习或改 ruoyi-vue-pro 仓库

## 背景

注解缓存能显著减少重复查库。重点是命中、失效与 ruoyi 实际用法。

## 需求

1. 定位项目 CacheManager / Redis 缓存配置。
2. 给只读服务方法加 `@Cacheable`，连续调用验证仅首次查库。
3. 写更新方法 `@CacheEvict` 或 `@CachePut`，更新后读到新值。
4. 列出 ruoyi 中 2 个真实缓存使用点（字典、用户等）。

## 提示

- key 表达式注意用户/租户维度，避免串数据。
- 空值缓存策略要小心。

## 验收标准

- [ ] 缓存命中可证
- [ ] 失效/更新路径正确
- [ ] 配置类路径已记录
- [ ] 两个真实业务缓存点列出
- [ ] 说明缓存与多租户共存时的 key 设计注意

## 延伸（选做）

- 测试缓存穿透：查询不存在 id。
- 统一用自定义 KeyGenerator。
