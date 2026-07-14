# 2.4 ruoyi 的缓存使用场景

> 通过真实代码理解 ruoyi 在哪些业务场景使用缓存，以及如何选型 Redis 缓存还是本地缓存。

## 🎯 学习目标

完成本文档后，你将能够：
- 识别 ruoyi 中典型的缓存场景（字典、配置、用户权限）
- 区分本地缓存 vs Redis 缓存的选型
- 掌握 `@Cacheable` 与本地缓存的组合用法
- 在自己的业务中合理使用 ruoyi 的缓存抽象

## 📚 前置知识

- Spring Cache 注解（参见 `09-cache-annotation.md`）
- Redis 基础（参见 `01-redis-basics.md`）

## 1. 核心概念

### 1.1 ruoyi 的典型缓存场景

| 场景 | 缓存类型 | TTL | 理由 |
|------|---------|-----|------|
| 字典项 dict | 本地 Cache | 5min | 读多写少、跨线程共享 |
| 系统配置 | Redis | 30min | 需要跨实例同步 |
| 用户权限 | Redis | 10min | 多实例必须一致 |
| OAuth2 token | Redis | 跟随 token 过期 | 安全敏感 |
| 防重提交 token | Redis | 5min | 短时、跨实例 |

### 1.2 本地 vs Redis 选型原则

- **本地缓存**：单实例高频读、不要求多实例一致（如字典项）
- **Redis 缓存**：跨实例共享、有变更广播需求（如权限）

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

## 3. ruoyi 仓库源码解读

### 3.1 CacheUtils 本地缓存构造

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/cache/CacheUtils.java`
**核心代码**（行 22-44）：

```java
/**
 * 异步刷新的 LoadingCache 最大缓存数量
 */
private static final Integer CACHE_MAX_SIZE = 10000;

/**
 * 构建异步刷新的 LoadingCache 对象
 *
 * 注意：如果你的缓存和 ThreadLocal 有关系，要么自己处理 ThreadLocal 的传递，要么使用 {@link #buildCache(Duration, CacheLoader)} 方法
 *
 * 或者简单理解：
 * 1、和"人"相关的，使用 {@link #buildCache(Duration, CacheLoader)} 方法
 * 2、和"全局"、"系统"相关的，使用当前缓存方法
 */
public static <K, V> LoadingCache<K, V> buildAsyncReloadingCache(Duration duration, CacheLoader<K, V> loader) {
    return CacheBuilder.newBuilder()
            .maximumSize(CACHE_MAX_SIZE)
            // 只阻塞当前数据加载线程，其他线程返回旧值
            .refreshAfterWrite(duration)
            // 通过 asyncReloading 实现全异步加载，包括 refreshAfterWrite 被阻塞的加载线程
            .build(CacheLoader.asyncReloading(loader, Executors.newCachedThreadPool()));
}
```

**解读**：
- 第 39 行：10000 上限，超出 LRU 淘汰
- 第 41 行：`refreshAfterWrite` 写入 N 时间后下次访问触发异步刷新
- 第 43 行：`asyncReloading` 让 refresh 在独立线程跑，**读线程永远不阻塞**
- 注释说明"和'人'相关的不要用本方法"——因为本地缓存无法跨进程，权限类数据要用 Redis

### 3.2 同步刷新版本（与 ThreadLocal 兼容）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/cache/CacheUtils.java`
**核心代码**（行 53-59）：

```java
public static <K, V> LoadingCache<K, V> buildCache(Duration duration, CacheLoader<K, V> loader) {
    return CacheBuilder.newBuilder()
            .maximumSize(CACHE_MAX_SIZE)
            // 只阻塞当前数据加载线程，其他线程返回旧值
            .refreshAfterWrite(duration)
            .build(loader);
}
```

**解读**：
- 同步刷新版本：刷新动作阻塞读线程
- 适用场景：与 ThreadLocal 相关（如用户身份），不能跨线程异步

### 3.3 ruoyi 的缓存 key 设计建议

从 ruoyi 业务代码常见 pattern 总结：
- `user:{id}`：单条用户
- `user:list:{tenantId}`：租户用户列表
- `dict:{type}`：字典项
- `permission:{userId}`：权限

命名规范：**业务域:实体名:标识**，冒号分割（与 Redis key 习惯一致）。

## 4. 关键要点总结

- ruoyi 用本地缓存（Guava `CacheBuilder`）处理"全局字典"等共享数据
- 用 Redis 缓存处理"用户、权限、配置"等需要跨实例的数据
- `asyncReloading` 保证读线程零阻塞
- 缓存 key 命名规范：`业务域:实体名:标识`

## 5. 练习题

### 练习 1：基础（必做）

判断以下场景用本地缓存还是 Redis 缓存：
1. 汇率（每天更新一次）
2. 用户登录态
3. 字典项（性别、状态）
4. 短信验证码

### 练习 2：进阶

阅读 `CacheUtils.buildAsyncReloadingCache`，解释为什么"和'人'相关"的数据不能用这个方法？给出具体反例。

### 练习 3：挑战（选做）

为"商品详情"接口设计缓存策略：要求 1 分钟 TTL，写操作后立即失效，多实例一致。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/util/cache/CacheUtils.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13