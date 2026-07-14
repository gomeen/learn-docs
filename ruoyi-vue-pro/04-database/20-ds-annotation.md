# 20 @DS 切换数据源

> `@DS` 是 dynamic-datasource 的核心注解，理解它就掌握了多数据源切换的关键。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `@DS` 注解的所有用法
- 知道 `@DS` 与 `@Transactional` 的关系
- 理解 `@DSTransactional` 解决的问题
- 在 ruoyi 中正确应用数据源切换

## 📚 前置知识

- 19-dynamic-datasource.md
- 02-mysql-transaction.md

## 1. 核心概念

### 1.1 `@DS` 注解的三种粒度

```java
// 方法级（最常用）
@DS("slave")
public List<Order> listFromSlave() { ... }

// 类级（对所有方法生效）
@DS("slave")
@Service
public class ReportService { ... }

// 类 + 方法（方法级别覆盖类级别）
@DS("slave")
@Service
public class ReportService {
    @DS("master")  // 这个方法走 master
    public void saveReport() { ... }
}
```

### 1.2 `@DS` 与 `@Transactional` 的执行顺序

```
请求 → @Transactional（开启事务）→ @DS（切换数据源）→ 业务方法
```

**重要**：`@Transactional` 必须在 `@DS` 的外层。

### 1.3 `@DSTransactional` 解决的事务问题

```
场景：跨多个数据源的操作需要事务
  - @Transactional：只支持单数据源
  - @DSTransactional：支持多数据源（基于 dynamic-datasource）
```

## 2. 代码示例

### 2.1 基础用法

```java
@Service
public class OrderServiceImpl implements OrderService {

    @Resource
    private OrderMapper orderMapper;

    // 默认 master
    public List<Order> listAll() {
        return orderMapper.selectList();
    }

    // 走从库（读多写少场景）
    @DS("slave")
    public PageResult<Order> pageOrders(OrderPageReqVO reqVO) {
        return orderMapper.selectPage(reqVO, new LambdaQueryWrapperX<>());
    }

    // 走其他数据源
    @DS("oracle")
    public List<LegacyOrder> listLegacyOrders() {
        return legacyOrderMapper.selectList();
    }
}
```

### 2.2 类级别使用

```java
@DS("slave")
@Service
public class ReportServiceImpl implements ReportService {

    // 所有方法都走 slave
    public ReportVO dailyReport() {
        return reportMapper.dailyReport();
    }

    // 覆盖：单独这个方法走 master
    @DS("master")
    public void saveReportSnapshot(ReportVO report) {
        reportMapper.insert(report);
    }
}
```

### 2.3 多数据源事务

```java
// ❌ 错误：@Transactional 只支持单数据源
@Transactional
public void processCrossDB(Order order, Log log) {
    orderMapper.insert(order);  // master
    logMapper.insert(log);       // slave（事务失效！）
}

// ✅ 正确：使用 @DSTransactional
@DSTransactional
public void processCrossDB(Order order, Log log) {
    orderMapper.insert(order);  // master 事务
    logMapper.insert(log);       // slave 事务（一起回滚）
}
```

### 2.4 动态数据源（运行时切换）

```java
// 手动切换数据源（不推荐，优先用 @DS）
DynamicDataSourceContextHolder.push("slave");
// ... 业务操作 ...
DynamicDataSourceContextHolder.poll();
```

## 3. ruoyi 仓库源码解读

