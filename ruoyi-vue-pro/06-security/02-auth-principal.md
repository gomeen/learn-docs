# 2 Authentication 与 Authorization（认证与授权）

> 区分两个容易混淆的概念：认证（你是谁）vs 授权（你能做什么）。

## 🎯 学习目标

完成本文档后，你将能够：
- 区分 Authentication（认证）和 Authorization（授权）
- 理解 Spring Security 的 `Authentication` 接口和 `SecurityContextHolder` 机制
- 能用 `SecurityFrameworkUtils` 工具类获取当前登录用户
- 看懂 ruoyi 的 `LoginUser` 实体设计

## 📚 前置知识

- 01-filter-chain.md（Spring Security 过滤器链）
- Java 集合基础（Map、List）

## 1. 核心概念

### 1.1 认证 vs 授权

| 维度 | 认证（Authentication） | 授权（Authorization） |
|------|----------------------|---------------------|
| 英文 | Authentication | Authorization |
| 缩写 | Authn | Authz |
| 问题 | 你是谁？ | 你能做什么？ |
| 答案 | 用户名/密码/Token | 权限列表、角色 |
| 失败状态码 | 401 Unauthorized | 403 Forbidden |
| ruoyi 处理类 | `AuthenticationEntryPointImpl` | `AccessDeniedHandlerImpl` |

### 1.2 Spring Security 的 Authentication 体系

```
SecurityContextHolder（线程级）
    ↓
SecurityContext（上下文）
    ↓
Authentication（认证信息）
    ↓
Principal（主体）+ Credentials（凭证）+ Authorities（权限）
```

**关键类**：
- `SecurityContextHolder`：静态工具类，使用 ThreadLocal 存储 SecurityContext
- `Authentication`：表示一次认证，核心方法 `getPrincipal()`、`getAuthorities()`、`isAuthenticated()`
- `Principal`：通常是 `UserDetails`（用户详情）

### 1.3 认证信息的存储位置

```java
// 1. 设置（登录成功后）
SecurityContextHolder.getContext().setAuthentication(authentication);

// 2. 获取（任意代码中）
Authentication auth = SecurityContextHolder.getContext().getAuthentication();
LoginUser user = (LoginUser) auth.getPrincipal();

// 3. 清理（请求结束后）
SecurityContextHolder.clearContext();
```

## 2. 代码示例

### 2.1 基础认证流程

```java
// 文件：LoginService.java
@Service
public class LoginService {

    public LoginUser login(String username, String password) {
        // 1. 验证用户名密码
        AdminUserDO user = userMapper.selectByUsername(username);
        if (user == null || !passwordEncoder.matches(password, user.getPassword())) {
            throw new BadCredentialsException("用户名或密码错误");
        }

        // 2. 构建 Authentication 对象
        UsernamePasswordAuthenticationToken authToken =
            new UsernamePasswordAuthenticationToken(user, null, user.getAuthorities());

        // 3. 设置到 SecurityContext
        SecurityContextHolder.getContext().setAuthentication(authToken);

        return user;
    }
}
```

### 2.2 在 Controller 中获取当前用户

```java
// ❌ 错误做法：每个方法都重复 getAuthentication 代码
@GetMapping("/profile")
public UserVO profile() {
    Authentication auth = SecurityContextHolder.getContext().getAuthentication();
    LoginUser user = (LoginUser) auth.getPrincipal();
    return userService.getProfile(user.getId());
}

// ✅ 正确做法：封装工具类（ruoyi 的做法）
@GetMapping("/profile")
public UserVO profile() {
    Long userId = SecurityFrameworkUtils.getLoginUserId();
    return userService.getProfile(userId);
}
```

## 3. ruoyi 仓库源码解读

### 3.1 LoginUser 实体

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/LoginUser.java`
**核心代码**（行 18-75）：

```java
@Data
public class LoginUser {

    public static final String INFO_KEY_NICKNAME = "nickname";
    public static final String INFO_KEY_DEPT_ID = "deptId";

    /** 用户编号 */
    private Long id;
    /** 用户类型：关联 UserTypeEnum（管理员/会员） */
    private Integer userType;
    /** 额外的用户信息（昵称、部门 ID 等） */
    private Map<String, String> info;
    /** 租户编号 */
    private Long tenantId;
    /** 授权范围 */
    private List<String> scopes;
    /** 过期时间 */
    private LocalDateTime expiresTime;

    /** 上下文字段，不进行持久化（基于 LoginUser 维度的临时缓存） */
    @JsonIgnore
    private Map<String, Object> context;
    /** 访问的租户编号（用于跨租户访问场景） */
    private Long visitTenantId;

    public void setContext(String key, Object value) {
        if (context == null) {
            context = new HashMap<>();
        }
        context.put(key, value);
    }

