# 6 @PreAuthorize 注解权限

> 详解 Spring Security 的方法级权限控制：@PreAuthorize、@PostAuthorize 和 SpEL 表达式。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `@PreAuthorize` 注解的语法和 SpEL 表达式
- 理解 `@EnableMethodSecurity` 开启方法级权限
- 看懂 ruoyi 的 `@ss.hasPermission('system:user:create')` 自定义语法
- 能区分 URL 级别权限（filterChain）和方法级别权限（@PreAuthorize）

## 📚 前置知识

- 03-security-config.md
- SpEL 表达式基础

## 1. 核心概念

### 1.1 三种权限控制粒度

```
URL 级：通过 SecurityFilterChain 配置（如 .hasRole("ADMIN")）
    ↓
方法级：通过 @PreAuthorize 注解（ruoyi 主要使用）
    ↓
数据级：通过 @DataPermission 注解（自动加 WHERE 条件）
```

**@PreAuthorize 的优势**：
- 与业务代码放一起，可读性高
- 支持 SpEL 表达式，灵活强大
- 不需要修改 filterChain

### 1.2 常用 SpEL 表达式

| 表达式 | 作用 |
|--------|------|
| `hasRole('ADMIN')` | 拥有 ADMIN 角色 |
| `hasAnyRole('ADMIN','USER')` | 拥有任一角色 |
| `hasAuthority('system:user:create')` | 拥有指定权限 |
| `hasAnyAuthority('...','...')` | 拥有任一权限 |
| `isAuthenticated()` | 已登录 |
| `isAnonymous()` | 匿名 |
| `principal.id == #userId` | 当前用户 ID == 参数 userId |

### 1.3 ruoyi 的自定义 @ss 语法

```java
@PreAuthorize("@ss.hasPermission('system:user:create')")
@PreAuthorize("@ss.hasRole('super_admin')")
@PreAuthorize("@ss.hasAnyRoles('super_admin','admin')")
```

`@ss` 是 ruoyi 定义的 Spring Bean，封装了权限判断逻辑。

## 2. 代码示例

### 2.1 基础用法

```java
// 文件：UserController.java
@RestController
@RequestMapping("/admin-api/system/user")
public class UserController {

    // 需要 system:user:query 权限
    @GetMapping("/list")
    @PreAuthorize("hasAuthority('system:user:query')")
    public CommonResult<List<UserVO>> list() { ... }

    // 需要 ADMIN 角色
    @DeleteMapping("/delete")
    @PreAuthorize("hasRole('ADMIN')")
    public CommonResult<Boolean> delete(@RequestParam Long id) { ... }

    // 只能删除自己创建的用户
    @DeleteMapping("/delete-mine")
    @PreAuthorize("hasAuthority('system:user:delete') and principal.id == #userId")
    public CommonResult<Boolean> deleteMine(@RequestParam Long userId) { ... }
}
```

### 2.2 自定义 PermissionService

```java
// 文件：PermissionService.java
@Service("ss")  // Bean 名字叫 ss
public class PermissionService {

    public boolean hasPermission(String permission) {
        LoginUser user = SecurityFrameworkUtils.getLoginUser();
        if (user == null) return false;
        // 调用业务服务判断
        return permissionBizService.hasPermission(user.getId(), permission);
    }

    public boolean hasRole(String role) {
        LoginUser user = SecurityFrameworkUtils.getLoginUser();
        if (user == null) return false;
        return roleBizService.hasRole(user.getId(), role);
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 @EnableMethodSecurity 开启

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/YudaoWebSecurityConfigurerAdapter.java`
**核心代码**（行 48）：

```java
@EnableMethodSecurity(securedEnabled = true)
public class YudaoWebSecurityConfigurerAdapter {
    // ...
}
```

**解读**：
- 开启方法级权限控制
- `securedEnabled = true` 兼容旧版 `@Secured` 注解
- 默认 `prePostEnabled = true`，支持 `@PreAuthorize` 和 `@PostAuthorize`

