# 7.3.7 短信发送：阿里云/腾讯云

> 理解 ruoyi 的短信发送模块，支持阿里云、腾讯云等多个平台。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 短信发送的抽象设计
- 理解验证码的生成和校验流程
- 学会配置阿里云/腾讯云短信
- 能扩展新的短信平台

## 📚 前置知识

- 邮件发送（详见 [邮件](./20-email.md)）
- 阿里云/腾讯云短信平台基础
- Redis 基础（详见 [Redis 数据结构](../../_common/01-redis/01-data-structures.md)）
- 接口限流（防刷验证码，详见 [限流算法](../../_common/03-cache-patterns/04-rate-limiting.md)）

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

## 3. 关键要点总结

- ruoyi 短信用 SmsClient 抽象多种平台
- 验证码存 Redis，自动过期
- 发送记录在 `infra_sms_log`
- 阿里云、腾讯云各自有 Client 实现
- 短信模板需要先在平台审核

---

**文档版本**：v1.0
**最后更新**：2026-07-13
