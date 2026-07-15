# 7.3.8 站内信

> 理解 ruoyi 的站内信（In-Site Message）实现，类似 IM 消息。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 站内信的设计
- 理解一对一消息和系统广播
- 学会站内信的已读未读状态管理
- 能实现自定义的站内信

## 📚 前置知识

- 短信（详见 [短信](./19-sms.md)）
- WebSocket 基础（详见 [WebSocket Starter](../03-spring-boot-starters/38-websocket.md)）
- 统一响应（详见 [CommonResult](./06-common-result.md)）

## 1. 核心概念

### 1.1 站内信 vs 通知公告

| 维度 | 通知公告 | 站内信 |
|------|----------|--------|
| 接收者 | 全部用户 | 指定用户 |
| 持久化 | `system_notice` | `system_notify_message` |
| 实时性 | WebSocket 推送 | WebSocket 推送 |
| 读未读 | 无 | 支持 |

### 1.2 站内信核心字段

```java
public class NotifyMessageDO {
    private Long id;
    private Long userId;         // 接收用户 ID
    private Integer userType;    // 用户类型
    private String templateCode; // 模板编码
    private String templateParams; // 模板参数
    private Boolean readStatus;  // 是否已读
    private LocalDateTime readTime; // 读取时间
    private LocalDateTime createTime;
}
```

### 1.3 站内信模板

```java
public class NotifyTemplateDO {
    private Long id;
    private String code;         // 模板编码
    private String name;         // 模板名
    private String nickname;     // 发送人昵称
    private String content;      // 消息内容
    private Integer type;        // 类型（系统/通知）
    private Integer status;
}
```

## 2. 代码示例

### 2.1 发送站内信

```java
@Resource
private NotifyMessageService notifyMessageService;

public void sendOrderMessage(Long userId, String orderNo) {
    // 构造模板参数
    Map<String, Object> params = new HashMap<>();
    params.put("orderNo", orderNo);
    // 发送
    notifyMessageService.sendMessage(
        NotifyTemplateEnum.ORDER_PAID,  // 模板
        userId,                          // 接收人
        params                           // 参数
    );
}
```

### 2.2 消息模板

```java
public enum NotifyTemplateEnum {
    ORDER_PAID("order_paid", "订单支付成功", "您的订单 {orderNo} 已支付成功"),
    ORDER_SHIPPED("order_shipped", "订单已发货", "您的订单 {orderNo} 已发货"),
    REFUND_APPROVED("refund_approved", "退款已通过", "您的退款申请已通过");
}
```

### 2.3 前端轮询/WebSocket

```js
// 方式1：轮询查询未读数
GET /system/notify-message/get-unread-count

// 方式2：WebSocket 实时接收
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'notify-message') {
        // 显示新消息
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 NotifyMessageController

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/notify/`

**核心代码**（简化）：

```java
@Tag(name = "管理后台 - 站内信")
@RestController
@RequestMapping("/system/notify-message")
@Validated
public class NotifyMessageController {

    @Resource
    private NotifyMessageService notifyMessageService;

    @GetMapping("/page")
    @PreAuthorize("@ss.hasPermission('system:notify-message:query')")
    public CommonResult<PageResult<NotifyMessageRespVO>> getMyMessagePage(
            @Valid NotifyMessagePageReqVO pageVO) {
        PageResult<NotifyMessageDO> pageResult = notifyMessageService.getMyMessagePage(pageVO);
        return success(BeanUtils.toBean(pageResult, NotifyMessageRespVO.class));
    }

    @GetMapping("/get-unread-count")
    public CommonResult<Long> getUnreadMessageCount() {
        return success(notifyMessageService.getUnreadMessageCount());
    }

    @PutMapping("/update-read")
    public CommonResult<Boolean> updateRead(@RequestParam("id") Long id) {
        notifyMessageService.updateRead(id);
        return success(true);
    }
}
```

### 3.2 发送站内信核心方法

```java
public Long sendMessage(NotifyTemplateEnum template, Long userId, Map<String, Object> params) {
    // 1. 加载模板
    NotifyTemplateDO tmpl = notifyTemplateService.getByCode(template.getCode());
    // 2. 渲染内容
    String content = renderTemplate(tmpl.getContent(), params);
    // 3. 写入消息表
    NotifyMessageDO message = new NotifyMessageDO();
    message.setUserId(userId);
    message.setTemplateCode(template.getCode());
    message.setContent(content);
    notifyMessageMapper.insert(message);
    // 4. 推送 WebSocket（如果在线）
    webSocketSenderApi.sendObject(userId, "notify-message", message);
    return message.getId();
}
```

## 4. 关键要点总结

- 站内信支持模板和参数渲染
- 接收者是指定用户（userId）
- 支持已读/未读状态
- 实时性通过 WebSocket 推送
- 消息持久化存储

## 5. 练习题

### 练习 1：基础（必做）

打开 `NotifyMessageDO.java`，列出字段。

### 练习 2：进阶

阅读 `NotifyMessageServiceImpl.java`，理解已读状态更新的实现。

### 练习 3：挑战（选做）

设计"全站广播"功能：向所有用户发送一条系统消息（如"系统升级通知"），需要考虑性能和实现思路。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/notify/NotifyMessageController.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
