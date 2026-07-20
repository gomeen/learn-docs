# 6.4 监控：Spring Boot Admin / Prometheus

> 掌握 yudao 监控体系，能集成 Spring Boot Admin 和 Prometheus。

## 🎯 学习目标

完成本文档后，你将能够：
- 了解 yudao 的监控能力（Tracer、Metrics、链路追踪）
- 掌握 Spring Boot Admin 集成
- 掌握 Prometheus + Grafana 监控
- 能自定义业务监控指标

## 📚 前置知识

- Spring Boot Actuator
- Micrometer
- Grafana + Prometheus

## 1. 核心概念

### 1.1 yudao 监控组件

| 组件 | 作用 |
|------|------|
| `BizTraceAspect` | 业务链路追踪（自定义注解） |
| `TraceFilter` | Trace ID 透传 |
| `TracerFrameworkUtils` | Trace 工具类 |
| `TracerProperties` | 链路追踪配置 |
| `YudaoMetricsAutoConfiguration` | 自定义指标 |

### 1.2 监控分层

```
应用层（Micrometer + Prometheus）
  ├── JVM 指标（内存、GC、线程）
  ├── HTTP 指标（QPS、延迟、错误率）
  ├── DB 指标（连接池、慢 SQL）
  └── 自定义业务指标
       ↓
Prometheus 抓取
       ↓
Grafana 展示
```

## 2. 代码示例

### 2.1 @BizTrace 注解（链路追踪）

```java
@Service
public class OrderServiceImpl {
    @BizTrace(operation = "createOrder")  // 自动记录到链路
    public Long createOrder(OrderCreateReq req) {
        // 业务逻辑
    }
}
```

### 2.2 集成 Spring Boot Admin

**服务端**：

```xml
<dependency>
    <groupId>de.codecentric</groupId>
    <artifactId>spring-boot-admin-starter-server</artifactId>
</dependency>
```

```java
@Configuration
@EnableAdminServer
public class AdminServerConfig { }
```

**客户端**：

```xml
<dependency>
    <groupId>de.codecentric</groupId>
    <artifactId>spring-boot-admin-starter-client</artifactId>
</dependency>
```

```yaml
spring:
  boot:
    admin:
      client:
        url: http://localhost:8080
```

### 2.3 集成 Prometheus

```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

```yaml
management:
  endpoints:
    web:
      exposure:
        include: '*'
  metrics:
    tags:
      application: yudao-server
```

## 3. 关键要点总结

- **yudao 用 Micrometer + Prometheus**
- **`@BizTrace`** 是 yudao 自研的业务链路追踪
- **Trace ID 透传** 通过 `TraceFilter`
- **Spring Boot Admin** 提供可视化 UI

---

**文档版本**：v1.0
**最后更新**：2026-07-13
