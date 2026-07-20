# 2.4 分页插件：PaginationInnerInterceptor

> 掌握 MyBatis Plus 分页插件的原理，能在 ruoyi 中实现复杂分页查询。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 MP 分页拦截器的执行流程
- 掌握 `PaginationInnerInterceptor` 的工作原理
- 理解 `IPage` 与 ruoyi `PageResult` 的转换
- 能在多表 Join 场景下使用分页

## 📚 前置知识

- [09-base-mapper.md](./09-base-mapper.md)
- MyBatis 拦截器（Interceptor）原理
- 数据库分页 SQL（MySQL `LIMIT`；MP 分页深水区见 [13-mp-pagination](../04-database/15-mp-pagination.md)）

## 1. 核心概念

### 1.1 分页拦截器做了什么？

MyBatis Plus 的 `PaginationInnerInterceptor` 是一个**`InnerInterceptor`**，它会拦截所有查询 SQL，在原 SQL 后**追加分页语句**：

| 数据库 | 原始 SQL | 追加分页 |
|--------|---------|---------|
| MySQL | `SELECT * FROM user` | `SELECT * FROM user LIMIT 0, 10` |
| Oracle | `SELECT * FROM user` | `SELECT * FROM user WHERE ROWNUM <= 10` |
| PostgreSQL | `SELECT * FROM user` | `SELECT * FROM user LIMIT 10 OFFSET 0` |

同时，会**额外查询一次 COUNT** 用于分页总数。

### 1.2 拦截器链

`MybatisPlusInterceptor` 内部维护一个拦截器链，按顺序执行：

```
MybatisPlusInterceptor
  ├── TenantLineInnerInterceptor  // 多租户过滤
  ├── DataPermissionInterceptor   // 数据权限
  ├── PaginationInnerInterceptor  // 分页
  └── ...
```

**顺序很重要**：先过滤租户/数据权限 → 再分页。

## 2. 代码示例

### 2.1 基本分页查询

```java
// Controller
@GetMapping("/page")
public CommonResult<PageResult<UserDO>> page(@Valid UserPageReqVO req) {
    return success(userService.getUserPage(req));
}

// Service
public PageResult<UserDO> getUserPage(UserPageReqVO req) {
    return userMapper.selectPage(req, new LambdaQueryWrapperX<UserDO>()
            .likeIfPresent(UserDO::getName, req.getName()));
}
```

### 2.2 自定义 COUNT SQL

有时主查询的 JOIN 复杂，COUNT 很慢，可以指定一个简单 COUNT：

```java
// 通过注解（不常用）或在 Mapper.xml 中写
@Select("SELECT COUNT(*) FROM sys_user WHERE deleted = 0")
Long customCount();
```

### 2.3 常见错误

```java
// ❌ 错误：分页参数传 null
userMapper.selectPage(null, wrapper);  // NPE

// ✅ 正确：传 PageParam
userMapper.selectPage(new PageParam(1, 10), wrapper);
```

## 3. 关键要点总结

- **MP 分页 = SQL 改写 + COUNT 查询**
- **`PaginationInnerInterceptor` 必须注册**到 `MybatisPlusInterceptor` 中
- **拦截器链顺序重要**：租户/数据权限 → 分页
- **多表 Join 时的 COUNT** 可能很慢，需要单独优化
- **`PageResult` 是 ruoyi 抽象**——业务方只看到 list + total

---

**文档版本**：v1.0
**最后更新**：2026-07-13
