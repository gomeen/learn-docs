# 2.5 数据权限（data-permission）实现

> 深入理解 ruoyi 的数据权限机制，能自定义部门/个人数据权限规则。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ruoyi 数据权限的 4 种模式（全部、本部门、本部门及下级、本人）
- 掌握 `@DataPermission` 注解的工作原理
- 理解 `DataPermissionRule` 接口与 `DeptDataPermissionRule` 实现
- 能自定义数据权限规则（如按项目、按区域）

## 📚 前置知识

- [10-pagination.md](./10-pagination.md)
- AOP 基础（MethodInterceptor、Advisor；详见 [03-aop](../02-spring-boot/03-aop.md)）
- JSqlParser 库（用于 SQL 解析）
- 授权模型见 [RBAC](../../_common/08-authorization/01-rbac.md) / [资源归属](../../_common/08-authorization/04-resource-ownership.md)

## 1. 核心概念

### 1.1 什么是数据权限？

**数据权限** 控制用户能"看到"哪些行（Row-Level Security），不同于"功能权限"控制"哪些按钮"（功能权限见 [24-preauthorize](./29-preauthorize.md) / [RBAC](../../_common/08-authorization/01-rbac.md)）。

例如：销售部经理只能看到销售部的订单。

### 1.2 ruoyi 的 5 种数据权限

| 模式 | 含义 | SQL 过滤 |
|------|------|---------|
| 全部 (ALL) | 看所有数据 | 无 |
| 本部门 (DEPT) | 仅本部门 | `dept_id = ?` |
| 本部门及下级 (DEPT_AND_CHILD) | 本部门 + 子部门 | `dept_id IN (...)` |
| 本人 (SELF) | 仅自己创建 | `creator = ?` |
| 自定义 (CUSTOM) | 通过规则类实现 | 自定义 |

### 1.3 ruoyi 数据权限的核心组件

| 组件 | 作用 |
|------|------|
| `@DataPermission` 注解 | 标记方法/类需要数据权限 |
| `DataPermissionContextHolder` | 栈式 ThreadLocal 存放注解 |
| `DataPermissionRuleHandler` | 拦截 SQL，追加过滤条件 |
| `DataPermissionRule` | 规则接口 |
| `DeptDataPermissionRule` | 默认的"部门"实现 |
| `DeptDataPermissionRuleCustomizer` | 业务方扩展 |

## 2. 代码示例

### 2.1 在 Service 方法上添加注解

```java
@Service
public class OrderServiceImpl implements OrderService {

    @Override
    @DataPermission(enable = true)  // 显式开启
    public PageResult<OrderDO> getOrderPage(OrderPageReqVO req) {
        return orderMapper.selectPage(req, new LambdaQueryWrapperX<OrderDO>()
                .eqIfPresent(OrderDO::getStatus, req.getStatus()));
    }
}
```

### 2.2 关闭某个方法的权限

```java
@Override
@DataPermission(enable = false)  // 关闭数据权限
public List<OrderDO> getAllOrdersForExport() {
    return orderMapper.selectList();
}
```

### 2.3 配置用户的部门权限

```java
// 后台管理页面：给用户配置
permissionApi.getDeptDataPermission(userId);
// 返回 DeptDataPermissionRespDTO { all: false, self: true, deptIds: [1,2,3] }
```

## 3. 关键要点总结

- **数据权限 = 拦截器 + JSqlParser + ThreadLocal**
- **`@DataPermission`** 注解 + **`DeptDataPermissionRule`** 规则
- **JsqlParser 解析 SQL**后改写，**应用层无感知**
- **ThreadLocal 栈**支持嵌套调用
- **ruoyi 提供了 DeptDataPermissionRuleCustomizer** 让业务方扩展

---

**文档版本**：v1.0
**最后更新**：2026-07-13
