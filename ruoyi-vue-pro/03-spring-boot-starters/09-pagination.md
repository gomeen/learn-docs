# 2.4 分页插件：PaginationInnerInterceptor

> 掌握 MyBatis Plus 分页插件的原理，能在 ruoyi 中实现复杂分页查询。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 MP 分页拦截器的执行流程
- 掌握 `PaginationInnerInterceptor` 的工作原理
- 理解 `IPage` 与 ruoyi `PageResult` 的转换
- 能在多表 Join 场景下使用分页

## 📚 前置知识

- [08-base-mapper.md](./08-base-mapper.md)
- MyBatis 拦截器（Interceptor）原理
- 数据库分页 SQL（MySQL `LIMIT`；MP 分页深水区见 [13-mp-pagination](../04-database/13-mp-pagination.md)）

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

## 3. ruoyi 仓库源码解读

### 3.1 分页拦截器注册

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`
**核心代码**（行 47-54）：

```java
@Bean
public MybatisPlusInterceptor mybatisPlusInterceptor() {
    MybatisPlusInterceptor mybatisPlusInterceptor = new MybatisPlusInterceptor();
    mybatisPlusInterceptor.addInnerInterceptor(new PaginationInnerInterceptor()); // 分页插件
    // mybatisPlusInterceptor.addInnerInterceptor(new BlockAttackInnerInterceptor());
    return mybatisPlusInterceptor;
}
```

**解读**：
- 创建 `MybatisPlusInterceptor` 拦截器链
- 添加 `PaginationInnerInterceptor` 作为分页插件
- 注释中的 `BlockAttackInnerInterceptor` 是"防全表更新/删除"插件（被注释，按需开启）

### 3.2 MyBatisUtils.buildPage

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/util/MyBatisUtils.java`
**核心代码**（节选）：

```java
public static <T> IPage<T> buildPage(PageParam pageParam, Collection<SortingField> sortingFields) {
    // 页码 + 每页条数
    IPage<T> mpPage = new Page<>(pageParam.getPageNo(), pageParam.getPageSize());
    // 排序
    addOrder(mpPage, sortingFields);
    return mpPage;
}

public static <T> void addOrder(IPage<T> mpPage, Collection<SortingField> sortingFields) {
    if (CollUtil.isEmpty(sortingFields)) return;
    // 遍历排序字段，添加到 IPage
    for (SortingField field : sortingFields) {
        mpPage.addOrder(new OrderItem()
                .setColumn(field.getColumn())
                .setAsc(field.isAsc()));
    }
}
```

**解读**：
- 把 ruoyi 的 `PageParam` 转换为 MP 的 `Page<T>`
- 把 `SortingField` 列表转换为 MP 的 `OrderItem` 列表
- `IPage` 是 MP 分页的**核心对象**：既包含分页参数，也包含查询结果

### 3.3 PageResult 转换

**核心代码**（`BaseMapperX.java` 行 53-54）：

```java
// MyBatis Plus 查询
IPage<T> mpPage = MyBatisUtils.buildPage(pageParam, sortingFields);
selectPage(mpPage, queryWrapper);
// 转换返回
return new PageResult<>(mpPage.getRecords(), mpPage.getTotal());
```

**解读**：
- 把 MP 的 `IPage`（含 records、total、current、size）转换为 ruoyi 的 `PageResult`
- `PageResult` 只暴露**业务需要的字段**（`list` + `total`），更干净

## 4. 关键要点总结

- **MP 分页 = SQL 改写 + COUNT 查询**
- **`PaginationInnerInterceptor` 必须注册**到 `MybatisPlusInterceptor` 中
- **拦截器链顺序重要**：租户/数据权限 → 分页
- **多表 Join 时的 COUNT** 可能很慢，需要单独优化
- **`PageResult` 是 ruoyi 抽象**——业务方只看到 list + total

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中找到 `BaseMapperX.selectPage` 的所有调用，理解 `PageParam` 的字段含义。

### 练习 2：进阶

为 `UserMapper` 加一个 `selectJoinPage` 方法，关联 `sys_dept` 表，按部门名搜索。运行测试。

### 练习 3：挑战（选做）

为大数据量表（如 `sys_operation_log`）实现**游标分页**（基于 `lastId`），避免深分页性能问题。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/util/MyBatisUtils.java`
- MyBatis-Plus 分页文档：https://baomidou.com/pages/97710a/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
