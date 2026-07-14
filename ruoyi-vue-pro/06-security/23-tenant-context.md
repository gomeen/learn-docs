# 23 TenantContext 租户上下文

> 详解 ruoyi 的 `TenantContextHolder` 设计与 `TransmittableThreadLocal` 跨线程传递。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `TenantContextHolder` 的所有 API
- 理解 `TransmittableThreadLocal` 的原理
- 知道如何在业务代码中切换/忽略租户
- 能用 `TenantUtils` 工具类处理复杂场景

## 📚 前置知识

- 21-multi-tenant.md
- 22-ruoyi-tenant.md
- ThreadLocal 原理
- Java 异步编程

## 1. 核心概念

### 1.1 TenantContextHolder 核心方法

```java
public class TenantContextHolder {
    public static Long getTenantId();
    public static Long getRequiredTenantId();  // 不存在抛异常
    public static void setTenantId(Long tenantId);
    public static boolean isIgnore();
    public static void setIgnore(Boolean ignore);
    public static void clear();
}
```

### 1.2 为什么用 TransmittableThreadLocal？

普通 `ThreadLocal` 在以下场景会丢值：
```java
ThreadLocal<Long> tenantId = new ThreadLocal<>();
tenantId.set(1L);  // 主线程设置

new Thread(() -> {
    Long t = tenantId.get();  // 子线程拿到 null
}).start();

CompletableFuture.runAsync(() -> {
    Long t = tenantId.get();  // 异步线程拿到 null
});
```

`TransmittableThreadLocal`（Alibaba 开源）：
- 在线程切换时**自动捕获和恢复**值
- 需要配合 `TtlExecutors.getTtlExecutorService(executor)` 使用

### 1.3 三种使用模式

| 模式 | 场景 | API |
|------|------|-----|
| 隐式注入 | 正常 Controller / Service | 自动从 Header / Token 拿 |
| 显式设置 | 自定义场景 | `TenantContextHolder.setTenantId(1L)` |
| 临时忽略 | 后台任务 / 跨租户查询 | `@TenantIgnore` / `TenantUtils.executeIgnore()` |

## 2. 代码示例

### 2.1 基本使用

```java
// 文件：DemoService.java
@Service
public class DemoService {

    public void doSomething() {
        // 1. 获取当前租户 ID
        Long tenantId = TenantContextHolder.getTenantId();
        if (tenantId == null) {
            throw new ServiceException("租户上下文未设置");
        }

        // 2. 临时切换租户
        Long oldTenantId = TenantContextHolder.getTenantId();
        try {
            TenantContextHolder.setTenantId(999L);
            // SQL 自动加 WHERE tenant_id = 999
            orderMapper.selectList();
        } finally {
            TenantContextHolder.setTenantId(oldTenantId);
        }

        // 3. 临时忽略租户
        TenantContextHolder.setIgnore(true);
        try {
            // SQL 不加 tenant_id
            orderMapper.selectList();
        } finally {
            TenantContextHolder.setIgnore(false);
        }
    }
}
```

### 2.2 异步任务中的租户

```java
// 文件：AsyncService.java
@Service
public class AsyncService {

    @Async
    public void asyncMethod() {
        // ❌ 错误：普通 ThreadLocal 在异步线程拿不到
        // Long tenantId = TenantContextHolder.getTenantId();  // null

        // ✅ 正确：用 TransmittableThreadLocal 自动传递
        Long tenantId = TenantContextHolder.getTenantId();  // 1L
        log.info("异步任务中的 tenantId = {}", tenantId);
    }
}
```

**为什么能拿到？** 因为 ruoyi 配置了 `TaskDecorator`，自动捕获和恢复 ThreadLocal。

## 3. ruoyi 仓库源码解读

### 3.1 TenantContextHolder 完整实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/context/TenantContextHolder.java`
**核心代码**（行 11-68）：

