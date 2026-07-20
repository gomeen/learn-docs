# 10 BaseMapper 通用 CRUD

> BaseMapper 是 MyBatis Plus 的核心，提供零 SQL 的 CRUD 能力。ruoyi 进一步封装为 `BaseMapperX`。

## 🎯 学习目标

完成本文档后，你将能够：
- 熟练使用 BaseMapper 提供的方法（insert/updateById/selectById/...）
- 理解 ruoyi BaseMapperX 的增强能力
- 知道何时用 BaseMapper，何时写自定义 SQL

## 📚 前置知识

- [11-mybatis-vs-mp.md](./11-mybatis-vs-mp.md)
- Java 泛型（详见 [03-generics](../01-java-fundamentals/03-generics.md)）
- Starter 侧 `BaseMapperX` 见 [08-base-mapper](../03-spring-boot-starters/09-base-mapper.md)

## 1. 核心概念

### 1.1 BaseMapper 接口签名

```java
public interface BaseMapper<T> {
    int insert(T entity);
    int updateById(T entity);
    int deleteById(Serializable id);
    T selectById(Serializable id);
    List<T> selectBatchIds(Collection<? extends Serializable> idList);
    List<T> selectList(Wrapper<T> queryWrapper);
    // ... 更多方法
}
```

### 1.2 ruoyi 的 BaseMapperX 增强

ruoyi 基于 `MPJBaseMapper`（mybatis-plus-join）扩展，提供：

- `selectOne(field, value)` —— 按字段查询单条
- `selectList(field, values)` —— 按字段 IN 查询
- `selectCount()` —— 查询总数
- `selectPage(PageParam, Wrapper)` —— 自定义分页
- `selectJoinPage(...)` —— 多表 Join 分页
- `insertBatch(entities)` / `updateBatch(entities)` —— 批量操作

### 1.3 何时用 BaseMapper vs 自定义 SQL

| 场景 | 推荐方式 |
|------|---------|
| 单表 CRUD | BaseMapper / LambdaQueryWrapperX |
| 多表 Join | `selectJoinPage`（MPJ）或自定义 SQL |
| 复杂聚合（GROUP BY + HAVING） | 自定义 XML/注解 |
| 性能极致的热点 SQL | 自定义 XML |

## 2. 代码示例

### 2.1 BaseMapper 基础 CRUD

```java
// 定义 Mapper（ruoyi 用法：继承 BaseMapperX）
public interface UserMapper extends BaseMapperX<User> {}

// 插入
User user = new User();
user.setName("test");
userMapper.insert(user);          // 自动回填主键到 user.id

// 按 ID 查询
User u = userMapper.selectById(1L);

// 按 ID 更新（只更新非空字段）
u.setName("test2");
userMapper.updateById(u);

// 按 ID 删除
userMapper.deleteById(1L);

// 按 ID 批量查询
List<User> users = userMapper.selectBatchIds(Arrays.asList(1L, 2L, 3L));
```

### 2.2 ruoyi 增强方法使用

```java
// 按字段查询单条（避免写 Wrapper）
User user = userMapper.selectOne(User::getUsername, "admin");

// 按字段 IN 查询
List<User> users = userMapper.selectList(User::getStatus, Arrays.asList(0, 1));

// 批量插入
List<User> newUsers = Arrays.asList(new User("a"), new User("b"));
userMapper.insertBatch(newUsers);

// 条件更新（全表）
int rows = userMapper.update(new User().setStatus(1), null);
```

### 2.3 自定义方法（default 方法）

```java
public interface UserMapper extends BaseMapperX<User> {
    // ruoyi 推荐写法：default 方法 + LambdaQueryWrapperX
    default List<User> selectActiveUsersByDept(Long deptId) {
        return selectList(new LambdaQueryWrapperX<User>()
                .eq(User::getDeptId, deptId)
                .eq(User::getStatus, 0)
                .orderByDesc(User::getId));
    }
}
```

## 3. 关键要点总结

- `BaseMapper` 提供 20+ 内置方法，无需任何 SQL
- ruoyi 进一步封装 `BaseMapperX`，加入连表、批量等增强
- **优先用 Lambda 方法引用**（`User::getName`）而非字符串（`"name"`）
- 自定义查询用 `default` 方法 + `LambdaQueryWrapperX`
- 复杂 SQL 才考虑 XML/注解

---

**文档版本**：v1.0
**最后更新**：2026-07-13
