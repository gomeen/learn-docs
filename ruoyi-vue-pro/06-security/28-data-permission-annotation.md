# 28 @DataPermission 注解

> 详解 `@DataPermission` 注解：如何在方法、类上声明数据权限规则。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `@DataPermission` 注解的所有属性
- 理解 `DataPermissionContextHolder` 栈式管理
- 知道如何自定义数据权限规则
- 能为新业务表接入数据权限

## 📚 前置知识

- 27-data-permission.md
- 22-ruoyi-tenant.md
- Spring AOP

## 1. 核心概念

### 1.1 @DataPermission 三个属性

```java
public @interface DataPermission {
    boolean enable() default true;
    Class<? extends DataPermissionRule>[] includeRules() default {};
    Class<? extends DataPermissionRule>[] excludeRules() default {};
}
```

| 属性 | 作用 |
|------|------|
| `enable = true` | 启用数据权限（默认） |
| `enable = false` | 关闭数据权限（特殊场景） |
| `includeRules` | 只使用指定的规则（优先级高） |
| `excludeRules` | 排除指定的规则（优先级低） |

### 1.2 ruoyi 的栈式管理

`DataPermissionContextHolder` 用 LinkedList 实现栈：

```java
private static final ThreadLocal<LinkedList<DataPermission>> DATA_PERMISSIONS =
        TransmittableThreadLocal.withInitial(LinkedList::new);
```

**为什么用栈？**
- 嵌套调用：`ServiceA` 调用 `ServiceB` → 入栈、出栈
- 不同方法可以有不同的 `@DataPermission` 配置

### 1.3 三个使用层级

```
类级别：影响所有方法
方法级别：只影响该方法
全局：所有受影响的 Service（默认）
```

## 2. 代码示例

### 2.1 基础使用

```java
// 文件：OrderService.java
@Service
public class OrderService {

    // 默认：所有规则都生效
    public List<OrderDO> listOrders() {
        return orderMapper.selectList();
    }

    // 关闭数据权限
    @DataPermission(enable = false)
    public List<OrderDO> listAllOrders() {
        return orderMapper.selectList();  // 不加 dept_id 条件
    }

    // 只使用指定的规则
    @DataPermission(includeRules = {DeptDataPermissionRule.class})
    public List<OrderDO> listByDeptRule() {
        return orderMapper.selectList();
    }
}
```

### 2.2 类级别

```java
// 文件：StatisticsService.java
@DataPermission(enable = false)  // 整个 Service 不走数据权限
@Service
public class StatisticsService {
    public List<StatisticsDO> summary() {
        return statsMapper.selectList();
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 @DataPermission 注解定义

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/annotation/DataPermission.java`
**核心代码**（行 13-35）：

```java
@Target({ElementType.TYPE, ElementType.METHOD})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface DataPermission {

    /**
     * 当前类或方法是否开启数据权限
     * 即使不添加 @DataPermission 注解，默认是开启状态
     * 可通过设置 enable 为 false 禁用
     */
    boolean enable() default true;

    /**
     * 生效的数据权限规则数组，优先级高于 {@link #excludeRules()}
     */
    Class<? extends DataPermissionRule>[] includeRules() default {};

    /**
     * 排除的数据权限规则数组，优先级最低
     */
    Class<? extends DataPermissionRule>[] excludeRules() default {};
}
```

**解读**：
- 第 13 行：可加在类或方法上
- 第 23 行 `enable = true`：默认开启
- 第 28 行 `includeRules`：只包含（白名单）
- 第 33 行 `excludeRules`：排除（黑名单）

### 3.2 DataPermissionContextHolder 栈式实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/aop/DataPermissionContextHolder.java`
**核心代码**（行 14-72）：

```java
public class DataPermissionContextHolder {

    /**
     * 使用 List 的原因，可能存在方法的嵌套调用
     */
    private static final ThreadLocal<LinkedList<DataPermission>> DATA_PERMISSIONS =
            TransmittableThreadLocal.withInitial(LinkedList::new);

    /**
     * 获得当前的 DataPermission 注解
     */
    public static DataPermission get() {
        return DATA_PERMISSIONS.get().peekLast();
    }

    /**
     * 入栈 DataPermission 注解
     */
    public static void add(DataPermission dataPermission) {
        DATA_PERMISSIONS.get().addLast(dataPermission);
    }

    /**
     * 出栈 DataPermission 注解
     */
    public static DataPermission remove() {
        DataPermission dataPermission = DATA_PERMISSIONS.get().removeLast();
        // 无元素时，清空 ThreadLocal
        if (DATA_PERMISSIONS.get().isEmpty()) {
            DATA_PERMISSIONS.remove();
        }
        return dataPermission;
    }

    /**
     * 获得所有 DataPermission
     */
    public static List<DataPermission> getAll() {
        return DATA_PERMISSIONS.get();
    }

    public static void clear() {
        DATA_PERMISSIONS.remove();
    }
}
```

