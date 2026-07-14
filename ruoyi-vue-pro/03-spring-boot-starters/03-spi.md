# 1.3 SPI 机制：META-INF/spring.factories 与 AutoConfiguration.imports

> 理解 Spring SPI 与 JDK SPI 的差异，能识别 ruoyi 中所有 SPI 注册文件。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 SPI（Service Provider Interface）的设计思想
- 区分 JDK SPI 与 Spring SPI 的差异
- 掌握 Spring Boot 3.x 的 `AutoConfiguration.imports` 新机制
- 能在 ruoyi 项目中找到所有 SPI 入口

## 📚 前置知识

- Java 类加载机制（ClassLoader）
- Spring Boot 启动流程
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

## 3. ruoyi 仓库源码解读

### 3.1 mybatis starter 的 imports 文件

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`
**内容**：

```
cn.iocoder.yudao.framework.datasource.config.YudaoDataSourceAutoConfiguration
cn.iocoder.yudao.framework.mybatis.config.YudaoMybatisAutoConfiguration
cn.iocoder.yudao.framework.mybatis.config.IdTypeEnvironmentPostProcessor
cn.iocoder.yudao.framework.translate.config.YudaoTranslateAutoConfiguration
```

**解读**：
- Spring Boot 3.x 启动时扫描该文件
- 按顺序加载 4 个 AutoConfiguration
- `IdTypeEnvironmentPostProcessor` 实现了 `EnvironmentPostProcessor`（另一种扩展点）

### 3.2 tenant starter 的 imports 文件

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`

**内容**：

```
cn.iocoder.yudao.framework.tenant.config.YudaoTenantAutoConfiguration
```

**解读**：
- 单一 AutoConfiguration 入口
- ruoyi 大量使用**嵌套 `@Configuration` 类**组织内部 Bean（见 `YudaoTenantAutoConfiguration` 内的 `TenantRedisMQConfiguration` 等）

### 3.3 SpringFactoriesLoader 的其他用途

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-monitor/src/main/resources/META-INF/spring.factories`

虽然 Spring Boot 3.x 移除了 AutoConfiguration 在 `spring.factories` 的注册，但 `spring.factories` 仍可用于注册其他 SPI，例如 `org.springframework.context.ApplicationListener`、`org.springframework.boot.env.EnvironmentPostProcessor` 等。

## 4. 关键要点总结

- **SPI = 面向接口编程 + 配置文件注册**
- **Spring Boot 3.x**：AutoConfiguration 用 `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`
- **Spring Boot 2.x**：AutoConfiguration 用 `META-INF/spring.factories` 的 `EnableAutoConfiguration` 键
- **`spring.factories` 在 3.x 仍可使用**，用于其他扩展点（Listener、PostProcessor）
- **ruoyi 的 starter 全部用 3.x 新机制**

## 5. 练习题

### 练习 1：基础（必做）

在 `yudao-framework/` 下用 `find` 命令找出所有 `AutoConfiguration.imports` 文件，列出每个 starter 的自动配置类。

### 练习 2：进阶

写一段代码，遍历 yudao-server 的 classpath，读取所有 `META-INF/spring.factories` 的内容。

### 练习 3：挑战（选做）

尝试用 JDK SPI 实现一个"多支付渠道"系统：定义 `PaymentProvider` 接口，提供 `AlipayProvider`、`WechatProvider` 实现，通过 `ServiceLoader` 加载。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`
- Spring 源码：`org.springframework.core.io.support.SpringFactoriesLoader`
- Spring Boot 源码：`org.springframework.boot.autoconfigure.AutoConfigurationImportSelector`
- JDK SPI 文档：https://docs.oracle.com/javase/tutorial/sound/SPI-intro.html

---

**文档版本**：v1.0
**最后更新**：2026-07-13
