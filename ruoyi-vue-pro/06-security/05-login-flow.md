# 12 登录流程：账号密码

> 详解 ruoyi 的账号密码登录完整流程：验证码 → 用户名密码 → Token 创建。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 完整的登录流程
- 理解验证码（Captcha）的作用
- 理解"登录失败写日志"的设计
- 能改造登录流程（如增加"密码错误 N 次锁定"）

## 📚 前置知识

- HTTP 认证与 Session/Token 模型（详见 [HTTP 认证](../../_common/07-authentication/01-http-auth.md)）
- Token + Redis（详见 [Token + Redis](./03-token-redis.md)）
- 密码存储与校验（BCrypt 等，详见 [哈希](../../_common/06-encryption/03-hash.md)）
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

> 📌 **Sighting**：社交登录（微信/钉钉）见 [社交登录](./06-social-login.md)；Token 工具封装见 [TokenUtils](./04-token-utils.md)。

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

## 3. 关键要点总结

- 登录流程：验证码 → 用户名密码 → Token 创建
- 失败一定要写 `LoginLog`，用于安全审计
- 错误信息要模糊（"账号或密码错误"），不要明确告知"账号不存在"
- ruoyi 提供 `/login`、`/logout`、`/refresh-token` 三个核心接口
- `LoginLogTypeEnum` 区分登录类型（账号/短信/社交）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
