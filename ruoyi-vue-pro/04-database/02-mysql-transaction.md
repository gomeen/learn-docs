# 02 MySQL 事务与隔离级别

> 事务是数据库的根基，ruoyi 中大量使用 `@Transactional` 保证业务一致性。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ACID 四大特性
- 区分四种隔离级别（READ UNCOMMITTED → SERIALIZABLE）
- 知道脏读、不可重复读、幻读的差异
- 掌握 Spring `@Transactional` 的传播行为和回滚规则

## 📚 前置知识

- 01-mysql-basics.md
- Spring AOP 基础概念

## 1. 核心概念

### 1.1 ACID 特性

| 特性 | 含义 | 实现机制 |
|------|------|---------|
| Atomicity（原子性） | 事务要么全成功要么全失败 | undo log |
| Consistency（一致性） | 事务前后数据完整性约束成立 | 应用层 + 数据库约束 |
| Isolation（隔离性） | 并发事务互不干扰 | MVCC + 锁 |
| Durability（持久性） | 事务提交后数据永久保存 | redo log |

### 1.2 四种隔离级别

```
READ UNCOMMITTED < READ COMMITTED < REPEATABLE READ < SERIALIZABLE
   隔离性弱          ↑               ↑ MySQL 默认             隔离性强
   并发高                                                并发低
```

| 隔离级别 | 脏读 | 不可重复读 | 幻读 |
|---------|------|----------|------|
| READ UNCOMMITTED | 可能 | 可能 | 可能 |
| READ COMMITTED | 避免 | 可能 | 可能 |
| REPEATABLE READ（MySQL 默认） | 避免 | 避免 | 部分避免 |
| SERIALIZABLE | 避免 | 避免 | 避免 |

### 1.3 三个并发问题

- **脏读**：读到其他事务**未提交**的数据
- **不可重复读**：同一行内，同一查询两次结果不同（其他事务修改了数据）
- **幻读**：范围查询两次返回的行数不同（其他事务插入/删除了行）

## 2. 代码示例

### 2.1 事务的基本使用

```sql
-- MySQL 显式事务
START TRANSACTION;

UPDATE system_role SET status = 1 WHERE id = 1;
UPDATE system_user SET status = 1 WHERE id = 100;

-- 任意一条 SQL 失败都应该 ROLLBACK
COMMIT;  -- 或 ROLLBACK;
```

### 2.2 Spring `@Transactional` 注解

```java
@Service
public class RoleServiceImpl implements RoleService {

    @Override
    @Transactional(rollbackFor = Exception.class)  // 关键：指定回滚异常类型
    public Long createRole(RoleSaveReqVO createReqVO, Integer type) {
        // 1. 校验角色名重复
        validateRoleDuplicate(createReqVO.getName(), createReqVO.getCode(), null);

        // 2. 插入到数据库
        RoleDO role = BeanUtils.toBean(createReqVO, RoleDO.class)
                .setType(ObjectUtil.defaultIfNull(type, RoleTypeEnum.CUSTOM.getType()))
                .setStatus(ObjUtil.defaultIfNull(createReqVO.getStatus(),
                                                 CommonStatusEnum.ENABLE.getStatus()))
                .setDataScope(DataScopeEnum.ALL.getScope());
        roleMapper.insert(role);

        // 3. 记录操作日志上下文（事务提交后异步写日志）
        LogRecordContext.putVariable("role", role);
        return role.getId();
    }
}
```

**说明**：
- `rollbackFor = Exception.class`：捕获所有 Exception（包括 RuntimeException）都触发回滚
- 默认情况下 Spring 只回滚 RuntimeException，不回滚普通 Exception，因此**显式声明 rollbackFor 是最佳实践**
- 事务方法必须是 public，且必须通过 Spring 代理调用（同类内部调用会失效）

## 3. ruoyi 仓库源码解读

