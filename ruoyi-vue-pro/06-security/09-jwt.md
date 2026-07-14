# 9 JWT 原理

> 理解 JWT（JSON Web Token）的结构、签名原理，以及它的优缺点。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 JWT 的三段式结构：Header、Payload、Signature
- 理解 JWT 的签名和验签过程
- 知道 JWT 适合什么场景、不适合什么场景
- 了解 ruoyi 为什么选择自研 Token + Redis 而不用纯 JWT

## 📚 前置知识

- HTTP Header
- Base64 编码
- 对称加密和非对称加密概念

## 1. 核心概念

### 1.1 JWT 是什么？

**JWT（JSON Web Token）** 是一种**自包含**的 Token 格式，Token 本身携带了所有必要信息，服务器不需要查数据库就能解析出用户信息。

**典型应用**：
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

### 1.2 JWT 的三段结构

```
┌──────────── HEADER (Base64) ─────────────┐
│ {"alg":"HS256","typ":"JWT"}              │
└──────────────────────────────────────────┘
┌──────────── PAYLOAD (Base64) ────────────┐
│ {"sub":"1234567890","name":"John",       │
│  "iat":1516239022,"exp":1516242626}      │
└──────────────────────────────────────────┘
┌──────────── SIGNATURE ───────────────────┐
│ HMACSHA256(                              │
│   base64UrlEncode(header) + "." +        │
│   base64UrlEncode(payload),              │
│   secret                                  │
│ )                                        │
└──────────────────────────────────────────┘
```

- **Header**：声明算法（如 HS256）和类型
- **Payload**：用户数据（**注意：未加密！任何人都能 Base64 解码看到内容**）
- **Signature**：用密钥对 header + payload 签名，防止篡改

### 1.3 JWT 的优缺点

**优点**：
- **无状态**：服务器不存 Session，天然支持分布式
- **跨语言**：Header/Payload 是 JSON，Java/Python/Go 都能解析
- **可验证**：Signature 防止篡改

**缺点**：
- **无法主动失效**：Token 一旦签发，在过期前都有效（除非引入黑名单）
- **Payload 可见**：Base64 不是加密，敏感数据**不能放** Payload
- **Token 体积大**：每次请求都要带 Header

### 1.4 ruoyi 的选择

ruoyi **没用纯 JWT**，而是**自研 Token + Redis**：
- Token 本身是**随机字符串**（如 UUID）
- 用户信息存 Redis：`access_token:xxx -> {userId, userType, ...}`
- 优点：
  - 可**主动失效**（删除 Redis key = 登出）
  - 可**强制下线**（修改密码后踢出所有设备）
  - 性能高（Redis 内存查询）

## 2. 代码示例

### 2.1 用 jjwt 库签发 JWT

```java
// 文件：JwtUtil.java
public class JwtUtil {

    private static final String SECRET = "your-256-bit-secret";
    private static final long EXPIRATION = 3600 * 1000; // 1 小时

    // 签发 Token
    public static String generateToken(Long userId) {
        return Jwts.builder()
                .setSubject(String.valueOf(userId))
                .setIssuedAt(new Date())
                .setExpiration(new Date(System.currentTimeMillis() + EXPIRATION))
                .signWith(SignatureAlgorithm.HS256, SECRET)
                .compact();
    }

    // 验签并解析
    public static Claims parseToken(String token) {
        return Jwts.parser()
                .setSigningKey(SECRET)
                .parseClaimsJws(token)
                .getBody();
    }
}
```

### 2.2 在 ruoyi 风格中模拟 Token

```java
// 文件：TokenService.java
@Service
public class TokenService {

    @Resource
    private StringRedisTemplate redis;

    public String createToken(Long userId) {
        // 1. 生成随机 Token
        String token = UUID.randomUUID().toString();
        // 2. 存 Redis，30 分钟过期
        redis.opsForValue().set("access_token:" + token,
                JSON.toJSONString(new LoginUser(userId)),
                Duration.ofMinutes(30));
        return token;
    }

    public LoginUser getLoginUser(String token) {
        String json = redis.opsForValue().get("access_token:" + token);
        if (json == null) return null;
        return JSON.parseObject(json, LoginUser.class);
    }

    public void deleteToken(String token) {
        redis.delete("access_token:" + token);  // 主动失效
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的 OAuth2AccessToken 模型

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/dataobject/oauth2/OAuth2AccessTokenDO.java`
**核心代码**（结构示意）：

