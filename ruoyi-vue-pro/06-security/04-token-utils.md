# 11 自研 TokenUtils

> 详解 ruoyi 自研的 TokenUtils 工具类，掌握 Token 生命周期的管理方法。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Token 工具类的核心方法
- 掌握 Token 创建、校验、刷新、删除的实现
- 看懂 ruoyi 的 `OAuth2TokenService` 设计
- 能独立封装一个 TokenUtils

## 📚 前置知识

- JWT / Bearer 认证（详见 [JWT](../../_common/07-authentication/03-jwt.md)、[HTTP 认证](../../_common/07-authentication/01-http-auth.md)）
- Token + Redis 存储（详见 [Token + Redis](./03-token-redis.md)）
- Token 刷新（详见 [Token 刷新](../../_common/07-authentication/04-token-refresh.md)）
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

ruoyi 把 Token 服务**独立**成一个 RPC 服务（`OAuth2TokenService`，命名来自 OAuth2 语义，协议详见 [OAuth 2.0](../../_common/07-authentication/05-oauth2.md)）：
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

## 3. 关键要点总结

- ruoyi 把 Token 校验抽象成 RPC 接口 `OAuth2TokenCommonApi`
- `buildLoginUserByToken` 调用 RPC，从 Redis 还原 `LoginUser`
- **自动续期**：每次访问都重置 TTL
- **用户类型不匹配** → 拒绝（防止 A 端 Token 用于 B 端）
- `mockLoginUser` 仅供开发调试，**生产必须关闭**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
