# 24 Spring Cache 与缓存抽象

> 掌握 Spring Cache 抽象，能在 ruoyi-vue-pro 中用 `@Cacheable` 提升接口性能。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Spring Cache 抽象（不绑定具体缓存实现）
- 掌握 `@Cacheable`、`@CacheEvict`、`@CachePut` 的使用
- 能在 ruoyi-vue-pro 中读懂 Redis Cache 配置
- 掌握缓存穿透、击穿、雪崩的解决方案

## 📚 前置知识

- 01-ioc.md
- 22-async.md

## 1. 核心概念

### 1.1 Spring Cache 抽象

Spring Cache 不直接提供缓存实现，而是定义一套**缓存接口**（`Cache`、`CacheManager`），底层可以切换：
- **内存**：`ConcurrentMapCacheManager`
- **Redis**：`RedisCacheManager`（ruoyi 默认）
- **Caffeine**：`CaffeineCacheManager`
- **多级**：`CompositeCacheManager`

### 1.2 三个核心注解

| 注解 | 作用 |
|------|------|
| `@Cacheable` | 方法执行前查缓存，有则返回；没有则执行方法，并把结果放入缓存 |
| `@CachePut` | 方法总会执行，并把结果放入缓存（更新缓存） |
| `@CacheEvict` | 方法执行后清除缓存（删除缓存） |

### 1.3 三大缓存问题

> 📌 **Sighting**：穿透 / 击穿 / 雪崩完整策略见 [缓存三大问题](../../_common/03-cache-patterns/02-three-problems.md)；缓存读写策略见 [缓存策略](../../_common/03-cache-patterns/01-strategies.md)。

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| **穿透** | 查询不存在的数据（每次都查 DB） | 缓存空值、布隆过滤器 |
| **击穿** | 热点 key 过期瞬间大量请求 | 分布式锁、逻辑过期 |
| **雪崩** | 大量 key 同时过期 | 过期时间加随机值 |

## 2. 代码示例

### 2.1 基础使用

```java
// 启动类
@SpringBootApplication
@EnableCaching
public class MyApplication { ... }

// Service
@Service
public class UserService {

    @Cacheable(value = "user", key = "#id")
    public UserVO getUser(Long id) {
        log.info("[getUser] 从数据库查询 {}", id);
        return userDao.selectById(id);
    }

    @CacheEvict(value = "user", key = "#id")
    public void deleteUser(Long id) {
        userDao.deleteById(id);
    }

    @CachePut(value = "user", key = "#user.id")
    public UserVO updateUser(UserVO user) {
        userDao.update(user);
        return user;
    }
}
```

### 2.2 条件缓存

```java
@Cacheable(value = "user", key = "#id", condition = "#id > 0")
public UserVO getUser(Long id) { ... }

@Cacheable(value = "user", key = "#id", unless = "#result == null")
public UserVO getUser(Long id) { ... }
```

### 2.3 多级注解

```java
@Caching(
    cacheable = @Cacheable(value = "user", key = "#id"),
    put = @CachePut(value = "user", key = "#result.name")
)
public UserVO getUserById(Long id) { ... }
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 YudaoCacheAutoConfiguration 启用缓存

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
**核心代码**（行 26-40）：

```java
/**
 * Cache 配置类，基于 Redis 实现
 */
@AutoConfiguration
@EnableConfigurationProperties({CacheProperties.class, YudaoCacheProperties.class})
@EnableCaching
public class YudaoCacheAutoConfiguration {

