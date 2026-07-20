# 17 关联查询：@One / @Many

> ruoyi 通过 mybatis-plus-join + 自定义方法实现多表关联查询，理解关联查询对阅读业务代码至关重要。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分一对一、一对多、多对多关联
- 掌握 mybatis-plus-join（MPJ）的基本语法
- 理解 ruoyi 的关联查询实战模式
- 避免 N+1 查询陷阱

## 📚 前置知识

- [11-mybatis-vs-mp.md](./11-mybatis-vs-mp.md)
- [14-query-wrapper.md](./14-query-wrapper.md)
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

## 3. 关键要点总结

- ruoyi 优先使用「单表多次查询 + 内存组装」模式（避免 N+1）
- 多对多关联通过中间表实现，每张中间表独立 Mapper
- mybatis-plus-join 提供 `selectJoinList/selectJoinPage` 语法糖
- **核心原则**：能用单 SQL 就用单 SQL；不能就用「2-3 次批量查询」组装

---

**文档版本**：v1.0
**最后更新**：2026-07-13
