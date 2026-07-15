# 4.4 RBAC 数据模型设计

> 理解 yudao 的 RBAC（Role-Based Access Control）数据模型。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 RBAC 的三种模型（用户-角色-权限）
- 掌握 yudai 的 5 张核心权限表设计
- 能在新业务中扩展权限模型
- 理解数据权限与功能权限的区别

## 📚 前置知识

- [10-data-permission.md](./10-data-permission.md)
- [19-security-starter.md](./19-security-starter.md)
- 关系型数据库设计
## 1. 核心概念

### 1.1 RBAC 的三种模型

> 📌 **Sighting**：RBAC/ABAC/ACL 对比见 [RBAC](../../_common/08-authorization/01-rbac.md) / [ABAC](../../_common/08-authorization/02-abac.md) / [ACL](../../_common/08-authorization/03-acl.md)。本文聚焦 yudao 表结构。

| 模型 | 特点 | 适用场景 |
|------|------|---------|
| RBAC0 | 用户-角色-权限 | 基础模型 |
| RBAC1 | 角色继承 | 角色有层级 |
| RBAC2 | 角色约束（互斥、基数） | 复杂权限 |
| RBAC3 | 包含 1 和 2 | 复杂系统 |

yudao 采用 **RBAC0 增强版**：
- 用户 → 角色（多对多）
- 角色 → 菜单（多对多）
- 菜单 → 权限（一一对应）

### 1.2 yudao 的核心权限表

| 表 | 作用 |
|---|------|
| `system_users` | 用户 |
| `system_roles` | 角色 |
| `system_user_role` | 用户-角色 |
| `system_menus` | 菜单（含权限标识） |
| `system_role_menu` | 角色-菜单 |
| `system_depts` | 部门 |
| `system_user_dept` | 用户-部门（多对多） |
| `system_role_dept` | 角色-数据权限范围 |
| `system_dict_data` | 字典 |

### 1.3 权限 vs 菜单

yudao 把"菜单"和"权限"绑定：
- 一个菜单对应一个**权限标识**（如 `system:user:create`）
- 给角色分配菜单 = 分配权限
- 前端通过权限标识控制按钮显示

## 2. 代码示例

### 2.1 数据库表设计

```sql
-- 用户表
CREATE TABLE system_users (
    id BIGINT PRIMARY KEY,
    username VARCHAR(30) NOT NULL,
    password VARCHAR(100) NOT NULL,
    nickname VARCHAR(30),
    status TINYINT NOT NULL DEFAULT 0,
    -- 继承 BaseDO 字段
    create_time DATETIME,
    creator VARCHAR(64),
    update_time DATETIME,
    updater VARCHAR(64),
    deleted BIT
);

-- 角色表
CREATE TABLE system_roles (
    id BIGINT PRIMARY KEY,
    name VARCHAR(30),
    code VARCHAR(100),  -- 角色编码，如 'admin'
    status TINYINT,
    type TINYINT,       -- 1: 内置, 2: 自定义
    sort INT
);

-- 菜单表（含权限标识）
CREATE TABLE system_menus (
    id BIGINT PRIMARY KEY,
    name VARCHAR(50),
    permission VARCHAR(100),  -- 权限标识，如 'system:user:create'
    type TINYINT,             -- 1: 目录, 2: 菜单, 3: 按钮
    parent_id BIGINT
);

-- 关联表
CREATE TABLE system_user_role (
    user_id BIGINT,
    role_id BIGINT,
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE system_role_menu (
    role_id BIGINT,
    menu_id BIGINT,
    PRIMARY KEY (role_id, menu_id)
);
```

### 2.2 权限校验 API

```java
@Resource(name = "ss")
private SecurityFrameworkService securityFrameworkService;

public void checkPermission() {
    // 校验角色
    securityFrameworkService.hasRole("admin");
    securityFrameworkService.hasAnyRoles(List.of("admin", "manager"));

    // 校验权限
    securityFrameworkService.hasPermission("system:user:create");
    securityFrameworkService.hasAnyPermissions(List.of("system:user:create", "system:user:update"));
}
```

