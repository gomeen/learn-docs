# 7.7.5 微信公众号

> 理解 ruoyi 微信公众号模块的设计。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 ruoyi 微信公众号模块的设计
- 理解微信公众平台接入流程
- 学会处理微信消息和事件
- 能实现自定义菜单、消息推送

## 📚 前置知识

- 微信公众平台文档
- XML 处理
- 会员认证（详见 [会员认证](./24-member-auth.md)）
- OAuth / 社交登录（详见 [OAuth 2.0](../../_common/07-authentication/05-oauth2.md)、[社交登录](../06-security/06-social-login.md)）

## 1. 核心概念

### 1.1 微信公众号架构

```
[微信服务器] --(HTTP)--> [ruoyi 后端]
                            ↓
                       [处理消息/事件]
                            ↓
                       [返回 XML 响应]
```

### 1.2 ruoyi 微信模块结构

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-module-mp/`

```
yudao-module-mp/
├── controller/admin/
│   ├── account/         # 公众号账号
│   ├── menu/            # 自定义菜单
│   ├── message/         # 消息推送
│   ├── user/            # 粉丝
│   └── tag/             # 标签
├── dal/
└── service/
```

### 1.3 核心概念

| 概念 | 说明 |
|------|------|
| 公众号账号 | 一个微信公众号对应一个账号配置 |
| AppID/AppSecret | 微信开放平台的凭证 |
| 关注/取消关注 | 用户的关注事件 |
| 消息类型 | 文本/图片/语音/视频/位置 |
| 自定义菜单 | 公众号底部菜单 |

## 2. 代码示例

### 2.1 微信公众号接入校验

```java
@GetMapping("/portal")
@PermitAll
public String verify(@RequestParam("signature") String signature,
                      @RequestParam("timestamp") String timestamp,
                      @RequestParam("nonce") String nonce,
                      @RequestParam("echostr") String echostr) {
    // 校验签名
    if (WxMpSignatureUtil.checkSignature(signature, timestamp, nonce, token)) {
        return echostr;  // 返回随机字符串
    }
    return "error";
}
```

### 2.2 接收微信消息

```java
@PostMapping(value = "/portal", produces = "application/xml; charset=UTF-8")
@PermitAll
public String handleMessage(@RequestBody String body, HttpServletRequest request) {
    // 1. 解析 XML
    WxMpXmlMessage message = WxMpXmlMessage.fromXml(body);
    // 2. 路由处理
    WxMpXmlOutMessage response = messageRouter.route(message);
    // 3. 返回 XML
    return response == null ? "" : response.toXml();
}
```

### 2.3 消息路由

```java
public WxMpXmlOutMessage route(WxMpXmlMessage message) {
    // 文本消息
    if (msgType == "text") {
        return handleText(message);
    }
    // 关注事件
    else if (msgType == "event" && event == "subscribe") {
        return handleSubscribe(message);
    }
    // 点击菜单
    else if (msgType == "event" && event == "CLICK") {
        return handleClick(message);
    }
}
```

### 2.4 主动推送消息

```java
public void pushMessage(Long userId, String content) {
    // 1. 查询用户 openId
    WxMpUserDO user = userMapper.selectById(userId);
    // 2. 构造消息
    WxMpCustomMessage message = WxMpCustomMessage.TEXT().toUser(user.getOpenid()).content(content).build();
    // 3. 发送
    wxMpService.getCustomMessageService().send(message);
}
```

## 3. 关键要点总结

- ruoyi 微信公众号模块基于 WxJava
- 支持多账号（一个系统对接多个公众号）
- 接入校验用 SHA1 签名
- 消息通过 XML 格式传输
- 支持消息路由（按类型分发）

---

**文档版本**：v1.0
**最后更新**：2026-07-13
