# 7.3.6 邮件发送

> 理解 ruoyi 的邮件发送模块，支持 HTML 邮件、模板、附件。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 邮件发送的设计
- 理解邮件模板和附件的处理
- 学会配置 SMTP 邮件服务
- 能实现自定义的邮件发送

## 📚 前置知识

- JavaMailSender 基础
- SMTP 协议基础
- API 日志（详见 [API 日志](./17-api-log.md)）
- 异步 / 消息发送（详见 [ruoyi Message](../05-cache-and-mq/02-ruoyi-message.md)）

## 1. 核心概念

### 1.1 ruoyi 邮件架构

```
[业务代码] → [MailService] → [JavaMailSender] → [SMTP 服务器]
                 ↓
            [日志记录 infra_mail_log]
```

**特点**：
- 同步发送（简单业务）
- 也提供**异步**接口（不阻塞业务）
- 自动记录发送日志

### 1.2 邮件核心字段

```java
public class MailLogDO {
    private Long id;
    private String fromMail;     // 发件人
    private String toMail;      // 收件人
    private String ccMail;      // 抄送
    private String subject;     // 主题
    private String content;     // 内容
    private Integer status;     // 状态（成功/失败）
    private String errorMessage;// 错误信息
    private String templateCode;// 模板编码
    private LocalDateTime sendTime;
}
```

### 1.3 邮件模板

邮件模板存储在 `infra_mail_template` 表：

```sql
CREATE TABLE infra_mail_template (
    id BIGINT PRIMARY KEY,
    code VARCHAR(64),         -- 模板编码
    name VARCHAR(255),        -- 模板名
    title VARCHAR(255),       -- 邮件标题
    content TEXT,             -- 邮件内容（HTML）
    account_id BIGINT,        -- 发件邮箱
    status TINYINT
);
```

**HTML 模板示例**：
```html
<p>亲爱的 {userName}：</p>
<p>您的验证码是：<strong>{code}</strong></p>
<p>5 分钟内有效。</p>
```

## 2. 代码示例

### 2.1 发送简单邮件

```java
@Resource
private MailService mailService;

public void sendSimpleMail() {
    mailService.sendMail(
        "admin@iocoder.cn",                          // to
        new String[]{"yunai@iocoder.cn"},            // cc
        "测试邮件",                                    // subject
        "<h1>这是一封测试邮件</h1>",                  // content
        new String[0]                                // bcc
    );
}
```

### 2.2 发送模板邮件

```java
public void sendTemplateMail() {
    // 1. 准备参数
    Map<String, Object> params = new HashMap<>();
    params.put("userName", "芋道");
    params.put("code", "123456");
    // 2. 发送（按模板编码）
    mailService.sendTemplateMail(
        "register_verify",  // 模板编码
        "yunai@iocoder.cn", // to
        params              // 模板参数
    );
}
```

### 2.3 发送带附件

```java
mailService.sendMail(
    "admin@iocoder.cn",
    new String[]{},
    "周报",
    "<p>本周工作内容</p>",
    new String[]{},
    new File("/tmp/report.xlsx")  // 附件
);
```

## 3. 关键要点总结

- ruoyi 邮件服务基于 Spring 的 `JavaMailSender`
- 支持简单邮件、HTML 邮件、模板邮件、附件
- 自动记录发送日志（成功/失败）
- 模板参数用 `{}` 占位符
- 多个发件账号可配置在 `infra_mail_account` 表

---

**文档版本**：v1.0
**最后更新**：2026-07-13