    /**
     * RedisCacheConfiguration Bean
     * <p>
     * 参考 org.springframework.boot.autoconfigure.cache.RedisCacheConfiguration 的 createConfiguration 方法
     */
    @Bean
    @Primary
    public RedisCacheConfiguration redisCacheConfiguration(CacheProperties cacheProperties) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig();
        // 设置使用 : 单冒号，而不是双 :: 冒号，避免 Redis Desktop Manager 多余空格
        // 详细可见 https://blog.csdn.net/chuixue24/article/details/103928965 博客
        // 再次修复单冒号，而不是双 :: 冒号问题，Issues 详情：https://gitee.com/zhijiantianya/yudao-cloud/issues/I86VY2
        config = config.computePrefixWith(cacheName -> {
            String keyPrefix = cacheProperties.getRedis().getKeyPrefix();
            if (StringUtils.hasText(keyPrefix)) {
                keyPrefix = keyPrefix.lastIndexOf(StrUtil.COLON) == -1 ? keyPrefix + StrUtil.COLON : keyPrefix;
                return keyPrefix + cacheName + StrUtil.COLON;
            }
            return cacheName + StrUtil.COLON;
        });
```

**解读**：
- 第 4 行：`@AutoConfiguration` 自动配置
- 第 5 行：同时启用 Spring 内置 `CacheProperties` 和 ruoyi 自定义 `YudaoCacheProperties`
- 第 6 行：`@EnableCaching` 开启 `@Cacheable` 注解支持
- 第 10 行：`@Primary` 标记为主 Bean（多个 `RedisCacheConfiguration` 时优先选这个）
- 第 12 行：默认 Redis 缓存配置
- **第 13-15 行**：关键注释！作者踩过坑——用单冒号 `:` 而不是双冒号 `::`，避免 Redis Desktop Manager 多余空格
- 第 16-24 行：自定义 Key 前缀（`yudao:cache:user:1`），避免与其他系统冲突
- **设计细节**：详细的注释 + Issue 链接，说明这是一个"血泪教训"沉淀下来的最佳实践

### 3.2 CacheManager 配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
**核心代码**（行 70-86）：

```java
@Bean
public RedisCacheManager redisCacheManager(RedisTemplate<String, Object> redisTemplate,
                                           RedisCacheConfiguration redisCacheConfiguration,
                                           YudaoCacheProperties yudaoCacheProperties) {
    // 创建 RedisCacheWriter 对象
    RedisConnectionFactory connectionFactory = Objects.requireNonNull(redisTemplate.getConnectionFactory());
    RedisCacheWriter cacheWriter = RedisCacheWriter.nonLockingRedisCacheWriter(connectionFactory,
            BatchStrategies.scan(yudaoCacheProperties.getRedisScanBatchSize()));
    // 创建 TimeoutRedisCacheManager 对象
    TimeoutRedisCacheManager cacheManager = new TimeoutRedisCacheManager(cacheWriter, redisCacheConfiguration);
    // 开启事务感知：@Transactional 方法内的 @CacheEvict / @CachePut 自动延迟到 afterCommit，
    //             避免事务未提交就清缓存被并发读穿写脏值；无事务时立即生效，行为不变
    cacheManager.setTransactionAware(true);
    return cacheManager;
}
```

**解读**：
- 第 6-7 行：`nonLockingRedisCacheWriter` + `BatchStrategies.scan` 提高批量操作性能
- 第 9 行：`TimeoutRedisCacheManager` 是 ruoyi 自定义的 CacheManager，支持每个 cacheName 单独设置过期时间
- **第 11-12 行** 关键注释：开启**事务感知**（`@Transactional` 详见 [04-transaction](./04-transaction.md)）
  - 在 `@Transactional` 方法内使用 `@CacheEvict` / `@CachePut`
  - 默认会**立即清缓存**，但事务还没提交，其他线程读到的可能是旧值（脏读）
  - 开启事务感知后，**延迟到事务 commit 后再清缓存**
  - 这是"并发读写一致性"的关键设计

### 3.3 ruoyi 中使用缓存的位置

ruoyi 在 `yudao-module-system` 等业务模块中大量使用 `@Cacheable` 缓存字典、配置等数据：

```java
@Service
public class DictServiceImpl {

    @Cacheable(value = "dict", key = "#type")
    public List<DictVO> getDictList(String type) {
        return dictDao.selectByType(type);
    }
}
```

**设计原则**：
- 字典、配置等"读多写少"的数据用 `@Cacheable`
- 业务数据谨慎使用（一致性要求高）
- 关键路径用 `YudaoCacheProperties` 配置短 TTL

## 4. 关键要点总结

- **Spring Cache 是抽象**，不绑定具体实现
- **3 个核心注解**：`@Cacheable`（查）、`@CachePut`（改）、`@CacheEvict`（删）
- **启用**：`@EnableCaching` + `CacheManager` Bean
- **ruoyi 用 Redis** 作为缓存后端
- **关键设计**：
  - 单冒号 Key 前缀（避免 RDM 多余空格）
  - 事务感知（避免脏读）
  - 自定义 `TimeoutRedisCacheManager`（支持每 cacheName 单独 TTL）
- **三大问题**：穿透、击穿、雪崩（策略见上文 Sighting 链接）

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `UserService.getUser(id)`，用 `@Cacheable` 缓存用户信息，启动类加 `@EnableCaching`，第一次查询后再次查询验证走缓存。

### 练习 2：进阶

阅读 `YudaoCacheAutoConfiguration.redisCacheConfiguration`，解释为什么 Key 前缀用单冒号 `:` 而不是双冒号 `::`？

### 练习 3：挑战（选做）

> 学完上文「三大缓存问题」与 [分布式锁](../../_common/04-distributed-locks/02-redis-redlock.md) 后再做：实现一个"防缓存击穿"功能：在 `@Cacheable` 标注的方法上加分布式锁（用 Redisson），缓存过期时只允许一个线程查 DB，其他线程等待。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
- Spring Cache 文档：https://docs.spring.io/spring-framework/reference/integration/cache.html
- 芋道 Spring Cache：https://doc.iocoder.cn/spring-boot-cache/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
