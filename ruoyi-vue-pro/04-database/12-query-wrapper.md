# 12 条件构造器：QueryWrapper / LambdaQueryWrapper

> 条件构造器是 MyBatis Plus 的精髓。ruoyi 通过 `LambdaQueryWrapperX` 进一步增强。

## 🎯 学习目标

完成本文档后，你将能够：
- 熟练使用 QueryWrapper / LambdaQueryWrapper
- 区分字符串字段名与方法引用的差异
- 掌握 ruoyi `LambdaQueryWrapperX` 的 IfPresent 系列方法
- 知道何时用条件构造器、何时写 XML

## 📚 前置知识

- 09-mybatis-vs-mp.md
- Java Lambda 表达式

## 1. 核心概念

### 1.1 三种 Wrapper

| 类型 | 特点 |
|------|------|
| `QueryWrapper<T>` | 字符串字段名（易写错字段） |
| `LambdaQueryWrapper<T>` | Lambda 方法引用（编译期类型安全） |
| `LambdaQueryWrapperX<T>` | ruoyi 增强（加 `xxxIfPresent` 系列） |

### 1.2 Lambda 方法引用的优势

```java
// ❌ QueryWrapper：字符串字段名，重构字段名不会报错
new QueryWrapper<User>().eq("name", "admin");

// ✅ LambdaQueryWrapper：编译期检查，重构安全
new LambdaQueryWrapper<User>().eq(User::getName, "admin");
```

### 1.3 LambdaQueryWrapperX 的 IfPresent 系列

```java
.likeIfPresent(...)   // 字符串非空时拼接 LIKE
.eqIfPresent(...)     // 值非空时拼接 =
.inIfPresent(...)     // 集合非空时拼接 IN
.betweenIfPresent(...)// 两端都非空时拼接 BETWEEN（否则拼接单边）
```

**作用**：参数可空时**自动跳过条件**——避免「传 null 时查出全部」。

## 2. 代码示例

### 2.1 LambdaQueryWrapper 链式调用

```java
List<User> users = userMapper.selectList(
    new LambdaQueryWrapper<User>()
        .eq(User::getStatus, 0)                     // WHERE status = 0
        .like(User::getName, "admin")               // AND name LIKE '%admin%'
        .ge(User::getCreateTime, startDate)         // AND create_time >= ?
        .orderByDesc(User::getId)                   // ORDER BY id DESC
        .last("LIMIT 10")                           // 追加 LIMIT 10
);
```

### 2.2 ruoyi 的 IfPresent 系列

```java
// 场景：用户列表查询（参数都可空）
public PageResult<User> page(UserQuery query) {
    return userMapper.selectPage(query, new LambdaQueryWrapperX<User>()
        .likeIfPresent(User::getUsername, query.getUsername())  // username 非空时 LIKE
        .eqIfPresent(User::getStatus, query.getStatus())        // status 非空时 =
        .betweenIfPresent(User::getCreateTime,
                          query.getCreateTime()[0],
                          query.getCreateTime()[1])              // 两端非空时 BETWEEN
        .inIfPresent(User::getDeptId, query.getDeptIds())        // deptIds 非空时 IN
        .orderByDesc(User::getId)
    );
}
```

### 2.3 常用方法对照

| 方法 | 生成的 SQL |
|------|----------|
| `eq(col, val)` | `col = val` |
| `ne(col, val)` | `col <> val` |
| `gt(col, val)` | `col > val` |
| `ge(col, val)` | `col >= val` |
| `lt(col, val)` | `col < val` |
| `le(col, val)` | `col <= val` |
| `between(col, v1, v2)` | `col BETWEEN v1 AND v2` |
| `like(col, val)` | `col LIKE '%val%'` |
| `likeLeft(col, val)` | `col LIKE '%val'` |
| `likeRight(col, val)` | `col LIKE 'val%'` |
| `in(col, coll)` | `col IN (...)` |
| `isNull(col)` | `col IS NULL` |
| `orderByAsc/Desc(col)` | `ORDER BY col ASC/DESC` |

## 3. ruoyi 仓库源码解读

