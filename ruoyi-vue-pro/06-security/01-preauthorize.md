# 6 @PreAuthorize 注解权限

> 详解 Spring Security 的方法级权限控制：@PreAuthorize、@PostAuthorize 和 SpEL 表达式。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `@PreAuthorize` 注解的语法和 SpEL 表达式
- 理解 `@EnableMethodSecurity` 开启方法级权限
- 看懂 ruoyi 的 `@ss.hasPermission('system:user:create')` 自定义语法
- 能区分 URL 级别权限（filterChain）和方法级别权限（@PreAuthorize）

## 📚 前置知识

- Spring Security 与方法级权限（详见 [Spring Security](../03-spring-boot-starters/24-spring-security.md)、[RBAC](../../_common/08-authorization/01-rbac.md)）
- SpEL 表达式基础
- AOP 方法拦截（详见 [AOP](../02-spring-boot/03-aop.md)）

## 1. 核心概念

### 1.1 三种权限控制粒度

```
URL 级：通过 SecurityFilterChain 配置（如 .hasRole("ADMIN")）
    ↓
方法级：通过 @PreAuthorize 注解（ruoyi 主要使用）
    ↓
数据级：通过 @DataPermission 注解（自动加 WHERE 条件，详见 [ruoyi 数据权限](./08-ruoyi-data-permission.md)）
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

## 3. 关键要点总结

- `@PreAuthorize` 是方法级权限控制，比 URL 级更细粒度
- ruoyi 用 `@ss.hasPermission('xxx:xxx:xxx')` 自定义语法调用业务服务判断权限
- `@EnableMethodSecurity(securedEnabled = true)` 开启方法级权限
- **超级管理员**通常自动拥有所有权限（`hasAnySuperAdmin` 兜底）
- 严格模式：权限标识必须存在数据库中，否则拒绝（防误配）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
