# 10 Token + Redis 实现

> 详解 ruoyi 的 Token 存储设计：OAuth2AccessToken、Redis Key 设计、TTL 刷新。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 ruoyi 的 access_token + refresh_token 双 Token 机制
- 掌握 Redis Key 的命名规范
- 理解 TTL 自动续期和主动失效的设计
- 能用 Spring Data Redis 实现类似方案

## 📚 前置知识

- JWT 机制（详见 [JWT](../../_common/07-authentication/03-jwt.md)）
- Token 刷新语义（详见 [Token 刷新](../../_common/07-authentication/04-token-refresh.md)）
- Redis 基础（String、TTL，详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）
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

工具类封装与生命周期管理详见 [自研 TokenUtils](./04-token-utils.md)；登录入口如何创建 Token 详见 [登录流程](./05-login-flow.md)。

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

## 3. 关键要点总结

- ruoyi 使用**双 Token 机制**：access_token（30 分钟）+ refresh_token（30 天）
- access_token 存 Redis，**TTL 自动续期**（活跃用户永不过期）
- Token Header：`Authorization: Bearer xxx`
- 支持 Parameter 传 Token（用于 WebSocket / SSE）
- mock 模式只用于开发调试，**生产必须关闭**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