### 3.2 PermissionController 中的 @PreAuthorize

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/permission/PermissionController.java`
**核心代码**（行 35-49）：

```java
@Operation(summary = "获得角色拥有的菜单编号")
@Parameter(name = "roleId", description = "角色编号", required = true)
@GetMapping("/list-role-menus")
@PreAuthorize("@ss.hasPermission('system:permission:assign-role-menu')")
public CommonResult<Set<Long>> getRoleMenuList(Long roleId) {
    return success(permissionService.getRoleMenuListByRoleId(roleId));
}

@PostMapping("/assign-role-menu")
@Operation(summary = "赋予角色菜单")
@PreAuthorize("@ss.hasPermission('system:permission:assign-role-menu')")
public CommonResult<Boolean> assignRoleMenu(@Validated @RequestBody PermissionAssignRoleMenuReqVO reqVO) {
    // 开启多租户的情况下，需要过滤掉未开通的菜单
    tenantService.handleTenantMenu(menuIds -> reqVO.getMenuIds().removeIf(menuId -> !CollUtil.contains(menuIds, menuId)));
    permissionService.assignRoleMenu(reqVO.getRoleId(), reqVO.getMenuIds());
    return success(true);
}
```

**解读**：
- 第 36 行：调用 `@ss.hasPermission('system:permission:assign-role-menu')` 检查权限
- 第 43 行：增删改操作同样需要权限校验
- 权限标识格式：`{模块}:{资源}:{操作}`，例如 `system:permission:assign-role-menu`
- **`@ss` 在 SpEL 中默认从 Spring 容器按 Bean 名称查找**（`@ss` 等价于 `getBean("ss")`）

### 3.3 hasAnyPermissions 业务实现

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

    // 情况一：遍历判断每个权限
    for (String permission : permissions) {
        if (hasAnyPermission(roles, permission)) {
            return true;
        }
    }

    // 情况二：如果是超管，也说明有权限
    return roleService.hasAnySuperAdmin(convertSet(roles, RoleDO::getId));
}

private boolean hasAnyPermission(List<RoleDO> roles, String permission) {
    List<Long> menuIds = menuService.getMenuIdListByPermissionFromCache(permission);
    if (CollUtil.isEmpty(menuIds)) {
        return false;  // 严格模式：找不到对应 Menu 就认为无权限
    }
    // 判断角色-菜单的交集
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
- 第 65-67 行：空权限列表 = 全部允许（用于 `@PreAuthorize("hasAuthority()")` 这种调用）
- 第 70 行：从缓存读取用户角色（避免每次查数据库）
- 第 76-80 行：只要有一个权限匹配就返回 true
- 第 83 行：**超级管理员**自动拥有所有权限（典型的"超管绕过"模式）
- 第 96 行：严格模式 — 权限标识**找不到对应的 Menu 记录**就拒绝（防止误配）

## 4. 关键要点总结

- `@PreAuthorize` 是方法级权限控制，比 URL 级更细粒度
- ruoyi 用 `@ss.hasPermission('xxx:xxx:xxx')` 自定义语法调用业务服务判断权限
- `@EnableMethodSecurity(securedEnabled = true)` 开启方法级权限
- **超级管理员**通常自动拥有所有权限（`hasAnySuperAdmin` 兜底）
- 严格模式：权限标识必须存在数据库中，否则拒绝（防误配）

## 5. 练习题

### 练习 1：基础（必做）

写一个 Controller，方法上加 `@PreAuthorize("hasRole('ADMIN')")`，用 Postman 测试不同角色用户的访问结果。

### 练习 2：进阶

实现一个 `LoginUserPermissionService`，Bean 名字叫 `ss`，提供 `hasPermission(String)` 方法。内部从 `LoginUser.roles`（假设已存）中判断是否拥有某权限。

### 练习 3：挑战（选做）

阅读 `PermissionServiceImpl.hasAnyPermissions`，画图说明：用户 → 角色 → 菜单（权限）三级关系，并解释为什么用缓存（`getEnableUserRoleListByUserIdFromCache`）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/permission/PermissionController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/permission/PermissionServiceImpl.java`
- Spring Security @PreAuthorize：https://docs.spring.io/spring-security/reference/servlet/authorization/method-security.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
