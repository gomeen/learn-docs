# 11 Actuator 监控端点

> 掌握 Spring Boot Actuator 的使用，能在 ruoyi-vue-pro 中通过 `/actuator/*` 端点监控应用健康状态、性能指标。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Actuator 的作用：暴露应用内部状态给监控系统
- 掌握常用端点：`/actuator/health`、`/actuator/info`、`/actuator/metrics`
- 能在 ruoyi-vue-pro 中启用和配置 Actuator
- 能与 Prometheus + Grafana 集成实现可视化监控

## 📚 前置知识

- [09-auto-config.md](./09-auto-config.md)（自动配置）
- [11-config.md](./11-config.md)（配置文件）
- 更完整的监控集成见 [35-monitor](../03-spring-boot-starters/42-monitor.md)

## 1. 核心概念

### 1.1 什么是 Actuator？

Spring Boot Actuator 提供了一系列**内置端点**，用于监控和管理应用：
- 健康检查、指标收集、日志查看、环境信息、线程快照等
- 默认通过 HTTP 暴露（也可通过 JMX）
- 生产环境通常只暴露 `/actuator/health` 和 `/actuator/info`

### 1.2 常用端点

| 端点 | 作用 | 是否敏感 |
|------|------|---------|
| `/actuator/health` | 应用健康状态 | 否 |
| `/actuator/info` | 应用信息（Git、版本） | 否 |
| `/actuator/metrics` | 性能指标（JVM、HTTP、DB） | 是 |
| `/actuator/env` | 环境变量、配置 | **高敏感** |
| `/actuator/loggers` | 动态调整日志级别 | 是 |
| `/actuator/threaddump` | 线程快照 | 是 |
| `/actuator/heapdump` | 堆内存快照 | **高敏感** |
| `/actuator/mappings` | 所有 URL 映射 | 是 |
| `/actuator/configprops` | 所有 `@ConfigurationProperties` | 是 |

### 1.3 安全考虑

- 默认只暴露 `health` 和 `info`
- 生产环境应禁用 `env`、`heapdump`、`configprops`
- 通过 Spring Security 配置访问控制

## 2. 代码示例

### 2.1 引入依赖

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

### 2.2 配置暴露端点

```yaml
# application.yml
management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics, loggers
        exclude: env, heapdump, configprops  # 不暴露
  endpoint:
    health:
      show-details: when-authorized  # 健康详情仅授权可见
      probes:
        enabled: true
  info:
    git:
      mode: full  # 显示完整 Git 信息
    env:
      enabled: true
  metrics:
    tags:
      application: ${spring.application.name}
```

### 2.3 自定义健康检查

```java
@Component
public class MyServiceHealthIndicator implements HealthIndicator {
    @Override
    public Health health() {
        if (checkMyService()) {
            return Health.up().withDetail("version", "1.0").build();
        }
        return Health.down().withDetail("error", "服务不可用").build();
    }
}
```

### 2.4 访问端点

```bash
# 健康检查
curl http://localhost:8080/actuator/health

# 性能指标
curl http://localhost:8080/actuator/metrics/jvm.memory.used

# Prometheus 格式（需引入 micrometer-registry-prometheus）
curl http://localhost:8080/actuator/prometheus
```

## 3. 关键要点总结

- **Actuator = 应用健康检查 + 指标暴露**
- **核心端点**：`health`、`info`、`metrics`、`prometheus`
- **生产安全**：禁用 `env`、`heapdump`、`configprops` 等敏感端点
- **可视化方案**：Actuator → Prometheus → Grafana
- ruoyi-vue-pro 中 `applicationName` 用于 Banner、异常日志、Metrics 标签
- ruoyi-vue-pro 默认引入 `spring-boot-starter-actuator`，可零成本启用

---

**文档版本**：v1.0
**最后更新**：2026-07-13
