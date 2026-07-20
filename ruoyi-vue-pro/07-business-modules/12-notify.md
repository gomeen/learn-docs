# 7.2.6 通知公告

> 理解 ruoyi 中通知公告（Notice）的实现，含 WebSocket 实时推送。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握通知公告的 CRUD 设计
- 理解 ruoyi 的 WebSocket 推送机制
- 学会通知公告的状态管理（草稿/发布）
- 能实现基于 WebSocket 的实时消息推送

## 📚 前置知识

- 字典（详见 [字典](./11-dict.md)）
- WebSocket 基础（详见 [WebSocket Starter](../03-spring-boot-starters/46-websocket.md)）
- 统一响应（详见 [CommonResult](./05-common-result.md)）
- 站内信对比（详见 [站内信](./22-in-site-message.md)）

## 1. 核心概念

### 1.1 通知公告 vs 站内信

| 功能 | 通知公告 | 站内信 |
|------|----------|--------|
| 接收者 | 全部用户 | 指定用户 |
| 实时性 | WebSocket 推送 | WebSocket 推送 |
| 来源 | `system_notice` 表 | `system_notify_message` 表 |
| 场景 | 系统通知 | 用户间消息 |

### 1.2 通知公告核心字段

```java
public class NoticeDO {
    private Long id;
    private String title;       // 标题
    private String content;     // 内容
    private Integer type;       // 类型（公告/通知）
    private Integer status;     // 状态（草稿/发布/关闭）
    private LocalDateTime publishTime;  // 发布时间
}
```

### 1.3 WebSocket 推送机制

ruoyi 通过 `WebSocketSenderApi` 实现实时推送：

```java
@Resource
private WebSocketSenderApi webSocketSenderApi;

// 推送给所有在线管理员
webSocketSenderApi.sendObject(
    UserTypeEnum.ADMIN.getValue(),  // 接收者类型
    "notice-push",                 // 消息类型
    notice                          // 消息内容
);
```

**前端订阅**：
```js
ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.type === 'notice-push') {
        // 显示通知
    }
}
```

## 2. 代码示例

### 2.1 通知公告 ReqVO

```java
@Schema(description = "管理后台 - 通知公告创建/修改 Request VO")
@Data
public class NoticeSaveReqVO {
    @Schema(description = "公告编号")
    private Long id;
    @Schema(description = "公告标题", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "公告标题不能为空")
    private String title;
    @Schema(description = "公告内容", requiredMode = Schema.RequiredMode.REQUIRED)
    @NotBlank(message = "公告内容不能为空")
    private String content;
    @Schema(description = "公告类型", requiredMode = Schema.RequiredMode.REQUIRED)
    private Integer type;
    @Schema(description = "状态", requiredMode = Schema.RequiredMode.REQUIRED)
    private Integer status;
}
```

### 2.2 WebSocket 推送

```java
// 推送通知给所有管理员
@PostMapping("/push")
public CommonResult<Boolean> push(@RequestParam("id") Long id) {
    NoticeDO notice = noticeService.getNotice(id);
    Assert.notNull(notice, "公告不能为空");
    // 通过 WebSocket 推送
    webSocketSenderApi.sendObject(
        UserTypeEnum.ADMIN.getValue(),
        "notice-push",
        notice
    );
    return success(true);
}
```

## 3. 关键要点总结

- 通知公告是系统级消息，推送给所有用户
- 通过 WebSocket 实现实时推送
- `WebSocketSenderApi` 是 RPC 接口，由 infra 模块实现
- 公告有"草稿/发布/关闭"状态
- 推送消息会经过 `notice-push` 消息类型标识

---

**文档版本**：v1.0
**最后更新**：2026-07-13
