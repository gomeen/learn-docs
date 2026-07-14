# 22 ruoyi 多租户实现原理

> 详解 ruoyi 多租户的整体架构：Web Filter → 拦截器 → 业务层。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 多租户的完整调用链路
- 理解 `TenantContextHolder`、`TenantContextWebFilter`、`TenantDatabaseInterceptor` 三者的关系
- 知道多租户相关的所有组件
- 能独立排查"多租户 SQL 没生效"的问题

## 📚 前置知识

- 21-multi-tenant.md
- Spring Filter 机制
- MyBatis-Plus 拦截器

## 1. 核心概念

### 1.1 整体架构

```
HTTP 请求（带 tenant-id Header）
    ↓
TenantContextWebFilter
    ├─ 从 Header 拿 tenantId
    └─ 放入 TenantContextHolder（ThreadLocal）
    ↓
TokenAuthenticationFilter
    ├─ 解析 Token，验证用户
    └─ 设置 LoginUser（含 tenantId）到 SecurityContext
    ↓
Controller / Service
    ↓
MyBatis 执行 SQL
    ↓
TenantLineInnerInterceptor
    ├─ 调用 TenantDatabaseInterceptor.getTenantId()
    │   → 从 ThreadLocal 拿 tenantId
    ├─ 调用 TenantDatabaseInterceptor.ignoreTable()
    │   → 判断表是否要加 tenant_id
    └─ 在 SQL 中加 "WHERE tenant_id = ?"
    ↓
执行最终 SQL
```

### 1.2 核心组件清单

| 组件 | 位置 | 作用 |
|------|------|------|
| `TenantContextHolder` | 上下文 | 存 tenantId（ThreadLocal） |
| `TenantContextWebFilter` | Web 层 | 从 Header 解析 tenantId |
| `TenantDatabaseInterceptor` | SQL 层 | 拦截 SQL 加 tenant_id |
| `TenantIgnore` | 注解 | 标记忽略租户隔离 |
| `TenantIgnoreAspect` | AOP | 处理 `@TenantIgnore` |
| `TenantProperties` | 配置 | 租户相关配置 |
| `TenantBaseDO` | 实体基类 | 自动启用租户隔离 |
| `TenantUtils` | 工具类 | 临时切换/忽略租户 |

## 2. 代码示例

### 2.1 整体使用示例

```java
// 1. 业务实体继承 TenantBaseDO（自动开启租户隔离）
@Data
@EqualsAndHashCode(callSuper = true)
public class OrderDO extends TenantBaseDO {
    private String orderNo;
    private BigDecimal amount;
}

// 2. 业务代码（自动加 tenant_id）
@Service
public class OrderService {
    public List<OrderDO> listOrders() {
        // SQL 自动变成：SELECT * FROM order WHERE tenant_id = ?
        return orderMapper.selectList();
    }
}

// 3. 临时忽略租户
@TenantIgnore  // 整个方法忽略
public void syncAllOrders() {
    // SQL 不加 tenant_id
    orderMapper.selectList();
}

TenantUtils.executeIgnore(() -> {
    // 这个 Runnable 内的代码忽略租户
    orderMapper.selectList();
});
```

## 3. ruoyi 仓库源码解读

### 3.1 完整启动配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/config/YudaoTenantAutoConfiguration.java`

```java
@AutoConfiguration
@ConditionalOnClass(MybatisPlusInterceptor.class)  // 只有引入 MyBatis-Plus 才生效
@EnableConfigurationProperties(TenantProperties.class)
public class YudaoTenantAutoConfiguration {

    @Bean
    public TenantDatabaseInterceptor tenantDatabaseInterceptor(TenantProperties properties) {
        return new TenantDatabaseInterceptor(properties);
    }

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor(TenantDatabaseInterceptor tenantInterceptor) {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
        interceptor.addInnerInterceptor(new TenantLineInnerInterceptor(tenantInterceptor));
        return interceptor;
    }

    @Bean
    public FilterRegistrationBean<TenantContextWebFilter> tenantContextWebFilter() {
        FilterRegistrationBean<TenantContextWebFilter> bean = new FilterRegistrationBean<>();
        bean.setFilter(new TenantContextWebFilter());
        bean.setOrder(-100);  // 优先级最高
        return bean;
    }
}
```

