# 27 数据权限概念：5 种数据范围

> 详解"数据权限"和"功能权限"的区别，以及 ruoyi 的 5 种数据范围。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分"功能权限"和"数据权限"
- 掌握 ruoyi 的 5 种数据范围
- 知道数据权限的实现原理
- 能为业务设计合适的数据权限

## 📚 前置知识

- 16-rbac.md
- MyBatis-Plus

## 1. 核心概念

### 1.1 功能权限 vs 数据权限

**功能权限**（能做什么）：
- 张三能查看"用户管理"菜单
- 李四能点击"删除用户"按钮

**数据权限**（能看哪些数据）：
- 张三是北京区经理，只能看**北京区**的订单
- 李四是销售员，只能看**自己**的订单
- 王五是超管，能看**所有**订单

### 1.2 ruoyi 的 5 种数据范围

```java
public enum DataScopeEnum {
    ALL(1),            // 全部数据权限
    DEPT_CUSTOM(2),    // 指定部门数据权限
    DEPT_ONLY(3),      // 部门数据权限
    DEPT_AND_CHILD(4), // 部门及以下数据权限
    SELF(5);           // 仅本人数据权限
}
```

| 数据范围 | 含义 | SQL 加什么条件 |
|---------|------|---------------|
| ALL | 全部 | 不加 |
| DEPT_CUSTOM | 自定义部门 | `dept_id IN (1,2,3)` |
| DEPT_ONLY | 本部门 | `dept_id = 5` |
| DEPT_AND_CHILD | 本部门及下级 | `dept_id IN (5,6,7,8)` |
| SELF | 仅本人 | `user_id = #{currentUserId}` |

### 1.3 数据权限的存储

`system_role.data_scope` 字段（tinyint）：
- 1 = ALL
- 2 = DEPT_CUSTOM
- 3 = DEPT_ONLY
- 4 = DEPT_AND_CHILD
- 5 = SELF

`system_role.data_scope_dept_ids` 字段（varchar）：DEPT_CUSTOM 时存的部门 ID 列表

## 2. 代码示例

### 2.1 手动实现（不推荐）

```java
// ❌ 错误：每个查询都要手动加
public List<OrderDO> listOrders() {
    Set<Long> deptIds = getCurrentUserVisibleDeptIds();
    return orderMapper.selectList(
        new LambdaQueryWrapperX<OrderDO>()
            .eq(OrderDO::getDeptId, ...)  // 容易漏！
    );
}
```

### 2.2 AOP + 拦截器实现（ruoyi 方式）

```java
// 用 @DataPermission 注解 + MyBatis 拦截器自动加条件
public List<OrderDO> listOrders() {
    // SQL 自动变成: SELECT * FROM order WHERE dept_id IN (...) OR user_id = ?
    return orderMapper.selectList();
}
```

## 3. ruoyi 仓库源码解读

### 3.1 DataScopeEnum 完整定义

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/enums/permission/DataScopeEnum.java`
**核心代码**（行 18-40）：

```java
@Getter
@AllArgsConstructor
public enum DataScopeEnum implements ArrayValuable<Integer> {

    ALL(1),            // 全部数据权限
    DEPT_CUSTOM(2),    // 指定部门数据权限
    DEPT_ONLY(3),      // 部门数据权限
    DEPT_AND_CHILD(4), // 部门及以下数据权限
    SELF(5);           // 仅本人数据权限

    /**
     * 范围
     */
    private final Integer scope;

    public static final Integer[] ARRAYS = Arrays.stream(values()).map(DataScopeEnum::getScope).toArray(Integer[]::new);

    @Override
    public Integer[] array() {
        return ARRAYS;
    }
}
```

**解读**：
- 5 个枚举值对应 5 种数据范围
- `ArrayValuable` 接口让前端可以拿到所有值生成下拉框

### 3.2 DeptDataPermissionRule 核心实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/rule/dept/DeptDataPermissionRule.java`
**核心代码**（行 91-146）：

