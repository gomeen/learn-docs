# 18 菜单权限：动态路由

> 详解 ruoyi 的"动态路由"机制：根据用户角色动态返回前端路由表。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解前后端分离架构下的动态路由
- 掌握 ruoyi 的 `/get-permission-info` 接口
- 知道前端如何根据菜单生成路由
- 能改造菜单结构（如增加"徽章"、"外链"等扩展字段）

## 📚 前置知识

- 16-rbac.md
- 17-ruoyi-permission-tables.md
- Vue Router 基础

## 1. 核心概念

### 1.1 静态路由 vs 动态路由

**传统方式（静态路由）**：
```javascript
// 路由表写死在代码里
const routes = [
  { path: '/user', component: User },
  { path: '/admin', component: Admin }
];
// 问题：所有用户都看到所有菜单
```

**动态路由（ruoyi 方式）**：
```javascript
// 1. 登录后，后端返回当前用户的菜单
GET /system/auth/get-permission-info
→ 返回 { menus: [...], roles: [...], permissions: [...] }

// 2. 前端根据 menus 动态注册路由
menus.forEach(menu => router.addRoute(menu));
```

### 1.2 动态路由的好处

- **安全性**：用户只能看到自己有权限的菜单
- **灵活性**：后端控制菜单，前端不用发版
- **多端复用**：管理员、会员看到不同的菜单

### 1.3 ruoyi 的菜单结构

```typescript
interface MenuVO {
  id: number;
  name: string;        // "用户管理"
  path: string;        // "/system/user"
  component: string;   // "system/user/index"
  icon: string;        // "ep:user"
  type: 1 | 2 | 3;     // 目录/菜单/按钮
  permission: string;  // "system:user:query"
  children?: MenuVO[]; // 子菜单
}
```

## 2. 代码示例

### 2.1 后端返回菜单

```java
// 文件：AuthController.java
@GetMapping("/get-permission-info")
public CommonResult<AuthPermissionInfoRespVO> getPermissionInfo() {
    // 1. 查用户角色
    Set<Long> roleIds = permissionService.getUserRoleIdListByUserId(getLoginUserId());

    // 2. 查角色菜单
    Set<Long> menuIds = permissionService.getRoleMenuListByRoleId(roleIds);
    List<MenuDO> menuList = menuService.getMenuList(menuIds);
    menuList = menuService.filterDisableMenus(menuList);

    // 3. 构建树形结构
    List<MenuVO> menus = buildMenuTree(menuList);

    return success(new AuthPermissionInfoRespVO(user, roles, menus));
}
```

### 2.2 前端动态注册路由

```typescript
// 文件：permission.ts
async function generateRoutes() {
    const res = await getPermissionInfo();
    const menus = res.data.menus;

    const routes = transformToRoutes(menus);
    routes.forEach(route => router.addRoute(route));
}
```

## 3. ruoyi 仓库源码解读

### 3.1 get-permission-info 接口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/auth/AuthController.java`
**核心代码**（行 93-118）：

```java
@GetMapping("/get-permission-info")
@Operation(summary = "获取登录用户的权限信息")
@DataPermission(enable = false) // 忽略数据权限，避免因为过滤，导致无法查询用户
public CommonResult<AuthPermissionInfoRespVO> getPermissionInfo() {
    // 1.1 获得用户信息
    AdminUserDO user = userService.getUser(getLoginUserId());
    if (user == null) {
        return success(null);
    }

    // 1.2 获得角色列表
    Set<Long> roleIds = permissionService.getUserRoleIdListByUserId(getLoginUserId());
    if (CollUtil.isEmpty(roleIds)) {
        return success(AuthConvert.INSTANCE.convert(user, Collections.emptyList(), Collections.emptyList()));
    }
    List<RoleDO> roles = roleService.getRoleList(roleIds);
    roles.removeIf(role -> !CommonStatusEnum.ENABLE.getStatus().equals(role.getStatus())); // 移除禁用的角色

    // 1.3 获得菜单列表
    Set<Long> menuIds = permissionService.getRoleMenuListByRoleId(convertSet(roles, RoleDO::getId));
    List<MenuDO> menuList = menuService.getMenuList(menuIds);
    menuList = menuService.filterDisableMenus(menuList);

    // 2. 拼接结果返回
    return success(AuthConvert.INSTANCE.convert(user, roles, menuList));
}
```

**解读**：
- 第 95 行 `@DataPermission(enable = false)`：**关键** — 关闭数据权限，否则会过滤掉自己的用户记录
- 第 98-101 行：用户不存在时返回 null（防御性）
- 第 104-107 行：用户的所有角色
- 第 109 行：**关键** — 过滤掉禁用的角色（role.status=1 视为无效）
- 第 112-114 行：角色的所有菜单，再过滤禁用菜单
- **完整数据**：用户信息 + 角色列表 + 菜单树

### 3.2 PermissionController 分配菜单

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/permission/PermissionController.java`
**核心代码**（行 41-51）：

```java
@PostMapping("/assign-role-menu")
@Operation(summary = "赋予角色菜单")
@PreAuthorize("@ss.hasPermission('system:permission:assign-role-menu')")
public CommonResult<Boolean> assignRoleMenu(@Validated @RequestBody PermissionAssignRoleMenuReqVO reqVO) {
    // 开启多租户的情况下，需要过滤掉未开通的菜单
    tenantService.handleTenantMenu(menuIds -> reqVO.getMenuIds().removeIf(menuId -> !CollUtil.contains(menuIds, menuId)));

    // 执行菜单的分配
    permissionService.assignRoleMenu(reqVO.getRoleId(), reqVO.getMenuIds());
    return success(true);
}
```

**解读**：
- 第 46 行：**多租户集成** — 只保留已开通的菜单
- 第 49 行：给角色分配菜单（更新 `system_role_menu` 表）

## 4. 关键要点总结

- ruoyi 的菜单**权限合一**：菜单和按钮权限都存在 `system_menu` 表
- `/get-permission-info` 返回：用户 + 角色 + 菜单树
- `@DataPermission(enable = false)` 是关键（不关闭会过滤掉当前用户）
- 过滤禁用角色/菜单（status=1 的不返回）
- 前端根据菜单**动态注册路由**

## 5. 练习题

### 练习 1：基础（必做）

写一个接口 `GET /api/menu`，返回当前用户的菜单树。表结构用 17-ruoyi-permission-tables.md 中的 `system_menu`。

### 练习 2：进阶

说明 `@DataPermission(enable = false)` 在 `get-permission-info` 接口中的作用。如果**不**关闭数据权限，会发生什么？

### 练习 3：挑战（选做）

设计"多租户菜单隔离"功能：每个租户可以单独配置自己的菜单（菜单的开通/关闭）。说明表结构如何修改、`tenantService.handleTenantMenu` 如何实现。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/auth/AuthController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/permission/PermissionController.java`
- Vue Router 动态路由：https://router.vuejs.org/guide/advanced/dynamic-routing.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
