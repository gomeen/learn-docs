# 4.3 Token 认证：JWT + Redis

> 理解 yudao 的 Token 认证机制，能自定义 Token 校验流程。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 yudao Token 认证的完整流程
- 掌握 OAuth2 AccessToken 的实现
- 理解为什么 yudao 用 RPC 而非 JWT
- 能扩展 Token 认证（如刷新、多端登录）

## 📚 前置知识

- [19-security-starter.md](./19-security-starter.md)
- [20-spring-security.md](./20-spring-security.md)
- OAuth2 基础（AccessToken、RefreshToken）

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

## 3. ruoyi 仓库源码解读

### 3.1 TokenAuthenticationFilter 解析 Token

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
**核心代码**（行 71-93）：

```java
private LoginUser buildLoginByToken(String token, Integer userType) {
    try {
        OAuth2AccessTokenCheckRespDTO accessToken = oauth2TokenApi.checkAccessToken(token);
        if (accessToken == null) return null;
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
        // 校验 Token 不通过时，返回 null（不抛异常）
        return null;
    }
}
```

**解读**：
- 通过 `OAuth2TokenCommonApi.checkAccessToken` **RPC 调用** 校验 Token
- 用户类型（admin / member）不匹配会拒绝
- **ServiceException 静默**——让无 token 请求继续走 Filter

### 3.2 OAuth2TokenCommonApi 接口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/biz/system/oauth2/OAuth2TokenCommonApi.java`
**核心代码**（节选）：

```java
public interface OAuth2TokenCommonApi {
    /** 创建 Token */
    CommonResult<OAuth2AccessTokenRespDTO> createAccessToken(OAuth2AccessTokenCreateReqDTO req);
    /** 校验 Token */
    CommonResult<OAuth2AccessTokenCheckRespDTO> checkAccessToken(String accessToken);
    /** 删除 Token（登出） */
    CommonResult<Boolean> removeAccessToken(String accessToken);
    /** 刷新 Token */
    CommonResult<OAuth2AccessTokenRespDTO> refreshAccessToken(String refreshToken, String clientId);
}
```

**解读**：
- 用 **RPC 抽象接口**（CommonResult 风格）
- 业务模块通过 `@Reference` 或 Feign 调用
- Token 服务与业务服务**完全解耦**

### 3.3 SecurityFrameworkUtils 设置 LoginUser

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/util/SecurityFrameworkUtils.java`
**核心代码**（节选）：

```java
public class SecurityFrameworkUtils {
    public static final String AUTHORIZATION_BEARER = "Bearer";

    public static void setLoginUser(LoginUser loginUser, HttpServletRequest request) {
        // 1. 创建 Authentication
        AbstractAuthenticationToken auth = new LoginUserAuthenticationToken(
                loginUser, loginUser.getScopes());
        auth.setAuthenticated(true);
        // 2. 设置到 SecurityContextHolder
        SecurityContextHolder.getContext().setAuthentication(auth);
        // 3. 保存到 Request（备用）
        request.setAttribute(LOGIN_USER_ATTRIBUTE, loginUser);
    }

    public static LoginUser getLoginUser() {
        // 1. 从 SecurityContextHolder 取
        Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
        if (authentication instanceof LoginUserAuthenticationToken) {
            return ((LoginUserAuthenticationToken) authentication).getLoginUser();
        }
        return null;
    }
}
```

**解读**：
- 用自定义的 `LoginUserAuthenticationToken` 包装 `LoginUser`
- 同时存入 `SecurityContextHolder` 和 `request`，方便不同场景读取
- `getLoginUser()` 任何地方都能拿到当前用户

### 3.4 TransmittableThreadLocal

通过 `TransmittableThreadLocalSecurityContextHolderStrategy` 配合 `@Async` 任务，**子线程能拿到父线程的 LoginUser**。

## 4. 关键要点总结

- **yudao 用 OAuth2 AccessToken**（非 JWT），存 Redis
- **Token 校验走 RPC**（`OAuth2TokenCommonApi`）
- **支持踢人下线**、**多端登录**、**Token 刷新**
- **`SecurityFrameworkUtils.setLoginUser`** 是设置上下文的入口
- **TTL 上下文**支持 `@Async`

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中执行登录请求，用 Redis CLI 查看 Token 在 Redis 中的存储格式。

### 练习 2：进阶

实现"踢人下线"接口：管理员可以把某用户的 Token 加入黑名单。

### 练习 3：挑战（选做）

把 yudao 的 OAuth2 Token 改造为 JWT 风格，对比两种方案的优缺点。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-security/src/main/java/cn/iocoder/yudao/framework/security/core/filter/TokenAuthenticationFilter.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-common/src/main/java/cn/iocoder/yudao/framework/common/biz/system/oauth2/OAuth2TokenCommonApi.java`
- OAuth2 规范：https://datatracker.ietf.org/doc/html/rfc6749
- Spring Authorization Server：https://spring.io/projects/spring-authorization-server

---

**文档版本**：v1.0
**最后更新**：2026-07-13
