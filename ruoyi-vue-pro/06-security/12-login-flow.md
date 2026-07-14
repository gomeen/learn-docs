# 12 登录流程：账号密码

> 详解 ruoyi 的账号密码登录完整流程：验证码 → 用户名密码 → Token 创建。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 完整的登录流程
- 理解验证码（Captcha）的作用
- 理解"登录失败写日志"的设计
- 能改造登录流程（如增加"密码错误 N 次锁定"）

## 📚 前置知识

- 04-user-details.md
- 10-token-redis.md
- Hutool 工具库

## 1. 核心概念

### 1.1 完整登录流程

```
[1] POST /system/auth/login
      { username, password, captchaVerification }
    ↓
[2] 校验验证码 (CaptchaService)
    ↓
[3] AdminAuthService.login()
    ├─ authenticate() — 验证用户名密码
    │   ├─ 查询 AdminUserDO
    │   ├─ isPasswordMatch()
    │   └─ 检查状态
    ├─ createToken() — 创建 OAuth2AccessToken
    │   ├─ 生成 access_token + refresh_token
    │   └─ 存 Redis
    └─ 返回 Token + 用户信息
    ↓
[4] 后续请求带 access_token，自动通过 TokenAuthenticationFilter 鉴权
```

### 1.2 登录失败处理

| 失败原因 | 日志类型 | 异常码 |
|---------|---------|--------|
| 账号不存在 | BAD_CREDENTIALS | AUTH_LOGIN_BAD_CREDENTIALS |
| 密码错误 | BAD_CREDENTIALS | AUTH_LOGIN_BAD_CREDENTIALS |
| 账号被禁用 | USER_DISABLED | AUTH_LOGIN_USER_DISABLED |
| 验证码错误 | CAPTCHA_ERROR | AUTH_LOGIN_CAPTCHA_ERROR |

**关键**：所有失败都写 `LoginLog`，用于：
- 追溯攻击源
- 分析可疑行为
- 触发安全告警

## 2. 代码示例

### 2.1 简化的 LoginService

```java
// 文件：LoginService.java
@Service
public class LoginService {

    @Resource
    private UserMapper userMapper;
    @Resource
    private PasswordEncoder passwordEncoder;
    @Resource
    private TokenService tokenService;

    public LoginResult login(String username, String password, String captcha) {
        // 1. 校验验证码
        if (!captchaService.verify(captcha)) {
            throw new ServiceException("验证码错误");
        }

        // 2. 查询用户
        UserDO user = userMapper.selectByUsername(username);
        if (user == null) {
            throw new ServiceException("账号或密码错误");  // 不要明确告诉用户"账号不存在"
        }

        // 3. 校验密码
        if (!passwordEncoder.matches(password, user.getPassword())) {
            // 记录登录日志
            loginLogService.create(user.getId(), LoginResultEnum.BAD_CREDENTIALS);
            throw new ServiceException("账号或密码错误");
        }

        // 4. 检查状态
        if (user.getStatus() == 0) {
            throw new ServiceException("账号被禁用");
        }

        // 5. 创建 Token
        String accessToken = tokenService.createAccessToken(user.getId());
        String refreshToken = tokenService.createRefreshToken(user.getId());
        return new LoginResult(accessToken, refreshToken, user);
    }
}
```

### 2.2 异常日志统一

```java
// 文件：LoginLogService.java
@Service
public class LoginLogService {

    public void create(Long userId, String username, LoginResultEnum result) {
        LoginLogDO log = new LoginLogDO();
        log.setUserId(userId);
        log.setUsername(username);
        log.setResult(result.getCode());
        log.setUserIp(ServletUtils.getClientIP());
        log.setUserAgent(ServletUtils.getUserAgent());
        log.setCreateTime(LocalDateTime.now());
        loginLogMapper.insert(log);
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 AuthController 登录接口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/auth/AuthController.java`
**核心代码**（行 66-91）：

