# 4 UserDetailsService：自定义用户加载

> 理解 Spring Security 的 `UserDetailsService` 机制，ruoyi 是如何从数据库加载用户信息的。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `UserDetails` 和 `UserDetailsService` 的作用
- 知道 ruoyi 为什么**不直接使用** `UserDetailsService`，而是走自定义的 `OAuth2Token` 流程
- 理解 `AdminAuthServiceImpl.authenticate()` 完整流程

## 📚 前置知识

- 01-filter-chain.md
- 02-auth-principal.md
- MyBatis-Plus 基础

## 1. 核心概念

### 1.1 Spring Security 标准流程

传统 Spring Security 登录流程：
```
UsernamePasswordAuthenticationFilter
    ↓ 调用
AuthenticationManager (ProviderManager)
    ↓ 委托给
DaoAuthenticationProvider
    ↓ 调用
UserDetailsService.loadUserByUsername(username)
    ↓ 返回
UserDetails → 构造 Authentication
    ↓ 设置到
SecurityContextHolder
```

### 1.2 ruoyi 的不同之处

ruoyi **没有用** `UserDetailsService`：
- **登录阶段**：`AdminAuthServiceImpl.authenticate()` 直接校验密码，返回 `AdminUserDO`
- **后续请求**：`TokenAuthenticationFilter` 解析 Token，调用 `OAuth2TokenService.checkAccessToken()` 还原 `LoginUser`
- **原因**：Token 是无状态的，每次请求都需要从 Redis 还原用户，不适合走 `UserDetailsService`

这种设计更适合前后端分离 + 多端登录（PC、App、小程序）。

## 2. 代码示例

### 2.1 传统 UserDetailsService 实现

```java
// 文件：CustomUserDetailsService.java
@Service
public class CustomUserDetailsService implements UserDetailsService {

    @Resource
    private UserMapper userMapper;

    @Override
    public UserDetails loadUserByUsername(String username) throws UsernameNotFoundException {
        // 1. 查询数据库
        UserDO user = userMapper.selectByUsername(username);
        if (user == null) {
            throw new UsernameNotFoundException("用户不存在");
        }

        // 2. 构造 UserDetails
        return User.builder()
                .username(user.getUsername())
                .password(user.getPassword())  // 已加密的密码
                .authorities(user.getRoles().stream()
                        .map(role -> new SimpleGrantedAuthority("ROLE_" + role))
                        .toList())
                .disabled(user.getStatus() == 0)
                .build();
    }
}
```

### 2.2 ruoyi 风格：直接 authenticate

```java
// 文件：AuthService.java
@Service
public class AuthService {

    @Resource
    private UserMapper userMapper;
    @Resource
    private PasswordEncoder passwordEncoder;

    public UserDO authenticate(String username, String password) {
        // 1. 查询用户
        UserDO user = userMapper.selectByUsername(username);
        if (user == null) {
            throw new BadCredentialsException("用户不存在");
        }
        // 2. 校验密码
        if (!passwordEncoder.matches(password, user.getPassword())) {
            throw new BadCredentialsException("密码错误");
        }
        // 3. 校验状态
        if (user.getStatus() == 0) {
            throw new DisabledException("用户被禁用");
        }
        return user;
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 AdminAuthServiceImpl.authenticate

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/auth/AdminAuthServiceImpl.java`
**核心代码**（行 80-99）：

```java
@Override
public AdminUserDO authenticate(String username, String password) {
    final LoginLogTypeEnum logTypeEnum = LoginLogTypeEnum.LOGIN_USERNAME;
    // 1. 校验账号是否存在
    AdminUserDO user = userService.getUserByUsername(username);
    if (user == null) {
        createLoginLog(null, username, logTypeEnum, LoginResultEnum.BAD_CREDENTIALS);
        throw exception(AUTH_LOGIN_BAD_CREDENTIALS);
    }
    // 2. 校验密码
    if (!userService.isPasswordMatch(password, user.getPassword())) {
        createLoginLog(user.getId(), username, logTypeEnum, LoginResultEnum.BAD_CREDENTIALS);
        throw exception(AUTH_LOGIN_BAD_CREDENTIALS);
    }
    // 3. 校验是否禁用
    if (CommonStatusEnum.isDisable(user.getStatus())) {
        createLoginLog(user.getId(), username, logTypeEnum, LoginResultEnum.USER_DISABLED);
        throw exception(AUTH_LOGIN_USER_DISABLED);
    }
    return user;
}
```

