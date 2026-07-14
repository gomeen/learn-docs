# 25 @TenantIgnore 忽略租户隔离

> 详解 `@TenantIgnore` 注解：临时跳过租户隔离的三种方式。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `@TenantIgnore` 注解的三种使用场景
- 理解 `TenantIgnoreAspect` 的实现
- 知道 `TenantUtils.executeIgnore()` 与 `@TenantIgnore` 的区别
- 能正确处理"跨租户"和"系统级"操作的 SQL 隔离

## 📚 前置知识

- 21-multi-tenant.md
- 22-ruoyi-tenant.md
- 23-tenant-context.md
- 24-tenant-interceptor.md
- Spring AOP

## 1. 核心概念

### 1.1 三种使用场景

| 场景 | 方式 | 作用范围 |
|------|------|---------|
| 整个方法忽略 | `@TenantIgnore` | Controller / Service 方法 |
| 整个实体类忽略 | `@TenantIgnore` 标在 DO 上 | 该表所有 SQL |
| 代码块忽略 | `TenantUtils.executeIgnore(Runnable)` | Runnable 内 |
| 整个 URL 忽略 | `@TenantIgnore` 标在 Controller 上 | 该 URL 所有方法 |

### 1.2 @TenantIgnore 的两个属性

```java
public @interface TenantIgnore {
    String enable() default "true";  // 支持 SpEL 表达式
}
```

- `enable = "true"`：默认忽略
- `enable = "${my.tenant.ignore}"`：从配置读
- `enable = "#param.ignore"`：从方法参数读

### 1.3 常见需要忽略的场景

- 定时任务清理所有租户的数据
- 系统级别的字典、配置查询
- 跨租户查询（如超管后台）
- 缓存预热（需要读所有租户的数据）

## 2. 代码示例

### 2.1 注解式

```java
// 文件：OrderService.java
@Service
public class OrderService {

    // 整个方法忽略租户
    @TenantIgnore
    public void cleanAllTenants() {
        orderMapper.delete(null);  // 不加 tenant_id
    }

    // 动态启用：根据参数决定
    @TenantIgnore(enable = "#forceClean")
    public void cleanExpiredOrders(boolean forceClean) {
        if (forceClean) {
            // 忽略租户
        } else {
            // 当前租户
        }
    }
}
```

### 2.2 工具类式

```java
// 文件：DemoService.java
@Service
public class DemoService {

    public void complexLogic() {
        // 普通租户隔离
        orderMapper.selectList();

        // 临时忽略
        TenantUtils.executeIgnore(() -> {
            // 这里面的 SQL 不加 tenant_id
            orderMapper.selectList();
        });

        // 又恢复租户隔离
        orderMapper.selectList();
    }
}
```

### 2.3 实体类级

```java
// 文件：DictDO.java
@TenantIgnore  // 字典表不需要租户隔离
@Data
@TableName("system_dict")
public class DictDO {
    private String key;
    private String value;
}
```

## 3. ruoyi 仓库源码解读

### 3.1 @TenantIgnore 注解定义

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/aop/TenantIgnore.java`
**核心代码**（行 20-32）：

```java
@Target({ElementType.METHOD, ElementType.TYPE})
@Retention(RetentionPolicy.RUNTIME)
@Inherited
public @interface TenantIgnore {

    /**
     * 是否开启忽略租户，默认为 true 开启
     *
     * 支持 Spring EL 表达式，如果返回 true 则满足条件，进行租户的忽略
     */
    String enable() default "true";

}
```

**解读**：
- 第 20 行：可加在方法或类上
- 第 30 行：默认 `true` 开启忽略
- **特殊用法**：
  - 加在 Controller 类上 → 该 URL 自动加入 `TenantProperties.getIgnoreUrls()`
  - 加在 DO 实体类上 → 该表名相当于加入 `TenantProperties.getIgnoreTables()`

### 3.2 TenantIgnoreAspect 实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/aop/TenantIgnoreAspect.java`
**核心代码**（行 20-41）：

