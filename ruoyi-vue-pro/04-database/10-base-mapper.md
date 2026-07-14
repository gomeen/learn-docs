# 10 BaseMapper 通用 CRUD

> BaseMapper 是 MyBatis Plus 的核心，提供零 SQL 的 CRUD 能力。ruoyi 进一步封装为 `BaseMapperX`。

## 🎯 学习目标

完成本文档后，你将能够：
- 熟练使用 BaseMapper 提供的方法（insert/updateById/selectById/...）
- 理解 ruoyi BaseMapperX 的增强能力
- 知道何时用 BaseMapper，何时写自定义 SQL

## 📚 前置知识

- 09-mybatis-vs-mp.md
- Java 泛型

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

## 3. ruoyi 仓库源码解读

### 3.1 RoleMapper：典型 ruoyi Mapper

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/mysql/permission/RoleMapper.java`

```java
@Mapper
public interface RoleMapper extends BaseMapperX<RoleDO> {

    default PageResult<RoleDO> selectPage(RolePageReqVO reqVO) {
        return selectPage(reqVO, new LambdaQueryWrapperX<RoleDO>()
                .likeIfPresent(RoleDO::getName, reqVO.getName())
                .likeIfPresent(RoleDO::getCode, reqVO.getCode())
                .eqIfPresent(RoleDO::getStatus, reqVO.getStatus())
                .betweenIfPresent(BaseDO::getCreateTime, reqVO.getCreateTime())
                .orderByAsc(RoleDO::getSort));
    }

    default RoleDO selectByName(String name) {
        return selectOne(RoleDO::getName, name);
    }

    default RoleDO selectByCode(String code) {
        return selectOne(RoleDO::getCode, code);
    }

    default List<RoleDO> selectListByStatus(@Nullable Collection<Integer> statuses) {
        return selectList(RoleDO::getStatus, statuses);
    }
}
```

**解读**：
- **第 3 行**：继承 `BaseMapperX<RoleDO>`（ruoyi 增强版 BaseMapper）
- **第 5-11 行**：`selectPage` 是 default 方法（**无 XML**），用 `LambdaQueryWrapperX` 构建条件
- **第 7-9 行**：`likeIfPresent` / `eqIfPresent` —— 参数为空时跳过条件（避免传 null 时被当成字符串匹配）
- **第 13 行**：`selectOne(RoleDO::getName, name)` —— 方法引用代替字符串字段名（编译期类型安全）
- **第 21 行**：`@Nullable Collection<Integer> statuses` —— 传 null 时 `BaseMapperX` 内部会处理返回空集合

### 3.2 BaseMapperX 的 selectOne 增强

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/mapper/BaseMapperX.java`
**核心代码**（行 101-120）：

```java
default T selectOne(String field, Object value) {
    return selectOne(new QueryWrapper<T>().eq(field, value));
}

default T selectOne(SFunction<T, ?> field, Object value) {
    return selectOne(new LambdaQueryWrapper<T>().eq(field, value));
}

default T selectOne(String field1, Object value1, String field2, Object value2) {
    return selectOne(new QueryWrapper<T>().eq(field1, value1).eq(field2, value2));
}

default T selectOne(SFunction<T, ?> field1, Object value1, SFunction<T, ?> field2, Object value2) {
    return selectOne(new LambdaQueryWrapper<T>().eq(field1, value1).eq(field2, value2));
}
```

**解读**：
- **方法重载**：既支持字符串字段名，也支持 `SFunction`（Lambda 引用）
- **Lambda 优势**：编译期检查字段是否存在，重构安全
- **应用场景**：`selectOne("name", "admin")` vs `selectOne(RoleDO::getName, "admin")` —— 后者类型安全
- **设计意图**：通过方法引用消除「字符串硬编码」，降低维护成本

## 4. 关键要点总结

- `BaseMapper` 提供 20+ 内置方法，无需任何 SQL
- ruoyi 进一步封装 `BaseMapperX`，加入连表、批量等增强
- **优先用 Lambda 方法引用**（`User::getName`）而非字符串（`"name"`）
- 自定义查询用 `default` 方法 + `LambdaQueryWrapperX`
- 复杂 SQL 才考虑 XML/注解

## 5. 练习题

### 练习 1：基础（必做）

用 `BaseMapperX` 写一个 `OrderMapper`：`selectByOrderNo(String orderNo)`、`selectListByUserId(Long userId)`、`updateStatus(Long id, Integer status)`。

### 练习 2：进阶

阅读 `RoleMapper`，用 `BaseMapperX` 重写以下方法（不用 XML）：
- 查询所有状态 = 0 的角色
- 按 ID 列表批量查询
- 按 name 模糊查询
- 按 createTime 范围查询

### 练习 3：挑战（选做）

设计 `selectOneForUpdate` 的事务场景：在事务内调用 `selectOneForUpdate(User::getId, 1L)`，说明 MySQL 加锁行为（行锁？间隙锁？），并验证：另一个事务尝试更新该行时会被阻塞。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/mysql/permission/RoleMapper.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/mapper/BaseMapperX.java`
- MyBatis Plus BaseMapper 文档：https://baomidou.com/pages/49cc81/

---

**文档版本**：v1.0
**最后更新**：2026-07-13