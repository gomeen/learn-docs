# 5.3 Prometheus + Grafana

> 理解 Prometheus 时序数据库 + Grafana 可视化的工作原理，掌握 Spring Boot 应用接入 Prometheus 的方法。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Prometheus 拉取模型与 PromQL
- 掌握 Spring Boot Actuator 暴露 Prometheus 指标
- 能搭建 Prometheus + Grafana 监控 Spring Boot
- 知道如何在 Grafana 中查看 JVM 指标

## 📚 前置知识

- `18-actuator.md`
- Docker 基础
- 时序数据基本概念

## 1. 核心概念

### 1.1 Prometheus 是什么？

Prometheus 是 **CNCF 毕业**的开源监控系统：
- **时序数据库**（按时间存储指标）
- **拉取模型**（Prometheus 主动 HTTP 拉取 `/metrics`）
- **PromQL**（强大的查询语言）
- **告警**（Alertmanager）

### 1.2 监控体系组成

```
Spring Boot App (暴露 /actuator/prometheus)
       ↑
       | HTTP 拉取（每 15 秒）
       |
   Prometheus（存储 + PromQL 查询）
       ↓
   Grafana（可视化）     Alertmanager（告警 → 邮件/钉钉/企微）
```

### 1.3 核心概念

| 概念 | 含义 |
|------|------|
| **Metric** | 指标名（如 `jvm_memory_used_bytes`） |
| **Label** | 维度（`{area="heap", id="G1 Eden Space"}`） |
| **Sample** | 某个时间点的指标值（timestamp + value） |
| **Counter** | 累计计数器（只增不减） |
| **Gauge** | 瞬时值（可增可减） |
| **Histogram** | 直方图（延迟分布） |

## 2. 代码示例

### 2.1 Spring Boot 暴露 Prometheus 指标

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
  prometheus:
    metrics:
      export:
        enabled: true
```

启动后访问 `http://localhost:48080/actuator/prometheus` 即可看到 Prometheus 格式指标。

### 2.2 prometheus.yml 配置

```yaml
# 文件：prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'yudao-server'
    metrics_path: '/actuator/prometheus'
    static_configs:
      - targets: ['yudao-server:48080']
        labels:
          application: yudao-server
```

### 2.3 docker-compose 部署 Prometheus + Grafana

```yaml
version: "3.4"
services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    volumes:
      - grafana-data:/var/lib/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin

volumes:
  prometheus-data:
  grafana-data:
```

## 3. ruoyi 仓库源码解读

**注**：ruoyi 仓库**没有内置 Prometheus 配置文件**。需要自己添加。

### 3.1 启动器中的链路追踪

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-monitor/src/main/java/cn/iocoder/yudao/framework/tracer/config/YudaoTracerAutoConfiguration.java`
**核心代码**（行 1-30）：

```java
package cn.iocoder.yudao.framework.tracer.config;

import cn.iocoder.yudao.framework.common.enums.WebFilterOrderEnum;
import cn.iocoder.yudao.framework.tracer.core.aop.BizTraceAspect;
import cn.iocoder.yudao.framework.tracer.core.filter.TraceFilter;
import io.opentelemetry.api.GlobalOpenTelemetry;
import io.opentelemetry.api.trace.Tracer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;

/**
 * Tracer 配置类
 *
 * @author mashu
 */
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
- 第 1 行：包名
- 第 6-7 行：导入 OpenTelemetry（链路追踪库）
- 第 9 行：导入 `Tracer` 接口
- 第 23-27 行：自动配置条件
  - `@AutoConfiguration` — Spring Boot 自动配置
  - `@ConditionalOnClass` — 类路径包含 `Tracer` 和 `Filter` 才生效
  - `@ConditionalOnProperty` — `yudao.tracer.enable=true`（默认 true）

### 3.2 Tracer Bean 定义

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-monitor/src/main/java/cn/iocoder/yudao/framework/tracer/config/YudaoTracerAutoConfiguration.java`
**核心代码**（行 30-57）：

```java
public class YudaoTracerAutoConfiguration {

    @Value("${spring.application.name:application}")
    private String applicationName;

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

}
```

**解读**：
- 第 32 行：读取 `spring.application.name`（默认 `application`）
- 第 34-37 行：定义 `Tracer` Bean（OpenTelemetry）
  - 用 `GlobalOpenTelemetry` 单例
- 第 39-42 行：定义业务追踪 AOP（`@BizTrace` 注解）
- 第 46-52 行：定义 `TraceFilter`，在响应头里加 `trace-id`
  - 配合 SkyWalking 可以在 UI 看到请求链路

### 3.3 ruoyi 接入 Prometheus 的推荐配置

由于 ruoyi 仓库没有内置 Prometheus 配置文件，建议补充：

**文件位置**：`script/docker/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  scrape_timeout: 10s

scrape_configs:
  - job_name: 'yudao-server'
    metrics_path: '/actuator/prometheus'
    static_configs:
      - targets: ['yudao-server:48080']
        labels:
          application: yudao-server
          env: local
```

**yudao-server 添加依赖**（pom.xml）：

```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

**Grafana Dashboard 推荐**：
- 导入社区 Dashboard：**4701** (JVM Micrometer)
- 或 **12856** (Spring Boot 2.x Statistics)

## 4. 关键要点总结

- Prometheus 是时序数据库，**拉取模型**（不是推送）
- Spring Boot 引入 `micrometer-registry-prometheus` 即可暴露 `/actuator/prometheus`
- 完整监控：Spring Boot → Prometheus → Grafana + Alertmanager
- ruoyi 启用了 **OpenTelemetry**（链路追踪），但**未内置 Prometheus 集成**
- 关键指标：`jvm_memory_used_bytes`、`http_server_requests_seconds`、`jvm_gc_pause_seconds`
- Grafana 导入社区 Dashboard ID 4701 即可看到完整 JVM 视图

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 的 pom.xml 添加 `micrometer-registry-prometheus` 依赖，启动后访问 `http://localhost:48080/actuator/prometheus`，搜索 `jvm_memory_used_bytes` 指标。

### 练习 2：进阶

用 docker-compose 启动 Prometheus + Grafana，配置 Prometheus 抓取 yudao-server，在 Grafana 中配置 Prometheus 数据源，绘制 JVM 堆内存使用率图表。

### 练习 3：挑战（选做）

为 Prometheus 配置 Alertmanager：JVM 堆内存使用率 > 80% 持续 5 分钟触发告警，发送邮件通知。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-monitor/src/main/java/cn/iocoder/yudao/framework/tracer/config/YudaoTracerAutoConfiguration.java`
- [Prometheus 官方文档](https://prometheus.io/docs/introduction/overview/)
- [Grafana 官方文档](https://grafana.com/docs/)
- [Spring Boot Actuator + Prometheus 指南](https://docs.spring.io/spring-boot/docs/2.7.x/reference/html/actuator.html#actuator.metrics.export.prometheus)
- ruoyi 监控文档：https://doc.iocoder.cn/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