**解读**：
- 第 82 行 `LoginLogTypeEnum.LOGIN_USERNAME`：登录日志类型（区分账号登录/短信登录/社交登录）
- 第 84 行：通过 username 查询 AdminUserDO
- 第 86-88 行：账号不存在 → 记录登录日志（**关键**，用于安全审计）+ 抛业务异常
- 第 89-91 行：密码不匹配 → 同样记录日志
- 第 94-97 行：账号被禁用 → 抛异常
- **设计亮点**：登录失败一定要写日志（防爆破、防追溯），与 Spring Security 标准的 `UserDetailsService` 不同

### 3.2 LoginUser 替代 UserDetails

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/LoginUser.java`
**核心代码**（行 18-49）：

```java
@Data
public class LoginUser {

    public static final String INFO_KEY_NICKNAME = "nickname";
    public static final String INFO_KEY_DEPT_ID = "deptId";

    /** 用户编号 */
    private Long id;
    /** 用户类型：关联 UserTypeEnum */
    private Integer userType;
    /** 额外的用户信息（昵称、部门 ID 等） */
    private Map<String, String> info;
    /** 租户编号 */
    private Long tenantId;
    /** 授权范围 */
    private List<String> scopes;
    /** 过期时间 */
    private LocalDateTime expiresTime;
    // ...
}
```

**解读**：
- **为什么不实现 `UserDetails`？** ruoyi 的 `LoginUser` 是**从 OAuth2 Token 还原出来的**，是已认证的状态，没必要再走 `UserDetails` 的密码校验流程
- `LoginUser` 主要承载**业务字段**（用户 ID、租户 ID、info 字典），Spring Security 的 `Authentication.principal` 直接是它
- `expiresTime`：Token 过期时间，方便业务层判断

### 3.3 TokenAuthenticationFilter 中的还原流程

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
**核心代码**（行 71-93）：

```java
private LoginUser buildLoginUserByToken(String token, Integer userType) {
    try {
        OAuth2AccessTokenCheckRespDTO accessToken = oauth2TokenApi.checkAccessToken(token);
        if (accessToken == null) {
            return null;
        }
        // 用户类型不匹配，无权限
        if (userType != null
                && ObjectUtil.notEqual(accessToken.getUserType(), userType)) {
            throw new AccessDeniedException("错误的用户类型");
        }
        // 关键：从 Token 还原 LoginUser
        return new LoginUser().setId(accessToken.getUserId()).setUserType(accessToken.getUserType())
                .setInfo(accessToken.getUserInfo())
                .setTenantId(accessToken.getTenantId()).setScopes(accessToken.getScopes())
                .setExpiresTime(accessToken.getExpiresTime());
    } catch (ServiceException serviceException) {
        // 校验 Token 不通过时，返回 null 即可（避免阻塞白名单接口）
        return null;
    }
}
```

**解读**：
- 第 73 行：调用 OAuth2 服务（实际是 Redis 查询），**不查数据库**
- 第 80-83 行：用户类型不匹配 → 抛 `AccessDeniedException`
- 第 85-88 行：把 `OAuth2AccessTokenCheckRespDTO` 的字段**复制**到 `LoginUser`
- 第 89-92 行：捕获 `ServiceException` 返回 null（白名单接口不需要 Token）

## 4. 关键要点总结

- Spring Security 标准的 `UserDetailsService` 适合**表单登录 + Session** 场景
- ruoyi 使用**自定义 Authenticate + Token 还原**方案，更适合**前后端分离 + 多端登录**
- `LoginUser` 不实现 `UserDetails`，是已认证的状态直接放在 `Authentication.principal`
- 登录失败一定要写日志（`LoginLog`），用于安全审计
- `TokenAuthenticationFilter` 解析 Token，调用 `oauth2TokenApi.checkAccessToken` 还原 `LoginUser`

## 5. 练习题

### 练习 1：基础（必做）

实现一个 `loadUserByUsername(String username)` 方法，从内存 Map 中查找用户，并返回 `UserDetails`。

### 练习 2：进阶

阅读 `AdminAuthServiceImpl.login()`（不只是 `authenticate`），画出完整时序图：登录请求 → 验证码 → 用户名密码 → 角色查询 → Token 创建 → 返回响应。

### 练习 3：挑战（选做）

如果不用 Spring Security 的 `UserDetailsService`，如何自定义**密码错误 N 次后锁定账号**的功能？提示：使用 Redis 计数器。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/auth/AdminAuthServiceImpl.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
- Spring Security UserDetailsService：https://docs.spring.io/spring-security/reference/servlet/authentication/passwords/user-details-service.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
