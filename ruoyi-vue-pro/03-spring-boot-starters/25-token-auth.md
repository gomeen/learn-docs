# 4.3 Token 认证：JWT + Redis

> 理解 yudao 的 Token 认证机制，能自定义 Token 校验流程。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 yudao Token 认证的完整流程
- 掌握 OAuth2 AccessToken 的实现
- 理解为什么 yudao 用 RPC 而非 JWT
- 能扩展 Token 认证（如刷新、多端登录）

## 📚 前置知识

- [23-security-starter.md](./23-security-starter.md)
- [24-spring-security.md](./24-spring-security.md)
- OAuth2 基础（AccessToken、RefreshToken；详见 [OAuth2](../../_common/07-authentication/05-oauth2.md)）
- JWT 原理见 [JWT](../../_common/07-authentication/03-jwt.md)；Token 刷新见 [Token 刷新](../../_common/07-authentication/04-token-refresh.md)

## 1. 核心概念

### 1.1 yudao 的 Token 方案

yudao 使用 **OAuth2 AccessToken**（非 JWT）：
- Token 是**随机字符串**，存放在**数据库** + **Redis** 中
- 微服务之间通过 **RPC** 校验 Token
- 支持**踢人下线**、**多端登录**

### 1.2 为什么不用 JWT？

| 方案 | 优点 | 缺点 |
|------|------|------|
| JWT | 无状态、跨服务 | 无法踢人下线、续签复杂 |
| OAuth2 AccessToken（yudao 用） | 可控、易撤销 | 需 RPC 校验 |

yudao 选 OAuth2 的核心理由：**企业内部系统需要踢人下线**。

### 1.3 Token 认证流程

```
1. 用户登录
   POST /auth/login
   ↓
2. 校验账号密码
   ↓
3. 生成 AccessToken (UUID)
   ↓
4. 存储到 Redis (key=token, value=loginUser) TTL=30分钟
   ↓
5. 返回 token 给前端

后续请求：
1. 前端传 Authorization: {token}
   ↓
2. TokenAuthenticationFilter 解析 token
   ↓
3. RPC 调用 OAuth2TokenCommonApi.checkAccessToken(token)
   ↓
4. 服务端从 Redis 查 token
   ↓
5. 返回 LoginUser / 401
```

## 2. 代码示例

### 2.1 登录生成 Token

```java
@Service
public class AuthServiceImpl implements AuthService {
    @Resource
    private OAuth2TokenCommonApi oauth2TokenApi;

    public LoginRespVO login(LoginReqVO req) {
        // 1. 校验账号密码
        AdminUserDO user = adminUserService.getByUsername(req.getUsername());
        if (!passwordEncoder.matches(req.getPassword(), user.getPassword())) {
            throw new ServiceException("账号或密码错误");
        }
        // 2. 创建 Token
        OAuth2AccessTokenCreateReqDTO tokenReq = new OAuth2AccessTokenCreateReqDTO()
                .setUserId(user.getId())
                .setUserType(UserTypeEnum.ADMIN.getValue())
                .setClientId("admin")
                .setScopes(Set.of("user.read"));
        OAuth2AccessTokenRespDTO tokenResp = oauth2TokenApi.createAccessToken(tokenReq);
        // 3. 返回
        return new LoginRespVO().setToken(tokenResp.getAccessToken());
    }
}
```

### 2.2 刷新 Token

```java
public CommonResult<LoginRespVO> refreshToken(String refreshToken) {
    OAuth2AccessTokenRespDTO tokenResp = oauth2TokenApi.refreshAccessToken(
        refreshToken, "admin");
    return success(new LoginRespVO().setToken(tokenResp.getAccessToken()));
}
```

### 2.3 登出

```java
public CommonResult<Boolean> logout(String token) {
    oauth2TokenApi.removeAccessToken(token);
    return success(true);
}
```

## 3. 关键要点总结

- **yudao 用 OAuth2 AccessToken**（非 JWT），存 Redis
- **Token 校验走 RPC**（`OAuth2TokenCommonApi`）
- **支持踢人下线**、**多端登录**、**Token 刷新**
- **`SecurityFrameworkUtils.setLoginUser`** 是设置上下文的入口
- **TTL 上下文**支持 `@Async`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
