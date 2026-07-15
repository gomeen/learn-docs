# 13 社交登录：微信/钉钉/企业微信

> 详解社交登录的原理和 ruoyi 的实现：OAuth 2.0 授权码模式 + 用户绑定。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解社交登录的"授权码模式"流程
- 知道如何接入微信、钉钉、企业微信
- 理解 ruoyi 的"用户绑定"机制
- 掌握 `SocialClientService` 的用法

## 📚 前置知识

- 账号密码登录流程（详见 [登录流程](./12-login-flow.md)）
- OAuth 2.0 授权码模式（详见 [OAuth 2.0](../../_common/07-authentication/05-oauth2.md)）
- HTTP 重定向

## 1. 核心概念

### 1.1 社交登录的授权码模式

> 📌 **Sighting**：OIDC / SSO 扩展见 [OIDC 与 SSO](../../_common/07-authentication/06-oidc-sso.md)。

```
[1] 用户点击"微信登录"
    ↓
[2] 前端跳转到微信授权页
    https://open.weixin.qq.com/connect/oauth2/authorize?
        appid=xxx
        &redirect_uri=https://yoursite.com/callback
        &response_type=code
        &scope=snsapi_login
    ↓
[3] 用户在微信页面同意授权
    ↓
[4] 微信回调 redirect_uri，带上 code
    https://yoursite.com/callback?code=xxxxx
    ↓
[5] 后端用 code + appsecret 调微信 API 换 access_token
    ↓
[6] 用 access_token 调微信 API 获取用户信息（openid、昵称、头像）
    ↓
[7] 业务系统：查 system_social_user 表
    ├─ 已绑定 → 直接登录
    └─ 未绑定 → 引导用户绑定已有账号 / 注册新账号
```

### 1.2 ruoyi 的社交登录表设计

```sql
-- 社交账号配置
CREATE TABLE system_social_client (
    id BIGINT PRIMARY KEY,
    name VARCHAR(50),         -- "微信"
    client_id VARCHAR(100),   -- 微信 AppID
    client_secret VARCHAR(100), -- 微信 AppSecret
    agent_id VARCHAR(50),     -- 钉钉用
    social_type TINYINT,      -- 1微信 2钉钉 3企业微信
    status TINYINT
);

-- 用户-社交账号 绑定关系
CREATE TABLE system_social_user (
    id BIGINT PRIMARY KEY,
    user_id BIGINT,           -- yudao 用户 ID
    openid VARCHAR(100),      -- 微信 openid
    unionid VARCHAR(100),     -- 微信 unionid（多应用统一）
    social_type TINYINT,
    user_info JSON,           -- 微信返回的用户信息
    create_time DATETIME,
    UNIQUE KEY (social_type, openid)
);
```

## 2. 代码示例

### 2.1 简化的社交登录流程

```java
// 文件：SocialLoginService.java
@Service
public class SocialLoginService {

    @Resource
    private SocialClientService socialClientService;

    // 第一步：前端跳转到授权页
    public String getAuthorizeUrl(Integer socialType, String redirectUri) {
        SocialClientDO client = socialClientService.getByType(socialType);
        // 拼接微信授权 URL
        return "https://open.weixin.qq.com/connect/oauth2/authorize?" +
                "appid=" + client.getClientId() +
                "&redirect_uri=" + URLEncoder.encode(redirectUri) +
                "&response_type=code" +
                "&scope=snsapi_login" +
                "&state=STATE#wechat_redirect";
    }

    // 第二步：微信回调，code 换 access_token
    public LoginUser socialLogin(Integer socialType, String code, String state) {
        // 1. 用 code 调微信 API 换 access_token
        WechatTokenResponse tokenResp = wechatClient.getToken(code);

        // 2. 用 access_token 拿用户信息
        WechatUserInfo userInfo = wechatClient.getUserInfo(tokenResp.getAccessToken(), tokenResp.getOpenId());

        // 3. 查找绑定关系
        SocialUserDO socialUser = socialUserMapper.selectByOpenId(socialType, userInfo.getOpenId());
        if (socialUser == null) {
            throw new ServiceException("未绑定系统账号，请先绑定");
        }

        // 4. 创建系统 Token
        return tokenService.createToken(socialUser.getUserId());
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 AuthController 社交登录接口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/auth/AuthController.java`
**核心代码**（行 156-174）：

