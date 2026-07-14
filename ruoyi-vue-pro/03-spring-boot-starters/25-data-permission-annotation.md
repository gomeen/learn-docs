# 4.7 数据权限：@DataPermission

> 深入理解 yudao 的 `@DataPermission` 注解，能在业务中灵活使用数据权限。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `@DataPermission` 注解的所有配置
- 理解 `includeRules` 与 `excludeRules` 的区别
- 能在 Service 层用 `@DataPermission` 控制数据访问
- 了解多租户与数据权限的关系

## 📚 前置知识

- [10-data-permission.md](./10-data-permission.md)
- [24-preauthorize.md](./24-preauthorize.md)
- AOP 原理

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

## 3. ruoyi 仓库源码解读

### 3.1 @DataPermission 注解

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/annotation/DataPermission.java`
**核心代码**：

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

### 3.2 DataPermissionRule 规则接口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/rule/DataPermissionRule.java`
**核心代码**：

```java
public interface DataPermissionRule {
    /** 规则影响的表名集合 */
    Set<String> getTableNames();
    /** 根据表名/别名返回 SQL 过滤 Expression */
    Expression getExpression(String tableName, Alias tableAlias);
}
```

**解读**：
- 自定义数据权限 = 实现 `DataPermissionRule` 接口
- 多个规则**叠加**（AND 关系）

### 3.3 DataPermissionContextHolder

**核心代码**（已在 [10-data-permission.md](./10-data-permission.md) 详细解读）：

```java
public class DataPermissionContextHolder {
    private static final ThreadLocal<LinkedList<DataPermission>> DATA_PERMISSIONS =
            TransmittableThreadLocal.withInitial(LinkedList::new);

    public static DataPermission get() { return DATA_PERMISSIONS.get().peekLast(); }
    public static void add(DataPermission dataPermission) { DATA_PERMISSIONS.get().addLast(dataPermission); }
    public static DataPermission remove() { return DATA_PERMISSIONS.get().removeLast(); }
}
```

### 3.4 DataPermissionRuleHandler（SQL 改写）

**核心代码**（节选）：

```java
public class DataPermissionRuleHandler implements InnerInterceptor {
    @Override
    public void beforeQuery(...) {
        // 1. 拿到当前 DataPermission 注解
        DataPermission dataPermission = DataPermissionContextHolder.get();
        if (dataPermission == null) return;
        if (!dataPermission.enable()) return;

        // 2. 解析 SQL
        Statement statement = CCJSqlParserUtil.parse(boundSql.getSql());
        PlainSelect selectStatement = (PlainSelect) statement;
        Table table = (Table) selectStatement.getFromItem();

        // 3. 遍历所有 DataPermissionRule
        List<DataPermissionRule> rules = dataPermissionRuleFactory.getDataPermissionRules(table, dataPermission);
        Expression where = selectStatement.getWhere();
        // 4. 拼接所有规则的 Expression
        for (DataPermissionRule rule : rules) {
            Expression expression = rule.getExpression(table.getName(), table.getAlias());
            if (expression == null) continue;
            if (where == null) {
                where = expression;
            } else {
                where = new AndExpression(where, expression);
            }
        }
        // 5. 重写 SQL
        selectStatement.setWhere(where);
        boundSql.setSql(selectStatement.toString());
    }
}
```

**解读**：
- `beforeQuery` 拦截所有 SELECT
- 拿到当前线程的 `DataPermission` 注解
- 通过 `DataPermissionRuleFactory` 拿到匹配的规则
- 多个规则的 Expression 用 **AND** 拼接
- 用 **JsqlParser** 改写 SQL

### 3.5 DeptDataPermissionRule 的 include 配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/rule/dept/DeptDataPermissionRuleCustomizer.java`

业务方通过 `DeptDataPermissionRuleCustomizer` 告诉规则"哪些表的部门字段是什么"：

```java
@Bean
public DeptDataPermissionRuleCustomizer deptDataPermissionRule() {
    return rule -> {
        rule.addDeptColumn(OrderDO.class);     // sys_order.dept_id
        rule.addDeptColumn(UserDO.class, "dept_id");
    };
}
```

## 4. 关键要点总结

- **`@DataPermission(enable = false)`** 关闭数据权限
- **`includeRules` / `excludeRules`** 控制规则范围
- **规则 = `DataPermissionRule` 实现**，多个规则 AND 拼接
- **运行时切换**：通过 `DataPermissionContextHolder.add/remove`
- **数据权限 vs 多租户**：前者管"看哪些行"，后者管"完全隔离"

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中找到 3 个使用 `@DataPermission` 的方法，理解其作用。

### 练习 2：进阶

实现"项目数据权限"：用户只能看到自己参与的项目。继承 `DataPermissionRule` 实现 `ProjectDataPermissionRule`。

### 练习 3：挑战（选做）

在 yudao 中实现"多租户 + 数据权限 + 部门"的三重过滤。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/annotation/DataPermission.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/rule/DataPermissionRule.java`
- JSqlParser 文档：https://github.com/JSQLParser/JSqlParser

---

**文档版本**：v1.0
**最后更新**：2026-07-13
