# 5.5 SkyWalking 链路追踪

> 理解分布式链路追踪原理，掌握 SkyWalking + Spring Boot 实战集成，看懂 ruoyi 的链路追踪配置。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解分布式链路追踪的工作原理（Trace、Span）
- 掌握 SkyWalking Agent 接入 Spring Boot
- 能在 SkyWalking UI 查看调用链
- 知道 ruoyi 部署脚本如何挂载 SkyWalking Agent

## 📚 前置知识

- 微服务调用链概念
- Java Agent 机制
- `18-actuator.md`

## 1. 核心概念

### 1.1 为什么需要链路追踪？

微服务架构下，一个用户请求可能经过 **10+ 个服务**。问题排查时：
- ❌ 日志散落在不同服务器
- ❌ 不知道请求经过哪些服务
- ❌ 无法定位慢请求

**链路追踪**解决：自动记录请求经过的每个服务、每个方法的耗时。

### 1.2 SkyWalking 是什么？

Apache SkyWalking 是 **APM（应用性能监控）** 工具：
- 分布式追踪（Distributed Tracing）
- 服务拓扑图
- 慢 SQL / 慢接口分析
- 告警

### 1.3 核心概念

| 概念 | 含义 |
|------|------|
| **Trace** | 一次完整的请求链路（多个 Span 组成） |
| **Span** | 链路中的一个节点（一个服务/方法） |
| **TraceId** | 链路 ID（贯穿整条链路） |
| **SpanId** | 当前节点的 ID |
| **ParentSpanId** | 父节点 ID |

**示例**：

```
Trace: abc123
  Span 1: GET /admin-api/order (前端控制器, 50ms)
    Span 1.1: OrderService.createOrder (20ms)
      Span 1.1.1: UserService.getUser (5ms)
      Span 1.1.2: ProductService.checkStock (8ms)
        Span 1.1.2.1: SQL: SELECT * FROM stock (5ms)
```

## 2. 代码示例

### 2.1 SkyWalking Agent 启动

下载 SkyWalking Agent 后启动：

```bash
java -javaagent:/path/to/skywalking-agent.jar \
     -Dskywalking.agent.service_name=yudao-server \
     -Dskywalking.collector.backend_service=127.0.0.1:11800 \
     -jar yudao-server.jar
```

**关键参数**：
- `-javaagent:` — Java Agent 入口
- `service_name` — 在 SkyWalking UI 显示的服务名
- `collector.backend_service` — OAP 服务地址

### 2.2 接入 OpenTelemetry（ruoyi 用的方式）

**pom.xml**：

```xml
<dependency>
    <groupId>io.opentelemetry</groupId>
    <artifactId>opentelemetry-api</artifactId>
    <version>1.32.0</version>
</dependency>
```

**代码**：

```java
Tracer tracer = GlobalOpenTelemetry.getTracer("yudao-server");
Span span = tracer.spanBuilder("createOrder").startSpan();
try (Scope scope = span.makeCurrent()) {
    // 业务逻辑
    orderService.createOrder();
} finally {
    span.end();
}
```

### 2.3 SkyWalking + Logback 集成

在日志中输出 `traceId`：

```xml
<configuration>
    <appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>%d{yyyy-MM-dd HH:mm:ss} [%thread] [traceId=%X{traceId}] %-5level %logger - %msg%n</pattern>
        </encoder>
    </appender>
</configuration>
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的链路追踪配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-monitor/src/main/java/cn/iocoder/yudao/framework/tracer/config/YudaoTracerAutoConfiguration.java`
**核心代码**（行 22-29）：

```java
@AutoConfiguration
@ConditionalOnClass(name = {
        "io.opentelemetry.api.trace.Tracer", // 来自 opentelemetry-api.jar
        "javax.servlet.Filter"
})
@EnableConfigurationProperties(TracerProperties.class)
@ConditionalOnProperty(prefix = "yudao.tracer", value = "enable", matchIfMissing = true)
public class YudaoTracerAutoConfiguration {
```

**解读**：
- 第 23-26 行：自动配置 — 类路径包含 OpenTelemetry 才生效
- 第 27 行：启用 `TracerProperties` 配置类
- 第 28 行：默认启用（`matchIfMissing = true`），可通过 `yudao.tracer.enable=false` 关闭

### 3.2 Tracer Bean

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-monitor/src/main/java/cn/iocoder/yudao/framework/tracer/config/YudaoTracerAutoConfiguration.java`
**核心代码**（行 34-44）：

```java
    @Bean
    @ConditionalOnMissingBean
    public Tracer tracer() {
        return GlobalOpenTelemetry.getTracer(applicationName);
    }

    @Bean
    @ConditionalOnMissingBean
    public BizTraceAspect bizTracingAop(Tracer tracer) {
        return new BizTraceAspect(tracer);
    }
