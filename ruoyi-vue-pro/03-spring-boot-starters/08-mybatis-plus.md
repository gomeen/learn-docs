# 2.2 MyBatis Plus 核心功能

> 掌握 MyBatis Plus 的核心概念与常用 API，能看懂 ruoyi 中所有 MyBatis Plus 相关代码。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 MyBatis Plus 的核心组件（BaseMapper、IService、Wrapper）
- 掌握 `LambdaQueryWrapper` 链式 API
- 理解 `@TableField`、`@TableLogic`、`@TableName` 等注解（逻辑删除详见 [15-logic-delete](../04-database/18-logic-delete.md)）
- 能在 yudao 中熟练使用 MyBatis Plus 进行 CRUD

## 📚 前置知识

- MyBatis 基础（Mapper.xml 方式；对比见 [09-mybatis-vs-mp](../04-database/11-mybatis-vs-mp.md)）
- Java 8 Lambda 表达式（详见 [08-stream-lambda](../01-java-fundamentals/09-stream-lambda.md)）
- [07-mybatis-starter.md](./07-mybatis-starter.md)

## 1. 核心概念

### 1.1 MyBatis Plus 是什么？

**MyBatis Plus（MP）** 是 MyBatis 的增强工具，在 MyBatis 基础上**只做增强不做改变**。官方口号："为简化开发、提高效率而生"。

### 1.2 核心组件

| 组件 | 作用 |
|------|------|
| `BaseMapper<T>` | 通用 CRUD Mapper 基类 |
| `IService<T>` | 通用 Service 基类 |
| `ServiceImpl<M, T>` | IService 的实现（聚合 Mapper） |
| `Wrapper<T>` | 查询/更新条件包装器 |
| `LambdaQueryWrapper<T>` | Lambda 风格的 Wrapper |
| `Page<T>` | 分页对象 |
| `MetaObjectHandler` | 字段自动填充接口 |

### 1.3 ruoyi 的增强

ruoyi 在 MP 之上做了**三层增强**：
1. `BaseMapperX extends MPJBaseMapper` — 加入多表 Join 能力
2. `LambdaQueryWrapperX` — 加入 `*IfPresent` 系列方法
3. `BaseDO` — 统一 createTime/creator/deleted 字段

## 2. 代码示例

### 2.1 基础 CRUD（MP 原生）

```java
public interface UserMapper extends BaseMapper<UserDO> { }

// 插入
userMapper.insert(userDO);
// 更新（根据 ID）
userMapper.updateById(userDO);
// 删除（根据 ID）
userMapper.deleteById(1L);
// 查询单个
UserDO user = userMapper.selectById(1L);
// 查询列表
List<UserDO> users = userMapper.selectList(null);
// 统计
Long count = userMapper.selectCount(null);
```

### 2.2 条件查询（Lambda Wrapper）

```java
LambdaQueryWrapper<UserDO> wrapper = new LambdaQueryWrapper<>();
wrapper.eq(UserDO::getStatus, 1)
       .like(UserDO::getName, "张")
       .ge(UserDO::getCreateTime, startDate)
       .orderByDesc(UserDO::getId);

List<UserDO> users = userMapper.selectList(wrapper);
```

### 2.3 常见错误

```java
// ❌ 错误：字符串列名，重构时易出错
QueryWrapper<UserDO> w = new QueryWrapper<>();
w.eq("user_name", "zhang");  // 字段名拼错不会报错

// ✅ 正确：Lambda 列名，重构安全
LambdaQueryWrapper<UserDO> w = new LambdaQueryWrapper<>();
w.eq(UserDO::getUserName, "zhang");  // 编译期检查
```

## 3. 关键要点总结

- **MyBatis Plus = MyBatis + 通用 CRUD + Wrapper + 分页 + 逻辑删除**
- **`@TableField(fill = FieldFill.INSERT)`** + `MetaObjectHandler` 实现自动填充
- **`@TableLogic`** 把物理删除转为逻辑删除
- **Lambda Wrapper** 防止字段名拼写错误
- **ruoyi 通过 `BaseDO` 统一所有实体的基础字段**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
