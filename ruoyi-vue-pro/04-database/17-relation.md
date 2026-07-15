# 17 关联查询：@One / @Many

> ruoyi 通过 mybatis-plus-join + 自定义方法实现多表关联查询，理解关联查询对阅读业务代码至关重要。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分一对一、一对多、多对多关联
- 掌握 mybatis-plus-join（MPJ）的基本语法
- 理解 ruoyi 的关联查询实战模式
- 避免 N+1 查询陷阱

## 📚 前置知识

- [09-mybatis-vs-mp.md](./09-mybatis-vs-mp.md)
- [12-query-wrapper.md](./12-query-wrapper.md)
- SQL JOIN（见 [01-mysql-basics.md](./01-mysql-basics.md)）

## 1. 核心概念

### 1.1 三种关联关系

```
一对一（1:1）：用户 ↔ 用户详情
一对多（1:N）：用户 ↔ 订单
多对多（N:M）：用户 ↔ 角色（通过中间表）
```

### 1.2 关联查询的实现方式

| 方式 | 复杂度 | 性能 | 适用 |
|------|--------|------|------|
| SQL JOIN（单条 SQL） | 中 | 优 | 主表 + 1-2 张关联表 |
| 子查询 | 高 | 优 | 复杂条件 |
| 多次查询 + 内存组装 | 低 | 良 | 关联数据可选 |
| N+1（反例） | 低 | 差 | 不推荐 |

### 1.3 ruoyi 的关联查询：MPJ（mybatis-plus-join）

ruoyi 通过 `mybatis-plus-join-boot-starter` 实现连表查询：

```java
return userMapper.selectJoinList(UserVO.class,
    new MPJLambdaWrapper<User>()
        .selectAll(UserDO.class)
        .selectAs(UserDO::getId, UserVO::getUserId)
        .select(DeptDO::getName)
        .leftJoin(DeptDO.class, DeptDO::getId, UserDO::getDeptId)
);
```

## 2. 代码示例

### 2.1 SQL JOIN（最直接）

```sql
-- 单条 SQL 查用户 + 部门
SELECT u.id, u.username, d.name AS dept_name
FROM user u
LEFT JOIN dept d ON u.dept_id = d.id
WHERE u.deleted = 0;
```

### 2.2 多次查询 + 内存组装（ruoyi 推荐）

```java
public List<UserVO> listUsersWithDept(List<UserDO> users) {
    if (CollectionUtil.isEmpty(users)) return new ArrayList<>();

    // 1. 收集所有部门 ID
    Set<Long> deptIds = users.stream().map(UserDO::getDeptId).collect(Collectors.toSet());

    // 2. 批量查询部门
    Map<Long, DeptDO> deptMap = deptService.getDeptMap(deptIds);

    // 3. 组装 VO
    return users.stream().map(u -> {
        UserVO vo = BeanUtils.toBean(u, UserVO.class);
        vo.setDeptName(deptMap.get(u.getDeptId()) != null ?
                       deptMap.get(u.getDeptId()).getName() : null);
        return vo;
    }).collect(Collectors.toList());
}
```

**优势**：
- 无论用户列表多长，**只查询 2 次**（user + dept）
- 避免 N+1 陷阱

### 2.3 MPJ 连表查询

```java
public List<UserVO> listUsersWithDept() {
    return userMapper.selectJoinList(UserVO.class,
        new MPJLambdaWrapper<UserDO>()
            .selectAll(UserDO.class)
            .selectAs(UserDO::getId, UserVO::getUserId)
            .select(DeptDO::getName)
            .leftJoin(DeptDO.class, DeptDO::getId, UserDO::getDeptId)
            .eq(UserDO::getStatus, 0)
    );
}
```

## 3. ruoyi 仓库源码解读