**解读**：
- 第 19-20 行：栈式管理，**TransmittableThreadLocal 支持跨线程**
- 第 27-29 行 `get()`：拿栈顶（最新入栈的）
- 第 35-37 行 `add()`：入栈
- 第 43-50 行 `remove()`：出栈 + 元素为空时清 ThreadLocal（**关键** — 防内存泄漏）

### 3.3 DataPermissionAnnotationInterceptor AOP

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/aop/DataPermissionAnnotationInterceptor.java`
**核心代码**（行 21-72）：

```java
@DataPermission // 该注解，用于 DATA_PERMISSION_NULL 的空对象
public class DataPermissionAnnotationInterceptor implements MethodInterceptor {

    static final DataPermission DATA_PERMISSION_NULL = DataPermissionAnnotationInterceptor.class.getAnnotation(DataPermission.class);

    @Getter
    private final Map<MethodClassKey, DataPermission> dataPermissionCache = new ConcurrentHashMap<>();

    @Override
    public Object invoke(MethodInvocation methodInvocation) throws Throwable {
        // 1. 入栈
        DataPermission dataPermission = this.findAnnotation(methodInvocation);
        if (dataPermission != null) {
            DataPermissionContextHolder.add(dataPermission);
        }
        try {
            // 2. 执行方法
            return methodInvocation.proceed();
        } finally {
            // 3. 出栈
            if (dataPermission != null) {
                DataPermissionContextHolder.remove();
            }
        }
    }

    private DataPermission findAnnotation(MethodInvocation methodInvocation) {
        // 1. 从缓存中获取
        Method method = methodInvocation.getMethod();
        Object targetObject = methodInvocation.getThis();
        Class<?> clazz = targetObject != null ? targetObject.getClass() : method.getDeclaringClass();
        MethodClassKey methodClassKey = new MethodClassKey(method, clazz);
        DataPermission dataPermission = dataPermissionCache.get(methodClassKey);
        if (dataPermission != null) {
            return dataPermission != DATA_PERMISSION_NULL ? dataPermission : null;
        }
        // 2.1 从方法中获取
        dataPermission = AnnotationUtils.findAnnotation(method, DataPermission.class);
        // 2.2 从类上获取
        if (dataPermission == null) {
            dataPermission = AnnotationUtils.findAnnotation(clazz, DataPermission.class);
        }
        // 2.3 添加到缓存中
        dataPermissionCache.put(methodClassKey, dataPermission != null ? dataPermission : DATA_PERMISSION_NULL);
        return dataPermission;
    }
}
```

**逐行解读**：
- **第 27 行 `DATA_PERMISSION_NULL`**：用 `DataPermissionAnnotationInterceptor` 自己的注解作为"空对象"
- **第 30 行 `dataPermissionCache`**：缓存 method → annotation 映射（**性能优化**，避免每次反射）
- **第 33-48 行 `invoke()`**：
  - 第 35 行：解析注解
  - 第 36-38 行：入栈
  - 第 41-43 行：执行方法
  - 第 44-46 行：出栈
- **第 50-70 行 `findAnnotation()`**：
  - 第 56-61 行：先从缓存查
  - 第 62-66 行：从方法 → 类的顺序找
  - 第 67-69 行：缓存到 `dataPermissionCache`

## 4. 关键要点总结

- `@DataPermission` 可加在类或方法上
- 默认开启数据权限；`enable = false` 关闭
- `DataPermissionContextHolder` 用栈式管理（支持嵌套）
- 注解信息**缓存**到 `ConcurrentHashMap`（性能优化）
- 出栈时空栈自动清理 ThreadLocal

## 5. 练习题

### 练习 1：基础（必做）

写一个 Service，方法上加 `@DataPermission(enable = false)`，对比开启和关闭时的 SQL 差异。

### 练习 2：进阶

实现一个自定义注解 `@DeptDataPermission`（包装 `@DataPermission`），要求自动加 `includeRules = DeptDataPermissionRule.class`。

### 练习 3：挑战（选做）

栈式管理是为了支持嵌套调用。但 `remove()` 时如果 `LinkedList` 为空会自动 `remove()` ThreadLocal。这种实现有没有线程安全风险？

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/annotation/DataPermission.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/aop/DataPermissionContextHolder.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/aop/DataPermissionAnnotationInterceptor.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
