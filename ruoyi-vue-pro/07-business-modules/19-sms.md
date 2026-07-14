# 7.3.7 短信发送：阿里云/腾讯云

> 理解 ruoyi 的短信发送模块，支持阿里云、腾讯云等多个平台。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 短信发送的抽象设计
- 理解验证码的生成和校验流程
- 学会配置阿里云/腾讯云短信
- 能扩展新的短信平台

## 📚 前置知识

- 18-email.md
- 阿里云/腾讯云短信平台基础
- Redis 基础

## 1. 核心概念

### 1.1 短信架构

```
[业务代码] → [SmsService.send()] → [SmsClient 抽象] → [阿里云 / 腾讯云]
                  ↓
            [Redis 存储验证码] → [SmsService.use()] 校验
                  ↓
            [infra_sms_log 发送日志]
```

### 1.2 短信核心组件

**SmsClient 接口**：
```java
public interface SmsClient {
    SmsSendRespDTO sendSms(SmsSendReqDTO req);
}
```

**实现**：
- `AliyunSmsClient`：阿里云
- `TencentSmsClient`：腾讯云
- ...

### 1.3 验证码流程

```
1. 用户请求发送验证码 → 校验手机号
2. 生成 6 位随机码
3. 调用 SMS 平台发送
4. 存入 Redis：key = "sms:code:login:13800001234", value = "123456", expire = 5min
5. 用户提交验证码 → 从 Redis 读取并比对
```

## 2. 代码示例

### 2.1 发送短信验证码

```java
@Resource
private SmsCodeService smsCodeService;

public void sendLoginCode(String mobile) {
    SmsCodeSendReqDTO req = new SmsCodeSendReqDTO();
    req.setMobile(mobile);
    req.setScene(SmsSceneEnum.LOGIN.getCode());
    smsCodeService.sendSmsCode(req);
}
```

### 2.2 校验验证码

```java
public boolean verifyCode(String mobile, String code, SmsSceneEnum scene) {
    SmsCodeUseReqDTO req = new SmsCodeUseReqDTO();
    req.setMobile(mobile);
    req.setCode(code);
    req.setScene(scene.getCode());
    smsCodeService.useSmsCode(req);
    return true;
}
```

### 2.3 短信发送记录

```sql
CREATE TABLE infra_sms_log (
    id BIGINT PRIMARY KEY,
    channel_code VARCHAR(64),    -- 短信平台编码
    api_template_id VARCHAR(64), -- 短信模板 ID
    mobile VARCHAR(20),          -- 手机号
    params VARCHAR(255),         -- 模板参数
    status TINYINT,              -- 状态
    user_ip VARCHAR(50),         -- 客户端 IP
    user_id BIGINT,              -- 用户 ID
    error_code VARCHAR(64),      -- 错误码
    error_message TEXT,          -- 错误信息
    create_time DATETIME
);
```

## 3. ruoyi 仓库源码解读

### 3.1 SmsCodeController

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/sms/SmsCodeController.java`

**核心代码**（简化）：

```java
@Tag(name = "管理后台 - 短信")
@RestController
@RequestMapping("/system/sms-code")
@Validated
public class SmsCodeController {

    @Resource
    private SmsCodeService smsCodeService;

    @PostMapping("/send")
    @Operation(summary = "发送短信验证码")
    public CommonResult<Boolean> sendSmsCode(@Valid @RequestBody SmsCodeSendReqVO sendReqVO) {
        smsCodeService.sendSmsCode(BeanUtils.toBean(sendReqVO, SmsCodeSendReqDTO.class));
        return success(true);
    }
}
```

### 3.2 SmsClient 抽象

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mq/src/main/java/cn/iocoder/yudao/framework/sms/core/client/SmsClient.java`

```java
public interface SmsClient {

    /**
     * 发送短信
     */
    SmsSendRespDTO sendSms(SmsSendReqDTO req);
}
```

### 3.3 阿里云短信实现

```java
public class AliyunSmsClient implements SmsClient {

    @Override
    public SmsSendRespDTO sendSms(SmsSendReqDTO req) {
        // 1. 构造请求参数
        // 2. 调用阿里云 SDK
        // 3. 解析返回结果
        // 4. 转换为统一响应
        return new SmsSendRespDTO();
    }
}
```

### 3.4 验证码存储到 Redis

```java
public void sendSmsCode(SmsCodeSendReqDTO req) {
    // 1. 生成 6 位随机码
    String code = generateCode();
    // 2. 调用短信平台
    smsClient.sendSms(...);
    // 3. 存入 Redis（5 分钟过期）
    String key = "sms:code:" + req.getScene() + ":" + req.getMobile();
    redisTemplate.opsForValue().set(key, code, Duration.ofMinutes(5));
}
```

## 4. 关键要点总结

- ruoyi 短信用 SmsClient 抽象多种平台
- 验证码存 Redis，自动过期
- 发送记录在 `infra_sms_log`
- 阿里云、腾讯云各自有 Client 实现
- 短信模板需要先在平台审核

## 5. 练习题

### 练习 1：基础（必做）

打开 `infra_sms_log` 的 DO 类，列出字段，理解每个字段含义。

### 练习 2：进阶

阅读 `SmsCodeServiceImpl.java`，理解验证码的**发送频率限制**实现（防止刷短信）。

### 练习 3：挑战（选做）

如果要支持"国际短信"，需要做哪些扩展？列出需要修改的类。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/sms/SmsCodeController.java`
- 阿里云短信文档：https://help.aliyun.com/product/44282.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
