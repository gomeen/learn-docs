# 7.4.1 会员注册/登录

> 理解 ruoyi 会员中心（Member）的注册登录实现。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 会员模块的注册/登录实现
- 理解手机号 + 密码、手机号 + 验证码、社交登录三种方式
- 学会 JWT Token 的生成和刷新机制
- 能看懂 AppAuthController 的完整流程

## 📚 前置知识

- 07-user.md（管理员登录）
- 19-sms.md（短信验证码）
- JWT 基础

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

## 3. ruoyi 仓库源码解读

### 3.1 AppAuthController 核心代码

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-member/src/main/java/cn/iocoder/yudao/module/member/controller/app/auth/AppAuthController.java`

**核心代码**（行 29-95）：

```java
@Tag(name = "用户 APP - 认证")
@RestController
@RequestMapping("/member/auth")
@Validated
@Slf4j
public class AppAuthController {

    @Resource
    private MemberAuthService authService;

    @PostMapping("/login")
    @Operation(summary = "使用手机 + 密码登录")
    @PermitAll
    public CommonResult<AppAuthLoginRespVO> login(@RequestBody @Valid AppAuthLoginReqVO reqVO) {
        return success(authService.login(reqVO));
    }

    @PostMapping("/logout")
    @Operation(summary = "登出系统")
    @PermitAll
    public CommonResult<Boolean> logout(HttpServletRequest request) {
        String token = SecurityFrameworkUtils.obtainAuthorization(request,
                securityProperties.getTokenHeader(), securityProperties.getTokenParameter());
        if (StrUtil.isNotBlank(token)) {
            authService.logout(token);
        }
        return success(true);
    }

    @PostMapping("/refresh-token")
    @Operation(summary = "刷新令牌")
    @PermitAll
    public CommonResult<AppAuthLoginRespVO> refreshToken(@RequestParam("refreshToken") String refreshToken) {
        return success(authService.refreshToken(refreshToken));
    }

    @PostMapping("/sms-login")
    @Operation(summary = "使用手机 + 验证码登录")
    @PermitAll
    public CommonResult<AppAuthLoginRespVO> smsLogin(@RequestBody @Valid AppAuthSmsLoginReqVO reqVO) {
        return success(authService.smsLogin(reqVO));
    }

    @PostMapping("/send-sms-code")
    @Operation(summary = "发送手机验证码")
    @PermitAll
    public CommonResult<Boolean> sendSmsCode(@RequestBody @Valid AppAuthSmsSendReqVO reqVO) {
        authService.sendSmsCode(getLoginUserId(), reqVO);
        return success(true);
    }
}
```

**解读**：
- 第 1-7 行：标准 Controller
- 第 11-13 行：登录接口，**`@PermitAll` 免鉴权**
- 第 15-21 行：登出，从请求头提取 token
- 第 23-27 行：刷新 token
- 第 29-33 行：短信登录
- 第 35-39 行：发送短信验证码

### 3.2 短信登录流程

```
1. 用户请求 /member/auth/send-sms-code  → 发送验证码到手机
2. 用户请求 /member/auth/sms-login (mobile + code)
3. 校验 code（从 Redis 读取）
4. 校验通过 → 查询/创建会员用户
5. 生成 token + refreshToken
6. 返回登录结果
```

### 3.3 MemberAuthService 登录核心

```java
@Override
@Transactional(rollbackFor = Exception.class)
public AppAuthLoginRespVO smsLogin(AppAuthSmsLoginReqVO reqVO) {
    // 1. 校验验证码
    smsCodeApi.useSmsCode(new SmsCodeUseReqDTO()
        .setMobile(reqVO.getMobile())
        .setCode(reqVO.getCode())
        .setScene(SmsSceneEnum.MEMBER_LOGIN.getCode()));
    // 2. 登录（自动注册）
    MemberUserDO user = memberUserService.getOrCreateByMobile(reqVO.getMobile());
    // 3. 创建 token
    return createToken(user);
}

private AppAuthLoginRespVO createToken(MemberUserDO user) {
    // 1. 生成访问 token
    String accessToken = JwtUtil.createToken(user.getId(), UserTypeEnum.MEMBER);
    // 2. 生成刷新 token
    String refreshToken = JwtUtil.createRefreshToken(user.getId());
    // 3. 返回
    return new AppAuthLoginRespVO(accessToken, refreshToken, ...);
}
```

## 4. 关键要点总结

- ruoyi 会员登录支持密码、短信、社交三种方式
- 通过 `@PermitAll` 注解免鉴权
- 验证码走 `smsCodeApi`（system 模块的 RPC）
- Token 用 JWT 实现
- 登录失败有密码错误次数限制

## 5. 练习题

### 练习 1：基础（必做）

打开 `AppAuthLoginReqVO.java` 和 `AppAuthLoginRespVO.java`，理解登录请求和响应结构。

### 练习 2：进阶

阅读 `MemberAuthServiceImpl.java`，理解 `login` 方法（密码登录）如何处理"密码错误次数限制"。

### 练习 3：挑战（选做）

设计"微信小程序登录"功能（OAuth2.0），列出实现步骤和需要的接口。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-member/src/main/java/cn/iocoder/yudao/module/member/controller/app/auth/AppAuthController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-member/src/main/java/cn/iocoder/yudao/module/member/service/auth/MemberAuthServiceImpl.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