```

**解读**：
- 第 36 行：`GlobalOpenTelemetry.getTracer(applicationName)` — 单例 Tracer
  - `applicationName` 来自 `spring.application.name`（yudao-server）
- 第 42 行：定义 `BizTraceAspect`（业务追踪 AOP）
  - 与 `@BizTrace` 注解配合使用

### 3.3 TraceFilter

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-monitor/src/main/java/cn/iocoder/yudao/framework/tracer/config/YudaoTracerAutoConfiguration.java`
**核心代码**（行 46-55）：

```java
    /**
     * 创建 TraceFilter 过滤器，响应 header 设置 traceId
     */
    @Bean
    public FilterRegistrationBean<TraceFilter> traceFilter() {
        FilterRegistrationBean<TraceFilter> registrationBean = new FilterRegistrationBean<>();
        registrationBean.setFilter(new TraceFilter());
        registrationBean.setOrder(WebFilterOrderEnum.TRACE_FILTER);
        return registrationBean;
    }
```

**解读**：
- 第 51 行：注册 `TraceFilter` 过滤器
- 第 52 行：`order` 决定过滤器顺序
- **关键作用**：在 HTTP 响应头里加 `trace-id` 字段
  - 客户端拿到的响应里就能看到本次请求的 traceId
  - 排查问题时把 traceId 给开发，就能直接定位日志

### 3.4 部署脚本挂载 SkyWalking Agent

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
**核心代码**（行 22-26）：

```bash
# SkyWalking Agent 配置
#export SW_AGENT_NAME=$SERVER_NAME
#export SW_AGENT_COLLECTOR_BACKEND_SERVICES=192.168.0.84:11800
#export SW_GRPC_LOG_SERVER_HOST=192.168.0.84
#export SW_AGENT_TRACE_IGNORE_PATH="Redisson/PING,/actuator/**,/admin/**"
#export JAVA_AGENT=-javaagent:/work/skywalking/apache-skywalking-apm-bin/agent/skywalking-agent.jar
```

**解读**：
- 第 22-26 行：**注释** — SkyWalking Agent 配置模板
- 第 24 行：`SW_AGENT_NAME` — 服务名（默认 `$SERVER_NAME` = yudao-server）
- 第 25 行：`SW_AGENT_COLLECTOR_BACKEND_SERVICES` — OAP 收集器地址
- 第 27 行：`SW_AGENT_TRACE_IGNORE_PATH` — 忽略路径（心跳、监控等）
- 第 28 行：`JAVA_AGENT` — SkyWalking Agent JAR 路径
- **使用方式**：取消注释 + 修改 IP 即可

### 3.5 启动命令使用 JAVA_AGENT

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
**核心代码**（行 102）：

```bash
    # 开始启动
    BUILD_ID=dontKillMe nohup java -server $JAVA_OPS $JAVA_AGENT -jar $BASE_PATH/$SERVER_NAME.jar --spring.profiles.active=$PROFILES_ACTIVE &
```

**解读**：
- `$JAVA_AGENT` — 引用第 28 行的 `JAVA_AGENT` 变量
- 启动时挂载 SkyWalking Agent
- 全部链路追踪数据会自动上报到 `SW_AGENT_COLLECTOR_BACKEND_SERVICES`

## 4. 关键要点总结

- SkyWalking = 链路追踪 + 性能监控 + 服务拓扑
- 通过 `-javaagent:` 挂载，**无需改代码**
- ruoyi 用 **OpenTelemetry** 替代（标准化 API）
- ruoyi 部署脚本预留了 `JAVA_AGENT` 变量，取消注释即可启用 SkyWalking
- `TraceFilter` 把 traceId 写入响应头，便于客户端排查问题
- SkyWalking UI 三大视图：拓扑图 / Trace 列表 / 服务指标

## 5. 练习题

### 练习 1：基础（必做）

启动 yudao-server，访问任意接口，查看响应头（浏览器 DevTools → Network → Response Headers），找到 `trace-id` 字段。

### 练习 2：进阶

下载 SkyWalking（[官方下载](https://skywalking.apache.org/downloads/)），启动 OAP 和 UI，修改 `deploy.sh` 启用 `JAVA_AGENT`，重启 yudao-server，在 SkyWalking UI 查看调用链。

### 练习 3：挑战（选做）

在 yudao-server 的代码中加一个 `@BizTrace` 注解方法（参考 BizTraceAspect 源码），自定义业务追踪点。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-monitor/src/main/java/cn/iocoder/yudao/framework/tracer/config/YudaoTracerAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-monitor/《芋道 Spring Boot 链路追踪 SkyWalking 入门》.md`
- [Apache SkyWalking 官方文档](https://skywalking.apache.org/docs/)
- [OpenTelemetry Java 文档](https://opentelemetry.io/docs/languages/java/)

---

**文档版本**：v1.0
**最后更新**：2026-07-13
