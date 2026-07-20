# 2.3 BaseMapperX 与 ServiceImpl

> 深入 ruoyi 增强的 BaseMapperX，掌握 20+ 个便捷方法。

## 🎯 学习目标

完成本文档后，你将能够：
- 熟练使用 `BaseMapperX` 的所有 `default` 方法
- 理解 `selectOneForUpdate`、`selectFirstOne` 等业务增强方法
- 掌握批量插入对 SQL Server 的特殊处理
- 能用 `BaseMapperX` 写出 90% 业务查询

## 📚 前置知识

- [07-mybatis-starter.md](./07-mybatis-starter.md)
- [08-mybatis-plus.md](./08-mybatis-plus.md)
- Java 8 `default` 方法（接口见 [02-oop](../01-java-fundamentals/02-oop.md)）
- 数据库篇对称讲解见 [10-base-mapper](../04-database/12-base-mapper.md)

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

## 3. 关键要点总结

- **`BaseMapperX` 用 `default` 方法扩展**了 MP 的能力，**业务方零感知**
- **`selectOneForUpdate`**：事务内悲观锁
- **`selectFirstOne`**：并发场景下避免 `TooManyResultsException`
- **`insertBatch`** 自动适配多数据库（特别是 SQL Server）
- **所有方法都支持 `SFunction`（Lambda 字段）**——编译期安全

---

**文档版本**：v1.0
**最后更新**：2026-07-13
