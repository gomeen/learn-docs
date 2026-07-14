# 5.6 Sentry 错误监控

> 理解 Sentry 错误监控平台的工作原理，掌握 Spring Boot 应用接入 Sentry 实战。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Sentry 的工作原理与价值
- 掌握 Spring Boot 集成 Sentry
- 能在 Sentry UI 查看异常堆栈和上下文
- 知道 ruoyi 中如何接入 Sentry

## 📚 前置知识

- Spring Boot 基础
- `21-elk.md`（日志收集）
- `18-actuator.md`

## 1. 核心概念

### 1.1 为什么需要 Sentry？

传统日志的问题是**事后排查**：
- 用户报"页面打不开" — 不知道哪个接口挂了
- 错误堆栈淹没在海量日志里
- 缺少上下文（哪个用户、哪个设备、哪个接口）

**Sentry 的价值**：
- **实时捕获**异常（主动上报，不是被动查日志）
- **自动收集上下文**：用户、浏览器、URL、调用栈
- **告警 + 聚合**：同类异常归并，发送通知
- **SourceMap 还原**：前端压缩代码还原可读

### 1.2 Sentry 架构

```
App throws exception
   ↓
Sentry SDK (Java/JS/Python/...)
   ↓ HTTPS
Sentry Server (Relay + Symbolicator + Web)
   ↓
UI / API / Webhooks
```

### 1.3 核心概念

| 概念 | 含义 |
|------|------|
| **Project** | 项目（一个应用对应一个 project） |
| **Event** | 一个异常事件 |
| **Issue** | 同类异常聚合 |
| **Tag** | 维度（如 `env:prod`、`user:123`） |
| **Breadcrumb** | 面包屑（异常前的操作记录） |
| **Release** | 版本号（追踪哪个版本引入的 bug） |

## 2. 代码示例

### 2.1 引入 Sentry SDK

```xml
<dependency>
    <groupId>io.sentry</groupId>
    <artifactId>sentry-spring-boot-starter</artifactId>
    <version>6.34.0</version>
</dependency>
```

### 2.2 配置 Sentry

```yaml
# application.yaml
sentry:
  dsn: https://xxx@xxx.ingest.sentry.io/123456  # Sentry DSN
  environment: prod
  release: yudao-server@2026.06.01
  sample-rate: 1.0           # 异常采样率（1.0 = 100%）
  traces-sample-rate: 0.2    # 性能追踪采样率（0.2 = 20%）
  send-default-pii: true     # 发送 PII 信息（用户 IP 等）
  debug: false
```

### 2.3 主动捕获异常

```java
import io.sentry.Sentry;

try {
    riskyOperation();
} catch (Exception e) {
    Sentry.captureException(e);  // 上报到 Sentry
    throw e;
}
```

### 2.4 设置用户上下文

```java
import io.sentry.Sentry;

Sentry.setUser(
    io.sentry.protocol.User.builder()
        .setId("12345")
        .setEmail("user@example.com")
        .setUsername("alice")
        .build()
);

// 业务逻辑...

Sentry.setUser(null);  // 退出时清除
```

## 3. ruoyi 仓库源码解读

**注**：ruoyi 仓库**没有内置 Sentry 集成**（属于第三方 SaaS，需要自己添加）。

### 3.1 ruoyi 的异常处理

ruoyi 通过 `GlobalExceptionHandler` 统一处理异常：

**推测路径**：`/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/GlobalExceptionHandler.java`

ruoyi 提供了 `ApiErrorLog` 机制（数据库表 `infra_api_error_log`），所有未捕获的异常都会记录到数据库。但**没有自动上报到 Sentry**。

### 3.2 ruoyi 接入 Sentry 的推荐方案

**步骤 1：添加依赖**

```xml
<!-- yudao-server/pom.xml -->
<dependency>
    <groupId>io.sentry</groupId>
    <artifactId>sentry-spring-boot-starter</artifactId>
    <version>6.34.0</version>
</dependency>
```

**步骤 2：配置 DSN**

```yaml
# application-prod.yaml
sentry:
  dsn: ${SENTRY_DSN}
  environment: prod
  release: yudao-server@${revision}
  sample-rate: 1.0
  traces-sample-rate: 0.1
```

**步骤 3：自定义异常上报**

在 `GlobalExceptionHandler` 中加 Sentry 上报：

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(value = Exception.class)
    public CommonResult<?> exceptionHandler(HttpServletRequest req, Exception ex) {
        // 原有逻辑：记录到数据库
        apiErrorLogService.create(...);

        // 新增：上报到 Sentry
        Sentry.setExtra("url", req.getRequestURI());
        Sentry.setExtra("method", req.getMethod());
        Sentry.captureException(ex);

        return CommonResult.error(...);
    }
}
```

### 3.3 自建 Sentry 服务

**docker-compose 部署 Sentry**：

```yaml
version: "3.4"
services:
  sentry:
    image: getsentry/sentry:latest
    ports:
      - "9000:9000"
    environment:
      SENTRY_SECRET_KEY: ...
      SENTRY_DB: postgres
      SENTRY_REDIS: redis
```

**注**：自建 Sentry 资源消耗大（至少 4G 内存），生产推荐使用 Sentry 官方 SaaS（免费 5K 事件/月）。

## 4. 关键要点总结

- Sentry = 实时异常监控 + 上下文聚合 + 告警
- 通过 `sentry-spring-boot-starter` 集成 Spring Boot
- 关键配置：DSN（项目地址）、environment、release、采样率
- ruoyi 通过 `GlobalExceptionHandler` 统一处理异常，但**没有内置 Sentry 集成**
- 推荐改造：在 `GlobalExceptionHandler` 中调用 `Sentry.captureException(ex)`
- 自建 Sentry 资源消耗大，推荐用官方 SaaS

## 5. 练习题

### 练习 1：基础（必做）

注册 Sentry 账号（[sentry.io](https://sentry.io)），创建项目，拿到 DSN，配置 yudao-server，启动后故意抛出一个异常（`Integer.parseInt("abc")`），在 Sentry UI 查看事件。

### 练习 2：进阶

在 `GlobalExceptionHandler` 中集成 Sentry，配置 `Sentry.setUser(...)` 透传登录用户，让每个异常都关联到具体用户。

### 练习 3：挑战（选做）

为 Sentry 配置 Webhook 告警：当日异常数 > 10 或新增 critical 级别异常时，发送企业微信通知。

## 6. 参考资料

- [Sentry 官方文档](https://docs.sentry.io/)
- [Sentry Java SDK](https://github.com/getsentry/sentry-java)
- ruoyi 异常处理：参考 `yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/core/handler/`
- ruoyi 部署文档：https://doc.iocoder.cn/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