```java
@Data
@TableName("system_oauth2_access_token")
public class OAuth2AccessTokenDO {
    /** 访问令牌 */
    private String accessToken;
    /** 刷新令牌 */
    private String refreshToken;
    /** 用户编号 */
    private Long userId;
    /** 用户类型 */
    private Integer userType;
    /** 客户端编号 */
    private String clientId;
    /** 授权范围 */
    private List<String> scopes;
    /** 过期时间 */
    private LocalDateTime expiresTime;
}
```

**解读**：
- 关键是 `accessToken` 字段是**随机 UUID**，不是 JWT
- `refreshToken` 用于刷新 access_token
- 整个对象**存入 Redis**，Token 只是个 key
- 这种设计可以**主动失效**：删除 Redis key 即可

### 3.2 TokenAuthenticationFilter 还原用户

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
**核心代码**（行 71-93）：

```java
private LoginUser buildLoginUserByToken(String token, Integer userType) {
    try {
        // 关键：通过 RPC 调用 OAuth2TokenService，从 Redis 查询
        OAuth2AccessTokenCheckRespDTO accessToken = oauth2TokenApi.checkAccessToken(token);
        if (accessToken == null) {
            return null;
        }
        // 用户类型不匹配，无权限
        if (userType != null
                && ObjectUtil.notEqual(accessToken.getUserType(), userType)) {
            throw new AccessDeniedException("错误的用户类型");
        }
        // 从 Token 还原 LoginUser
        return new LoginUser().setId(accessToken.getUserId()).setUserType(accessToken.getUserType())
                .setInfo(accessToken.getUserInfo())
                .setTenantId(accessToken.getTenantId()).setScopes(accessToken.getScopes())
                .setExpiresTime(accessToken.getExpiresTime());
    } catch (ServiceException serviceException) {
        // 校验 Token 不通过时，返回 null（白名单接口不需要 Token）
        return null;
    }
}
```

**解读**：
- 第 73 行：`oauth2TokenApi.checkAccessToken(token)` 是 RPC 调用，**底层是 Redis 查询**
- 整个流程：**Token → Redis → OAuth2AccessToken → LoginUser**
- 与纯 JWT 的区别：ruoyi 的 Token 本身**不携带用户信息**，需要查 Redis

### 3.3 Token 格式示例

ruoyi 实际生成的 access_token 类似于：
```
f7d3e2c1-4b5a-6c7d-8e9f-0a1b2c3d4e5f
```

**特点**：
- **不透明**（不像 JWT 可以解析出内容）
- 安全性高：攻击者拿到 Token 也读不出任何信息
- **可撤销**：删除 Redis 即可

## 4. 关键要点总结

- JWT 是**自包含** Token（Header.Payload.Signature），适合无状态场景
- JWT **无法主动失效**（除非引入黑名单），ruoyi 选择自研 Token + Redis 解决
- ruoyi 的 access_token 是**随机字符串**，用户信息存 Redis
- 优点：可主动失效、强制下线、性能高
- 缺点：每次请求都要查 Redis（但 Redis 性能足够强）

## 5. 练习题

### 练习 1：基础（必做）

用 jjwt 库签发一个 Token，包含 `userId=123, username=alice`，过期时间 1 小时。然后用同样的 SECRET 验签并解析。

### 练习 2：进阶

解释为什么 JWT 适合"一次性 Token"（如邮箱验证链接），但**不适合**电商网站的登录态？

### 练习 3：挑战（选做）

ruoyi 的 Token 设计有什么"高招"？分析"修改密码后强制下线所有设备"是如何实现的。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
- JWT 官方：https://jwt.io/
- Spring Security OAuth2：https://docs.spring.io/spring-security/reference/servlet/oauth2/index.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