```java
@Override
public Expression getExpression(String tableName, Alias tableAlias) {
    // 1. 只有有登陆用户的情况下，才进行数据权限的处理
    LoginUser loginUser = SecurityFrameworkUtils.getLoginUser();
    if (loginUser == null) {
        return null;
    }
    // 2. 只有管理员类型的用户，才进行数据权限的处理
    if (ObjectUtil.notEqual(loginUser.getUserType(), UserTypeEnum.ADMIN.getValue())) {
        return null;
    }

    // 3. 获得数据权限（从 LoginUser.context 缓存）
    DeptDataPermissionRespDTO deptDataPermission = loginUser.getContext(CONTEXT_KEY, DeptDataPermissionRespDTO.class);
    if (deptDataPermission == null) {
        deptDataPermission = permissionApi.getDeptDataPermission(loginUser.getId());
        if (deptDataPermission == null) {
            throw new NullPointerException(...);
        }
        // 缓存到 LoginUser.context
        loginUser.setContext(CONTEXT_KEY, deptDataPermission);
    }

    // 4. 情况一：ALL 可查看全部
    if (deptDataPermission.getAll()) {
        return null;
    }

    // 5. 情况二：既不能看部门，又不能看自己 → 100% 无权限
    if (CollUtil.isEmpty(deptDataPermission.getDeptIds())
        && Boolean.FALSE.equals(deptDataPermission.getSelf())) {
        return new EqualsTo(null, null); // WHERE null = null, 永远 false
    }

    // 6. 情况三：拼接 Dept 和 User 条件
    Expression deptExpression = buildDeptExpression(tableName, tableAlias, deptDataPermission.getDeptIds());
    Expression userExpression = buildUserExpression(tableName, tableAlias, deptDataPermission.getSelf(), loginUser.getId());
    if (deptExpression == null && userExpression == null) {
        return new EqualsTo(null, null);
    }
    if (deptExpression == null) return userExpression;
    if (userExpression == null) return deptExpression;
    // 关键：OR 拼接
    return new ParenthesedExpressionList(new OrExpression(deptExpression, userExpression));
}
```

**解读**：
- 第 93-96 行：未登录不处理
- 第 98-100 行：非管理员不处理（普通会员无数据权限）
- 第 103-114 行：**关键** — 数据权限结果缓存在 `LoginUser.context`（避免每次 SQL 都 RPC 调用）
- 第 117-119 行：ALL 权限 → 不加条件
- 第 122-125 行：100% 无权限 → `WHERE null = null`（永远返回空）
- 第 128-145 行：拼接 `dept_id` 和 `user_id` 条件，**用 OR 组合**

### 3.3 数据权限 DTO

```java
@Data
public class DeptDataPermissionRespDTO {
    /** 是否可查看全部数据 */
    private Boolean all;
    /** 可查看的部门编号数组 */
    private Set<Long> deptIds;
    /** 是否可查看本人数据 */
    private Boolean self;
}
```

**对应关系**：
- `all = true` → `DataScopeEnum.ALL`
- `deptIds != null` → `DEPT_CUSTOM` / `DEPT_ONLY` / `DEPT_AND_CHILD`
- `self = true` → `DataScopeEnum.SELF`

## 4. 关键要点总结

- **功能权限** = 能做什么；**数据权限** = 能看哪些数据
- ruoyi 的 5 种数据范围：ALL / 自定义 / 本部门 / 本部门及下级 / 仅本人
- 实现原理：MyBatis 拦截器自动加 WHERE 条件
- 数据权限结果**缓存**在 `LoginUser.context`
- 用 `WHERE null = null` 实现"100% 无权限"（永远返回空）

## 5. 练习题

### 练习 1：基础（必做）

画表说明 5 种数据范围与 SQL 条件的对应关系。

### 练习 2：进阶

阅读 `DeptDataPermissionRule.getExpression()`，解释为什么"既能看部门又能看自己"时用 `OR` 拼接而不是 `AND`？

### 练习 3：挑战（选做）

如果一个表既没有 `dept_id` 也没有 `user_id` 字段，但业务上需要数据权限（如按 `region_id` 分区），如何扩展 `DeptDataPermissionRule`？

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/enums/permission/DataScopeEnum.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-data-permission/src/main/java/cn/iocoder/yudao/framework/datapermission/core/rule/dept/DeptDataPermissionRule.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