```java
@Aspect
@Slf4j
public class TenantIgnoreAspect {

    @Around("@annotation(tenantIgnore)")
    public Object around(ProceedingJoinPoint joinPoint, TenantIgnore tenantIgnore) throws Throwable {
        Boolean oldIgnore = TenantContextHolder.isIgnore();
        try {
            // 1. 计算条件：解析 SpEL 表达式
            Object enable = SpringExpressionUtils.parseExpression(tenantIgnore.enable());
            if (Boolean.TRUE.equals(enable)) {
                // 2. 设置 IGNORE=true
                TenantContextHolder.setIgnore(true);
            }

            // 3. 执行方法
            return joinPoint.proceed();
        } finally {
            // 4. 恢复原来的状态
            TenantContextHolder.setIgnore(oldIgnore);
        }
    }
}
```

**逐行解读**：
- **第 24 行 `@Around("@annotation(tenantIgnore)")`**：拦截所有标了 `@TenantIgnore` 的方法
- **第 26 行 `oldIgnore = TenantContextHolder.isIgnore()`**：保存当前状态（**关键** — 不保存会覆盖外部设置）
- **第 29 行 `parseExpression(tenantIgnore.enable())`**：解析 SpEL 表达式
  - `"true"` → 解析为 `true`
  - `"${my.config}"` → 从配置读
  - `"#param"` → 从方法参数读
- **第 30-32 行**：如果表达式返回 `true`，设置 `IGNORE=true`
- **第 35 行**：`joinPoint.proceed()` 执行实际方法
- **第 37 行 `finally`**：**关键** — 恢复原来的 `IGNORE` 状态（不影响外部）

### 3.3 实体类 @TenantIgnore 怎么处理

在 `TenantDatabaseInterceptor.computeIgnoreTable()` 中：

```java
private boolean computeIgnoreTable(String tableName) {
    TableInfo tableInfo = TableInfoHelper.getTableInfo(tableName);
    if (tableInfo == null) {
        return true;
    }
    if (TenantBaseDO.class.isAssignableFrom(tableInfo.getEntityType())) {
        return false;  // 继承 TenantBaseDO 不忽略
    }
    // 关键：加了 @TenantIgnore 就忽略
    TenantIgnore tenantIgnore = tableInfo.getEntityType().getAnnotation(TenantIgnore.class);
    return tenantIgnore != null;
}
```

**解读**：
- 实体类上的 `@TenantIgnore` 会被 `TenantDatabaseInterceptor.ignoreTable()` 识别
- **不需要写 AOP 拦截器**，因为这是 SQL 层的判断

### 3.4 TenantUtils 工具类（推测实现）

```java
public class TenantUtils {

    /**
     * 在忽略租户的情况下执行
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
     * 在指定租户下执行
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

**与 @TenantIgnore 的区别**：
| 维度 | `@TenantIgnore` | `TenantUtils.executeIgnore()` |
|------|-----------------|-------------------------------|
| 形式 | 注解 | 代码块 |
| 灵活度 | 中（SpEL 表达式） | 高（可编程控制） |
| 适用 | 固定忽略 | 条件性忽略 |

## 4. 关键要点总结

- `@TenantIgnore` 标在方法/类上，自动让该方法/表的 SQL 不加 `tenant_id`
- 支持 SpEL 表达式 `enable`，可动态启用
- `TenantIgnoreAspect` 用 AOP 拦截，在方法前后切换 `IGNORE` 状态
- `finally` 必须恢复状态（不恢复会污染外部）
- 实体类上的 `@TenantIgnore` 由 `TenantDatabaseInterceptor` 在 SQL 层判断

## 5. 练习题

### 练习 1：基础（必做）

写一个 `@TenantIgnore` 注解的方法，调用 `userMapper.delete(null)`，观察 MySQL 慢日志中的 SQL 是否带 `tenant_id`。

### 练习 2：进阶

实现一个 `executeIgnore(Runnable)` 工具类（参照 `TenantUtils`），并写一个测试验证：外部 `IGNORE=false` 时，方法内 SQL 全部租户；方法内 `IGNORE=true` 时，SQL 不加租户；执行后 `IGNORE` 恢复 `false`。

### 练习 3：挑战（选做）

`@TenantIgnore` 用 AOP 实现。如果方法内部又调用了另一个标了 `@TenantIgnore` 的方法，会发生什么？需要"嵌套忽略"功能吗？

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/aop/TenantIgnore.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/aop/TenantIgnoreAspect.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/core/db/TenantDatabaseInterceptor.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
