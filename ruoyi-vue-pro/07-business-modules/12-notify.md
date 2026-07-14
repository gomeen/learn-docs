# 7.2.6 通知公告

> 理解 ruoyi 中通知公告（Notice）的实现，含 WebSocket 实时推送。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握通知公告的 CRUD 设计
- 理解 ruoyi 的 WebSocket 推送机制
- 学会通知公告的状态管理（草稿/发布）
- 能实现基于 WebSocket 的实时消息推送

## 📚 前置知识

- 11-dict.md
- WebSocket 基础概念
- 06-common-result.md

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

## 3. ruoyi 仓库源码解读

### 3.1 NoticeController 完整代码

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/notice/NoticeController.java`

**核心代码**（行 27-100）：

```java
@Tag(name = "管理后台 - 通知公告")
@RestController
@RequestMapping("/admin-api/system/notice")
@Validated
public class NoticeController {

    @Resource
    private NoticeService noticeService;

    @Resource
    private WebSocketSenderApi webSocketSenderApi;

    @PostMapping("/create")
    @Operation(summary = "创建通知公告")
    @PreAuthorize("@ss.hasPermission('system:notice:create')")
    public CommonResult<Long> createNotice(@Valid @RequestBody NoticeSaveReqVO createReqVO) {
        Long noticeId = noticeService.createNotice(createReqVO);
        return success(noticeId);
    }

    @GetMapping("/page")
    @Operation(summary = "获取通知公告列表")
    @PreAuthorize("@ss.hasPermission('system:notice:query')")
    public CommonResult<PageResult<NoticeRespVO>> getNoticePage(@Validated NoticePageReqVO pageReqVO) {
        PageResult<NoticeDO> pageResult = noticeService.getNoticePage(pageReqVO);
        return success(BeanUtils.toBean(pageResult, NoticeRespVO.class));
    }

    @PostMapping("/push")
    @Operation(summary = "推送通知公告", description = "只发送给 websocket 连接在线的用户")
    @Parameter(name = "id", description = "编号", required = true, example = "1024")
    @PreAuthorize("@ss.hasPermission('system:notice:update')")
    public CommonResult<Boolean> push(@RequestParam("id") Long id) {
        NoticeDO notice = noticeService.getNotice(id);
        Assert.notNull(notice, "公告不能为空");
        // 通过 websocket 推送给在线的用户
        webSocketSenderApi.sendObject(UserTypeEnum.ADMIN.getValue(), "notice-push", notice);
        return success(true);
    }
}
```

**解读**：
- 第 6-9 行：标准 Controller
- 第 11-12 行：除了 NoticeService，还注入了 `WebSocketSenderApi`
- 第 15-19 行：创建公告
- 第 24-28 行：分页查询
- 第 31-38 行：**WebSocket 推送公告**给所有在线管理员

### 3.2 NoticeService 业务方法

```java
@Override
@Transactional(rollbackFor = Exception.class)
public Long createNotice(NoticeSaveReqVO createReqVO) {
    // 1. 转换 VO -> DO
    NoticeDO notice = BeanUtils.toBean(createReqVO, NoticeDO.class);
    // 2. 插入数据库
    noticeMapper.insert(notice);
    return notice.getId();
}

@Override
public PageResult<NoticeDO> getNoticePage(NoticePageReqVO reqVO) {
    return noticeMapper.selectPage(reqVO);
}
```

## 4. 关键要点总结

- 通知公告是系统级消息，推送给所有用户
- 通过 WebSocket 实现实时推送
- `WebSocketSenderApi` 是 RPC 接口，由 infra 模块实现
- 公告有"草稿/发布/关闭"状态
- 推送消息会经过 `notice-push` 消息类型标识

## 5. 练习题

### 练习 1：基础（必做）

打开 `NoticeDO.java`，列出所有字段，理解每个字段的含义。

### 练习 2：进阶

阅读 `WebSocketSenderApi.java`（在 `yudao-module-infra` 下），理解它提供的 sendObject 方法的参数。

### 练习 3：挑战（选做）

思考：如果要给"通知公告"添加"定时发布"功能（到点自动发布并推送），需要修改哪些文件？列出具体方案。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/controller/admin/notice/NoticeController.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/dataobject/notice/NoticeDO.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/api/websocket/WebSocketSenderApi.java`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
