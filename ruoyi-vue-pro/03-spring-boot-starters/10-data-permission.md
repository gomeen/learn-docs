# 2.5 数据权限（data-permission）实现

> 深入理解 ruoyi 的数据权限机制，能自定义部门/个人数据权限规则。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ruoyi 数据权限的 4 种模式（全部、本部门、本部门及下级、本人）
- 掌握 `@DataPermission` 注解的工作原理
- 理解 `DataPermissionRule` 接口与 `DeptDataPermissionRule` 实现
- 能自定义数据权限规则（如按项目、按区域）

## 📚 前置知识

- [09-pagination.md](./09-pagination.md)
- AOP 基础（MethodInterceptor、Advisor；详见 [03-aop](../02-spring-boot/03-aop.md)）
- JSqlParser 库（用于 SQL 解析）
- 授权模型见 [RBAC](../../_common/08-authorization/01-rbac.md) / [资源归属](../../_common/08-authorization/04-resource-ownership.md)

## 1. 核心概念

### 1.1 什么是数据权限？

**数据权限** 控制用户能"看到"哪些行（Row-Level Security），不同于"功能权限"控制"哪些按钮"（功能权限见 [24-preauthorize](./24-preauthorize.md) / [RBAC](../../_common/08-authorization/01-rbac.md)）。

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

## 3. ruoyi 仓库源码解读

### 3.1 @DataPermission 注解

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/annotation/DataPermission.java`
**核心代码**（行 13-35）：

```java
@Target({ElementType.TYPE, ElementType.METHOD})
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface DataPermission {

    boolean enable() default true;

    Class<? extends DataPermissionRule>[] includeRules() default {};

    Class<? extends DataPermissionRule>[] excludeRules() default {};
}
```

**解读**：
- 可声明在类或方法上
- `enable = false` 关闭数据权限
- `includeRules` 优先级高，`excludeRules` 优先级低

### 3.2 DataPermissionContextHolder（栈式 ThreadLocal）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/aop/DataPermissionContextHolder.java`
**核心代码**（行 19-50）：

```java
public class DataPermissionContextHolder {

    private static final ThreadLocal<LinkedList<DataPermission>> DATA_PERMISSIONS =
            TransmittableThreadLocal.withInitial(LinkedList::new);

    public static DataPermission get() {
        return DATA_PERMISSIONS.get().peekLast();  // 取栈顶
    }

    public static void add(DataPermission dataPermission) {
        DATA_PERMISSIONS.get().addLast(dataPermission);  // 入栈
    }

    public static DataPermission remove() {
        DataPermission dataPermission = DATA_PERMISSIONS.get().removeLast();  // 出栈
        if (DATA_PERMISSIONS.get().isEmpty()) {
            DATA_PERMISSIONS.remove();
        }
        return dataPermission;
    }
}
```

**解读**：
- 使用 `LinkedList`（栈）**支持方法嵌套**
- 使用 `TransmittableThreadLocal` 支持**线程池**间的值传递（TTL）
- 每次 Service 方法调用前入栈，结束后出栈

### 3.3 DataPermissionAnnotationInterceptor

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/aop/DataPermissionAnnotationInterceptor.java`
**核心代码**（行 32-50）：

```java
@Override
public Object invoke(MethodInvocation methodInvocation) throws Throwable {
    // 入栈
    DataPermission dataPermission = this.findAnnotation(methodInvocation);
    if (dataPermission != null) {
        DataPermissionContextHolder.add(dataPermission);
    }
    try {
        // 执行逻辑
        return methodInvocation.proceed();
    } finally {
        // 出栈
        if (dataPermission != null) {
            DataPermissionContextHolder.remove();
        }
    }
}
```

**解读**：
- 用 AOP 拦截 Service 方法
- **方法前**：找到注解并入栈
- **方法后**：从栈中移除
- 即使方法异常也会出栈（finally）

### 3.4 DeptDataPermissionRule（核心实现）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/rule/dept/DeptDataPermissionRule.java`
**核心代码**（行 91-145）：

