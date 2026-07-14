# 17 ruoyi 的权限表设计

> 详解 ruoyi 的权限相关表结构：user、role、menu、dept、post 五大表，以及它们之间的关系。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 权限系统的 5 大核心表
- 理解表之间的 N:N 关系（user_role、role_menu）
- 知道 role 表的 `data_scope` 字段如何与数据权限配合
- 能独立设计一套权限系统的表结构

## 📚 前置知识

- 16-rbac.md
- MySQL 基础

## 1. 核心概念

### 1.1 5 大核心表

```
system_user       → 用户
system_role       → 角色
system_menu       → 菜单/权限
system_dept       → 部门
system_post       → 岗位
```

加上 2 个关系表：
```
system_user_role  → 用户-角色
system_role_menu  → 角色-菜单
```

### 1.2 表关系图

```
                    ┌──────────┐
                    │   User   │
                    └────┬─────┘
                         │ N
                         │
                         │ N
                    ┌────┴─────┐         ┌──────────┐
                    │   Role   │←────────│  Dept    │
                    └────┬─────┘  N:1    └──────────┘
                         │ N
                         │
                         │ N
                    ┌────┴─────┐
                    │   Menu   │
                    └──────────┘

                    ┌──────────┐
                    │  Post    │ (岗位，多个用户共享)
                    └────┬─────┘
                         │ N:N (user_post)
                         │
                    ┌────┴─────┐
                    │   User   │
                    └──────────┘
```

## 2. ruoyi 权限表 SQL（基于 yudao 数据库）

### 2.1 角色表

```sql
CREATE TABLE system_role (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '角色ID',
    name VARCHAR(30) NOT NULL COMMENT '角色名称',
    code VARCHAR(100) NOT NULL COMMENT '角色权限字符串（如 super_admin）',
    sort INT NOT NULL COMMENT '显示顺序',
    data_scope TINYINT NOT NULL DEFAULT 1 COMMENT '数据范围：1全部 2本部门 3本部门及下级 4自定义 5本人',
    data_scope_dept_ids VARCHAR(500) COMMENT '数据范围（指定部门数组）',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '角色状态：0正常 1停用',
    type TINYINT NOT NULL DEFAULT 2 COMMENT '角色类型：1系统内置 2自定义',
    remark VARCHAR(500) COMMENT '备注',
    creator VARCHAR(64) DEFAULT '',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updater VARCHAR(64) DEFAULT '',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BIT NOT NULL DEFAULT 0,
    UNIQUE KEY uk_code (code, deleted)
);
```

### 2.2 菜单/权限表

```sql
CREATE TABLE system_menu (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '菜单ID',
    name VARCHAR(50) NOT NULL COMMENT '菜单名称',
    permission VARCHAR(100) NOT NULL DEFAULT '' COMMENT '权限标识（如 system:user:create）',
    type TINYINT NOT NULL COMMENT '菜单类型：1目录 2菜单 3按钮',
    sort INT NOT NULL DEFAULT 0 COMMENT '显示顺序',
    parent_id BIGINT NOT NULL DEFAULT 0 COMMENT '父菜单ID',
    path VARCHAR(200) DEFAULT '' COMMENT '路由地址',
    icon VARCHAR(100) DEFAULT '#' COMMENT '菜单图标',
    component VARCHAR(255) DEFAULT NULL COMMENT '组件路径',
    component_name VARCHAR(255) DEFAULT NULL COMMENT '组件名',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '菜单状态：0显示 1隐藏',
    visible BIT NOT NULL DEFAULT 1 COMMENT '是否可见',
    keep_alive BIT NOT NULL DEFAULT 1 COMMENT '是否缓存',
    always_show BIT NOT NULL DEFAULT 1 COMMENT '是否总是显示',
    creator VARCHAR(64) DEFAULT '',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updater VARCHAR(64) DEFAULT '',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BIT NOT NULL DEFAULT 0
);
```

### 2.3 用户表

```sql
CREATE TABLE system_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(30) NOT NULL COMMENT '用户名',
    password VARCHAR(100) NOT NULL DEFAULT '' COMMENT '密码（BCrypt）',
    nickname VARCHAR(30) NOT NULL COMMENT '昵称',
    remark VARCHAR(500) DEFAULT NULL COMMENT '备注',
    dept_id BIGINT DEFAULT NULL COMMENT '部门ID',
    post_ids VARCHAR(255) DEFAULT NULL COMMENT '岗位编号数组',
    email VARCHAR(50) DEFAULT '' COMMENT '邮箱',
    mobile VARCHAR(11) DEFAULT '' COMMENT '手机号',
    sex TINYINT DEFAULT 0 COMMENT '性别：0未知 1男 2女',
    avatar VARCHAR(255) DEFAULT '' COMMENT '头像',
    status TINYINT NOT NULL DEFAULT 0 COMMENT '状态：0正常 1停用',
    login_ip VARCHAR(50) DEFAULT '' COMMENT '最后登录IP',
    login_date DATETIME DEFAULT NULL COMMENT '最后登录时间',
    creator VARCHAR(64) DEFAULT '',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updater VARCHAR(64) DEFAULT '',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BIT NOT NULL DEFAULT 0,
    UNIQUE KEY uk_username (username, deleted)
);
```