### 3.1 PermissionServiceImpl 使用 @DSTransactional

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`

```java
@Override
@DSTransactional // 多数据源，使用 @DSTransactional 保证本地事务，以及数据源的切换
@Caching(evict = {
        @CacheEvict(value = RedisKeyConstants.MENU_ROLE_ID_LIST, allEntries = true),
        @CacheEvict(value = RedisKeyConstants.PERMISSION_MENU_ID_LIST, allEntries = true)
})
public void assignRoleMenu(Long roleId, Set<Long> menuIds) {
    Set<Long> dbMenuIds = convertSet(roleMenuMapper.selectListByRoleId(roleId), RoleMenuDO::getMenuId);
    Set<Long> menuIdList = CollUtil.emptyIfNull(menuIds);
    Collection<Long> createMenuIds = CollUtil.subtract(menuIdList, dbMenuIds);
    Collection<Long> deleteMenuIds = CollUtil.subtract(dbMenuIds, menuIdList);
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
- 第 2 行：`@DSTransactional` —— 多数据源事务
- **为什么用 `@DSTransactional`？**
  - 角色-菜单的分配可能涉及 master（写）和 slave（读历史数据）—— `roleMenuMapper.selectListByRoleId` 可能从从库读
  - 即使都在 master，用 `@DSTransactional` 也保证多数据源情况下的一致性
- **缓存清理**：事务回滚时缓存也避免脏读（通过 `@CacheEvict` 的执行时机）
- **业务场景**：分配菜单涉及「删除旧关联 + 插入新关联」，必须原子

### 3.2 多数据源场景：processRoleDeleted

**文件位置**：同文件

```java
@Override
@Transactional(rollbackFor = Exception.class)  // 单数据源事务
@Caching(evict = {
        @CacheEvict(value = RedisKeyConstants.MENU_ROLE_ID_LIST, allEntries = true),
        @CacheEvict(value = RedisKeyConstants.USER_ROLE_ID_LIST, allEntries = true)
})
public void processRoleDeleted(Long roleId) {
    // 标记删除 UserRole（单数据源即可）
    userRoleMapper.deleteListByRoleId(roleId);
    // 标记删除 RoleMenu
    roleMenuMapper.deleteListByRoleId(roleId);
}
```

**解读**：
- 第 2 行：`@Transactional`（单数据源）—— 因为这里没有跨数据源操作
- **对比 3.1 的 `assignRoleMenu`**：为什么用 `@DSTransactional` 而这里用 `@Transactional`？
  - `assignRoleMenu` 涉及「读历史 + 写新」—— 可能跨数据源（read 走从，write 走主）
  - `processRoleDeleted` 全部是写操作 → 单数据源事务足够
- **设计意图**：根据业务是否真的跨数据源选择合适的事务注解

### 3.3 ruoyi 中的 @DS 使用模式

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`（其他方法）

```java
// 多数方法不写 @DS，使用默认 master
@Override
public boolean hasAnySuperAdmin(Collection<Long> ids) {
    if (CollectionUtil.isEmpty(ids)) {
        return false;
    }
    RoleServiceImpl self = getSelf();
    return ids.stream().anyMatch(id -> {
        RoleDO role = self.getRoleFromCache(id);
        return role != null && RoleCodeEnum.isSuperAdmin(role.getCode());
    });
}
```

**解读**：
- **默认行为**：不写 `@DS` 时使用 yml 中的 `primary: master`
- **最佳实践**：只在确实需要切换时才写 `@DS`，避免代码噪音
- **自动路由**（可选）：可通过拦截器实现「读走 slave、写走 master」自动分流，无需每个方法都写 `@DS`

## 4. 关键要点总结

- `@DS("name")` 用于切换数据源，可加在方法或类上
- 单数据源用 `@Transactional`，多数据源用 `@DSTransactional`
- `@Transactional` 必须在 `@DS` 的外层（确保数据源在事务开启前确定）
- ruoyi 通过 `assignRoleMenu` 演示了 `@DSTransactional` 的正确用法
- 数据源名称必须在 yml 中预先配置

## 5. 练习题

### 练习 1：基础（必做）

配置两个数据源（master + slave），写一个 `UserService.listUsers()` 用 `@DS("slave")`，另一个 `UserService.saveUser()` 用 `@DS("master")`，分别测试读写分离效果。

### 练习 2：进阶

为什么 `assignRoleMenu` 用 `@DSTransactional` 而 `processRoleDeleted` 用 `@Transactional`？阅读两者源代码，找出业务上的关键差异。

### 练习 3：挑战（选做）

设计一个「自动读写分离」拦截器：根据方法名前缀（`select*/list*/get*` 走 slave，其他走 master）自动设置数据源。要求：不能影响事务边界。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`
- dynamic-datasource @DS 文档：https://github.com/baomidou/dynamic-datasource

---

**文档版本**：v1.0
**最后更新**：2026-07-13