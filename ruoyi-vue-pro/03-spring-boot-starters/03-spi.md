# 1.3 SPI 机制：META-INF/spring.factories 与 AutoConfiguration.imports

> 理解 Spring SPI 与 JDK SPI 的差异，能识别 ruoyi 中所有 SPI 注册文件。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 SPI（Service Provider Interface）的设计思想
- 区分 JDK SPI 与 Spring SPI 的差异
- 掌握 Spring Boot 3.x 的 `AutoConfiguration.imports` 新机制
- 能在 ruoyi 项目中找到所有 SPI 入口

## 📚 前置知识

- Java 类加载机制（ClassLoader，详见 [20-classloader](../01-java-fundamentals/24-classloader.md)）
- Spring Boot 启动流程（详见 [07-startup](../02-spring-boot/08-startup.md)）
- [01-starter-mechanism.md](./01-starter-mechanism.md)

## 1. 核心概念

### 1.1 什么是 SPI？

**SPI（Service Provider Interface）** 是一种**服务发现机制**：第三方实现接口，框架通过 classpath 扫描自动加载。

经典应用：
- JDBC Driver 加载（`META-INF/services/java.sql.Driver`）
- Spring 自动装配（`META-INF/spring/...`）
- SLF4J 日志门面加载

### 1.2 JDK SPI vs Spring SPI

| 维度 | JDK SPI | Spring SPI |
|------|---------|------------|
| 注册位置 | `META-INF/services/xxx` | `META-INF/spring/...` |
| 加载方式 | `ServiceLoader.load()` | `SpringFactoriesLoader` / `AutoConfiguration.imports` |
| 文件格式 | 文件名 = 接口全限定名 | `spring.factories` 是 properties，`imports` 是行分隔 |
| 触发时机 | 调用 `load()` 时 | Spring Boot 启动时 |
| 典型应用 | JDBC Driver | Spring Boot AutoConfiguration |

### 1.3 Spring Boot 2.x vs 3.x

| 版本 | AutoConfiguration 注册位置 |
|------|--------------------------|
| 2.x | `META-INF/spring.factories`（`EnableAutoConfiguration=xxx`） |
| 3.x | `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` |

ruoyi-vue-pro 当前使用的是 **3.x** 机制（Spring Boot 3 + JDK 17）。

## 2. 代码示例

### 2.1 JDK SPI 示例

**接口**：

```java
// 文件：com.example.spi.DataSourceProvider.java
package com.example.spi;

public interface DataSourceProvider {
    String name();
    Object create();
}
```

**实现**：

```java
// 文件：com.example.spi.HikariProvider.java
package com.example.spi.impl;

public class HikariProvider implements DataSourceProvider {
    public String name() { return "hikari"; }
    public Object create() { return new HikariDataSource(); }
}
```

**注册文件** `META-INF/services/com.example.spi.DataSourceProvider`：

```
com.example.spi.impl.HikariProvider
```

**加载**：

```java
ServiceLoader<DataSourceProvider> loader = ServiceLoader.load(DataSourceProvider.class);
for (DataSourceProvider provider : loader) {
    System.out.println(provider.name());
}
```

### 2.2 Spring Boot 3.x AutoConfiguration.imports

**文件** `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`：

```
# 注释以 # 开头
com.example.starter.HelloServiceAutoConfiguration
com.example.starter.DataSourceAutoConfiguration
```

每行一个全限定类名，Spring Boot 启动时自动加载。

### 2.3 常见错误

```java
// ❌ 错误：使用 @Configuration 替代 @AutoConfiguration
@Configuration
public class MyAutoConfiguration { }
```

```java
// ✅ 正确：使用专用注解
@AutoConfiguration
public class MyAutoConfiguration { }
```

## 3. 关键要点总结

- **SPI = 面向接口编程 + 配置文件注册**
- **Spring Boot 3.x**：AutoConfiguration 用 `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`
- **Spring Boot 2.x**：AutoConfiguration 用 `META-INF/spring.factories` 的 `EnableAutoConfiguration` 键
- **`spring.factories` 在 3.x 仍可使用**，用于其他扩展点（Listener、PostProcessor）
- **ruoyi 的 starter 全部用 3.x 新机制**

---

**文档版本**：v1.0
**最后更新**：2026-07-13
