# 14 OAuth 2.0 接入

> 详解 OAuth 2.0 的四种授权模式，以及 ruoyi 是如何作为 OAuth 2.0 服务端和客户端的。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 OAuth 2.0 的四种授权模式
- 理解 ruoyi 既是 OAuth 2.0 **服务端**（给前端用）又是 **客户端**（接入第三方）
- 看懂 `OAuth2TokenService` 的实现
- 能用 Spring Authorization Server 搭建一个 OAuth 2.0 服务

## 📚 前置知识

- 09-jwt.md
- 13-social-login.md
- Spring Boot

## 1. 核心概念

### 1.1 OAuth 2.0 四种授权模式

| 模式 | 适用场景 | 关键角色 |
|------|---------|---------|
| **授权码模式**（Authorization Code） | Web 服务端（有后端） | 最安全、最常用 |
| 隐式模式（Implicit） | 纯前端 SPA（不推荐） | 已被 PKCE 取代 |
| 密码模式（Password） | 高度信任的第一方应用 | ruoyi 内部用 |
| 客户端模式（Client Credentials） | 服务间调用 | ruoyi 内部用 |

### 1.2 OAuth 2.0 核心角色

```
Resource Owner（资源所有者）= 用户
Resource Server（资源服务器）= API 服务
Authorization Server（授权服务器）= 签发 Token
Client（客户端）= 应用
```

### 1.3 ruoyi 的双面角色

```
作为服务端（给前端用）：
  客户端：浏览器 / App
  流程：账号密码登录 → access_token

作为客户端（接入第三方）：
  服务端：微信 / 钉钉
  流程：拿授权码 → 换 access_token
```

## 2. 代码示例

### 2.1 授权码模式流程

```
[1] GET /oauth2/authorize?
        response_type=code
        &client_id=xxx
        &redirect_uri=https://yoursite.com/callback
        &scope=read,write
    ↓
[2] 用户在授权服务器登录 + 同意授权
    ↓
[3] 回调 redirect_uri，带上 code
    https://yoursite.com/callback?code=ABC123
    ↓
[4] POST /oauth2/token
        grant_type=authorization_code
        &code=ABC123
        &client_id=xxx
        &client_secret=xxx
        &redirect_uri=https://yoursite.com/callback
    ↓
[5] 授权服务器返回
    {
        "access_token": "...",
        "refresh_token": "...",
        "expires_in": 3600
    }
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的 OAuth2 设计

ruoyi 自研了一个轻量级 OAuth 2.0 实现，核心类：

```java
// 文件：yudao-module-system/.../service/oauth2/OAuth2TokenService.java
public interface OAuth2TokenService {
    // 1. 创建访问令牌
    OAuth2AccessTokenDO createAccessToken(Long userId, Integer userType, String clientId, List<String> scopes);

    // 2. 校验访问令牌
    OAuth2AccessTokenDO checkAccessToken(String accessToken);

    // 3. 移除访问令牌
    void removeAccessToken(String accessToken);

    // 4. 刷新访问令牌
    OAuth2AccessTokenDO refreshAccessToken(String refreshToken, String clientId);
}
```

**核心字段**：

```java
@Data
@TableName("system_oauth2_access_token")
public class OAuth2AccessTokenDO {
    private String accessToken;     // 访问令牌
    private String refreshToken;    // 刷新令牌
    private Long userId;            // 用户编号
    private Integer userType;       // 用户类型
    private String clientId;        // 客户端编号（如 yudao-admin、yudao-app）
    private List<String> scopes;    // 授权范围
    private LocalDateTime expiresTime;
}
```

### 3.2 createAccessToken 流程

```java
public OAuth2AccessTokenDO createAccessToken(Long userId, Integer userType, String clientId, List<String> scopes) {
    // 1. 生成 access_token（UUID）
    String accessToken = IdUtil.fastSimpleUUID();

    // 2. 生成 refresh_token
    String refreshToken = IdUtil.fastSimpleUUID();

    // 3. 构造对象
    OAuth2AccessTokenDO token = new OAuth2AccessTokenDO();
    token.setAccessToken(accessToken);
    token.setRefreshToken(refreshToken);
    token.setUserId(userId);
    token.setUserType(userType);
    token.setClientId(clientId);
    token.setScopes(scopes);
    token.setExpiresTime(LocalDateTime.now().plusSeconds(EXPIRES_SECONDS));

    // 4. 存 Redis（30 分钟过期）
    redisTemplate.opsForValue().set("oauth2_access_token:" + accessToken,
            JSON.toJSONString(token), Duration.ofSeconds(EXPIRES_SECONDS));

    return token;
}
```

### 3.3 AuthController 中的使用

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/auth/AuthController.java`

ruoyi 内部 `AdminAuthServiceImpl.login()` 调用 `oauth2TokenService.createAccessToken()` 来签发 Token，本质上是**简化版 OAuth 2.0 密码模式**：

```java
// 登录成功后
public AuthLoginRespVO login(AuthLoginReqVO reqVO) {
    // 1. 校验用户名密码
    AdminUserDO user = authenticate(reqVO.getUsername(), reqVO.getPassword());

    // 2. 创建 Token（OAuth 2.0 密码模式：用户名密码直接换 Token）
    String clientId = reqVO.getClientId();  // "yudao-admin" / "yudao-app"
    OAuth2AccessTokenDO token = oauth2TokenService.createAccessToken(
            user.getId(), UserTypeEnum.ADMIN.getValue(), clientId, Collections.emptyList());

    // 3. 返回
    return AuthConvert.INSTANCE.convert(user, token);
}
```

**解读**：
- 这就是 OAuth 2.0 **密码模式**（最简单，但只用于受信任的第一方）
- `clientId` 区分不同客户端（PC 端、App 端）
- 与标准 OAuth 2.0 不同：ruoyi 省略了 `/authorize` 步骤，直接 `/token`

## 4. 关键要点总结

- OAuth 2.0 有四种模式，ruoyi 主要用**密码模式**（自用）和**授权码模式**（接入第三方）
- ruoyi 的 `OAuth2TokenService` 是自研的轻量级实现
- `clientId` 区分客户端（PC / App / 小程序）
- 双 Token 机制：access_token（30 分钟）+ refresh_token（30 天）
- 用户类型（userType）也参与校验，防止"PC Token 用于 App"

## 5. 练习题

### 练习 1：基础（必做）

列举 OAuth 2.0 的四种授权模式，并说明每种适用什么场景。

### 练习 2：进阶

阅读 `OAuth2TokenServiceImpl`（如果有的话），对比它和 Spring Authorization Server 的区别。ruoyi 为什么要自研？

### 练习 3：挑战（选做）

用 Spring Authorization Server 搭建一个标准 OAuth 2.0 授权服务器，要求支持授权码模式。前端用 `client_credentials` + `authorization_code` 两种模式调用 API。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/auth/AuthController.java`
- OAuth 2.0 RFC：https://tools.ietf.org/html/rfc6749
- Spring Authorization Server：https://docs.spring.io/spring-authorization-server/reference/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