**解读**：
- `@ConditionalOnClass(MybatisPlusInterceptor.class)`：只在引入 MyBatis-Plus 时生效
- 创建 `TenantDatabaseInterceptor` 并注册到 MyBatis-Plus
- 创建 `TenantContextWebFilter` 并注册为 Web Filter（顺序 -100，最高优先级）

### 3.2 完整调用链详解

**Step 1：HTTP 请求进入**
```
GET /admin-api/system/user/list
Header: tenant-id: 1
```

**Step 2：TenantContextWebFilter 执行**
**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/web/TenantContextWebFilter.java`
**核心代码**（行 19-37）：

```java
public class TenantContextWebFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        // 1. 设置：从 Header / Attribute 拿 tenantId
        Long tenantId = WebFrameworkUtils.getTenantId(request);
        if (tenantId != null) {
            TenantContextHolder.setTenantId(tenantId);
        }
        try {
            // 2. 继续过滤链
            chain.doFilter(request, response);
        } finally {
            // 3. 清理 ThreadLocal
            TenantContextHolder.clear();
        }
    }
}
```

**Step 3：业务执行 SQL**
```java
// Service 层
public List<UserDO> listUsers() {
    return userMapper.selectList();  // 简单调用
}
```

**Step 4：TenantLineInnerInterceptor 拦截**
```java
// 原始 SQL: SELECT * FROM system_user
// 变成: SELECT * FROM system_user WHERE tenant_id = 1
```

### 3.3 TenantContextHolder 跨线程问题

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/context/TenantContextHolder.java`
**核心代码**（行 11-22）：

```java
public class TenantContextHolder {

    /**
     * 当前租户编号
     */
    private static final ThreadLocal<Long> TENANT_ID = new TransmittableThreadLocal<>();
    // ...
}
```

**为什么用 `TransmittableThreadLocal`？**
- 普通 `ThreadLocal` 在 `@Async` 异步线程中**会丢值**
- `TransmittableThreadLocal` 是阿里开源的，**可以跨线程传递**
- ruoyi 的 `@TenantJob`、`@TenantIgnore` 配合使用，解决异步任务中的租户问题

### 3.4 异步任务支持

`@TenantJob` 注解用于异步任务，**自动恢复租户上下文**：

```java
// 文件：TenantJobAspect.java（推测）
@Around("@annotation(tenantJob)")
public Object around(ProceedingJoinPoint joinPoint, TenantJob tenantJob) throws Throwable {
    Long tenantId = tenantJob.tenantId();
    Boolean oldIgnore = TenantContextHolder.isIgnore();
    try {
        TenantContextHolder.setTenantId(tenantId);
        return joinPoint.proceed();
    } finally {
        TenantContextHolder.setIgnore(oldIgnore);
        TenantContextHolder.setTenantId(null);
    }
}
```

## 4. 关键要点总结

- 多租户三大组件：`TenantContextHolder`（上下文）+ `TenantContextWebFilter`（Web 层）+ `TenantDatabaseInterceptor`（SQL 层）
- 用 `TransmittableThreadLocal` 解决 `@Async` 跨线程问题
- `TenantBaseDO` 是"自动开启租户隔离"的标记
- `@TenantIgnore` + `@TenantJob` 配合，处理异步场景
- 配置类 `YudaoTenantAutoConfiguration` 统一装配

## 5. 练习题

### 练习 1：基础（必做）

画出 ruoyi 多租户的完整调用链图，标注每个组件的位置（Web / Security / AOP / MyBatis）。

### 练习 2：进阶

解释为什么 ruoyi 用 `TransmittableThreadLocal` 而不是普通 `ThreadLocal`？如果用普通 `ThreadLocal`，异步任务会出什么问题？

### 练习 3：挑战（选做）

排查"多租户 SQL 没生效"的可能原因（至少 5 个）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/config/YudaoTenantAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/web/TenantContextWebFilter.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/db/TenantDatabaseInterceptor.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