```java
@GetMapping("/social-auth-redirect")
@PermitAll
@Operation(summary = "社交授权的跳转")
@Parameters({
        @Parameter(name = "type", description = "社交类型", required = true),
        @Parameter(name = "redirectUri", description = "回调路径")
})
public CommonResult<String> socialLogin(@RequestParam("type") Integer type,
                                        @RequestParam("redirectUri") String redirectUri) {
    return success(socialClientService.getAuthorizeUrl(
            type, UserTypeEnum.ADMIN.getValue(), redirectUri));
}

@PostMapping("/social-login")
@PermitAll
@Operation(summary = "社交快捷登录，使用 code 授权码", description = "适合未登录的用户，但是社交账号已绑定用户")
public CommonResult<AuthLoginRespVO> socialQuickLogin(@RequestBody @Valid AuthSocialLoginReqVO reqVO) {
    return success(authService.socialLogin(reqVO));
}
```

**解读**：
- 第 156-167 行：第一步，前端调用 `social-auth-redirect` 拿到授权 URL，前端跳转
- 第 169-174 行：第二步，微信回调后用 `code` 调用 `social-login` 换系统 Token
- **`@PermitAll`**：两个接口都不需要登录

### 3.2 socialLogin 业务实现

`AdminAuthServiceImpl.socialLogin()`（推测）：

```java
public AuthLoginRespVO socialLogin(AuthSocialLoginReqVO reqVO) {
    // 1. 根据 type 拿到对应的 SocialClient（微信/钉钉/企微）
    SocialClientDO client = socialClientService.getByType(reqVO.getType());

    // 2. 用 code 调第三方 API 拿用户信息
    SocialUserRespDTO socialUser = socialClientService.getSocialUserInfo(client, reqVO.getCode(), reqVO.getState());

    // 3. 查绑定关系
    SocialUserDO bindUser = socialUserService.getByTypeAndOpenId(reqVO.getType(), socialUser.getOpenid());
    if (bindUser == null) {
        // 未绑定 → 抛异常，前端引导用户绑定
        throw new ServiceException("社交账号未绑定");
    }

    // 4. 用 yudao 用户 ID 登录（创建 Token）
    return createToken(bindUser.getUserId());
}
```

**解读**：
- 第 2 步：不同的社交平台（微信/钉钉/企微）调用不同的 API
- 第 3 步：核心是 `system_social_user` 表的查询
- 第 4 步：**绑定关系是社交登录的前提**，未绑定需要走绑定流程

## 4. 关键要点总结

- 社交登录使用 OAuth 2.0 **授权码模式**（最安全）
- ruoyi 用 `system_social_client`（平台配置）+ `system_social_user`（绑定关系）两张表
- 流程：拿授权 URL → 用户授权 → 回调 code → code 换 access_token → 拿用户信息 → 查绑定 → 登录
- 未绑定的社交账号需要走"绑定"流程（已有账号 / 注册新账号）

## 5. 练习题

### 练习 1：基础（必做）

手写 OAuth 2.0 授权码模式的 4 个步骤（不用真调 API，伪代码即可）。

### 练习 2：进阶

设计"社交账号绑定"功能：用户已登录系统，要把微信账号绑定到当前系统账号。说明 API 设计和数据库表修改。

### 练习 3：挑战（选做）

为什么 ruoyi 区分"社交授权跳转"和"社交登录"两个接口？合并成一个有什么坏处？

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/auth/AuthController.java`
- 微信开放文档：https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_Login.html
- OAuth 2.0 授权码模式：https://tools.ietf.org/html/rfc6749#section-1.3.1

---

**文档版本**：v1.0
**最后更新**：2026-07-13
