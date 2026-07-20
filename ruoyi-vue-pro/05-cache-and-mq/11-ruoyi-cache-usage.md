# 2.4 ruoyi 的缓存使用场景

> 通过真实代码理解 ruoyi 在哪些业务场景使用缓存，以及如何选型 Redis 缓存还是本地缓存。

## 🎯 学习目标

完成本文档后，你将能够：
- 识别 ruoyi 中典型的缓存场景（字典、配置、用户权限）
- 区分本地缓存 vs Redis 缓存的选型
- 掌握 `@Cacheable` 与本地缓存的组合用法
- 在自己的业务中合理使用 ruoyi 的缓存抽象

## 📚 前置知识

- Spring Cache 注解（详见 [@Cacheable 等](./09-cache-annotation.md)）
- Redis 基础（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）
- 缓存策略选型（详见 [缓存策略](../../_common/03-cache-patterns/01-strategies.md)）

## 1. 核心概念

### 1.1 ruoyi 的典型缓存场景

| 场景 | 缓存类型 | TTL | 理由 |
|------|---------|-----|------|
| 字典项 dict | 本地 Cache | 5min | 读多写少、跨线程共享 |
| 系统配置 | Redis | 30min | 需要跨实例同步 |
| 用户权限 | Redis | 10min | 多实例必须一致 |
| OAuth2 token | Redis | 跟随 token 过期 | 安全敏感（Token/JWT 详见 [JWT](../../_common/07-authentication/03-jwt.md)） |
| 防重提交 token | Redis | 5min | 短时、跨实例 |

### 1.2 本地 vs Redis 选型原则

- **本地缓存**：单实例高频读、不要求多实例一致（如字典项）
- **Redis 缓存**：跨实例共享、有变更广播需求（如权限）

> 📌 **Sighting**：跨实例 Session 类场景还可参考 [分布式 Session](../../_common/03-cache-patterns/05-distributed-session.md)。

## 2. 代码示例

### 2.1 字典项本地缓存（伪代码）

```java
@Service
public class DictService {
    private final LoadingCache<String, List<DictData>> cache =
        CacheUtils.buildAsyncReloadingCache(Duration.ofMinutes(5),
            new CacheLoader<>() {
                @Override
                public List<DictData> load(String dictType) {
                    return dictMapper.selectByType(dictType);
                }
            });

    public List<DictData> getDict(String type) {
        return cache.getUnchecked(type);
    }
}
```

### 2.2 用户 Redis 缓存

```java
@Service
public class AdminUserService {
    @Cacheable(cacheNames = "user#10m", key = "#id")
    public AdminUser getUser(Long id) {
        return userMapper.selectById(id);
    }

    @CacheEvict(cacheNames = "user#10m", key = "#user.id")
    public void updateUser(AdminUser user) {
        userMapper.updateById(user);
    }
}
```

### 2.3 防重提交 token（Redis）

```java
@Service
public class RepeatSubmitService {
    @Resource
    private StringRedisTemplate redisTemplate;

    public boolean tryLock(String token, long ttlSeconds) {
        return redisTemplate.opsForValue().setIfAbsent(
            "repeat_submit:" + token, "1", Duration.ofSeconds(ttlSeconds));
    }
}
```

## 3. 关键要点总结

- ruoyi 用本地缓存（Guava `CacheBuilder`）处理"全局字典"等共享数据
- 用 Redis 缓存处理"用户、权限、配置"等需要跨实例的数据
- `asyncReloading` 保证读线程零阻塞
- 缓存 key 命名规范：`业务域:实体名:标识`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
