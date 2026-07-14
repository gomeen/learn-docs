# 30 自定义数据权限规则

> 学习如何为新业务实现自定义数据权限规则。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `DataPermissionRule` 接口的实现方法
- 理解 `DeptDataPermissionRuleCustomizer` 的注册流程
- 能独立实现"按 `region_id` 分区"等自定义规则
- 知道常见的数据权限规则类型

## 📚 前置知识

- 27-data-permission.md
- 28-data-permission-annotation.md
- 29-ruoyi-data-permission.md

## 1. 核心概念

### 1.1 自定义规则的两种方式

| 方式 | 适用场景 |
|------|---------|
| 复用 `DeptDataPermissionRule` + `Customizer` | 字段名是 `dept_id` 或 `user_id` |
| 实现新的 `DataPermissionRule` | 字段名不同（`region_id`）或逻辑完全不同 |

### 1.2 DataPermissionRule 接口

```java
public interface DataPermissionRule {
    /**
     * 返回规则适用的表名集合
     */
    Set<String> getTableNames();

    /**
     * 生成 WHERE 条件
     */
    Expression getExpression(String tableName, Alias tableAlias);
}
```

## 2. 代码示例

### 2.1 复用 DeptDataPermissionRule

```java
// 文件：OrderDataPermissionCustomizer.java
@Component
public class OrderDataPermissionCustomizer implements DeptDataPermissionRuleCustomizer {
    @Override
    public void customize(DeptDataPermissionRule rule) {
        // 1. 标准 dept_id 字段
        rule.addDeptColumn(OrderDO.class);

        // 2. 自定义字段名（部门字段叫 department_id）
        rule.addDeptColumn(OrderDO.class, "department_id");

        // 3. 注册 user_id 字段
        rule.addUserColumn(OrderDO.class);
    }
}
```

### 2.2 自定义 Rule（按 region_id 分区）

```java
// 文件：RegionDataPermissionRule.java
@Component
public class RegionDataPermissionRule implements DataPermissionRule {

    private static final String REGION_COLUMN = "region_id";

    @Resource
    private RegionPermissionApi regionApi;

    @Override
    public Set<String> getTableNames() {
        return Set.of("order", "product");  // 哪些表按 region 过滤
    }

    @Override
    public Expression getExpression(String tableName, Alias tableAlias) {
        // 1. 查当前用户可见的 region 列表
        LoginUser user = SecurityFrameworkUtils.getLoginUser();
        if (user == null) return null;

        Set<Long> regionIds = regionApi.getVisibleRegionIds(user.getId());
        if (regionIds.isEmpty()) {
            return new EqualsTo(null, null);  // 无权限
        }

        // 2. 生成 IN 条件
        Column regionColumn = new Column(tableAlias != null ? tableAlias.getName() : tableName)
                .withColumnName(REGION_COLUMN);
        ExpressionList<LongValue> valueList = new ExpressionList<>(
            regionIds.stream().map(LongValue::new).toList()
        );
        return new InExpression(regionColumn, new ParenthesedExpressionList(valueList));
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 DeptDataPermissionRuleCustomizer 接口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/rule/dept/DeptDataPermissionRuleCustomizer.java`

```java
public interface DeptDataPermissionRuleCustomizer {
    /**
     * 自定义部门数据权限规则
     */
    void customize(DeptDataPermissionRule rule);
}
```

**解读**：
- 这是一个**函数式接口**（Customizer 模式）
- 业务 Module 实现它，注册自己的表
- 多个 Customizer 自动收集（Spring 的 `List<>` 注入）

### 3.2 自动注册示例（系统模块）

```java
// 文件：yudao-module-system 中的 customizer（推测）
@Component
public class SystemDeptDataPermissionRuleCustomizer implements DeptDataPermissionRuleCustomizer {
    @Override
    public void customize(DeptDataPermissionRule rule) {
        // 注册 system 模块的表
        rule.addDeptColumn(UserDO.class);
        rule.addUserColumn(UserDO.class);
        // ... 更多
    }
}
```

### 3.3 DeptDataPermissionRule 的扩展方法

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/rule/dept/DeptDataPermissionRule.java`
**核心代码**（行 179-205）：

```java
// ==================== 添加配置 ====================

public void addDeptColumn(Class<? extends BaseDO> entityClass) {
    addDeptColumn(entityClass, DEPT_COLUMN_NAME);  // 默认 "dept_id"
}

public void addDeptColumn(Class<? extends BaseDO> entityClass, String columnName) {
    String tableName = TableInfoHelper.getTableInfo(entityClass).getTableName();
    addDeptColumn(tableName, columnName);
}

public void addDeptColumn(String tableName, String columnName) {
    deptColumns.put(tableName, columnName);
    TABLE_NAMES.add(tableName);
}

public void addUserColumn(Class<? extends BaseDO> entityClass) {
    addUserColumn(entityClass, USER_COLUMN_NAME);  // 默认 "user_id"
}

// ... 类似的 addUserColumn 方法
```

**解读**：
- 两个层级的 API：
  - 传 `Class`：自动获取表名（从 MyBatis-Plus 注解）
  - 传 `String`：手动指定表名
- 两个重载：默认列名 / 自定义列名

### 3.4 自定义规则的注册

`YudaoDataPermissionAutoConfiguration.deptDataPermissionRule`：

```java
@Bean
public DeptDataPermissionRule deptDataPermissionRule(
        PermissionCommonApi permissionApi,
        List<DeptDataPermissionRuleCustomizer> customizers) {

    DeptDataPermissionRule rule = new DeptDataPermissionRule(permissionApi);

    // 关键：所有 Customizer 自动应用
    customizers.forEach(c -> c.customize(rule));

    return rule;
}
```

**解读**：
- Spring 注入 `List<DeptDataPermissionRuleCustomizer>` 会自动收集所有实现
- 业务 Module 实现这个接口就能扩展

## 4. 关键要点总结

- 两种自定义方式：Customizer（复用）/ 新 Rule（自定义）
- `DeptDataPermissionRuleCustomizer` 用 Spring `List<>` 注入自动收集
- 自定义 Rule 实现 `DataPermissionRule` 接口
- 新规则用 `getExpression` 返回 JSqlParser `Expression`
- 多个规则在 `DataPermissionRuleHandler` 中**AND 拼接**

## 5. 练习题

### 练习 1：基础（必做）

写一个 `OrderDataPermissionCustomizer`，给 `OrderDO` 注册 `dept_id` 字段。

### 练习 2：进阶

实现一个 `ProductDataPermissionRule`，按 `category_id` 分区：管理员可见所有分类，普通用户只看自己负责的分类。说明 `getTableNames` 和 `getExpression` 的实现。

### 练习 3：挑战（选做）

设计"动态数据权限"：管理员可以**配置**每个角色的数据权限规则（如"销售员只能看自己创建的订单"）。需要新增哪些表？如何让数据权限规则可配置？

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/rule/dept/DeptDataPermissionRule.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/rule/dept/DeptDataPermissionRuleCustomizer.java`
- JSqlParser 文档：https://github.com/JSQLParser/JSqlParser/wiki

---

**文档版本**：v1.0
**最后更新**：2026-07-13
