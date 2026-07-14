# 11 Actuator 监控端点

> 掌握 Spring Boot Actuator 的使用，能在 ruoyi-vue-pro 中通过 `/actuator/*` 端点监控应用健康状态、性能指标。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Actuator 的作用：暴露应用内部状态给监控系统
- 掌握常用端点：`/actuator/health`、`/actuator/info`、`/actuator/metrics`
- 能在 ruoyi-vue-pro 中启用和配置 Actuator
- 能与 Prometheus + Grafana 集成实现可视化监控

## 📚 前置知识

- 08-auto-config.md（自动配置）
- 10-config.md（配置文件）

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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 Banner 启动后输出（间接使用 ApplicationRunner）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/banner/core/BannerApplicationRunner.java`
**核心代码**（行 22-35）：

```java
@Slf4j
@Order(0)  // 越小越靠前
public class BannerApplicationRunner implements ApplicationRunner {

    private final String applicationName;

    public BannerApplicationRunner(@Value("${spring.application.name}") String applicationName) {
        this.applicationName = applicationName;
    }

    @Override
    public void run(ApplicationArguments args) throws Exception {
        log.info("""
                
                ----------------------------------------------------------
                \t项目启动成功！
                \t项目名称：{}
                \t启动时间：{}
                ----------------------------------------------------------
                """,
                applicationName, LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
    }
}
```

**解读**：
- ruoyi-vue-pro 中 Banner 在项目启动时输出应用名，启动时间
- **Actuator 关联**：在生产环境运维人员可通过 `actuator/health` 快速判断应用是否就绪
- **设计意图**：Banner 让开发者 / 运维一眼看到应用名（多模块部署时区分服务）

### 3.2 Web 配置中注入 applicationName

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
**核心代码**（行 40-50）：

```java
@AutoConfiguration
@EnableConfigurationProperties(WebProperties.class)
public class YudaoWebAutoConfiguration {

    /**
     * 应用名
     */
    @Value("${spring.application.name}")
    private String applicationName;

    @Bean
    public WebMvcRegistrations webMvcRegistrations(WebProperties webProperties) {
```

**解读**：
- 第 8 行：`@Value("${spring.application.name}")` 注入应用名
- **Actuator 关联**：Spring Boot 的所有 Actuator 指标都会带上 `application` 标签，值为 `spring.application.name`
- ruoyi 在多个地方使用 `applicationName`（异常日志、API 日志、Metrics 标签）

### 3.3 集成 Nacos + Prometheus（生产环境）

ruoyi-vue-pro 通过 `spring-cloud-starter-alibaba-nacos-discovery` + `micrometer-registry-prometheus` 集成：
- Nacos：服务发现、配置中心
- Prometheus：指标采集
- Grafana：可视化监控面板

**典型 application.yml**：

```yaml
management:
  endpoints:
    web:
      exposure:
        include: '*'
  endpoint:
    health:
      show-details: always
  metrics:
    export:
      prometheus:
        enabled: true
```

## 4. 关键要点总结

- **Actuator = 应用健康检查 + 指标暴露**
- **核心端点**：`health`、`info`、`metrics`、`prometheus`
- **生产安全**：禁用 `env`、`heapdump`、`configprops` 等敏感端点
- **可视化方案**：Actuator → Prometheus → Grafana
- ruoyi-vue-pro 中 `applicationName` 用于 Banner、异常日志、Metrics 标签
- ruoyi-vue-pro 默认引入 `spring-boot-starter-actuator`，可零成本启用

## 5. 练习题

### 练习 1：基础（必做）

启动 ruoyi-vue-pro，访问 `/actuator/health`，查看应用健康状态；访问 `/actuator/info` 查看应用信息。

### 练习 2：进阶

在 `application.yml` 中暴露 `/actuator/env` 端点，访问后查找 `spring.datasource.url` 配置项，验证配置生效。

### 练习 3：挑战（选做）

自定义一个 `RedisHealthIndicator`，当 Redis 不可用时 `/actuator/health` 返回 `DOWN`，否则返回 `UP`（含 Redis 版本号等详情）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/banner/core/BannerApplicationRunner.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
- Spring Boot Actuator 官方文档：https://docs.spring.io/spring-boot/docs/current/reference/html/actuator.html
- 芋道监控：https://doc.iocoder.cn/spring-boot-actuator/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
