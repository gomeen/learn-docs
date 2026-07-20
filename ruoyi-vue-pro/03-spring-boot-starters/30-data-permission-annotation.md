# 4.7 数据权限：@DataPermission

> 深入理解 yudao 的 `@DataPermission` 注解，能在业务中灵活使用数据权限。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `@DataPermission` 注解的所有配置
- 理解 `includeRules` 与 `excludeRules` 的区别
- 能在 Service 层用 `@DataPermission` 控制数据访问
- 了解多租户与数据权限的关系

## 📚 前置知识

- [12-data-permission.md](./12-data-permission.md)
- [29-preauthorize.md](./29-preauthorize.md)
- AOP 原理（详见 [03-aop](../02-spring-boot/03-aop.md)）

## 1. 核心概念

### 1.1 @DataPermission 注解字段

```java
public @interface DataPermission {
    boolean enable() default true;
    Class<? extends DataPermissionRule>[] includeRules() default {};
    Class<? extends DataPermissionRule>[] excludeRules() default {};
}
```

| 字段 | 作用 |
|------|------|
| `enable` | 是否开启数据权限（默认 `true`） |
| `includeRules` | 包含的规则类（**优先级高**） |
| `excludeRules` | 排除的规则类（**优先级低**） |

### 1.2 includeRules vs excludeRules

- **includeRules** 指定：只用哪些规则
- **excludeRules** 指定：不用哪些规则
- 都为空时：用**所有**已注册的规则

### 1.3 典型场景

```java
// 场景 1：完全关闭
@DataPermission(enable = false)

// 场景 2：只用部门规则
@DataPermission(includeRules = DeptDataPermissionRule.class)

// 场景 3：排除部门规则（用其他规则）
@DataPermission(excludeRules = DeptDataPermissionRule.class)
```

## 2. 代码示例

### 2.1 Service 启用数据权限

```java
@Service
public class OrderServiceImpl implements OrderService {
    // 默认开启数据权限
    @Override
    public PageResult<OrderDO> getOrderPage(OrderPageReqVO req) {
        return orderMapper.selectPage(req, wrapper);
    }
}
```

### 2.2 关闭数据权限

```java
@Override
@DataPermission(enable = false)  // 关闭
public List<OrderDO> exportAll() {
    return orderMapper.selectList();
}
```

### 2.3 临时切换

```java
public void doSpecial() {
    // 临时关闭：仅当前线程
    DataPermissionContextHolder.add(
        new DataPermissionImpl() {
            public boolean enable() { return false; }
        });
    try {
        // 业务
    } finally {
        DataPermissionContextHolder.remove();
    }
}
```

## 3. 关键要点总结

- **`@DataPermission(enable = false)`** 关闭数据权限
- **`includeRules` / `excludeRules`** 控制规则范围
- **规则 = `DataPermissionRule` 实现**，多个规则 AND 拼接
- **运行时切换**：通过 `DataPermissionContextHolder.add/remove`
- **数据权限 vs 多租户**：前者管"看哪些行"，后者管"完全隔离"

---

**文档版本**：v1.0
**最后更新**：2026-07-13
