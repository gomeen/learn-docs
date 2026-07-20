# 4.6 注解权限控制：@PreAuthorize

> 掌握 Spring Security 注解级权限控制，能用 `@PreAuthorize` 保护方法。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `@PreAuthorize`、`@PostAuthorize` 注解
- 理解 SpEL 表达式与权限的结合
- 掌握 yudao 中的 `@PreAuthorize` 实践
- 能在业务代码中灵活使用注解鉴权

## 📚 前置知识

- [28-security-config.md](./28-security-config.md)
- SpEL 表达式
- [26-rbac-model.md](./26-rbac-model.md)
- AOP 实现权限切面的原理见 [03-aop](../02-spring-boot/03-aop.md)

## 1. 核心概念

### 1.1 方法级安全注解

| 注解 | 作用 |
|------|------|
| `@PreAuthorize` | 方法调用**前**校验 |
| `@PostAuthorize` | 方法调用**后**校验（可访问返回值） |
| `@PreFilter` | 方法调用**前**过滤参数 |
| `@PostFilter` | 方法调用**后**过滤返回值 |
| `@Secured` | 简化版 `@PreAuthorize`（只支持角色） |

### 1.2 yudao 的常用写法

```java
// 必须有 ROLE_ADMIN 角色
@PreAuthorize("hasRole('admin')")

// 必须有 system:user:create 权限
@PreAuthorize("hasAuthority('system:user:create')")

// 必须有任一权限
@PreAuthorize("hasAnyAuthority('system:user:create', 'system:user:update')")

// 匿名访问
@PreAuthorize("isAnonymous()")

// 自定义 SpEL（调用 Bean 方法）
@PreAuthorize("@ss.hasPermission('system:user:create')")
```

## 2. 代码示例

### 2.1 Controller 级别

```java
@RestController
@RequestMapping("/admin-api/system/user")
public class UserController {

    @GetMapping("/page")
    @PreAuthorize("@ss.hasPermission('system:user:query')")
    public CommonResult<PageResult<UserRespVO>> page(@Valid UserPageReqVO req) {
        return success(userService.getUserPage(req));
    }

    @PostMapping("/create")
    @PreAuthorize("@ss.hasPermission('system:user:create')")
    public CommonResult<Long> create(@Valid @RequestBody UserSaveReqVO req) {
        return success(userService.createUser(req));
    }

    @DeleteMapping("/delete")
    @PreAuthorize("@ss.hasPermission('system:user:delete')")
    public CommonResult<Boolean> delete(@RequestParam("id") Long id) {
        userService.deleteUser(id);
        return success(true);
    }
}
```

### 2.2 Service 级别

```java
@Service
public class UserServiceImpl implements UserService {

    @Override
    @PreAuthorize("hasRole('super_admin')")  // 仅超管
    public void resetPassword(Long userId) {
        // 重置密码逻辑
    }

    @Override
    @PostAuthorize("returnObject.userId == authentication.principal.id or hasRole('admin')")
    public UserDO getUser(Long id) {
        // 只能查看自己，或者是管理员
        return userMapper.selectById(id);
    }
}
```

### 2.3 开启方法安全

```java
@Configuration
@EnableMethodSecurity(prePostEnabled = true, securedEnabled = true)
public class SecurityConfig {
    // ...
}
```

## 3. 关键要点总结

- **`@PreAuthorize`** 在方法执行前校验
- **`@ss.hasPermission(...)`** 是 yudao 推荐的写法（调用 `SecurityFrameworkService`）
- **`hasRole` / `hasAuthority` / `hasAnyAuthority`** 是 SpEL 内置函数
- **功能权限 + 数据权限**双层校验
- **权限标识命名**：模块:资源:操作

---

**文档版本**：v1.0
**最后更新**：2026-07-13
