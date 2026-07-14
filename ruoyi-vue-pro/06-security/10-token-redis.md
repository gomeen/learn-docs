# 10 Token + Redis 实现

> 详解 ruoyi 的 Token 存储设计：OAuth2AccessToken、Redis Key 设计、TTL 刷新。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ruoyi 的 access_token + refresh_token 双 Token 机制
- 掌握 Redis Key 的命名规范
- 理解 TTL 自动续期和主动失效的设计
- 能用 Spring Data Redis 实现类似方案

## 📚 前置知识

- 09-jwt.md
- Redis 基础（String、TTL）
- Spring Data Redis

## 1. 核心概念

### 1.1 双 Token 机制

| Token | 用途 | 生命周期 | 存储位置 |
|-------|------|---------|---------|
| access_token | 鉴权（每次 API 请求） | 30 分钟 | Redis |
| refresh_token | 刷新 access_token | 30 天 | Redis |

**为什么需要两个 Token？**
- access_token 频繁使用（每次请求），要**短**
- refresh_token 不频繁使用（只在 access 过期时），可以**长**
- 攻击者拿到 access_token，30 分钟后失效
- refresh_token 一般只存在客户端，泄露风险低

### 1.2 Redis Key 设计

ruoyi 的 Redis Key（推测）：

```
oauth2_access_token:{token}        -> OAuth2AccessTokenDO（30 分钟）
oauth2_refresh_token:{token}       -> accessTokenId（30 天）
```

### 1.3 TTL 自动续期

```
00:00  登录 → access_token (TTL 30min)
00:25  请求 API → 续期，TTL 重新变成 30min
00:55  请求 API → 续期，TTL 重新变成 30min
01:25  用户 30 分钟没操作 → Token 过期
```

**好处**：活跃用户永远不退出，僵尸用户自动释放。

## 2. 代码示例

### 2.1 简化的 TokenService

```java
// 文件：TokenService.java
@Service
public class TokenService {

    @Resource
    private StringRedisTemplate redis;

    private static final Duration ACCESS_TTL = Duration.ofMinutes(30);
    private static final Duration REFRESH_TTL = Duration.ofDays(30);

    public TokenPair createToken(Long userId) {
        // 1. 生成 access_token
        String accessToken = UUID.randomUUID().toString();
        OAuth2AccessTokenDO tokenDO = new OAuth2AccessTokenDO();
        tokenDO.setAccessToken(accessToken);
        tokenDO.setUserId(userId);
        tokenDO.setExpiresTime(LocalDateTime.now().plus(ACCESS_TTL));

        // 2. 存 Redis
        redis.opsForValue().set(
            "oauth2_access_token:" + accessToken,
            JSON.toJSONString(tokenDO),
            ACCESS_TTL
        );

        // 3. 生成 refresh_token
        String refreshToken = UUID.randomUUID().toString();
        redis.opsForValue().set(
            "oauth2_refresh_token:" + refreshToken,
            accessToken,
            REFRESH_TTL
        );

        return new TokenPair(accessToken, refreshToken);
    }

    public OAuth2AccessTokenDO checkAccessToken(String token) {
        String json = redis.opsForValue().get("oauth2_access_token:" + token);
        if (json == null) return null;
        OAuth2AccessTokenDO tokenDO = JSON.parseObject(json, OAuth2AccessTokenDO.class);

        // 关键：自动续期（每次访问都延长 30 分钟）
        redis.expire("oauth2_access_token:" + token, ACCESS_TTL);
        return tokenDO;
    }

    public TokenPair refresh(String refreshToken) {
        // 1. 通过 refresh_token 找到 access_token
        String accessToken = redis.opsForValue().get("oauth2_refresh_token:" + refreshToken);
        if (accessToken == null) {
            throw new ServiceException("refresh_token 已过期");
        }
        // 2. 删除旧的 access_token
        redis.delete("oauth2_access_token:" + accessToken);
        // 3. 重新签发
        OAuth2AccessTokenDO oldToken = checkAccessToken(accessToken);
        return createToken(oldToken.getUserId());
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 TokenAuthenticationFilter 中的 Token 校验

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
**核心代码**（行 44-65）：

```java
String token = SecurityFrameworkUtils.obtainAuthorization(request,
        securityProperties.getTokenHeader(), securityProperties.getTokenParameter());
