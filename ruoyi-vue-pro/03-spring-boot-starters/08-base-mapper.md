# 2.3 BaseMapperX 与 ServiceImpl

> 深入 ruoyi 增强的 BaseMapperX，掌握 20+ 个便捷方法。

## 🎯 学习目标

完成本文档后，你将能够：
- 熟练使用 `BaseMapperX` 的所有 `default` 方法
- 理解 `selectOneForUpdate`、`selectFirstOne` 等业务增强方法
- 掌握批量插入对 SQL Server 的特殊处理
- 能用 `BaseMapperX` 写出 90% 业务查询

## 📚 前置知识

- [06-mybatis-starter.md](./06-mybatis-starter.md)
- [07-mybatis-plus.md](./07-mybatis-plus.md)
- Java 8 `default` 方法

## 1. 核心概念

### 1.1 为什么需要 BaseMapperX？

`com.baomidou.mybatisplus.core.mapper.BaseMapper` 提供的 API 偏底层：
- 写 Wrapper 繁琐
- 分页返回的是 MP 的 `IPage`（不通用）
- 缺少业务常用方法（`selectOneForUpdate` 等）

ruoyi 通过 `BaseMapperX<T> extends MPJBaseMapper<T>` 增加了 **20+ 个 default 方法**，让业务代码更简洁。

### 1.2 方法分类

| 分类 | 方法 |
|------|------|
| 分页 | `selectPage`, `selectJoinPage` |
| 单条 | `selectOne`, `selectOneForUpdate`, `selectFirstOne`, `selectLastOne` |
| 列表 | `selectList` |
| 统计 | `selectCount` |
| 批量 | `insertBatch`, `updateBatch` |
| 删除 | `delete`, `deleteBatch` |

## 2. 代码示例

### 2.1 selectPage 各种用法

```java
// 基础分页
PageResult<UserDO> page = userMapper.selectPage(pageReqVO, wrapper);

// 带排序
PageResult<UserDO> page = userMapper.selectPage(pageReqVO, sortingFields, wrapper);

// 不分页（导出全部）
PageResult<UserDO> all = userMapper.selectPage(
    new PageParam().setPageSize(PageParam.PAGE_SIZE_NONE), wrapper);
```

### 2.2 selectOne 各种重载

```java
// 单字段查询
UserDO user = userMapper.selectOne("username", "admin");

// Lambda 字段（推荐）
UserDO user = userMapper.selectOne(UserDO::getEmail, "a@b.com");

// 多字段
UserDO user = userMapper.selectOne(
    UserDO::getUsername, "admin",
    UserDO::getStatus, 1);

// FOR UPDATE 锁
UserDO user = userMapper.selectOneForUpdate(UserDO::getId, 1L);
```

### 2.3 批量插入（注意 SQL Server）

```java
List<UserDO> users = ...;
userMapper.insertBatch(users);       // 默认每 1000 条一批
userMapper.insertBatch(users, 500);  // 自定义批次大小
```

**特殊处理**：如果数据库是 SQL Server，`insertBatch` 会**逐条插入**，避免 ID 获取错误。

## 3. ruoyi 仓库源码解读

### 3.1 selectOneForUpdate 的设计

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/mapper/BaseMapperX.java`
**核心代码**（行 122-145）：

```java
/**
 * 获得满足条件的一条记录，并使用 FOR UPDATE 锁定。
 *
 * 注意：需要在事务中调用，否则锁会立即释放。
 */
default T selectOneForUpdate(LambdaQueryWrapper<T> queryWrapper) {
    return selectOne(queryWrapper.last("FOR UPDATE"));
}

default T selectOneForUpdate(SFunction<T, ?> field, Object value) {
    return selectOneForUpdate(new LambdaQueryWrapper<T>().eq(field, value));
}

default T selectOneForUpdate(SFunction<T, ?> field1, Object value1, SFunction<T, ?> field2, Object value2) {
    return selectOneForUpdate(new LambdaQueryWrapper<T>().eq(field1, value1).eq(field2, value2));
}
```

**解读**：
- 使用 `.last("FOR UPDATE")` 在 SQL 末尾追加悲观锁
- 必须在 `@Transactional` 事务中调用——锁才有效
- 适用于"扣减库存"等并发场景

### 3.2 selectFirstOne 解决并发问题

**核心代码**（行 156-160）：

```java
/**
 * 获取满足条件的第 1 条记录
 *
 * 目的：解决并发场景下，插入多条记录后，使用 selectOne 会报错的问题
 */
default T selectFirstOne(SFunction<T, ?> field, Object value) {
    // 如果明确使用 MySQL 等场景，可以考虑使用 LIMIT 1 进行优化
    List<T> list = selectList(new LambdaQueryWrapper<T>().eq(field, value));
    return CollUtil.getFirst(list);
}
```

**解读**：
- 解决并发问题：两个请求都尝试插入相同业务数据，A 成功、B 失败；但 B 仍需要**拿到那条数据**
- 不用 `selectOne`（多结果会抛 `TooManyResultsException`）
- 取 `List` 第一条，避免异常
- ruoyi 经典模式："**insert + selectFirstOne**" 替代分布式锁

### 3.3 insertBatch 的多数据库适配

**核心代码**（行 232-256）：

```java
default Boolean insertBatch(Collection<T> entities) {
    DbType dbType = JdbcUtils.getDbType();
    if (JdbcUtils.isSQLServer(dbType)) {
        entities.forEach(this::insert);
        return CollUtil.isNotEmpty(entities);
    }
    return Db.saveBatch(entities);
}

default Boolean insertBatch(Collection<T> entities, int size) {
    DbType dbType = JdbcUtils.getDbType();
    if (JdbcUtils.isSQLServer(dbType)) {
        entities.forEach(this::insert);
        return CollUtil.isNotEmpty(entities);
    }
    return Db.saveBatch(entities, size);
}
```

**解读**：
- 通过 `JdbcUtils.getDbType()` 检测数据库类型
- SQL Server 的批量插入**不会自动返回主键**，所以走单条循环
- MySQL/PostgreSQL/Oracle 都走 `Db.saveBatch`（MP 的工具方法）

## 4. 关键要点总结

- **`BaseMapperX` 用 `default` 方法扩展**了 MP 的能力，**业务方零感知**
- **`selectOneForUpdate`**：事务内悲观锁
- **`selectFirstOne`**：并发场景下避免 `TooManyResultsException`
- **`insertBatch`** 自动适配多数据库（特别是 SQL Server）
- **所有方法都支持 `SFunction`（Lambda 字段）**——编译期安全

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中找到 `UserMapper` 接口，确认它继承自 `BaseMapperX`，列出它**直接使用**的 5 个 default 方法。

### 练习 2：进阶

为 `UserMapper` 添加一个 `selectActiveUsers()` 方法，使用 `selectList` + `LambdaQueryWrapperX` 查询 status=1 的用户。

### 练习 3：挑战（选做）

封装一个"幂等插入"工具方法：如果 username 已存在则返回已存在记录，否则插入新记录。用 `selectFirstOne + insert` 模式实现。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/mapper/BaseMapperX.java`
- MyBatis-Plus BaseMapper 文档：https://baomidou.com/pages/49cc81/
- MyBatis-Plus Join 文档：https://gitee.com/best_handsome/mybatis-plus-join

---

**文档版本**：v1.0
**最后更新**：2026-07-13
