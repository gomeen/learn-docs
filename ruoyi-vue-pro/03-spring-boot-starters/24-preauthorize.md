# 4.6 注解权限控制：@PreAuthorize

> 掌握 Spring Security 注解级权限控制，能用 `@PreAuthorize` 保护方法。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 `@PreAuthorize`、`@PostAuthorize` 注解
- 理解 SpEL 表达式与权限的结合
- 掌握 yudao 中的 `@PreAuthorize` 实践
- 能在业务代码中灵活使用注解鉴权

## 📚 前置知识

- [23-security-config.md](./23-security-config.md)
- SpEL 表达式
- [22-rbac-model.md](./22-rbac-model.md)
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

## 3. ruoyi 仓库源码解读

### 3.1 @EnableMethodSecurity 开启

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/`

yudao 框架中**默认开启** `@EnableMethodSecurity`（在 yudao-server 的 SecurityConfig 中）。

### 3.2 @PreAuthorize 的典型应用

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/module/system/controller/admin/user/UserController.java`
**核心代码**（节选）：

```java
@PostMapping("/create")
@Operation(summary = "新增用户")
@PreAuthorize("@ss.hasPermission('system:user:create')")
public CommonResult<Long> createUser(@Valid @RequestBody UserSaveReqVO reqVO) {
    return success(userService.createUser(reqVO));
}

@DeleteMapping("/delete")
@Operation(summary = "删除用户")
@PreAuthorize("@ss.hasPermission('system:user:delete')")
public CommonResult<Boolean> deleteUser(@RequestParam("id") Long id) {
    userService.deleteUser(id);
    return success(true);
}

@GetMapping("/get")
@Operation(summary = "获得用户")
@PreAuthorize("@ss.hasPermission('system:user:query')")
public CommonResult<UserRespVO> getUser(@RequestParam("id") Long id) {
    UserRespVO user = userService.getUser(id);
    return success(user);
}
```

**解读**：
- 全部用 `@ss.hasPermission(...)` 调用 yudao 的 `SecurityFrameworkService`
- **CRUD 4 个方法**对应 4 个权限（`query`/`create`/`update`/`delete`）

### 3.3 数据权限的注解

```java
// 上面是功能权限（@PreAuthorize），下面是数据权限（@DataPermission）

@Override
@DataPermission(enable = true)  // 自动追加 dept_id 过滤
public PageResult<UserDO> getUserPage(UserPageReqVO req) {
    return userMapper.selectPage(req, wrapper);
}
```

**两层校验**：
- `@PreAuthorize` 检查**功能权限**（能不能调）
- `@DataPermission` 自动追加**数据权限** SQL 过滤

### 3.4 yudao 的权限命名规范

yudai 的权限标识采用**模块:资源:操作** 三段式：

```
system:user:create      # 系统模块-用户-创建
system:user:update      # 系统模块-用户-更新
system:user:delete      # 系统模块-用户-删除
system:user:query       # 系统模块-用户-查询
system:user:export      # 系统模块-用户-导出
system:role:create      # 系统模块-角色-创建
infra:file:upload       # 基础设施-文件-上传
```

## 4. 关键要点总结

- **`@PreAuthorize`** 在方法执行前校验
- **`@ss.hasPermission(...)`** 是 yudao 推荐的写法（调用 `SecurityFrameworkService`）
- **`hasRole` / `hasAuthority` / `hasAnyAuthority`** 是 SpEL 内置函数
- **功能权限 + 数据权限**双层校验
- **权限标识命名**：模块:资源:操作

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中找到 5 个使用 `@PreAuthorize` 的方法，理解权限命名规范。

### 练习 2：进阶

实现"项目 CRUD"接口，定义 4 个权限（`project:query`/`create`/`update`/`delete`），在 Controller 上加 `@PreAuthorize`。

### 练习 3：挑战（选做）

用 `@PostFilter` 实现"用户只能看到自己创建的订单"。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/java/cn/iocoder/yudao/module/system/controller/admin/user/UserController.java`
- Spring Security 方法安全：https://docs.spring.io/spring-security/reference/servlet/authorization/method-security.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