```java
public class TenantContextHolder {

    /**
     * 当前租户编号
     */
    private static final ThreadLocal<Long> TENANT_ID = new TransmittableThreadLocal<>();

    /**
     * 是否忽略租户
     */
    private static final ThreadLocal<Boolean> IGNORE = new TransmittableThreadLocal<>();

    /**
     * 获得租户编号
     */
    public static Long getTenantId() {
        return TENANT_ID.get();
    }

    /**
     * 获得租户编号。如果不存在，则抛出 NullPointerException 异常
     */
    public static Long getRequiredTenantId() {
        Long tenantId = getTenantId();
        if (tenantId == null) {
            throw new NullPointerException("TenantContextHolder 不存在租户编号！可参考文档："
                + DocumentEnum.TENANT.getUrl());
        }
        return tenantId;
    }

    public static void setTenantId(Long tenantId) {
        TENANT_ID.set(tenantId);
    }

    public static void setIgnore(Boolean ignore) {
        IGNORE.set(ignore);
    }

    /**
     * 当前是否忽略租户
     */
    public static boolean isIgnore() {
        return Boolean.TRUE.equals(IGNORE.get());
    }

    public static void clear() {
        TENANT_ID.remove();
        IGNORE.remove();
    }
}
```

**解读**：
- 第 16 行 `TransmittableThreadLocal` 替代普通 `ThreadLocal`
- 第 21 行 `IGNORE` 是独立的 ThreadLocal，可以单独控制
- 第 37-44 行 `getRequiredTenantId()`：不存在时抛 NPE 并提示文档
- 第 63-66 行 `clear()`：请求结束时清理（由 `TenantContextWebFilter.finally` 调用）

### 3.2 TenantContextWebFilter 中的清理

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/web/TenantContextWebFilter.java`
**核心代码**（行 19-37）：

```java
public class TenantContextWebFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        // 1. 设置：从 Header 拿 tenantId
        Long tenantId = WebFrameworkUtils.getTenantId(request);
        if (tenantId != null) {
            TenantContextHolder.setTenantId(tenantId);
        }
        try {
            // 2. 继续过滤链
            chain.doFilter(request, response);
        } finally {
            // 3. 清理 ThreadLocal（防内存泄漏 + 防跨请求污染）
            TenantContextHolder.clear();
        }
    }
}
```

**关键作用**：
- **必须清理**！否则下一个请求会读到上次的 tenantId
- Tomcat 线程池复用线程，不清理会导致严重 bug

### 3.3 TenantUtils 工具类（推测）

```java
public class TenantUtils {

    /**
     * 在忽略租户的情况下执行 Runnable
     */
    public static void executeIgnore(Runnable runnable) {
        Boolean oldIgnore = TenantContextHolder.isIgnore();
        try {
            TenantContextHolder.setIgnore(true);
            runnable.run();
        } finally {
            TenantContextHolder.setIgnore(oldIgnore);
        }
    }

    /**
     * 在指定租户下执行 Runnable
     */
    public static void execute(Long tenantId, Runnable runnable) {
        Long oldTenantId = TenantContextHolder.getTenantId();
        Boolean oldIgnore = TenantContextHolder.isIgnore();
        try {
            TenantContextHolder.setTenantId(tenantId);
            TenantContextHolder.setIgnore(false);
            runnable.run();
        } finally {
            TenantContextHolder.setTenantId(oldTenantId);
            TenantContextHolder.setIgnore(oldIgnore);
        }
    }
}
```

## 4. 关键要点总结

- `TenantContextHolder` 用 `TransmittableThreadLocal` 存租户 ID，**支持跨线程**
- `WebFilter` 负责在请求开始时设置、结束时清理
- `getRequiredTenantId()` 在租户未设置时抛 NPE
- `IGNORE` 是独立的 ThreadLocal，可单独控制"忽略"
- **必须清理** ThreadLocal，否则线程复用会导致 bug

## 5. 练习题

### 练习 1：基础（必做）

写一个测试：主线程设置 `ThreadLocal`，用 `Thread` 启动子线程，子线程能否拿到值？换成 `TransmittableThreadLocal` + `TtlExecutors` 呢？

### 练习 2：进阶

实现一个 `@TenantSwitch` 注解，可以在方法参数里指定租户 ID：
```java
@TenantSwitch(tenantId = 999L)
public void syncOrder(Long orderId) {
    // 临时切换到租户 999
    orderMapper.selectById(orderId);
}
```

### 练习 3：挑战（选做）

`TransmittableThreadLocal` 需要 JDK 的 `InheritableThreadLocal` 支持，且必须在 `Thread` 创建前设置。如果使用 `ForkJoinPool`（CompletableFuture 默认池），会怎样？

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/context/TenantContextHolder.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/web/TenantContextWebFilter.java`
- TransmittableThreadLocal：https://github.com/alibaba/transmittable-thread-local

---

**文档版本**：v1.0
**最后更新**：2026-07-13
