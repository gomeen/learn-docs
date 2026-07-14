# 08 自动配置原理：@SpringBootApplication

> 深入理解 Spring Boot 自动配置（Auto-Configuration）原理，能读懂 ruoyi-vue-pro 中 `YudaoXxxAutoConfiguration` 的设计模式。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `@SpringBootApplication` 的三个核心注解：`@Configuration` + `@EnableAutoConfiguration` + `@ComponentScan`
- 掌握 `spring.factories`（Spring Boot 2.x）和 `AutoConfiguration.imports`（3.x）的机制
- 能在 ruoyi-vue-pro 中读懂 `YudaoXxxAutoConfiguration` 的 `@Conditional` 注解
- 能自定义一个 Starter

## 📚 前置知识

- 01-ioc.md
- 07-startup.md

## 1. 核心概念

### 1.1 `@SpringBootApplication` 拆解

```java
@Target(ElementType.TYPE)
@Retention(RetentionPolicy.RUNTIME)
@Documented
@Inherited
@SpringBootConfiguration      // 实质是 @Configuration
@EnableAutoConfiguration     // 启用自动配置（核心！）
@ComponentScan(excludeFilters = ...)  // 扫描 Bean
public @interface SpringBootApplication { ... }
```

### 1.2 自动配置原理

1. `@EnableAutoConfiguration` 导入 `AutoConfigurationImportSelector`
2. 扫描所有 jar 包的 `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`
3. 根据 `@Conditional` 注解决定是否启用某个自动配置类
4. 启用后，自动配置类中的 `@Bean` 方法被调用，注册到 Spring 容器

### 1.3 常见 `@Conditional` 注解

| 注解 | 说明 |
|------|------|
| `@ConditionalOnClass` | 类路径存在某个类 |
| `@ConditionalOnMissingClass` | 类路径不存在某个类 |
| `@ConditionalOnBean` | 容器中存在某个 Bean |
| `@ConditionalOnMissingBean` | 容器中不存在某个 Bean（用户可覆盖） |
| `@ConditionalOnProperty` | 配置项符合条件 |
| `@ConditionalOnResource` | 资源文件存在 |
| `@ConditionalOnWebApplication` | Web 应用 |
| `@ConditionalOnExpression` | SpEL 表达式为 true |

## 2. 代码示例

### 2.1 自定义自动配置类

```java
// 文件：MyAutoConfiguration.java
@AutoConfiguration  // Spring Boot 2.7+ / 3.x 推荐用 @AutoConfiguration
@ConditionalOnClass(MyService.class)
@EnableConfigurationProperties(MyProperties.class)
public class MyAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public MyService myService(MyProperties properties) {
        return new MyService(properties);
    }
}
```

### 2.2 注册自动配置（Spring Boot 3.x）

```text
# 文件：META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports
cn.iocoder.yudao.framework.web.config.YudaoWebAutoConfiguration
```

### 2.3 注册自动配置（Spring Boot 2.x）

```properties
# 文件：META-INF/spring.factories
org.springframework.boot.autoconfigure.EnableAutoConfiguration=\
cn.iocoder.yudao.framework.web.config.YudaoWebAutoConfiguration
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 YudaoWebAutoConfiguration 自动配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
**核心代码**（行 1-40）：

```java
package cn.iocoder.yudao.framework.web.config;

import cn.hutool.core.util.StrUtil;
import cn.iocoder.yudao.framework.common.biz.infra.logger.ApiErrorLogCommonApi;
import cn.iocoder.yudao.framework.common.enums.WebFilterOrderEnum;
import cn.iocoder.yudao.framework.web.core.filter.CacheRequestBodyFilter;
import cn.iocoder.yudao.framework.web.core.filter.DemoFilter;
import cn.iocoder.yudao.framework.web.core.handler.GlobalExceptionHandler;
import cn.iocoder.yudao.framework.web.core.handler.GlobalResponseBodyHandler;
import cn.iocoder.yudao.framework.web.core.util.WebFrameworkUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.core.annotation.Order;
import org.springframework.web.bind.annotation.RestController;