### 3.1 多对多关联：用户的角色列表

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

    default List<RoleDO> selectListByStatus(@Nullable Collection<Integer> statuses) {
        return selectList(RoleDO::getStatus, statuses);
    }
}
```

**解读**：
- 角色表本身只关心单表查询
- **角色-菜单**、**角色-用户** 等关联查询由专门的 `RoleMenuMapper`、`UserRoleMapper` 处理
- **设计意图**：每张中间表独立 Mapper，符合 DDD 思想（一个聚合根对应一个 Mapper）

### 3.2 关联查询组装（多次查询模式）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`

```java
public void assignRoleMenu(Long roleId, Set<Long> menuIds) {
    // 1. 获得角色已有菜单（单次查询）
    Set<Long> dbMenuIds = convertSet(roleMenuMapper.selectListByRoleId(roleId), RoleMenuDO::getMenuId);
    // 2. 计算差集（内存操作）
    Set<Long> menuIdList = CollUtil.emptyIfNull(menuIds);
    Collection<Long> createMenuIds = CollUtil.subtract(menuIdList, dbMenuIds);
    Collection<Long> deleteMenuIds = CollUtil.subtract(dbMenuIds, menuIdList);
    // 3. 批量插入/删除（单次 SQL）
    if (CollUtil.isNotEmpty(createMenuIds)) {
        roleMenuMapper.insertBatch(...);
    }
    if (CollUtil.isNotEmpty(deleteMenuIds)) {
        roleMenuMapper.deleteListByRoleIdAndMenuIds(roleId, deleteMenuIds);
    }
}
```

**解读**：
- **第 3 行**：单次查询获取当前关联
- **第 4-5 行**：内存中用 `CollUtil.subtract` 计算差集
- **第 8-12 行**：批量写入新关联（避免逐条 INSERT）
- **第 13-15 行**：批量删除旧关联
- **整体设计意图**：用「单查询 + 内存计算 + 批量写」代替「JOIN + 逐条更新」，效率更高

### 3.3 BaseMapperX 的 selectJoinList

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/core/mapper/BaseMapperX.java`

```java
// BaseMapperX 继承 MPJBaseMapper，自动拥有：
// - selectJoinList(Class<R> resultTypeClass, MPJLambdaWrapper<T> joinQueryWrapper)
// - selectJoinPage(IPage<D> page, Class<D> clazz, MPJLambdaWrapper<T> lambdaWrapper)
// - selectJoinPage(SortablePageParam, Class<D>, MPJLambdaWrapper<T>)
```

**解读**：
- 通过继承 `MPJBaseMapper<RoleDO>`，`RoleMapper` 自动拥有连表能力
- **典型用法**：`selectJoinPage(reqVO, UserVO.class, new MPJLambdaWrapper<UserDO>()...)`

## 4. 关键要点总结

- ruoyi 优先使用「单表多次查询 + 内存组装」模式（避免 N+1）
- 多对多关联通过中间表实现，每张中间表独立 Mapper
- mybatis-plus-join 提供 `selectJoinList/selectJoinPage` 语法糖
- **核心原则**：能用单 SQL 就用单 SQL；不能就用「2-3 次批量查询」组装

## 5. 练习题

### 练习 1：基础（必做）

设计「用户 + 部门 + 角色」关联查询：
1. 用 JOIN 单 SQL 查询
2. 用多次查询 + 内存组装
3. 用 MPJ 连表

### 练习 2：进阶

阅读 `RoleServiceImpl` 的 `getRoleListFromCache`，分析其「多次单查」的实现模式。相比 `IN` 查询，这种模式的优缺点是什么？

### 练习 3：挑战（选做）

实现 `selectUserListWithRoles`：返回所有用户 + 每个用户的角色列表。比较两种方案：① 两次查询（user + user_role），② MPJ 连表 + GROUP_CONCAT。在 1000 用户 × 3 角色规模下，对比性能。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/mysql/permission/RoleMapper.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`
- mybatis-plus-join 官方文档：https://github.com/yulichang/mybatis-plus-join

---

**文档版本**：v1.0
**最后更新**：2026-07-13