### 2.4 关系表

```sql
-- 用户-角色
CREATE TABLE system_user_role (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    creator VARCHAR(64),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    updater VARCHAR(64),
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BIT DEFAULT 0
);

-- 角色-菜单
CREATE TABLE system_role_menu (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    role_id BIGINT NOT NULL,
    menu_id BIGINT NOT NULL,
    creator VARCHAR(64),
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    updater VARCHAR(64),
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted BIT DEFAULT 0
);
```

## 3. ruoyi 仓库源码解读

### 3.1 DataScopeEnum 枚举

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/enums/permission/DataScopeEnum.java`
**核心代码**（行 18-40）：

```java
@Getter
@AllArgsConstructor
public enum DataScopeEnum implements ArrayValuable<Integer> {

    ALL(1),            // 全部数据权限
    DEPT_CUSTOM(2),    // 指定部门数据权限
    DEPT_ONLY(3),      // 部门数据权限
    DEPT_AND_CHILD(4), // 部门及以下数据权限
    SELF(5);           // 仅本人数据权限

    private final Integer scope;

    public static final Integer[] ARRAYS = Arrays.stream(values()).map(DataScopeEnum::getScope).toArray(Integer[]::new);

    @Override
    public Integer[] array() {
        return ARRAYS;
    }
}
```

**解读**：
- 5 种数据范围（与 `system_role.data_scope` 字段对应）
- 用于**数据权限**（与"功能权限"区分）

### 3.2 MenuTypeEnum 枚举

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/enums/permission/MenuTypeEnum.java`
**核心代码**（行 12-25）：

```java
@Getter
@AllArgsConstructor
public enum MenuTypeEnum {
    DIR(1),    // 目录
    MENU(2),   // 菜单
    BUTTON(3)  // 按钮
    ;

    private final Integer type;
}
```

**解读**：
- `permission` 字段只对 `BUTTON` 类型有意义（如 `system:user:create`）
- `DIR` 和 `MENU` 主要是前端路由用

### 3.3 权限判断完整链路

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`
**核心代码**（行 62-110）：

```java
@Override
public boolean hasAnyPermissions(Long userId, String... permissions) {
    if (ArrayUtil.isEmpty(permissions)) {
        return true;
    }
    // 1. 查用户的角色
    List<RoleDO> roles = getEnableUserRoleListByUserIdFromCache(userId);
    if (CollUtil.isEmpty(roles)) {
        return false;
    }
    // 2. 遍历权限
    for (String permission : permissions) {
        if (hasAnyPermission(roles, permission)) {
            return true;
        }
    }
    // 3. 超管兜底
    return roleService.hasAnySuperAdmin(convertSet(roles, RoleDO::getId));
}

private boolean hasAnyPermission(List<RoleDO> roles, String permission) {
    // 1. permission → menu
    List<Long> menuIds = menuService.getMenuIdListByPermissionFromCache(permission);
    if (CollUtil.isEmpty(menuIds)) {
        return false;  // 严格模式
    }
    // 2. menu → role
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

**完整链路**：
```
用户 (user_id)
    ↓
角色列表 (role_ids) ←  system_user_role
    ↓
菜单/权限列表 (menu_ids) ←  system_role_menu
    ↓
判断 permission 是否在 menu_ids 中
```

## 4. 关键要点总结

- 5 大核心表：user、role、menu、dept、post
- 2 个关系表：user_role、role_menu
- `role.data_scope` 字段决定**数据权限**（5 种枚举）
- `menu.permission` 字段是**功能权限**标识（如 `system:user:create`）
- 权限判断链路：user → role → menu（permission 匹配）

## 5. 练习题

### 练习 1：基础（必做）

画出 user、role、menu 三张表的 ER 图，标注外键和 N:N 关系。

### 练习 2：进阶

说明 `system_role.data_scope` 字段的作用。它如何与 `system_user.dept_id` 配合实现"本部门及下级"的数据权限？

### 练习 3：挑战（选做）

设计"用户组"功能：可以把多个用户编为一组，给用户组统一分配角色。需要新增哪些表？Service 层如何改造？

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/enums/permission/DataScopeEnum.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/enums/permission/MenuTypeEnum.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
