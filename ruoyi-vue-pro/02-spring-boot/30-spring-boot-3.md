# 26 Spring Boot 3.x 迁移要点

> 了解 Spring Boot 3.x 的核心变化，掌握从 2.x 迁移到 3.x 的关键点（Jakarta EE 9+、GraalVM、Spring Security 6）。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Spring Boot 3.x 的核心变化
- 掌握从 `javax.*` 到 `jakarta.*` 的迁移
- 了解 GraalVM Native Image 基础
- 能在 ruoyi-vue-pro 中识别 Spring Boot 3.x 的新特性

## 📚 前置知识

- 01-25 全部文档

## 1. 核心概念

### 1.1 Spring Boot 3.x 关键变化

| 变化 | 说明 |
|------|------|
| **Jakarta EE 9+** | `javax.*` → `jakarta.*`（包名空间迁移） |
| **Java 17+** | 最低 Java 版本 17 |
| **Spring Framework 6** | 大量 API 升级 |
| **Spring Security 6** | 配置文件大改（lambda DSL；Security 见 [20-spring-security](../03-spring-boot-starters/24-spring-security.md)） |
| **GraalVM Native** | 原生镜像支持（启动快、内存小） |
| **Observability** | Micrometer + OpenTelemetry 替代 Spring Cloud Sleuth |
| **Logback 1.4** | 日志格式调整 |

### 1.2 `javax.*` → `jakarta.*` 迁移

```java
// ❌ Spring Boot 2.x / Java EE 8
import javax.servlet.http.HttpServletRequest;
import javax.persistence.Entity;
import javax.validation.constraints.NotBlank;

// ✅ Spring Boot 3.x / Jakarta EE 9+
import jakarta.servlet.http.HttpServletRequest;
import jakarta.persistence.Entity;
import jakarta.validation.constraints.NotBlank;
```

**原因**：Oracle 将 Java EE 捐赠给 Eclipse 基金会，更名 Jakarta EE，包名空间需要从 `javax` 改为 `jakarta`。

### 1.3 GraalVM Native Image

- **传统 JVM**：启动慢（~3-10 秒），内存大（~200-500 MB）
- **Native Image**：启动快（~0.1 秒），内存小（~50-100 MB）
- **原理**：AOT（Ahead-of-Time）编译，运行时无 JVM
- **代价**：反射 / 动态代理受限，需配置 `reflect-config.json`

## 2. 代码示例

### 2.1 Jakarta 包名迁移

```java
// 文件：UserController.java
import jakarta.servlet.http.HttpServletRequest;     // 替代 javax.servlet
import jakarta.validation.Valid;                   // 替代 javax.validation
import jakarta.validation.constraints.NotBlank;    // 替代 javax.validation.constraints

@RestController
public class UserController {

    @PostMapping("/create")
    public CommonResult<Long> create(@Valid @RequestBody UserCreateReqVO req,
                                     HttpServletRequest request) {
        return CommonResult.success(userService.createUser(req));
    }
}
```

### 2.2 Spring Security 6 配置（Lambda DSL）

```java
// ❌ Spring Security 5.x（链式）
@Configuration
public class SecurityConfig extends WebSecurityConfigurerAdapter {
    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http.authorizeRequests()
            .antMatchers("/admin-api/**").authenticated()
            .and().csrf().disable();
    }
}

// ✅ Spring Security 6.x（Lambda DSL）
@Configuration
public class SecurityConfig {
    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        return http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/admin-api/**").authenticated())
            .csrf(csrf -> csrf.disable())
            .build();
    }
}
```

### 2.3 Spring Boot 3.x 日志格式

```properties
# application.yml
logging:
  pattern:
    # 默认格式：%clr(%d{${LOG_DATEFORMAT_PATTERN:-yyyy-MM-dd'T'HH:mm:ss.SSSXXX}}){faint} %clr(${LOG_LEVEL_PATTERN:-%5p}) ...
    # Spring Boot 3.x 默认包含 traceId 和 spanId（来自 Micrometer Observation）
```

## 3. 关键要点总结

- **Spring Boot 3.x = Jakarta EE 9+ + Java 17+ + Spring Framework 6**
- **最大变化**：`javax.*` → `jakarta.*`
- **Spring Security 6**：用 Lambda DSL 配置，废弃 `WebSecurityConfigurerAdapter`
- **`@AutoConfiguration`**：替代 `@Configuration`，专为自动配置设计
- **自动配置注册**：用 `META-INF/spring/...imports` 替代 `spring.factories`
- **GraalVM Native Image**：可选，启动快但有反射限制
- **ruoyi-vue-pro 已迁移到 Spring Boot 3.x**，使用 Jakarta EE 9+

---

**文档版本**：v1.0
**最后更新**：2026-07-13
