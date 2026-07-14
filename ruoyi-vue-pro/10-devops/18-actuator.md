# 5.1 Spring Boot Actuator

> 理解 Spring Boot Actuator 提供的监控端点，掌握 ruoyi 的 Actuator 配置与实践。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Actuator 的核心端点（health / info / metrics / prometheus）
- 掌握 Actuator 的配置与安全控制
- 能在 ruoyi 中使用 `/actuator/health` 做健康检查
- 知道如何暴露自定义健康指标

## 📚 前置知识

- Spring Boot 基础
- REST 概念

## 1. 核心概念

### 1.1 什么是 Actuator？

Spring Boot Actuator 是 Spring Boot 自带的**生产级监控**模块，提供一系列 HTTP 端点：

| 端点 | 作用 | 敏感度 |
|------|------|-------|
| `/actuator/health` | 健康检查 | 低 |
| `/actuator/info` | 应用信息 | 低 |
| `/actuator/metrics` | 指标（JVM、HTTP、数据库连接池） | 中 |
| `/actuator/env` | 环境变量 | **高**（含密码） |
| `/actuator/loggers` | 日志级别动态调整 | 中 |
| `/actuator/threaddump` | 线程快照 | 中 |
| `/actuator/prometheus` | Prometheus 格式指标 | 中 |

### 1.2 默认端点 vs 自定义暴露

Spring Boot 默认**只暴露 health 和 info**，其他端点需要显式开启。

### 1.3 健康检查的状态

```json
{
  "status": "UP",
  "components": {
    "db": { "status": "UP" },
    "diskSpace": { "status": "UP" },
    "redis": { "status": "UP" }
  }
}
```

状态值：`UP` / `DOWN` / `OUT_OF_SERVICE` / `UNKNOWN`

## 2. 代码示例

### 2.1 引入依赖

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

### 2.2 暴露所有端点

```yaml
# application.yaml
management:
  endpoints:
    web:
      base-path: /actuator
      exposure:
        include: '*'   # 暴露所有端点（生产环境应过滤）
```

### 2.3 访问常用端点

```bash
# 健康检查
curl http://localhost:48080/actuator/health

# 查看 JVM 堆内存
curl http://localhost:48080/actuator/metrics/jvm.memory.used

# 列出所有指标
curl http://localhost:48080/actuator/metrics

# 查看环境变量（含数据库密码！）
curl http://localhost:48080/actuator/env
```

### 2.4 自定义健康指标

```java
@Component
public class MyServiceHealthIndicator implements HealthIndicator {
    @Override
    public Health health() {
        // 检查依赖
        boolean ok = checkMyService();
        if (ok) {
            return Health.up().withDetail("version", "1.0").build();
        } else {
            return Health.down().withDetail("error", "连接失败").build();
        }
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的 Actuator 配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
**核心代码**（行 146-154）：

```yaml
# Actuator 监控端点的配置项
management:
  endpoints:
    web:
      base-path: /actuator # Actuator 提供的 API 接口的根目录。默认为 /actuator
      exposure:
        include: '*' # 需要开放的端点。默认值只打开 health 和 info 两个端点。通过设置 * ，可以开放所有端点。
```

**解读**：
- 第 147 行：根路径 `/actuator`
- 第 150-151 行：`include: '*'` — 暴露所有端点（**开发环境**配置）
- **生产环境警告**：`/actuator/env` 会泄露数据库密码，必须配合 Spring Security 鉴权或限制 IP 访问

### 3.2 deploy.sh 的健康检查

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
**核心代码**（行 12-14）：

```bash
# 环境
PROFILES_ACTIVE=development
# 健康检查 URL
HEALTH_CHECK_URL=http://127.0.0.1:48080/actuator/health/
```

**解读**：
- 第 5 行：`HEALTH_CHECK_URL` 指向 `/actuator/health/`
- ruoyi 的部署脚本用 Actuator 的 health 端点判断服务是否启动完成

### 3.3 docker-compose 的健康检查

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/script/docker/docker-compose.yml`（建议补充）

**注**：当前 docker-compose.yml **没有**配置 healthcheck。推荐补充：

```yaml
  server:
    image: yudao-server
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:48080/actuator/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 60s
```

**说明**：
- `interval: 10s` — 每 10 秒检查一次
- `retries: 5` — 5 次失败判定为 unhealthy
- `start_period: 60s` — 启动后等 60 秒再开始检查（Spring Boot 启动需要时间）

### 3.4 XSS 配置排除 actuator

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application.yaml`
**核心代码**（行 267-271）：

```yaml
  xss:
    enable: false
    exclude-urls: # 如下两个 url，仅仅是为了演示，去掉配置也没关系
      - ${spring.boot.admin.context-path}/** # 不处理 Spring Boot Admin 的请求
      - ${management.endpoints.web.base-path}/** # 不处理 Actuator 的请求
```

**解读**：
- 第 1 行：`xss.enable: false` — 默认关闭 XSS 防护
- 第 3 行：即使开启 XSS，过滤器会跳过 `/admin/**` 和 `/actuator/**` 路径
- 避免 Actuator 返回的 JSON 被 XSS 过滤器改写

## 4. 关键要点总结

- Actuator 是 Spring Boot 内置的监控模块，通过 HTTP 端点暴露应用状态
- 默认只暴露 `health` 和 `info`，需要 `include: '*'` 开放更多
- `/actuator/health` 是健康检查标准端点
- `/actuator/env` **危险** — 会泄露密码，生产环境必须鉴权
- ruoyi 用 `/actuator/health` 做部署后的健康检查
- 推荐在 docker-compose 中配置 `healthcheck` 实现真正的服务就绪

## 5. 练习题

### 练习 1：基础（必做）

启动 yudao-server，访问 `http://localhost:48080/actuator/health`，查看 `status` 和 `components` 字段。访问 `http://localhost:48080/actuator/env` 观察所有环境变量。

### 练习 2：进阶

为 yudao-server 添加一个自定义 HealthIndicator（如"检查 Redis 连接"），故意让 Redis 不可用，观察 `/actuator/health` 的 status 变为 `DOWN`。

### 练习 3：挑战（选做）

为 yudao-server 配置 Spring Security，给 `/actuator/**` 加 Basic 鉴权（`admin / admin`），验证无凭证时返回 401。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/script/shell/deploy.sh`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application.yaml`
- [Spring Boot Actuator 官方文档](https://docs.spring.io/spring-boot/docs/2.7.x/reference/html/actuator.html)

---

**文档版本**：v1.0
**最后更新**：2026-07-13
