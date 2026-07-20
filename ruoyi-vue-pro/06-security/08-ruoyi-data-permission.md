# 29 ruoyi 的数据权限实现

> 详解 ruoyi 数据权限的完整实现：DataPermissionRule → RuleFactory → Handler → 拦截器。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握数据权限的完整调用链路
- 理解 `DataPermissionRule` 接口设计
- 知道 `DataPermissionRuleFactory` 如何管理多个规则
- 能为新业务表注册数据权限规则

## 📚 前置知识

- RBAC 与资源范围控制（详见 [RBAC](../../_common/08-authorization/01-rbac.md)、[资源所有权](../../_common/08-authorization/04-resource-ownership.md)）
- 多租户隔离（详见 [多租户](../../_common/08-authorization/05-multi-tenant.md)）
- MyBatis-Plus 数据权限插件（详见 [数据权限](../03-spring-boot-starters/12-data-permission.md)、[数据权限注解](../03-spring-boot-starters/30-data-permission-annotation.md)）

## 1. 核心概念

### 1.1 数据权限的整体架构

```
SQL 执行
    ↓
MyBatis-Plus DataPermissionInterceptor 拦截
    ↓
DataPermissionRuleHandler.getSqlSegment()
    ↓
DataPermissionRuleFactory.getDataPermissionRule(mapperId)
    ├─ 找到所有 DataPermissionRule Bean
    └─ 返回该 Mapper 关联的规则列表
    ↓
遍历调用 rule.getExpression(tableName, tableAlias)
    ↓
DeptDataPermissionRule 等具体规则
    ├─ 计算该用户的 deptIds
    └─ 返回 JSqlParser Expression
    ↓
Handler 拼接所有 Expression
    ↓
加入 SQL 的 WHERE 条件
    ↓
执行最终的 SQL
```

### 1.2 DataPermissionRule 接口

```java
public interface DataPermissionRule {
    Set<String> getTableNames();
    Expression getExpression(String tableName, Alias tableAlias);
}
```

- `getTableNames()`：规则应用的表名集合
- `getExpression()`：生成 WHERE 条件的 JSqlParser AST 节点

### 1.3 自动注册

ruoyi 通过 `DeptDataPermissionRuleCustomizer` 自动注册：

```java
public class DeptDataPermissionRuleCustomizer implements DataPermissionRuleCustomizer {
    @Override
    public void customize(DeptDataPermissionRule rule) {
        // 自动注册需要数据权限的表
        rule.addDeptColumn(OrderDO.class);
        rule.addUserColumn(OrderDO.class);
    }
}
```

## 2. 代码示例

### 2.1 简化版数据权限实现

```java
// 文件：DataPermissionAspect.java
@Aspect
@Component
public class DataPermissionAspect {

    @Around("@annotation(dataPermission)")
    public Object around(ProceedingJoinPoint joinPoint, DataPermission dataPermission) throws Throwable {
        // 1. 查当前用户的数据权限
        Long userId = SecurityFrameworkUtils.getLoginUserId();
        DataPermissionContext context = dataPermissionService.getContext(userId);

        // 2. 放入 ThreadLocal
        DataPermissionContextHolder.set(context);

        try {
            return joinPoint.proceed();
        } finally {
            DataPermissionContextHolder.clear();
        }
    }
}
```

## 3. 关键要点总结

- 数据权限的链路：Handler → RuleFactory → Rule → Expression
- 多个规则用 **AND 拼接**（不是 OR）
- `DeptDataPermissionRule` 通过 `Customizer` 模式自动注册业务表
- 数据权限结果**缓存**在 `LoginUser.context`
- 跨租户时跳过数据权限

---

**文档版本**：v1.0
**最后更新**：2026-07-13