    public <T> T getContext(String key, Class<T> type) {
        return MapUtil.get(context, key, type);
    }
}
```

**解读**：
- 第 27 行 `id`：用户编号，是认证主体的唯一标识
- 第 37 行 `info`：用 Map 存储昵称、部门 ID 等附加信息，避免在 LoginUser 中定义过多字段
- 第 41 行 `tenantId`：多租户字段，标识该 Token 属于哪个租户
- 第 58 行 `context`：**关键** — 用于临时缓存，例如数据权限规则的结果，避免每次 SQL 都重新计算
- 第 64-69 行 `setContext/getContext`：封装 Map 操作，支持类型转换

### 3.2 SecurityFrameworkUtils 工具类

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/util/SecurityFrameworkUtils.java`
**核心代码**（行 74-114）：

```java
@Nullable
public static LoginUser getLoginUser() {
    Authentication authentication = getAuthentication();
    if (authentication == null) {
        return null;
    }
    return authentication.getPrincipal() instanceof LoginUser ? (LoginUser) authentication.getPrincipal() : null;
}

@Nullable
public static Long getLoginUserId() {
    LoginUser loginUser = getLoginUser();
    return loginUser != null ? loginUser.getId() : null;
}

@Nullable
public static String getLoginUserNickname() {
    LoginUser loginUser = getLoginUser();
    return loginUser != null ? MapUtil.getStr(loginUser.getInfo(), LoginUser.INFO_KEY_NICKNAME) : null;
}
```

**解读**：
- 第 76 行：从 `SecurityContextHolder` 获取 `Authentication`
- 第 80 行：把 `Principal` 强转为 `LoginUser`（自定义的）
- 第 88-92 行：**封装** — 业务代码调用 `SecurityFrameworkUtils.getLoginUserId()` 即可获取用户 ID
- 第 100-103 行：从 `LoginUser.info` Map 中获取昵称，避免在 LoginUser 中硬编码 `nickname` 字段

### 3.3 认证失败 vs 授权失败的处理

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/handler/AuthenticationEntryPointImpl.java`
**核心代码**（行 26-33）：

```java
public class AuthenticationEntryPointImpl implements AuthenticationEntryPoint {
    @Override
    public void commence(HttpServletRequest request, HttpServletResponse response, AuthenticationException e) {
        log.debug("[commence][访问 URL({}) 时，没有登录]", request.getRequestURI(), e);
        // 返回 401
        ServletUtils.writeJSON(response, CommonResult.error(UNAUTHORIZED));
    }
}
```

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/handler/AccessDeniedHandlerImpl.java`
**核心代码**（行 31-42）：

```java
public class AccessDeniedHandlerImpl implements AccessDeniedHandler {
    @Override
    public void handle(HttpServletRequest request, HttpServletResponse response, AccessDeniedException e) {
        log.warn("[commence][访问 URL({}) 时，用户({}) 权限不够]", request.getRequestURI(),
                SecurityFrameworkUtils.getLoginUserId(), e);
        // 返回 403
        ServletUtils.writeJSON(response, CommonResult.error(FORBIDDEN));
    }
}
```

**解读**：
- **AuthenticationEntryPoint** 处理"未登录"（返回 401）
- **AccessDeniedHandler** 处理"已登录但权限不足"（返回 403）
- 这两个 Handler 被 `ExceptionTranslationFilter` 调用，是 Spring Security 处理异常的"最后一公里"

## 4. 关键要点总结

- **认证**（Authn）解决"你是谁"，失败返回 401
- **授权**（Authz）解决"你能做什么"，失败返回 403
- `SecurityContextHolder` 用 ThreadLocal 存储当前线程的 `Authentication`
- ruoyi 自定义 `LoginUser` 作为 Principal，通过 `SecurityFrameworkUtils` 工具类简化使用
- `LoginUser.context` 是临时缓存（如数据权限），避免重复计算

## 5. 练习题

### 练习 1：基础（必做）

手写一个方法 `getCurrentUserDeptId()`，从 `SecurityContextHolder` 中获取当前登录用户的部门 ID。

### 练习 2：进阶

阅读 `LoginUser.java`，解释为什么把 `info` 设计成 `Map<String, String>` 而不是具体的 `nickname` 字段。这样设计有什么好处？

### 练习 3：挑战（选做）

Spring Security 默认使用 `ThreadLocal` 存储 SecurityContext。如果使用 `@Async` 异步执行任务，会发生什么？ruoyi 是如何解决这个问题的？（提示：搜索 `TransmittableThreadLocal`）

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/LoginUser.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/util/SecurityFrameworkUtils.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/handler/AuthenticationEntryPointImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/handler/AccessDeniedHandlerImpl.java`
- Spring Security 认证：https://docs.spring.io/spring-security/reference/servlet/authentication/architecture.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
