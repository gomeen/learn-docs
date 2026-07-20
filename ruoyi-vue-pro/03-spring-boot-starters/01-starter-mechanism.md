# 1.1 Spring Boot Starter 机制原理

> 理解 Spring Boot Starter 的设计思想，能看懂 ruoyi-vue-pro 全部 Starter 的目录结构。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Spring Boot Starter 的"约定优于配置"思想
- 掌握 Starter 的两个核心组件：`xxx-spring-boot-starter` 和 `xxx-spring-boot-autoconfigure`
- 能区分 Starter 与自动装配的区别
- 能看懂 ruoyi 全部 15+ 个 Starter 的目录命名规则

## 📚 前置知识

- Spring IoC 容器基本概念（详见 [01-ioc](../02-spring-boot/01-ioc.md)）
- Maven 多模块项目结构（详见 [11-maven-modules](../01-java-fundamentals/13-maven-modules.md)）
- Java 注解基础（详见 [04-annotation](../01-java-fundamentals/04-annotation.md)）
- 自动配置入门见 [08-auto-config](../02-spring-boot/09-auto-config.md) / [09-custom-starter](../02-spring-boot/10-custom-starter.md)

## 1. 核心概念

### 1.1 什么是 Starter？

**Starter** 是 Spring Boot 的一种**依赖封装模式**。本质上是一个 Maven 模块（jar 包），引入它就能获得一整套开箱即用的功能。

**核心思想**：把"功能实现 + 自动装配 + 默认配置 + 依赖管理"打包成一个 starter，业务方只需一行 Maven 依赖，就能使用整套能力。

### 1.2 Starter 的组成

一个标准的 Starter 通常包含两部分：

| 模块 | 作用 | 命名规范 |
|------|------|---------|
| Autoconfigure 模块 | 定义 AutoConfiguration 类、`META-INF/spring/...imports` | `xxx-spring-boot-autoconfigure` |
| Starter 模块 | 引入 autoconfigure + 其他依赖（传递依赖） | `xxx-spring-boot-starter` |

注意：**Spring 官方 Starter** 命名是 `spring-boot-starter-xxx`（如 `spring-boot-starter-web`），**第三方**则是 `xxx-spring-boot-starter`（如 `mybatis-spring-boot-starter`）。

### 1.3 ruoyi-vue-pro 的 Starter 命名

ruoyi 全部采用**第三方命名规范**：

```
yudao-framework/
├── yudao-spring-boot-starter-mybatis      # MyBatis 增强
├── yudao-spring-boot-starter-redis        # Redis 封装
├── yudao-spring-boot-starter-security     # Spring Security 整合
├── yudao-spring-boot-starter-mq           # 统一消息队列
├── yudao-spring-boot-starter-biz-data-permission  # 数据权限
├── yudao-spring-boot-starter-biz-tenant   # 多租户
├── yudao-spring-boot-starter-biz-ip       # IP 解析
├── yudao-spring-boot-starter-job          # 定时任务
├── yudao-spring-boot-starter-monitor      # 监控/链路追踪
├── yudao-spring-boot-starter-protection   # 限流/幂等/锁
├── yudao-spring-boot-starter-excel        # EasyExcel 增强
├── yudao-spring-boot-starter-websocket    # WebSocket 集群
├── yudao-spring-boot-starter-web          # Web 增强（CORS/加密）
└── yudao-spring-boot-starter-test         # 单测增强
```

`biz-` 前缀表示**业务相关**（需要 yudao 业务模块支持），其他是**通用能力**。

## 2. 代码示例

### 2.1 一个最小 Starter

**autoconfigure 模块**（`my-starter-spring-boot-autoconfigure`）：

```java
// 文件：com.example.mystarter.HelloService.java
package com.example.mystarter;

public class HelloService {
    private String prefix = "Hello";

    public String greet(String name) {
        return prefix + ", " + name + "!";
    }

    public void setPrefix(String prefix) {
        this.prefix = prefix;
    }
}

// 文件：com.example.mystarter.HelloServiceAutoConfiguration.java
package com.example.mystarter;

import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.context.annotation.Bean;

@AutoConfiguration  // Spring Boot 3.x 引入
public class HelloServiceAutoConfiguration {

    @Bean
    public HelloService helloService() {
        return new HelloService();
    }
}
```

**META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports**：

```
com.example.mystarter.HelloServiceAutoConfiguration
```

**starter 模块**（`my-starter-spring-boot-starter`）的 pom：

```xml
<dependencies>
    <dependency>
        <groupId>com.example</groupId>
        <artifactId>my-starter-spring-boot-autoconfigure</artifactId>
    </dependency>
</dependencies>
```

**业务方使用**：

```java
@RestController
public class DemoController {
    @Resource
    private HelloService helloService;

    @GetMapping("/hello")
    public String hello() {
        return helloService.greet("ruoyi");  // "Hello, ruoyi!"
    }
}
```

### 2.2 常见错误：Starter 缺少 imports 文件

```xml
<!-- ❌ 错误：starter 中没有引入 autoconfigure -->
<dependencies>
    <dependency>
        <groupId>com.example</groupId>
        <artifactId>my-starter-spring-boot-autoconfigure</artifactId>
    </dependency>
    <!-- 缺少 spring-boot-starter（autoconfigure 通常需要） -->
</dependencies>
```

```xml
<!-- ✅ 正确：autoconfigure 模块声明 spring-boot-starter 依赖 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter</artifactId>
</dependency>
```

## 3. 关键要点总结

- **Starter = autoconfigure + 传递依赖**：用户引入 starter，自动获得全部能力
- **命名规则**：第三方 `xxx-spring-boot-starter`，官方 `spring-boot-starter-xxx`
- **Spring Boot 3.x 注册方式**：用 `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`（替代旧版 `spring.factories`）
- **ruoyi 的 15+ Starter** 覆盖了企业开发的所有通用能力：DB、缓存、消息、权限、租户、限流、定时任务等
- **`@AutoConfiguration`** 是新注解，语义与 `@Configuration` 相似，但**仅用于自动装配**场景

---

**文档版本**：v1.0
**最后更新**：2026-07-13
