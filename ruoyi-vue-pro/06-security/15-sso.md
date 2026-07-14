# 15 SSO 单点登录

> 详解 SSO（Single Sign-On）单点登录的原理、协议，以及 ruoyi 的多端登录实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 SSO 的价值和实现方式
- 区分"同源 SSO"（Cookie）和"跨域 SSO"（Token）
- 掌握 CAS 协议和 OAuth 2.0 SSO
- 知道 ruoyi 是如何实现"一处登录，多处可用"

## 📚 前置知识

- 14-oauth2.md
- HTTP Cookie 机制
- 跨域相关

## 1. 核心概念

### 1.1 SSO 的价值

传统多系统登录问题：
```
OA 系统 → 输入账号密码
邮件系统 → 再次输入账号密码
CRM 系统 → 第三次输入账号密码
用户体验差
```

SSO 解决：
```
SSO Server（统一认证中心） → 登录一次
OA 系统 → 免登录
邮件系统 → 免登录
CRM 系统 → 免登录
```

### 1.2 SSO 的两种实现

| 类型 | 方案 | 适用场景 |
|------|------|---------|
| 同源 SSO | 共享 Cookie + 统一 Session | 所有系统在同一个父域名下 |
| 跨域 SSO | OAuth 2.0 / CAS / JWT | 系统分散在不同域名 |

### 1.3 CAS 协议（经典 SSO）

```
[1] 用户访问 app1.com
    ↓
[2] app1 发现用户未登录，重定向到 sso.com/login
    ↓
[3] 用户在 sso.com 登录
    ↓
[4] sso.com 颁发 TGC（Ticket Granting Cookie）
    ↓
[5] sso.com 重定向回 app1.com，附带 ST（Service Ticket）
    https://app1.com/callback?ticket=ST-xxx
    ↓
[6] app1.com 拿 ST 调 sso.com 验证
    POST /serviceValidate?ticket=ST-xxx&service=app1.com
    ↓
[7] sso.com 返回用户信息
    ↓
[8] app1.com 创建本地 session，登录成功
```

### 1.4 ruoyi 的多端登录

ruoyi 本身不直接提供 SSO Server，但它有"多端"概念：
- **管理后台**（`/admin-api/**`）：管理员使用
- **App 接口**（`/app-api/**`）：移动端使用
- **多端共享 Token**（可选）：用 `clientId` 区分

ruoyi 的 `OAuth2Token` 可以**多端复用**同一个 `userId`：
```java
token.setUserId(userId);
token.setUserType(ADMIN);   // 或 MEMBER
token.setClientId("yudao-admin");  // 或 "yudao-app"
```

## 2. 代码示例

### 2.1 简化版 SSO 实现（基于 Token）

```java
// 文件：SsoServer.java
@RestController
@RequestMapping("/sso")
public class SsoServer {

    @PostMapping("/login")
    public SsoLoginRespVO login(@RequestBody SsoLoginReqVO req) {
        // 1. 校验用户名密码
        UserDO user = userService.authenticate(req.getUsername(), req.getPassword());

        // 2. 生成全局 Token
        String ssoToken = IdUtil.fastSimpleUUID();
        redis.opsForValue().set("sso:" + ssoToken,
                JSON.toJSONString(new SsoUser(user.getId(), user.getUsername())),
                Duration.ofHours(2));

        // 3. 同时为每个 App 生成子 Token
        Map<String, String> appTokens = new HashMap<>();
        for (String appId : req.getAppIds()) {
            String appToken = IdUtil.fastSimpleUUID();
            redis.opsForValue().set("app_token:" + appToken, ssoToken, Duration.ofHours(2));
            appTokens.put(appId, appToken);
        }

        return new SsoLoginRespVO(ssoToken, appTokens);
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的多端实现

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/auth/AuthController.java`

ruoyi 通过 `clientId` 区分不同客户端：
- `yudao-admin`：管理后台
- `yudao-app`：App / 小程序

虽然 ruoyi 不是真正的 SSO Server，但它的 Token 设计支持**多端共享用户**：
```java
// 同一个 userId 可以签发不同 clientId 的 Token
OAuth2AccessTokenDO adminToken = createAccessToken(userId, ADMIN, "yudao-admin", scopes);
OAuth2AccessTokenDO appToken = createAccessToken(userId, ADMIN, "yudao-app", scopes);
```

### 3.2 Token 跨应用共享

`OAuth2AccessTokenDO` 表设计：
```sql
CREATE TABLE system_oauth2_access_token (
    id BIGINT PRIMARY KEY,
    access_token VARCHAR(255),
    refresh_token VARCHAR(255),
    user_id BIGINT,           -- 共享 userId
    user_type TINYINT,
    client_id VARCHAR(50),    -- 区分 client
    scopes VARCHAR(500),
    expires_time DATETIME
);
```

**查询时通过 user_id 找到该用户的所有 Token**：
```sql
SELECT * FROM system_oauth2_access_token WHERE user_id = #{userId}
```

这正是实现"踢出用户所有设备"的基础。

### 3.3 userType 隔离

虽然共享 userId，但通过 `userType` 隔离：
- 管理员（ADMIN）Token 只能访问 `/admin-api/**`
- 会员（MEMBER）Token 只能访问 `/app-api/**`

`TokenAuthenticationFilter` 校验：
```java
if (userType != null
        && ObjectUtil.notEqual(accessToken.getUserType(), userType)) {
    throw new AccessDeniedException("错误的用户类型");
}
```

## 4. 关键要点总结

- SSO 让用户**一次登录、多处访问**
- 主流协议：CAS（传统）、OAuth 2.0（现代）
- ruoyi 不是真正的 SSO Server，但通过 `clientId` 支持多端
- 多端共享 `userId`，通过 `userType` 隔离
- Token 表存 user_id 是"踢出所有设备"的基础

## 5. 练习题

### 练习 1：基础（必做）

画图说明 CAS 协议（重定向 3-4 次）vs OAuth 2.0 授权码模式的区别。

### 练习 2：进阶

设计"管理后台 + 商城 + CRM"三系统的 SSO 方案。说明 SSO Server 是什么、Token 怎么传递、如何登出。

### 练习 3：挑战（选做）

ruoyi 本身没有 SSO Server。如果要为它接入标准 CAS SSO，思路是什么？需要在哪些层做改造？

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/auth/AuthController.java`
- CAS 协议：https://apereo.github.io/cas/6.6.x/protocol/CAS-Protocol.html
- Keycloak SSO：https://www.keycloak.org/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
