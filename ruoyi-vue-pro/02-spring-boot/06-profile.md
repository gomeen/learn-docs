# 06 Spring Profile 多环境配置

> 掌握 Spring Profile 的使用，能在 ruoyi-vue-pro 中正确切换 dev / test / prod 环境。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Profile 的作用：同一套代码在不同环境使用不同配置
- 掌握 `@Profile`、`spring.profiles.active`、多配置文件（`application-{profile}.yml`）的使用
- 能在 ruoyi-vue-pro 中根据环境启用/禁用 Bean（如 DemoFilter）
- 了解 Nacos 配置中心如何与 Profile 结合

## 📚 前置知识

- Spring 基础配置（application.yml 详见 [10-config](./11-config.md)）
- Maven 多模块项目（详见 [11-maven-modules](../01-java-fundamentals/13-maven-modules.md)）

## 1. 核心概念

### 1.1 什么是 Profile？

Profile 是 Spring 提供的**环境隔离机制**，让你能：
- `application-dev.yml`：开发环境（本地数据库、调试日志）
- `application-test.yml`：测试环境（测试数据库）
- `application-prod.yml`：生产环境（生产数据库、关闭调试）

激活方式：
1. `application.yml` 中：`spring.profiles.active: dev`
2. 启动参数：`--spring.profiles.active=prod`
3. 环境变量：`SPRING_PROFILES_ACTIVE=prod`
4. JVM 系统属性：`-Dspring.profiles.active=prod`

### 1.2 Profile 与 Bean 条件注册

```java
@Component
@Profile("dev")  // 只在 dev 环境注册
public class DevDataInitializer { ... }

@Component
@Profile("!prod")  // 非生产环境注册
public class DebugFilter { ... }
```

### 1.3 配置文件拆分

```yaml
# application.yml —— 公共配置
spring:
  application:
    name: yudao-server
  profiles:
    active: dev  # 默认激活 dev

---
# application-dev.yml —— 开发环境
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/yudao_dev

---
# application-prod.yml —— 生产环境
spring:
  datasource:
    url: jdbc:mysql://prod-db:3306/yudao_prod
```

## 2. 代码示例

### 2.1 启动类激活 Profile

```java
// 文件：YudaoServerApplication.java
@SpringBootApplication
public class YudaoServerApplication {
    public static void main(String[] args) {
        // 方式 1：环境变量激活
        SpringApplication.run(YudaoServerApplication.class, args);

        // 方式 2：代码硬编码（不推荐）
        // System.setProperty("spring.profiles.active", "dev");
    }
}
```

### 2.2 条件注册 DemoFilter

```java
// 文件：YudaoWebAutoConfiguration.java
@Bean
@ConditionalOnProperty(value = "yudao.demo", havingValue = "true")
public FilterRegistrationBean<DemoFilter> demoFilter() {
    return createFilterBean(new DemoFilter(), WebFilterOrderEnum.DEMO_FILTER);
}
```

**说明**：
- `@ConditionalOnProperty` 比 `@Profile` 更细粒度（基于配置项值）
- `yudao.demo=true` 在 dev 环境配置，prod 不配置则不启用演示模式

## 3. 关键要点总结

- **Profile = 环境隔离**，dev / test / prod 各自一套配置
- **3 种激活方式**：配置文件、启动参数、环境变量
- **细粒度控制用 `@ConditionalOnProperty`**（按配置项值判断）
- **粗粒度控制用 `@Profile`**（按环境名判断）
- ruoyi-vue-pro 用 `application-{profile}.yml` 分离环境配置
- ruoyi 的 `DemoFilter` 是 `@ConditionalOnProperty` 的典型应用

---

**文档版本**：v1.0
**最后更新**：2026-07-13