### 3.1 AdminUserMapper 的复杂查询

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/mysql/user/AdminUserMapper.java`
**核心代码**（行 28-37）：

```java
default PageResult<AdminUserDO> selectPage(UserPageReqVO reqVO, Collection<Long> deptIds, Collection<Long> userIds) {
    return selectPage(reqVO, new LambdaQueryWrapperX<AdminUserDO>()
            .likeIfPresent(AdminUserDO::getUsername, reqVO.getUsername())
            .likeIfPresent(AdminUserDO::getMobile, reqVO.getMobile())
            .eqIfPresent(AdminUserDO::getStatus, reqVO.getStatus())
            .betweenIfPresent(AdminUserDO::getCreateTime, reqVO.getCreateTime())
            .inIfPresent(AdminUserDO::getDeptId, deptIds)
            .inIfPresent(AdminUserDO::getId, userIds)
            .orderByDesc(AdminUserDO::getId));
}
```

**解读**：
- 第 3-4 行：`likeIfPresent` —— 用户名/手机号为空时跳过
- 第 5 行：`eqIfPresent` —— 状态为空时跳过
- 第 6 行：`betweenIfPresent` —— 时间范围数组可能为 null 或只有一端
- 第 7-8 行：`inIfPresent` —— 部门 ID 列表 / 用户 ID 列表为空时跳过
- **设计意图**：通过 IfPresent 系列，让「参数可空」的查询方法实现极简，无需大量 if 判断

### 3.2 LambdaQueryWrapperX 的实现原理

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/query/LambdaQueryWrapperX.java`
**核心代码**（行 49-90）：

```java
public LambdaQueryWrapperX<T> eqIfPresent(SFunction<T, ?> column, Object val) {
    if (ObjectUtil.isNotEmpty(val)) {
        return (LambdaQueryWrapperX<T>) super.eq(column, val);
    }
    return this;
}

public LambdaQueryWrapperX<T> likeIfPresent(SFunction<T, ?> column, String val) {
    if (StringUtils.hasText(val)) {
        return (LambdaQueryWrapperX<T>) super.like(column, val);
    }
    return this;
}

public LambdaQueryWrapperX<T> betweenIfPresent(SFunction<T, ?> column, Object val1, Object val2) {
    if (val1 != null && val2 != null) {
        return (LambdaQueryWrapperX<T>) super.between(column, val1, val2);
    }
    if (val1 != null) {
        return (LambdaQueryWrapperX<T>) ge(column, val1);
    }
    if (val2 != null) {
        return (LambdaQueryWrapperX<T>) le(column, val2);
    }
    return this;
}
```

**解读**：
- 第 1-3 行：`eqIfPresent` —— 用 `ObjectUtil.isNotEmpty` 判断（空集合、空字符串也算空）
- 第 5-7 行：`likeIfPresent` —— 用 `StringUtils.hasText`（空字符串 + 纯空格都跳过）
- 第 9-17 行：`betweenIfPresent` —— **智能处理单边范围**：
  - 两端都有 → BETWEEN
  - 只有 start → `>= start`
  - 只有 end → `<= end`
  - 都没有 → 跳过
- **返回 `this`**：保持链式调用流畅

## 4. 关键要点总结

- 优先使用 `LambdaQueryWrapper`（方法引用）而非 `QueryWrapper`（字符串）
- ruoyi 的 `LambdaQueryWrapperX` 提供 IfPresent 系列，让空值处理极简
- `betweenIfPresent` 支持单边范围（只有 start 或只有 end）
- 复杂 SQL（多表 Join、GROUP BY）仍需 XML/注解

## 5. 练习题

### 练习 1：基础（必做）

用 `LambdaQueryWrapperX` 写一个「订单查询」：
- 订单号（模糊）
- 状态（精确）
- 创建时间范围（区间）
- 用户 ID（IN）
所有条件都可空，使用 `xxxIfPresent`。

### 练习 2：进阶

阅读 `LambdaQueryWrapperX.java` 全部方法，画出方法分类图（等值类 / 范围类 / 模糊类 / IN 类），并对比 MP 原生 `LambdaQueryWrapper`，说明 ruoyi 增强了哪些场景。

### 练习 3：挑战（选做）

为 `LambdaQueryWrapperX` 扩展一个 `nestedIfPresent(boolean condition, Consumer<LambdaQueryWrapperX<T>> consumer)` 方法：用于 OR 嵌套条件。要求：`condition` 为 false 时跳过整个嵌套块。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/mysql/user/AdminUserMapper.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/query/LambdaQueryWrapperX.java`
- MyBatis Plus Wrapper 文档：https://baomidou.com/pages/10a804/

---

**文档版本**：v1.0
**最后更新**：2026-07-13