# 09 自定义 Starter

> 掌握 Spring Boot Starter 的开发流程，能仿照 ruoyi-vue-pro 编写自己的 Starter。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Starter 的本质：一组"开箱即用"的依赖 + 自动配置
- 掌握 Starter 的标准结构：xxx-spring-boot-autoconfigure + xxx-spring-boot-starter
- 能在 ruoyi-vue-pro 中读懂 `yudao-spring-boot-starter-*` 模块
- 能自定义一个完整 Starter

## 📚 前置知识

- [09-auto-config.md](./09-auto-config.md)
- Maven 多模块项目（详见 [11-maven-modules](../01-java-fundamentals/13-maven-modules.md)）

## 1. 核心概念

### 1.1 什么是 Starter？

Starter 是 Spring Boot 的"约定优于配置"理念的集大成者：
- **用户**：在 `pom.xml` 加一行依赖，就能用某个功能
- **框架**：通过自动配置 + 条件注解决定启用哪些 Bean

**官方 Starter 命名**：`spring-boot-starter-{name}`（如 `spring-boot-starter-data-jpa`）
**第三方 Starter 命名**：`{name}-spring-boot-starter`（如 `mybatis-spring-boot-starter`）

ruoyi-vue-pro 的 Starter 命名：`yudao-spring-boot-starter-{name}`（如 `yudao-spring-boot-starter-web`）

### 1.2 Starter 的标准结构

```
my-starter/
├── my-spring-boot-autoconfigure/         # 自动配置模块
│   └── src/main/java/
│       ├── cn.iocoder.yudao.my.autoconfig/
│       │   ├── MyAutoConfiguration.java
│       │   └── MyProperties.java
│       └── META-INF/spring/
│           └── org.springframework.boot.autoconfigure.AutoConfiguration.imports
└── my-spring-boot-starter/               # 启动器模块（仅 pom.xml）
    └── pom.xml   (依赖 autoconfigure + 实际实现库)
```

### 1.3 命名规范

- `my-spring-boot-starter`：用户引入的依赖（只有 pom.xml）
- `my-spring-boot-autoconfigure`：自动配置代码（不要让用户直接引入）

## 2. 代码示例

### 2.1 创建 Properties 配置类

```java
// 文件：MyProperties.java
@Data
@ConfigurationProperties(prefix = "yudao.my")
public class MyProperties {
    /** 是否启用 */
    private boolean enabled = true;
    /** API Key */
    private String apiKey;
    /** 超时时间（毫秒） */
    private Duration timeout = Duration.ofSeconds(3);
}
```

### 2.2 创建自动配置类

```java
// 文件：MyAutoConfiguration.java
@AutoConfiguration
@ConditionalOnClass(MyService.class)
@EnableConfigurationProperties(MyProperties.class)
public class MyAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    @ConditionalOnProperty(prefix = "yudao.my", value = "enabled", havingValue = "true", matchIfMissing = true)
    public MyService myService(MyProperties properties) {
        return new MyService(properties);
    }
}
```

### 2.3 注册自动配置

```text
# 文件：META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports
cn.iocoder.yudao.framework.my.config.MyAutoConfiguration
```

### 2.4 Starter 的 pom.xml

```xml
<!-- 文件：my-spring-boot-starter/pom.xml -->
<project>
    <dependencies>
        <dependency>
            <groupId>cn.iocoder.yudao</groupId>
            <artifactId>my-spring-boot-autoconfigure</artifactId>
        </dependency>
        <dependency>
            <groupId>com.example</groupId>
            <artifactId>my-core</artifactId>  <!-- 实际功能库 -->
        </dependency>
    </dependencies>
</project>
```

## 3. 关键要点总结

- **Starter = pom 依赖 + 自动配置 + 配置属性**
- **标准结构**：autoconfigure 模块（代码） + starter 模块（仅 pom）
- **命名规范**：`{name}-spring-boot-autoconfigure` + `{name}-spring-boot-starter`
- **注册方式**：`META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`
- **核心注解**：`@AutoConfiguration` + `@EnableConfigurationProperties` + `@ConditionalOnMissingBean`
- ruoyi-vue-pro 的 starter 模式：`yudao-spring-boot-starter-{name}` 包含多个相关功能模块
- **设计原则**：通过 Starter 复用通用功能，业务模块只关注业务

---

**文档版本**：v1.0
**最后更新**：2026-07-13
