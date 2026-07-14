# 11 自研 TokenUtils

> 详解 ruoyi 自研的 TokenUtils 工具类，掌握 Token 生命周期的管理方法。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Token 工具类的核心方法
- 掌握 Token 创建、校验、刷新、删除的实现
- 看懂 ruoyi 的 `OAuth2TokenService` 设计
- 能独立封装一个 TokenUtils

## 📚 前置知识

- 09-jwt.md
- 10-token-redis.md
- Hutool 工具库

## 1. 核心概念

### 1.1 TokenUtils 的核心方法

```java
public class TokenUtils {
    public TokenPair createToken(Long userId);
    public LoginUser checkToken(String token);
    public TokenPair refreshToken(String refreshToken);
    public void deleteToken(String token);
}
```

### 1.2 ruoyi 的 RPC 设计

ruoyi 把 Token 服务**独立**成一个 RPC 服务（`OAuth2TokenService`）：
- Controller 通过 RPC 调用（同进程内 Dubbo）
- 业务层（`yudao-module-system`）提供实现
- 框架层（`yudao-framework/security`）定义接口
- **好处**：未来支持多端、跨服务调用

### 1.3 Token 失效场景

| 场景 | 处理方式 |
|------|---------|
| 用户登出 | 删除 Redis key |
| 用户改密码 | 删除该用户所有 Token |
| Token 过期 | Redis TTL 自动失效 |
| 管理员强制下线 | 删除该用户所有 Token |

## 2. 代码示例

### 2.1 简化的 TokenUtils

```java
// 文件：TokenUtils.java
public class TokenUtils {

    private static final String ACCESS_KEY_PREFIX = "oauth2_access_token:";
    private static final String REFRESH_KEY_PREFIX = "oauth2_refresh_token:";
    private static final Duration ACCESS_TTL = Duration.ofMinutes(30);
    private static final Duration REFRESH_TTL = Duration.ofDays(30);

    @Resource
    private StringRedisTemplate redis;

    public String createAccessToken(Long userId, LoginUser user) {
        String token = IdUtil.fastSimpleUUID();
        String key = ACCESS_KEY_PREFIX + token;
        redis.opsForValue().set(key, JSON.toJSONString(user), ACCESS_TTL);
        return token;
    }

    public LoginUser parseToken(String token) {
        String key = ACCESS_KEY_PREFIX + token;
        String json = redis.opsForValue().get(key);
        if (json == null) {
            throw new ServiceException("Token 无效或已过期");
        }
        // 自动续期
        redis.expire(key, ACCESS_TTL);
        return JSON.parseObject(json, LoginUser.class);
    }

    public void removeToken(String token) {
        redis.delete(ACCESS_KEY_PREFIX + token);
    }
}
```

### 2.2 强制下线实现

```java
// 文件：KickoutService.java
@Service
public class KickoutService {

    @Resource
    private StringRedisTemplate redis;

    public void kickout(Long userId) {
        // 1. 找到该用户的所有 Token
        Set<String> keys = redis.keys("oauth2_access_token:*");
        for (String key : keys) {
            String json = redis.opsForValue().get(key);
            if (json == null) continue;
            LoginUser user = JSON.parseObject(json, LoginUser.class);
            if (user.getId().equals(userId)) {
                redis.delete(key);
            }
        }
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 OAuth2TokenCommonApi（接口）

ruoyi 把 Token 校验抽象成 RPC 接口：

```java
// 文件：framework/common/biz/system/oauth2/OAuth2TokenCommonApi.java
public interface OAuth2TokenCommonApi {
    /**
     * 校验 Token，返回对应的登录用户信息
     */
    CommonResult<OAuth2AccessTokenCheckRespDTO> checkAccessToken(String accessToken);
}
```

**实现类位置**：`yudao-module-system` 中的 `OAuth2TokenServiceImpl`
**实现逻辑**（推测）：

```java
@Service
public class OAuth2TokenServiceImpl implements OAuth2TokenCommonApi {

    @Resource
    private OAuth2AccessTokenMapper tokenMapper;

    @Override
    public CommonResult<OAuth2AccessTokenCheckRespDTO> checkAccessToken(String accessToken) {
        // 1. 从 Redis 查 Token
        OAuth2AccessTokenDO tokenDO = tokenMapper.selectByAccessToken(accessToken);
        if (tokenDO == null) {
            return success(null);  // Token 不存在
        }
        // 2. 检查过期
        if (tokenDO.getExpiresTime().isBefore(LocalDateTime.now())) {
            return success(null);
        }
        // 3. 自动续期
        tokenMapper.refreshExpiresTime(accessToken, Duration.ofMinutes(30));
        // 4. 返回 LoginUser
        return success(BeanUtils.toBean(tokenDO, OAuth2AccessTokenCheckRespDTO.class));
    }
}
```

### 3.2 buildLoginUserByToken

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
        // 构建登录用户
        return new LoginUser().setId(accessToken.getUserId()).setUserType(accessToken.getUserType())
                .setInfo(accessToken.getUserInfo())
                .setTenantId(accessToken.getTenantId()).setScopes(accessToken.getScopes())
                .setExpiresTime(accessToken.getExpiresTime());
    } catch (ServiceException serviceException) {
        // 校验 Token 不通过时，返回 null
        return null;
    }
}
```

**解读**：
- 第 73 行：调用 RPC 接口（实际是同进程 Dubbo 调用）
- 第 80-83 行：用户类型不匹配 → 拒绝
- 第 85-88 行：把 `OAuth2AccessTokenCheckRespDTO` 转成 `LoginUser`
- 第 89-92 行：捕获 `ServiceException` 返回 null（白名单接口不需要 Token）

### 3.3 mockLoginUser 模拟登录

**核心代码**（行 105-117）：

```java
private LoginUser mockLoginUser(HttpServletRequest request, String token, Integer userType) {
    if (!securityProperties.getMockEnable()) {
        return null;
    }
    // 必须以 mockSecret 开头
    if (!token.startsWith(securityProperties.getMockSecret())) {
        return null;
    }
    // 构建模拟用户
    Long userId = Long.valueOf(token.substring(securityProperties.getMockSecret().length()));
    return new LoginUser().setId(userId).setUserType(userType)
            .setTenantId(WebFrameworkUtils.getTenantId(request));
}
```

**解读**：
- 仅当 `yudao.security.mock-enable=true` 才生效
- Token 格式：`test123`（mockSecret="test" + userId="123"）
- 实际用户就是 userId=123，**没有密码校验**
- **生产环境务必关闭**，否则任何人只要知道 secret 就能登录任意用户

## 4. 关键要点总结

- ruoyi 把 Token 校验抽象成 RPC 接口 `OAuth2TokenCommonApi`
- `buildLoginUserByToken` 调用 RPC，从 Redis 还原 `LoginUser`
- **自动续期**：每次访问都重置 TTL
- **用户类型不匹配** → 拒绝（防止 A 端 Token 用于 B 端）
- `mockLoginUser` 仅供开发调试，**生产必须关闭**

## 5. 练习题

### 练习 1：基础（必做）

用 `StringRedisTemplate` 实现 `removeToken(String token)`，要求支持**一次删除一个用户的所有 Token**。

### 练习 2：进阶

实现"双 Token 自动刷新"：当 access_token 过期时，客户端用 refresh_token 自动换新，**无需用户重新登录**。

### 练习 3：挑战（选做）

设计一个支持"设备管理"功能：用户可以查看"我的登录设备"，并远程踢出指定设备。请说明 Token 表结构需要加什么字段，接口如何设计。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/config/SecurityProperties.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