if (StrUtil.isNotEmpty(token)) {
    Integer userType = WebFrameworkUtils.getLoginUserType(request);
    try {
        // 1.1 基于 token 构建登录用户
        LoginUser loginUser = buildLoginUserByToken(token, userType);
        // 1.2 模拟 Login 功能，方便日常开发调试
        if (loginUser == null) {
            loginUser = mockLoginUser(request, token, userType);
        }

        // 2. 设置当前用户
        if (loginUser != null) {
            SecurityFrameworkUtils.setLoginUser(loginUser, request);
        }
    } catch (Throwable ex) {
        CommonResult<?> result = globalExceptionHandler.allExceptionHandler(request, ex);
        ServletUtils.writeJSON(response, result);
        return;
    }
}
chain.doFilter(request, response);
```

**解读**：
- 第 44-45 行：从 Header 提取 Token（如果 Header 没有，尝试 Parameter，用于 WebSocket / SSE）
- 第 50 行：`buildLoginUserByToken` 内部调用 `oauth2TokenApi.checkAccessToken`，是 RPC 调用
- 第 60-64 行：异常处理，直接返回 JSON 响应（不抛给 Spring MVC）

### 3.2 SecurityProperties Token 配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/SecurityProperties.java`
**核心代码**（行 17-45）：

```java
@ConfigurationProperties(prefix = "yudao.security")
@Validated
@Data
public class SecurityProperties {

    /** HTTP 请求时，访问令牌的请求 Header */
    @NotEmpty(message = "Token Header 不能为空")
    private String tokenHeader = "Authorization";
    /** HTTP 请求时，访问令牌的请求参数
     * 初始目的：解决 WebSocket 无法通过 header 传参，只能通过 token 参数拼接 */
    @NotEmpty(message = "Token Parameter 不能为空")
    private String tokenParameter = "token";

    /** mock 模式的开关 */
    @NotNull(message = "mock 模式的开关不能为空")
    private Boolean mockEnable = false;
    /** mock 模式的密钥 */
    @NotEmpty(message = "mock 模式的密钥不能为空")
    private String mockSecret = "test";

    /** 免登录的 URL 列表 */
    private List<String> permitAllUrls = Collections.emptyList();

    /** PasswordEncoder 加密复杂度 */
    private Integer passwordEncoderLength = 4;
}
```

**解读**：
- `tokenHeader = "Authorization"`：Token 放在 `Authorization: Bearer xxx` Header 中
- `tokenParameter = "token"`：支持从 `?token=xxx` 读取（用于 WebSocket / SSE）
- `mockEnable` / `mockSecret`：开发环境模拟登录，**生产必须关闭**

### 3.3 obtainAuthorization 工具方法

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/util/SecurityFrameworkUtils.java`
**核心代码**（行 41-54）：

```java
public static String obtainAuthorization(HttpServletRequest request,
                                         String headerName, String parameterName) {
    // 1. 获得 Token。优先级：Header > Parameter
    String token = request.getHeader(headerName);
    if (StrUtil.isEmpty(token)) {
        token = request.getParameter(parameterName);
    }
    if (!StringUtils.hasText(token)) {
        return null;
    }
    // 2. 去除 Token 中带的 Bearer
    int index = token.indexOf(AUTHORIZATION_BEARER + " ");
    return index >= 0 ? token.substring(index + 7).trim() : token;
}
```

**解读**：
- 第 44-47 行：Header 优先，Parameter 兜底
- 第 52-53 行：去掉 `Bearer ` 前缀（如 `Bearer xxx` → `xxx`）
- **为什么优先 Header？** Header 更安全（不会进入 URL 日志）

## 4. 关键要点总结

- ruoyi 使用**双 Token 机制**：access_token（30 分钟）+ refresh_token（30 天）
- access_token 存 Redis，**TTL 自动续期**（活跃用户永不过期）
- Token Header：`Authorization: Bearer xxx`
- 支持 Parameter 传 Token（用于 WebSocket / SSE）
- mock 模式只用于开发调试，**生产必须关闭**

## 5. 练习题

### 练习 1：基础（必做）

用 Redis 实现一个简化版 TokenService：登录后返回 access_token，每次访问都续期 30 分钟。

### 练习 2：进阶

实现"修改密码后强制下线所有设备"功能。提示：用户表加一个 `password_version` 字段，Token 存版本号，登录时校验版本。

### 练习 3：挑战（选做）

解释为什么 ruoyi 的 `obtainAuthorization` 方法优先从 Header 取 Token，再从 Parameter 取？这样做有什么安全考虑？

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/util/SecurityFrameworkUtils.java`
- Spring Data Redis 文档：https://spring.io/projects/spring-data-redis

---

**文档版本**：v1.0
**最后更新**：2026-07-13
