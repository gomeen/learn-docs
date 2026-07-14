# 16 RBAC 概念：用户/角色/权限

> 理解 RBAC（Role-Based Access Control）权限模型的核心思想和优缺点。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 RBAC 0/1/2/3 四种模型的演进
- 掌握"用户-角色-权限"三层关系
- 区分"功能权限"和"数据权限"
- 知道 ruoyi 用的是哪种 RBAC 模型

## 📚 前置知识

- 关系数据库基础
- ER 图设计

## 1. 核心概念

### 1.1 为什么需要 RBAC？

**直接给用户分配权限**的问题：
```
100 个用户 × 50 个权限 = 5000 条记录
新增 1 个权限 → 修改 100 个用户的记录（噩梦）
```

**RBAC 的解决方案**：
```
用户 ──N:N── 角色 ──N:N── 权限
新增 1 个权限 → 只改 1 个角色
```

### 1.2 RBAC 四种模型

**RBAC 0（基础）**：
```
用户 ←→ 角色 ←→ 权限
```

**RBAC 1（角色继承）**：
```
    [超管]
   ↙     ↘
[经理]   [主管]
   ↘     ↙
   [员工]
子角色继承父角色的权限
```

**RBAC 2（约束）**：
- 互斥角色：不能同时拥有
- 基数限制：一个用户最多 5 个角色
- 先决条件：拥有角色 A 才能拥有角色 B

**RBAC 3（统一）** = RBAC 1 + RBAC 2

ruoyi 使用的是 **RBAC 1**（角色继承）+ 互斥约束。

### 1.3 ruoyi 的 RBAC 设计

```
用户 (system_user) ←→ 角色 (system_role) ←→ 菜单/权限 (system_menu)
   ↓
   部门 (system_dept) ←→ 岗位 (system_post)
```

**关键表**：
- `system_user`：用户
- `system_role`：角色（如"超级管理员"、"普通管理员"）
- `system_menu`：菜单 + 权限（如`system:user:query`）
- `system_user_role`：用户-角色 关系
- `system_role_menu`：角色-菜单 关系

## 2. 代码示例

### 2.1 简化版 RBAC 数据结构

```sql
-- 用户表
CREATE TABLE sys_user (
    id BIGINT PRIMARY KEY,
    username VARCHAR(50),
    password VARCHAR(100)
);

-- 角色表
CREATE TABLE sys_role (
    id BIGINT PRIMARY KEY,
    name VARCHAR(50),  -- "超级管理员"
    code VARCHAR(50)   -- "super_admin"
);

-- 权限表（合并到 menu 表）
CREATE TABLE sys_menu (
    id BIGINT PRIMARY KEY,
    name VARCHAR(50),
    permission VARCHAR(100),  -- "system:user:create"
    type TINYINT              -- 1目录 2菜单 3按钮
);

-- 用户-角色 关系
CREATE TABLE sys_user_role (
    user_id BIGINT,
    role_id BIGINT,
    PRIMARY KEY (user_id, role_id)
);

-- 角色-权限 关系
CREATE TABLE sys_role_menu (
    role_id BIGINT,
    menu_id BIGINT,
    PRIMARY KEY (role_id, menu_id)
);
```

### 2.2 权限判断逻辑

```java
// 文件：PermissionService.java
public boolean hasPermission(Long userId, String permission) {
    // 1. 查用户的所有角色
    List<RoleDO> roles = userRoleMapper.selectRolesByUserId(userId);

    // 2. 查这些角色的所有权限
    for (RoleDO role : roles) {
        List<MenuDO> menus = roleMenuMapper.selectMenusByRoleId(role.getId());
        for (MenuDO menu : menus) {
            if (permission.equals(menu.getPermission())) {
                return true;
            }
        }
    }
    return false;
}
```

## 3. ruoyi 仓库源码解读

### 3.1 角色-菜单 关系

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`
**核心代码**（行 62-84）：

```java
@Override
public boolean hasAnyPermissions(Long userId, String... permissions) {
    // 如果为空，说明已经有权限
    if (ArrayUtil.isEmpty(permissions)) {
        return true;
    }
    // 获得当前登录的角色
    List<RoleDO> roles = getEnableUserRoleListByUserIdFromCache(userId);
    if (CollUtil.isEmpty(roles)) {
        return false;
    }
    // 遍历判断每个权限
    for (String permission : permissions) {
        if (hasAnyPermission(roles, permission)) {
            return true;
        }
    }
    // 超级管理员自动拥有所有权限
    return roleService.hasAnySuperAdmin(convertSet(roles, RoleDO::getId));
}
```

**解读**：
- 第 70 行：用户的所有角色（带 Redis 缓存）
- 第 76-80 行：判断每个权限是否匹配
- 第 83 行：**超管兜底**（超管有所有权限）

### 3.2 角色-菜单 关联查询

**核心代码**（行 93-110）：

```java
private boolean hasAnyPermission(List<RoleDO> roles, String permission) {
    // 1. 通过 permission 找到对应的菜单
    List<Long> menuIds = menuService.getMenuIdListByPermissionFromCache(permission);
    if (CollUtil.isEmpty(menuIds)) {
        return false;  // 严格模式：找不到 Menu 就认为没权限
    }
    // 2. 判断角色-菜单的交集
    Set<Long> roleIds = convertSet(roles, RoleDO::getId);
    for (Long menuId : menuIds) {
        Set<Long> menuRoleIds = getSelf().getMenuRoleIdListByMenuIdFromCache(menuId);
        if (CollUtil.containsAny(menuRoleIds, roleIds)) {
            return true;
        }
    }
    return false;
}
```

**解读**：
- 第 94 行：通过 `permission` 找到对应 `menuIds`（一个权限可能挂多个菜单）
- 第 96-98 行：**严格模式**，防误配
- 第 102-108 行：判断"角色-菜单" 是否有交集

## 4. 关键要点总结

- RBAC 通过"用户-角色-权限"三层关系，**解耦**用户和权限
- ruoyi 用 **RBAC 1**：角色继承（如 `super_admin` 继承 `admin`）
- 超级管理员**绕过**所有权限判断（`hasAnySuperAdmin` 兜底）
- **严格模式**：权限标识找不到 Menu 记录就拒绝（防误配）
- 权限和菜单**复用同一张表**（`system_menu`），`type` 区分目录/菜单/按钮

## 5. 练习题

### 练习 1：基础（必做）

设计 5 张表（用户、角色、菜单、用户角色关系、角色菜单关系）的 ER 图。

### 练习 2：进阶

实现 `hasRole(Long userId, String roleCode)` 方法。说明"角色继承"如何在代码中实现（提示：parent_role_id 字段）。

### 练习 3：挑战（选做）

设计"互斥角色"功能：财务和审计不能是同一个人。说明表结构如何加约束、Service 层如何校验。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`
- NIST RBAC 模型：https://csrc.nist.gov/projects/role-based-access-control
- RBAC vs ABAC：https://en.wikipedia.org/wiki/Attribute-based_access_control

---

**文档版本**：v1.0
**最后更新**：2026-07-13
