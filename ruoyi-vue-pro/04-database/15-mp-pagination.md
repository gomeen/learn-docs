# 13 分页查询：Page / PaginationInnerInterceptor

> 分页是后端 API 的必备能力。MP 提供完整的分页插件，ruoyi 在此基础上封装。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 MySQL 分页的底层实现（LIMIT/OFFSET）
- 掌握 MP 分页插件的配置
- 掌握 ruoyi 的 PageParam / PageResult / SortablePageParam
- 知道深度分页的优化方案

## 📚 前置知识

- [11-mybatis-vs-mp.md](./11-mybatis-vs-mp.md)
- [14-query-wrapper.md](./14-query-wrapper.md)
- MySQL LIMIT 语法
- Starter 分页插件见 [09-pagination](../03-spring-boot-starters/10-pagination.md)

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

## 3. 关键要点总结

- 分页三件套：`PaginationInnerInterceptor`（拦截器）+ `IPage`（MP 对象）+ `PageResult`（ruoyi 出参）
- ruoyi 通过 `PAGE_SIZE_NONE = -1` 复用方法支持「不分页」
- 深度分页（offset 大）很慢，**优先用游标分页**（`WHERE id > lastId`）
- 分页插件会自动执行两次 SQL（数据 + COUNT）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
