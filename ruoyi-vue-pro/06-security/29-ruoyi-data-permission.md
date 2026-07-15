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
- MyBatis-Plus 数据权限插件（详见 [数据权限](../03-spring-boot-starters/10-data-permission.md)、[数据权限注解](../03-spring-boot-starters/25-data-permission-annotation.md)）

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

## 3. ruoyi 仓库源码解读

### 3.1 DataPermissionRuleHandler 核心

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/db/DataPermissionRuleHandler.java`
**核心代码**（行 26-64）：

```java
@RequiredArgsConstructor
public class DataPermissionRuleHandler implements MultiDataPermissionHandler {

    private final DataPermissionRuleFactory ruleFactory;

    @Override
    public Expression getSqlSegment(Table table, Expression where, String mappedStatementId) {
        // 1. 特殊：跨租户访问
        if (skipPermissionCheck()) {
            return null;
        }

        // 2. 获得 Mapper 对应的数据权限的规则
        List<DataPermissionRule> rules = ruleFactory.getDataPermissionRule(mappedStatementId);
        if (CollUtil.isEmpty(rules)) {
            return null;
        }

        // 3. 生成条件
        Expression allExpression = null;
        for (DataPermissionRule rule : rules) {
            // 3.1 判断表名是否匹配
            String tableName = MyBatisUtils.getTableName(table);
            if (!rule.getTableNames().contains(tableName)) {
                continue;
            }

            // 3.2 单条规则的条件
            Expression oneExpress = rule.getExpression(tableName, table.getAlias());
            if (oneExpress == null) {
                continue;
            }
            // 3.3 拼接到 allExpression 中
            allExpression = allExpression == null ? oneExpress
                    : new AndExpression(allExpression, oneExpress);
        }
        return allExpression;
    }
}
```

**逐行解读**：
- **第 32-35 行**：跨租户访问时**直接返回 null**（不检查数据权限）
- **第 38-40 行**：通过 `ruleFactory` 拿到这个 Mapper 关联的所有规则
- **第 42-60 行**：遍历所有规则
  - 第 46-48 行：表名匹配检查
  - 第 52-54 行：调用规则生成 Expression
  - 第 57-59 行：**用 AND 拼接所有规则**

### 3.2 DataPermissionRuleFactory 实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/rule/DataPermissionRuleFactory.java`
**核心代码**（推测）：

```java
public interface DataPermissionRuleFactory {
    /**
     * 获得指定 Mapper 的数据权限规则
     */
    List<DataPermissionRule> getDataPermissionRule(String mapperId);
}
```

**实现类**（`DataPermissionRuleFactoryImpl`）：

```java
public class DataPermissionRuleFactoryImpl implements DataPermissionRuleFactory {

    private final List<DataPermissionRule> rules;  // 注入所有规则

    @Override
    public List<DataPermissionRule> getDataPermissionRule(String mapperId) {
        // 返回所有规则（让 Handler 自己过滤表名）
        return rules;
    }
}
```

### 3.3 DeptDataPermissionRule 完整实现

**核心代码**（前面已读，再贴关键部分）：

```java
public class DeptDataPermissionRule implements DataPermissionRule {

    private static final String DEPT_COLUMN_NAME = "dept_id";
    private static final String USER_COLUMN_NAME = "user_id";

    private final Map<String, String> deptColumns = new HashMap<>();
    private final Map<String, String> userColumns = new HashMap<>();
    private final Set<String> TABLE_NAMES = new HashSet<>();

    @Override
    public Set<String> getTableNames() {
        return TABLE_NAMES;
    }

    // 注册部门列
    public void addDeptColumn(Class<? extends BaseDO> entityClass) {
        addDeptColumn(entityClass, DEPT_COLUMN_NAME);
    }

    public void addDeptColumn(Class<? extends BaseDO> entityClass, String columnName) {
        String tableName = TableInfoHelper.getTableInfo(entityClass).getTableName();
        addDeptColumn(tableName, columnName);
    }

    public void addDeptColumn(String tableName, String columnName) {
        deptColumns.put(tableName, columnName);
        TABLE_NAMES.add(tableName);
    }
}
```

**解读**：
- `deptColumns`：表名 → 部门列名（默认 `dept_id`，可自定义）
- `userColumns`：表名 → 用户列名（默认 `user_id`）
- `TABLE_NAMES`：所有需要数据权限的表

### 3.4 DeptDataPermissionRuleCustomizer 注册

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/rule/dept/DeptDataPermissionRuleCustomizer.java`

```java
@Component
public class DeptDataPermissionRuleCustomizer implements DataPermissionRuleCustomizer {

    @Override
    public void customize(DeptDataPermissionRule rule) {
        // 注册需要数据权限的表（业务表）
        rule.addDeptColumn(OrderDO.class);
        rule.addUserColumn(OrderDO.class);
        // ... 更多表
    }
}
```

**解读**：
- 用 `Customizer` 模式：每个业务 Module 可以注册自己的表
- 不需要改 `DeptDataPermissionRule` 本身

### 3.5 自动装配

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/config/YudaoDataPermissionAutoConfiguration.java`

```java
@Bean
public DeptDataPermissionRule deptDataPermissionRule(
        PermissionCommonApi permissionApi,
        List<DeptDataPermissionRuleCustomizer> customizers) {

    // 1. 创建规则
    DeptDataPermissionRule rule = new DeptDataPermissionRule(permissionApi);

    // 2. 应用所有 customizer（自动注册业务表）
    customizers.forEach(c -> c.customize(rule));

    return rule;
}

@Bean
public DataPermissionRuleFactory dataPermissionRuleFactory(List<DataPermissionRule> rules) {
    return new DataPermissionRuleFactoryImpl(rules);
}

@Bean
public MybatisPlusInterceptor mybatisPlusInterceptor(
        DataPermissionRuleFactory factory,
        DataPermissionRuleHandler handler) {

    MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
    interceptor.addInnerInterceptor(new DataPermissionInterceptor(new JsqlParserPlusOptimize(), handler));
    return interceptor;
}
```

## 4. 关键要点总结

- 数据权限的链路：Handler → RuleFactory → Rule → Expression
- 多个规则用 **AND 拼接**（不是 OR）
- `DeptDataPermissionRule` 通过 `Customizer` 模式自动注册业务表
- 数据权限结果**缓存**在 `LoginUser.context`
- 跨租户时跳过数据权限

## 5. 练习题

### 练习 1：基础（必做）

画图说明数据权限的完整调用链路。

### 练习 2：进阶

解释 `DataPermissionRuleFactory` 的设计：为什么用接口 + 多个 Bean，而不是把规则硬编码到 Handler 中？

### 练习 3：挑战（选做）

设计"自定义数据权限规则"功能：业务方想要按 `region_id` 而不是 `dept_id` 过滤。说明要实现哪些接口、如何注册。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/db/DataPermissionRuleHandler.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/rule/dept/DeptDataPermissionRule.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/rule/dept/DeptDataPermissionRuleCustomizer.java`
- MyBatis-Plus 数据权限：https://baomidou.com/plugins/data-permission/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
