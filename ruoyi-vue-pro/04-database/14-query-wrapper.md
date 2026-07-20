# 12 条件构造器：QueryWrapper / LambdaQueryWrapper

> 条件构造器是 MyBatis Plus 的精髓。ruoyi 通过 `LambdaQueryWrapperX` 进一步增强。

## 🎯 学习目标

完成本文档后，你将能够：
- 熟练使用 QueryWrapper / LambdaQueryWrapper
- 区分字符串字段名与方法引用的差异
- 掌握 ruoyi `LambdaQueryWrapperX` 的 IfPresent 系列方法
- 知道何时用条件构造器、何时写 XML

## 📚 前置知识

- [11-mybatis-vs-mp.md](./11-mybatis-vs-mp.md)
- Java Lambda 表达式（详见 [08-stream-lambda](../01-java-fundamentals/09-stream-lambda.md)）

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

## 3. 关键要点总结

- 优先使用 `LambdaQueryWrapper`（方法引用）而非 `QueryWrapper`（字符串）
- ruoyi 的 `LambdaQueryWrapperX` 提供 IfPresent 系列，让空值处理极简
- `betweenIfPresent` 支持单边范围（只有 start 或只有 end）
- 复杂 SQL（多表 Join、GROUP BY）仍需 XML/注解

---

**文档版本**：v1.0
**最后更新**：2026-07-13