## 3. ruoyi 仓库源码解读

### 3.1 SecurityFrameworkService 接口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/service/SecurityFrameworkService.java`
**核心代码**：

```java
public interface SecurityFrameworkService {
    boolean hasLoginUser();  // 是否已登录
    boolean hasRole(String role);
    boolean hasAnyRoles(Collection<String> roles);
    boolean hasScope(String scope);
    boolean hasPermission(String permission);
    boolean hasAnyPermissions(Collection<String> permissions);
    LoginUser getLoginUser();
    Long getLoginUserId();
}
```

**解读**：
- 业务方通过这个 API 检查权限
- 内部委托给 `PermissionCommonApi`（RPC 调用）

### 3.2 SecurityFrameworkServiceImpl 实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/service/SecurityFrameworkServiceImpl.java`
**核心代码**（节选）：

```java
public class SecurityFrameworkServiceImpl implements SecurityFrameworkService {

    private final PermissionCommonApi permissionApi;

    @Override
    public boolean hasRole(String role) {
        return hasAnyRoles(Set.of(role));
    }

    @Override
    public boolean hasAnyRoles(Collection<String> roles) {
        LoginUser loginUser = SecurityFrameworkUtils.getLoginUser();
        if (loginUser == null) return false;
        // 1. 内置超管：直接通过
        if (loginUser.getScopes().contains("*")) return true;
        // 2. RPC 校验
        CommonResult<Set<String>> result = permissionApi.getUserRoleCodeList(loginUser.getId());
        if (result.isError()) return false;
        return CollUtil.isNotEmpty(CollUtil.intersectionDistinct(result.getData(), roles));
    }
}
```

**解读**：
- `*` 角色 = 超管（全部权限）
- 通过 `PermissionCommonApi.getUserRoleCodeList` 拿用户角色
- `CollUtil.intersectionDistinct` 计算交集

### 3.3 yudao 业务模块的权限管理

yudao-server 的 `system` 模块实现了所有 RBAC 表的 CRUD：
- `RoleService` — 角色管理
- `MenuService` — 菜单管理
- `UserService` — 用户管理
- `RoleMenuService` — 角色菜单关联

### 3.4 数据权限的范围

```sql
-- system_role_dept：角色能查看哪些部门的数据
CREATE TABLE system_role_data_permission (
    id BIGINT PRIMARY KEY,
    role_id BIGINT,
    data_scope TINYINT,  -- 1: 全部, 2: 本部门, 3: 本部门及下级, 4: 本人, 5: 自定义
    dept_ids JSON         -- 自定义时的部门 ID 列表
);
```

**与 RBAC 的关系**：
- 功能权限（`hasPermission`）= RBAC 的角色/权限
- 数据权限（`@DataPermission`）= RBAC 的数据范围

## 4. 关键要点总结

- **yudao 用 RBAC0 增强**：用户-角色-菜单(权限)
- **菜单即权限**：菜单的 `permission` 字段是权限标识
- **`SecurityFrameworkService`** 是权限校验的统一入口
- **超管 (`*`)** 跳过所有权限校验
- **数据权限**是独立维度（`@DataPermission`）

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中找到 `RoleController`，看 5 个核心接口，理解角色管理流程。

### 练习 2：进阶

为业务新增"项目管理"模块，实现 3 个权限（`project:create`、`project:update`、`project:delete`），并测试权限校验。

### 练习 3：挑战（选做）

设计一个"ABAC"（属性基访问控制）扩展：用户只能访问"自己部门"且"金额 < 1万"的项目订单。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/service/SecurityFrameworkService.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/service/SecurityFrameworkServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/module/system/controller/admin/permission/RoleController.java`
- RBAC 维基百科：https://en.wikipedia.org/wiki/Role-based_access_control

---

**文档版本**：v1.0
**最后更新**：2026-07-13
