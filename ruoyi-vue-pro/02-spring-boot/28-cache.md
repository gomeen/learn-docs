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
- 26-async.md

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

## 3. 关键要点总结

- **Spring Cache 是抽象**，不绑定具体实现
- **3 个核心注解**：`@Cacheable`（查）、`@CachePut`（改）、`@CacheEvict`（删）
- **启用**：`@EnableCaching` + `CacheManager` Bean
- **ruoyi 用 Redis** 作为缓存后端
- **关键设计**：
  - 单冒号 Key 前缀（避免 RDM 多余空格）
  - 事务感知（避免脏读）
  - 自定义 `TimeoutRedisCacheManager`（支持每 cacheName 单独 TTL）
- **三大问题**：穿透、击穿、雪崩（策略见上文 Sighting 链接）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