### 3.1 多表写入 + 事务回滚

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`
**核心代码**（行 131-160）：

```java
@Override
@DSTransactional // 多数据源，使用 @DSTransactional 保证本地事务，以及数据源的切换
@Caching(evict = {
        @CacheEvict(value = RedisKeyConstants.MENU_ROLE_ID_LIST, allEntries = true),
        @CacheEvict(value = RedisKeyConstants.PERMISSION_MENU_ID_LIST, allEntries = true)
})
public void assignRoleMenu(Long roleId, Set<Long> menuIds) {
    // 获得角色拥有菜单编号
    Set<Long> dbMenuIds = convertSet(roleMenuMapper.selectListByRoleId(roleId), RoleMenuDO::getMenuId);
    // 计算新增和删除的菜单编号
    Set<Long> menuIdList = CollUtil.emptyIfNull(menuIds);
    Collection<Long> createMenuIds = CollUtil.subtract(menuIdList, dbMenuIds);
    Collection<Long> deleteMenuIds = CollUtil.subtract(dbMenuIds, menuIdList);
    // 执行新增和删除。对于已经授权的菜单，不用做任何处理
    if (CollUtil.isNotEmpty(createMenuIds)) {
        roleMenuMapper.insertBatch(CollectionUtils.convertList(createMenuIds, menuId -> {
            RoleMenuDO entity = new RoleMenuDO();
            entity.setRoleId(roleId);
            entity.setMenuId(menuId);
            return entity;
        }));
    }
    if (CollUtil.isNotEmpty(deleteMenuIds)) {
        roleMenuMapper.deleteListByRoleIdAndMenuIds(roleId, deleteMenuIds);
    }
}
```

**解读**：
- 第 3 行：`@DSTransactional`（来自 dynamic-datasource）——支持**多数据源切换 + 本地事务**
- **业务场景**：给角色分配菜单，需要删除旧关联 + 插入新关联。两步要么都成功，要么都回滚（不能出现「删除了一部分但没插入新数据」的脏状态）
- 第 11 行：`CollUtil.subtract` 计算差集，只处理有变化的菜单
- 第 16-22 行：批量插入，避免逐条 INSERT
- **整体设计意图**：业务操作（删除 + 插入）必须原子；缓存清理与事务解耦（通过 @CacheEvict 的执行时机保证）

### 3.2 删除角色 + 级联清理

**文件位置**：同文件，行 162-178

```java
@Override
@Transactional(rollbackFor = Exception.class)
@Caching(evict = {
        @CacheEvict(value = RedisKeyConstants.MENU_ROLE_ID_LIST, allEntries = true),
        @CacheEvict(value = RedisKeyConstants.USER_ROLE_ID_LIST, allEntries = true)
})
public void processRoleDeleted(Long roleId) {
    // 标记删除 UserRole
    userRoleMapper.deleteListByRoleId(roleId);
    // 标记删除 RoleMenu
    roleMenuMapper.deleteListByRoleId(roleId);
}
```

**解读**：
- 第 2 行：`@Transactional(rollbackFor = Exception.class)` —— 单数据源事务
- **业务场景**：删除一个角色时，必须同时清理「用户-角色」和「角色-菜单」两张关联表的记录
- 如果 `userRoleMapper.deleteListByRoleId` 抛异常，`roleMenuMapper.deleteListByRoleId` 不会执行，整体回滚

## 4. 关键要点总结

- MySQL 默认隔离级别是 **REPEATABLE READ**
- Spring 中**永远显式声明** `rollbackFor = Exception.class`，避免 Checked Exception 不回滚
- `@Transactional` 必须通过代理对象调用才生效（避免同类内部调用）
- 多数据源场景使用 `@DSTransactional` 代替 `@Transactional`
- ruoyi 中事务 + 缓存清理经常组合使用：事务回滚时缓存也要避免脏读

## 5. 练习题

### 练习 1：基础（必做）

阅读 `RoleServiceImpl.createRole`，画出其事务边界（哪些 SQL 在同一事务中？事务从哪开始到哪结束？）。

### 练习 2：进阶

为什么 `PermissionServiceImpl.assignRoleMenu` 用 `@DSTransactional` 而不是 `@Transactional`？搜索 dynamic-datasource 文档说明原因。

### 练习 3：挑战（选做）

设计一个转账业务 `transfer(fromUserId, toUserId, amount)`：
1. 至少使用 `@Transactional` 保证原子性
2. 处理余额不足（自定义异常触发回滚）
3. 写出对应的 SQL 表结构（user_account 表）

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/RoleServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`
- MySQL 事务官方文档：https://dev.mysql.com/doc/refman/8.0/en/innodb-transaction-model.html
- 极客时间 - MySQL 实战 45 讲（事务章节）

---

**文档版本**：v1.0
**最后更新**：2026-07-13