# 08 自动配置原理：@SpringBootApplication

> 深入理解 Spring Boot 自动配置（Auto-Configuration）原理，能读懂 ruoyi-vue-pro 中 `YudaoXxxAutoConfiguration` 的设计模式。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `@SpringBootApplication` 的三个核心注解：`@Configuration` + `@EnableAutoConfiguration` + `@ComponentScan`
- 掌握 `spring.factories`（Spring Boot 2.x）和 `AutoConfiguration.imports`（3.x）的机制
- 能在 ruoyi-vue-pro 中读懂 `YudaoXxxAutoConfiguration` 的 `@Conditional` 注解
- 能自定义一个 Starter

## 📚 前置知识

- [01-ioc.md](./01-ioc.md)
- [08-startup.md](./08-startup.md)

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
3. 根据 `@Conditional` 注解决定是否启用某个自动配置类（条件装配深水区见 [04-conditional](../03-spring-boot-starters/04-conditional.md)）
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

## 3. 关键要点总结

- **自动配置核心**：`@EnableAutoConfiguration` + `AutoConfiguration.imports` + `@Conditional`
- **3.x 改用 `AutoConfiguration.imports`** 替代 `spring.factories`（更快、更安全）
- **ruoyi 命名规范**：`YudaoXxxAutoConfiguration` + `XxxProperties`
- **`@ConditionalOnMissingBean`** 让用户可以覆盖框架默认 Bean
- **`@AutoConfiguration`** 是 `@Configuration` 的"自动配置特化版"
- ruoyi-vue-pro 的每个 Starter 都遵循"一个 AutoConfiguration + 一个 Properties"的结构

---

**文档版本**：v1.0
**最后更新**：2026-07-13
