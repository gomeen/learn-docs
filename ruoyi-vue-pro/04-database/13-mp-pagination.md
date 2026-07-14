# 13 分页查询：Page / PaginationInnerInterceptor

> 分页是后端 API 的必备能力。MP 提供完整的分页插件，ruoyi 在此基础上封装。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 MySQL 分页的底层实现（LIMIT/OFFSET）
- 掌握 MP 分页插件的配置
- 掌握 ruoyi 的 PageParam / PageResult / SortablePageParam
- 知道深度分页的优化方案

## 📚 前置知识

- 09-mybatis-vs-mp.md
- 12-query-wrapper.md
- MySQL LIMIT 语法

## 1. 核心概念

### 1.1 分页的三层抽象

```
PageParam（入参）：pageNo=1, pageSize=10, sort=createTime DESC
    ↓
IPage<T>（MP 层）：current=1, size=10, records=List<T>, total=100
    ↓
PageResult<T>（ruoyi 出参）：list=List<T>, total=100
```

### 1.2 MySQL LIMIT 语法

```sql
SELECT * FROM user LIMIT 10 OFFSET 0;     -- 第 1 页
SELECT * FROM user LIMIT 10 OFFSET 10;    -- 第 2 页
SELECT * FROM user LIMIT 10 OFFSET 1000000; -- 深度分页（慢）
```

### 1.3 PaginationInnerInterceptor 作用

自动改写 SQL：把 `IPage` 的 `current/size` 转成 `LIMIT/OFFSET`，并在查询后返回总记录数（`SELECT COUNT(*)`）。

## 2. 代码示例

### 2.1 ruoyi 的 PageParam / PageResult

```java
// 入参（Controller 层 VO 通常继承 PageParam）
public class UserPageReqVO extends PageParam {
    private String username;
    private Integer status;
}

// 出参（Service 层返回）
public class PageResult<T> {
    private List<T> list;
    private Long total;
}

// Service 中使用
public PageResult<User> pageUser(UserPageReqVO reqVO) {
    return userMapper.selectPage(reqVO, new LambdaQueryWrapperX<User>()
        .likeIfPresent(User::getUsername, reqVO.getUsername())
        .eqIfPresent(User::getStatus, reqVO.getStatus()));
}
```

### 2.2 MP 默认分页用法

```java
// 1. 构造 Page 对象
Page<User> page = new Page<>(1, 10);

// 2. 调用 selectPage
Page<User> result = userMapper.selectPage(page, wrapper);

// 3. 取出数据
List<User> records = result.getRecords();
long total = result.getTotal();
```

### 2.3 深度分页优化

```sql
-- ❌ 慢：扫描 1000010 行后丢弃前 1000000
SELECT * FROM user ORDER BY id LIMIT 1000000, 10;

-- ✅ 延迟关联（先查 id 再 join）
SELECT u.* FROM user u
INNER JOIN (SELECT id FROM user ORDER BY id LIMIT 1000000, 10) t
ON u.id = t.id;

-- ✅ 游标分页（推荐）
SELECT * FROM user WHERE id > 1000000 ORDER BY id LIMIT 10;
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的 BaseMapperX 分页方法

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/mapper/BaseMapperX.java`
**核心代码**（行 34-55）：

```java
default PageResult<T> selectPage(SortablePageParam pageParam, @Param("ew") Wrapper<T> queryWrapper) {
    return selectPage(pageParam, pageParam.getSortingFields(), queryWrapper);
}

default PageResult<T> selectPage(PageParam pageParam, @Param("ew") Wrapper<T> queryWrapper) {
    return selectPage(pageParam, null, queryWrapper);
}

default PageResult<T> selectPage(PageParam pageParam, Collection<SortingField> sortingFields,
                                  @Param("ew") Wrapper<T> queryWrapper) {
    // 特殊：不分页，直接查询全部
    if (PageParam.PAGE_SIZE_NONE.equals(pageParam.getPageSize())) {
        MyBatisUtils.addOrder(queryWrapper, sortingFields);
        List<T> list = selectList(queryWrapper);
        return new PageResult<>(list, (long) list.size());
    }

    // MyBatis Plus 查询
    IPage<T> mpPage = MyBatisUtils.buildPage(pageParam, sortingFields);
    selectPage(mpPage, queryWrapper);
    // 转换返回
    return new PageResult<>(mpPage.getRecords(), mpPage.getTotal());
}
```

**解读**：
- 第 3-4 行：重载支持 `SortablePageParam`（带排序字段）
- 第 11-15 行：**特殊处理**：当 `pageSize = -1` 时不分页，直接查询全部（用于「导出全部数据」）
- 第 18-21 行：分页查询流程：`buildPage` → `selectPage` → 转 `PageResult`
- **设计意图**：通过 `PAGE_SIZE_NONE`（值为 -1）让分页查询复用同一方法，避免写两套代码

### 3.2 分页插件配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`

**核心代码**（行 47-54）：

```java
@Bean
public MybatisPlusInterceptor mybatisPlusInterceptor() {
    MybatisPlusInterceptor mybatisPlusInterceptor = new MybatisPlusInterceptor();
    mybatisPlusInterceptor.addInnerInterceptor(new PaginationInnerInterceptor()); // 分页插件
    // ↓↓↓ 按需开启，可能会影响到 updateBatch 的地方：例如说文件配置管理 ↓↓↓
    // mybatisPlusInterceptor.addInnerInterceptor(new BlockAttackInnerInterceptor()); // 拦截没有指定条件的 update 和 delete 语句
    return mybatisPlusInterceptor;
}
```

**解读**：
- 第 4 行：`PaginationInnerInterceptor` —— 启用分页插件（必须注册才能用 IPage）
- 第 6 行（注释）：`BlockAttackInnerInterceptor` —— 防「无条件 update/delete 全表」拦截器
- **关键依赖**：MyBatis Plus 4.x 分页插件的 ID 生成器要求 ≥ 5.2.0
- **分页溢出处理**：MP 默认当 `current > 总页数` 返回空集合（可配置 `overflow=false` 让其回到第一页）

## 4. 关键要点总结

- 分页三件套：`PaginationInnerInterceptor`（拦截器）+ `IPage`（MP 对象）+ `PageResult`（ruoyi 出参）
- ruoyi 通过 `PAGE_SIZE_NONE = -1` 复用方法支持「不分页」
- 深度分页（offset 大）很慢，**优先用游标分页**（`WHERE id > lastId`）
- 分页插件会自动执行两次 SQL（数据 + COUNT）

## 5. 练习题

### 练习 1：基础（必做）

用 MP 写一个分页查询：每页 5 条，查询 status=0 的用户，按 create_time 倒序。打印实际执行的 SQL（`MybatisPlusInterceptor` 开启 `setShowSql(true)`）。

### 练习 2：进阶

阅读 `BaseMapperX.selectPage` 源码，找出「不分页」和「分页」两个分支的差异。如果 `pageSize = 0` 会发生什么？为什么？

### 练习 3：挑战（选做）

实现「游标分页」：基于上一页最后一条的 id，查询下一页数据。写出 Mapper 方法签名 + Service 调用方式，并对比 OFFSET 分页的 EXPLAIN 执行计划。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/mapper/BaseMapperX.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`
- MyBatis Plus 分页文档：https://baomidou.com/pages/97710a/

---

**文档版本**：v1.0
**最后更新**：2026-07-13