```java
@PostMapping("/login")
@PermitAll
@Operation(summary = "使用账号密码登录")
public CommonResult<AuthLoginRespVO> login(@RequestBody @Valid AuthLoginReqVO reqVO) {
    return success(authService.login(reqVO));
}

@PostMapping("/logout")
@PermitAll
@Operation(summary = "登出系统")
public CommonResult<Boolean> logout(HttpServletRequest request) {
    String token = SecurityFrameworkUtils.obtainAuthorization(request,
            securityProperties.getTokenHeader(), securityProperties.getTokenParameter());
    if (StrUtil.isNotBlank(token)) {
        authService.logout(token, LoginLogTypeEnum.LOGOUT_SELF.getType());
    }
    return success(true);
}

@PostMapping("/refresh-token")
@PermitAll
@Operation(summary = "刷新令牌")
@Parameter(name = "refreshToken", description = "刷新令牌", required = true)
public CommonResult<AuthLoginRespVO> refreshToken(@RequestParam("refreshToken") String refreshToken) {
    return success(authService.refreshToken(refreshToken));
}
```

**解读**：
- 第 66-71 行：`/login` 接口需要 `@PermitAll`（白名单）
- 第 73-83 行：`/logout` 只需要 Token，不需要登录态校验
- 第 85-91 行：`/refresh-token` 用 refresh_token 换新 access_token

### 3.2 AdminAuthServiceImpl.authenticate

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
- 第 85-88 行：账号不存在 → 日志（userId=null）+ 抛异常
- 第 89-92 行：密码错误 → 日志（userId 已知）+ 抛异常
- 第 94-97 行：账号被禁用 → 日志 + 抛异常
- **第 86 行的 `createLoginLog` 关键**：记录 userId=null 的失败（说明登录者输入的账号根本不存在）

### 3.3 登录日志表设计

```sql
CREATE TABLE system_login_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT,                    -- 用户 ID（可能为 NULL，账号不存在）
    username VARCHAR(50),              -- 用户名（攻击者输入的）
    user_ip VARCHAR(50),               -- 来源 IP
    user_agent VARCHAR(500),           -- 浏览器 User-Agent
    result TINYINT,                    -- 登录结果：1成功 2失败 3被禁用
    login_type TINYINT,                -- 登录类型：1账号 2短信 3社交
    create_time DATETIME,
    INDEX idx_user_id (user_id),
    INDEX idx_create_time (create_time)
);
```

**分析场景**：
- 同一 IP 5 分钟内失败 100 次 → 暴力破解
- 同一账号 1 小时内失败 20 次 → 撞库
- 同一 IP 切换多个账号失败 → IP 拉黑

## 4. 关键要点总结

- 登录流程：验证码 → 用户名密码 → Token 创建
- 失败一定要写 `LoginLog`，用于安全审计
- 错误信息要模糊（"账号或密码错误"），不要明确告知"账号不存在"
- ruoyi 提供 `/login`、`/logout`、`/refresh-token` 三个核心接口
- `LoginLogTypeEnum` 区分登录类型（账号/短信/社交）

## 5. 练习题

### 练习 1：基础（必做）

用 Spring Boot 写一个 `LoginService.login(username, password)`，要求：
- 密码错误 N 次（5 次）后锁定 30 分钟
- 用 Redis 计数器实现

### 练习 2：进阶

阅读 `AdminAuthServiceImpl.login()` 完整方法（不只是 `authenticate`），画时序图说明：登录请求 → 验证码 → 用户名密码 → 创建 Token → 写日志 → 返回响应。

### 练习 3：挑战（选做）

设计"异地登录告警"功能：用户从陌生城市/设备登录时，发送短信通知用户。提示：登录成功时记录 `last_login_ip` 和 `last_login_city`，与本次登录对比。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/auth/AuthController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/auth/AdminAuthServiceImpl.java`
- Spring Security 认证：https://docs.spring.io/spring-security/reference/servlet/authentication/index.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
