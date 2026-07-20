# 7.4.1 会员注册/登录

> 理解 ruoyi 会员中心（Member）的注册登录实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 会员模块的注册/登录实现
- 理解手机号 + 密码、手机号 + 验证码、社交登录三种方式
- 学会 JWT Token 的生成和刷新机制
- 能看懂 AppAuthController 的完整流程

## 📚 前置知识

- 管理员登录（详见 [用户管理](./07-user.md)、[登录流程](../06-security/05-login-flow.md)）
- 短信验证码（详见 [短信](./21-sms.md)）
- JWT / Token（详见 [JWT](../../_common/07-authentication/03-jwt.md)、[Token + Redis](../06-security/03-token-redis.md)）
- 社交登录（详见 [社交登录](../06-security/06-social-login.md)）

## 1. 核心概念

### 1.1 会员 vs 管理员

ruoyi 有两套用户体系：

| 维度 | 管理员 | 会员 |
|------|--------|------|
| 包路径 | `yudao-module-system` | `yudao-module-member` |
| DO | `AdminUserDO` | `MemberUserDO` |
| 登录接口 | `/admin-api/system/auth/login` | `/member/auth/login` |
| 用户类型 | `UserTypeEnum.ADMIN` | `UserTypeEnum.MEMBER` |
| 场景 | 后台管理 | 商城、C 端 |

### 1.2 会员登录方式

ruoyi 会员支持多种登录方式：

1. **手机号 + 密码**
2. **手机号 + 验证码**（短信登录）
3. **社交登录**（微信、QQ 等）

### 1.3 Token 设计

```java
public class AppAuthLoginRespVO {
    private String token;          // 访问令牌
    private String refreshToken;   // 刷新令牌
    private Long expiresIn;        // 过期时间（秒）
}
```

**Token 流程**：
1. 登录成功 → 返回 accessToken + refreshToken
2. 携带 accessToken 访问业务接口
3. accessToken 过期 → 用 refreshToken 换新 accessToken
4. refreshToken 也过期 → 重新登录

## 2. 代码示例

### 2.1 短信登录

```java
@PostMapping("/sms-login")
@Operation(summary = "使用手机 + 验证码登录")
@PermitAll
public CommonResult<AppAuthLoginRespVO> smsLogin(@RequestBody @Valid AppAuthSmsLoginReqVO reqVO) {
    return success(authService.smsLogin(reqVO));
}
```

### 2.2 短信登录 ReqVO

```java
@Schema(description = "用户 APP - 短信登录 Request VO")
@Data
public class AppAuthSmsLoginReqVO {
    @Schema(description = "手机号", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "手机号不能为空")
    @Mobile
    private String mobile;
    @Schema(description = "短信验证码", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "短信验证码不能为空")
    private String code;
}
```

### 2.3 MemberUserDO

```java
@TableName("member_user")
@Data
public class MemberUserDO {
    @TableId
    private Long id;
    private String mobile;         // 手机号（登录用）
    private String password;       // 密码
    private String nickname;       // 昵称
    private String avatar;         // 头像
    private Integer status;        // 状态
    private Long levelId;          // 会员等级
    private Integer point;         // 积分
    private LocalDateTime registerIp; // 注册 IP
    private LocalDateTime loginDate;  // 最后登录
}
```

## 3. 关键要点总结

- ruoyi 会员登录支持密码、短信、社交三种方式
- 通过 `@PermitAll` 注解免鉴权
- 验证码走 `smsCodeApi`（system 模块的 RPC）
- Token 用 JWT 实现
- 登录失败有密码错误次数限制

---

**文档版本**：v1.0
**最后更新**：2026-07-13