@AutoConfiguration
@EnableConfigurationProperties(WebProperties.class)
public class YudaoWebAutoConfiguration {
```

**解读**：
- 第 19 行：`@AutoConfiguration`（Spring Boot 2.7+ / 3.x）替代 `@Configuration`，专用于自动配置类
- 第 20 行：`@EnableConfigurationProperties` 启用 `WebProperties` 配置类
- **设计意图**：把 Web 相关 Bean（过滤器、拦截器、异常处理器）的注册逻辑集中在一个类，符合"职责单一"原则
- **注册位置**：`META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`

### 3.2 GlobalExceptionHandler 的条件注册

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
**核心代码**（行 83-92）：

```java
@Bean
@SuppressWarnings("SpringJavaInjectionPointsAutowiringInspection")
public GlobalExceptionHandler globalExceptionHandler(ApiErrorLogCommonApi apiErrorLogApi) {
    return new GlobalExceptionHandler(applicationName, apiErrorLogApi);
}

@Bean
public GlobalResponseBodyHandler globalResponseBodyHandler() {
    return new GlobalResponseBodyHandler();
}
```

**解读**：
- 第 3-5 行：`globalExceptionHandler` Bean 在自动配置中显式构造
- **关键设计**：使用 `new GlobalExceptionHandler(applicationName, apiErrorLogApi)` 手动构造，而不是让 Spring 扫描 `@Component` 自动注册
- **为什么？** 避免 `@Component` 自动注册和 `@Bean` 手动注册冲突，确保 `applicationName` 来自 `YudaoWebAutoConfiguration` 的 `@Value` 注入
- **Spring Boot 哲学**：约定优于配置，框架帮你做"合理默认"，用户可覆盖

### 3.3 完整自动配置注册（YudaoCacheAutoConfiguration）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
**核心代码**（行 1-30）：

```java
package cn.iocoder.yudao.framework.redis.config;

import cn.hutool.core.util.StrUtil;
import cn.iocoder.yudao.framework.redis.core.TimeoutRedisCacheManager;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.cache.CacheProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;

/**
 * Cache 配置类，基于 Redis 实现
 */
@AutoConfiguration
@EnableConfigurationProperties({CacheProperties.class, YudaoCacheProperties.class})
@EnableCaching
public class YudaoCacheAutoConfiguration {
```

**解读**：
- 第 17 行：`@AutoConfiguration` 注册到 Spring Boot 自动配置 SPI
- 第 18 行：启用 Spring Boot 内置的 `CacheProperties` 和 ruoyi 自定义的 `YudaoCacheProperties`
- 第 19 行：`@EnableCaching` 开启 Spring Cache 注解支持（`@Cacheable` 等）
- **设计模式**：一个 Starter 一个 `AutoConfiguration` + 一个 `Properties`，是 ruoyi-vue-pro 的标准结构

## 4. 关键要点总结

- **自动配置核心**：`@EnableAutoConfiguration` + `AutoConfiguration.imports` + `@Conditional`
- **3.x 改用 `AutoConfiguration.imports`** 替代 `spring.factories`（更快、更安全）
- **ruoyi 命名规范**：`YudaoXxxAutoConfiguration` + `XxxProperties`
- **`@ConditionalOnMissingBean`** 让用户可以覆盖框架默认 Bean
- **`@AutoConfiguration`** 是 `@Configuration` 的"自动配置特化版"
- ruoyi-vue-pro 的每个 Starter 都遵循"一个 AutoConfiguration + 一个 Properties"的结构

## 5. 练习题

### 练习 1：基础（必做）

在 ruoyi-vue-pro 的 `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` 中查看所有自动配置类，列出前 5 个。

### 练习 2：进阶

阅读 `YudaoWebAutoConfiguration`，解释 `WebProperties` 的作用，以及 `@EnableConfigurationProperties` 和 `@ConfigurationProperties` 的关系。

### 练习 3：挑战（选做）

仿照 ruoyi 的 `yudao-spring-boot-starter-web`，自定义一个 `yudao-spring-boot-starter-email`，实现：自动配置 JavaMailSender，支持 `yudao.email.host`、`yudao.email.port` 等配置项。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
- Spring Boot 自动配置：https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.developing-auto-configuration
- 芋道 Spring Boot Starter：https://doc.iocoder.cn/spring-boot-starter/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
