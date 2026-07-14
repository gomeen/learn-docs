# 6.2 多租户：TenantContext / @TenantIgnore

> 深入理解 yudao 多租户的实现，能为业务添加多租户能力。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 yudao 多租户的核心 API
- 理解 `@TenantIgnore` 的使用场景
- 能用 `TenantContextHolder` 在代码中获取/设置租户
- 了解多租户在 MQ/缓存中的传播

## 📚 前置知识

- [11-tenant-interceptor.md](./11-tenant-interceptor.md)
- SaaS 多租户架构

## 1. 核心概念

### 1.1 多租户 API 速查

| API | 作用 |
|------|------|
| `TenantContextHolder.getTenantId()` | 拿当前租户 ID |
| `TenantContextHolder.getRequiredTenantId()` | 必须有租户，否则抛异常 |
| `TenantContextHolder.setTenantId(id)` | 设置租户 |
| `TenantContextHolder.setIgnore(true)` | 临时忽略租户 |
| `@TenantIgnore` | 方法/类级忽略 |
| `TenantBaseDO` | 实体基类（带 tenant_id） |

## 2. 代码示例

### 2.1 获取当前租户

```java
@Service
public class OrderServiceImpl {
    public void createOrder(OrderCreateReq req) {
        // 拿到当前租户
        Long tenantId = TenantContextHolder.getRequiredTenantId();
        OrderDO order = new OrderDO();
        order.setTenantId(tenantId);  // 自动设置（也可不写，BaseDO 自动填充）
        // ...
    }
}
```

### 2.2 临时忽略租户

```java
public void exportAll() {
    TenantContextHolder.setIgnore(true);
    try {
        return orderMapper.selectList();  // 不会加 tenant_id 过滤
    } finally {
        TenantContextHolder.setIgnore(false);
    }
}
```

### 2.3 @TenantIgnore 注解

```java
@Service
public class SysConfigServiceImpl {
    @TenantIgnore  // 字典表不需要租户隔离
    public List<SysConfigDO> getAllConfigs() {
        return configMapper.selectList();
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 TenantContextHolder

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/context/TenantContextHolder.java`
**核心代码**（节选）：

```java
public class TenantContextHolder {
    private static final ThreadLocal<Long> TENANT_ID = TransmittableThreadLocal.withInitial(() -> 0L);
    private static final ThreadLocal<Boolean> IGNORE = new ThreadLocal<>();

    public static void setTenantId(Long tenantId) { TENANT_ID.set(tenantId); }
    public static Long getTenantId() { return TENANT_ID.get(); }
    public static Long getRequiredTenantId() {
        Long tenantId = TENANT_ID.get();
        if (tenantId == null || tenantId == 0L) {
            throw new IllegalStateException("租户 ID 未设置");
        }
        return tenantId;
    }
    public static boolean isIgnore() {
        Boolean ignore = IGNORE.get();
        return ignore != null && ignore;
    }
    public static void setIgnore(Boolean ignore) { IGNORE.set(ignore); }
}
```

### 3.2 @TenantIgnore 注解

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/aop/TenantIgnore.java`

```java
@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface TenantIgnore {
}
```

### 3.3 TenantContextWebFilter

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/web/TenantContextWebFilter.java`

```java
public class TenantContextWebFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain) {
        // 1. 从 Header 拿租户 ID
        Long tenantId = WebFrameworkUtils.getTenantId(request);
        if (tenantId != null) {
            TenantContextHolder.setTenantId(tenantId);
        }
        try {
            chain.doFilter(request, response);
        } finally {
            TenantContextHolder.clear();  // 清理 ThreadLocal
        }
    }
}
```

### 3.4 多租户在缓存中的传播

**TenantRedisCacheManager**（来自 tenant starter）：

```java
public class TenantRedisCacheManager extends RedisCacheManager {
    @Override
    public Cache getCache(String name) {
        Long tenantId = TenantContextHolder.getTenantId();
        if (tenantId != null) {
            name = tenantId + ":" + name;  // key 前缀加租户
        }
        return super.getCache(name);
    }
}
```

**解读**：
- 缓存 key 自动加 `tenantId:` 前缀
- 不同租户的缓存**完全隔离**

### 3.5 多租户在 MQ 中的传播

**TenantRedisMessageInterceptor**（在 [27-message.md](./27-message.md) 已读）：

```java
public class TenantRedisMessageInterceptor implements RedisMessageInterceptor {
    @Override
    public void sendMessageBefore(AbstractRedisMessage message) {
        Long tenantId = TenantContextHolder.getTenantId();
        if (tenantId != null) {
            message.addHeader(HEADER_TENANT_ID, tenantId.toString());
        }
    }
}
```

## 4. 关键要点总结

- **`TenantContextHolder`** 是多租户 API 入口
- **`@TenantIgnore`** 用于不需要租户隔离的方法
- **Web Filter** 从 Header 拿租户 ID
- **缓存 / MQ 自动加租户前缀** 隔离
- **TTL ThreadLocal**支持线程池

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中找到 3 个 `TenantContextHolder` 的使用点，理解租户传递。

### 练习 2：进阶

实现"超级管理员"接口：可以查看所有租户的数据（用 `setIgnore(true)`）。

### 练习 3：挑战（选做）

实现"租户切换"：管理员可以在登录后切换租户，重新加载数据。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/context/TenantContextHolder.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/aop/TenantIgnore.java`
- SaaS 多租户：https://en.wikipedia.org/wiki/Multitenancy

---

**文档版本**：v1.0
**最后更新**：2026-07-13