```java
@Override
public Expression getExpression(String tableName, Alias tableAlias) {
    // 1. 没登录用户不处理
    LoginUser loginUser = SecurityFrameworkUtils.getLoginUser();
    if (loginUser == null) return null;

    // 2. 不是管理员不处理（普通用户只能看自己）
    if (ObjectUtil.notEqual(loginUser.getUserType(), UserTypeEnum.ADMIN.getValue())) {
        return null;
    }

    // 3. 获得数据权限配置
    DeptDataPermissionRespDTO deptDataPermission = loginUser.getContext(CONTEXT_KEY, DeptDataPermissionRespDTO.class);
    if (deptDataPermission == null) {
        deptDataPermission = permissionApi.getDeptDataPermission(loginUser.getId());
        loginUser.setContext(CONTEXT_KEY, deptDataPermission);
    }

    // 4. 全部可见
    if (deptDataPermission.getAll()) return null;

    // 5. 没有任何权限
    if (CollUtil.isEmpty(deptDataPermission.getDeptIds())
        && Boolean.FALSE.equals(deptDataPermission.getSelf())) {
        return new EqualsTo(null, null); // WHERE null = null
    }

    // 6. 拼接部门 + 自己的条件
    Expression deptExpression = buildDeptExpression(tableName, tableAlias, deptDataPermission.getDeptIds());
    Expression userExpression = buildUserExpression(tableName, tableAlias, deptDataPermission.getSelf(), loginUser.getId());
    if (deptExpression == null) return userExpression;
    if (userExpression == null) return deptExpression;
    return new ParenthesedExpressionList(new OrExpression(deptExpression, userExpression));
}
```

**解读**：
- 通过 JSqlParser 构建 SQL `Expression`（`WHERE dept_id IN ? OR user_id = ?`）
- **情况 1**：未登录或非管理员 → 不处理（**注意：这里跳过了过滤！需要谨慎**）
- **情况 2**：用户 `all=true` → 不过滤
- **情况 3**：都没权限 → 返回 `WHERE null = null`（永远不返回数据）
- **情况 4**：拼接 dept + user 条件（OR）

### 3.5 DataPermissionRuleHandler（SQL 改写）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/db/DataPermissionRuleHandler.java`
**核心逻辑**（节选）：

```java
public class DataPermissionRuleHandler implements InnerInterceptor {
    @Override
    public void beforeQuery(Executor executor, MappedStatement ms, Object parameter,
                            RowBounds rowBounds, ResultHandler resultHandler, BoundSql boundSql) {
        // 1. 解析 SQL
        Statement statement = CCJSqlParserUtil.parse(boundSql.getSql());
        // 2. 遍历表名
        // 3. 拼接 Expression
        // 4. 重写 SQL
    }
}
```

**解读**：
- 实现了 MP 的 `InnerInterceptor` 接口
- 在 `beforeQuery` 中**改写 SQL**，把 Expression 拼接到 `WHERE` 中

## 4. 关键要点总结

- **数据权限 = 拦截器 + JSqlParser + ThreadLocal**
- **`@DataPermission`** 注解 + **`DeptDataPermissionRule`** 规则
- **JsqlParser 解析 SQL**后改写，**应用层无感知**
- **ThreadLocal 栈**支持嵌套调用
- **ruoyi 提供了 DeptDataPermissionRuleCustomizer** 让业务方扩展

## 5. 练习题

### 练习 1：基础（必做）

阅读 `DeptDataPermissionRule.java` 全文，画出数据权限流程图：用户登录 → Service 调用 → SQL 改写。

### 练习 2：进阶

实现一个 `ProjectDataPermissionRule`，按"项目"过滤：用户只能看到自己参与的项目。复用 `DataPermissionRule` 接口。

### 练习 3：挑战（选做）

实现"租户 + 数据权限"的混合过滤。两者都用 JSqlParser 改写 SQL，需要保证它们能叠加。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/annotation/DataPermission.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/aop/DataPermissionContextHolder.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/rule/dept/DeptDataPermissionRule.java`
- JSqlParser 文档：https://github.com/JSQLParser/JSqlParser

---

**文档版本**：v1.0
**最后更新**：2026-07-13
