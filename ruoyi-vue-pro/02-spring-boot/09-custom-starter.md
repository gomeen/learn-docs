# 09 自定义 Starter

> 掌握 Spring Boot Starter 的开发流程，能仿照 ruoyi-vue-pro 编写自己的 Starter。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 Starter 的本质：一组"开箱即用"的依赖 + 自动配置
- 掌握 Starter 的标准结构：xxx-spring-boot-autoconfigure + xxx-spring-boot-starter
- 能在 ruoyi-vue-pro 中读懂 `yudao-spring-boot-starter-*` 模块
- 能自定义一个完整 Starter

## 📚 前置知识

- [08-auto-config.md](./08-auto-config.md)
- Maven 多模块项目（详见 [11-maven-modules](../01-java-fundamentals/11-maven-modules.md)）

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

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 yudao-spring-boot-starter-web 模块结构

ruoyi-vue-pro 的 web starter 位于 `yudao-framework/yudao-spring-boot-starter-web/`，包含：

```
yudao-spring-boot-starter-web/
├── pom.xml
└── src/main/
    ├── java/cn/iocoder/yudao/framework/
    │   ├── web/         # Web 配置（YudaoWebAutoConfiguration）
    │   ├── apilog/      # API 日志
    │   ├── banner/      # 启动 Banner
    │   ├── encrypt/     # API 加密
    │   ├── jackson/     # JSON 序列化
    │   ├── swagger/     # 接口文档
    │   └── xss/         # XSS 防护（XSS 原理见 [XSS](../../_common/05-web-security/02-xss.md)）
    └── resources/
        └── META-INF/spring/
            └── org.springframework.boot.autoconfigure.AutoConfiguration.imports
```

**解读**：
- 一个 starter 把多个相关的"功能模块"（web、apilog、encrypt、xss、swagger）打包在一起
- 所有自动配置类在 `META-INF/spring/...imports` 中集中注册
- 用户引入 `yudao-spring-boot-starter-web` 即可使用所有这些功能

### 3.2 YudaoWebAutoConfiguration 是 Starter 的核心

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
**核心代码**（行 35-50）：

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
        return new WebMvcRegistrations() {

            @Override
            public RequestMappingHandlerMapping getRequestMappingHandlerMapping() {
                RequestMappingHandlerMapping mapping = new RequestMappingHandlerMapping();
                // 实例化时就带上前缀
                mapping.setPathPrefixes(buildPathPrefixes(webProperties));
                return mapping;
            }
```

**解读**：
- 第 2 行：`@AutoConfiguration` 是 Spring Boot 3.x 推荐的自动配置注解
- 第 3 行：`@EnableConfigurationProperties` 启用 `WebProperties`（用户可配置的 web 属性）
- 第 8 行：`@Value` 注入应用名（用于异常日志、API 日志）
- 第 11-19 行：自定义 `WebMvcRegistrations` 给所有 `/admin-api/**` 和 `/app-api/**` 的 Controller 加前缀
- **Starter 设计哲学**：通过自动配置"无侵入"地修改框架行为，用户无感知

### 3.3 WebProperties 配置类

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/WebProperties.java`
**核心代码**（行 1-30）：

```java
package cn.iocoder.yudao.framework.web.config;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.servlet.config.annotation.PathMatchConfigurer;

import javax.validation.Valid;
import javax.validation.constraints.NotEmpty;
import javax.validation.constraints.NotNull;

@ConfigurationProperties(prefix = "yudao.web")
@Validated
@Data
public class WebProperties {

    @NotNull(message = "APP API 不能为空")
    private Api appApi = new Api("/app-api", "**.controller.app.**");
    @NotNull(message = "Admin API 不能为空")
    private Api adminApi = new Api("/admin-api", "**.controller.admin.**");

    @NotNull(message = "Admin UI 不能为空")
    private Ui adminUi;
```

**解读**：
- 第 13 行：`@ConfigurationProperties(prefix = "yudao.web")` 把 `yudao.web.*` 配置映射到 `WebProperties` 字段
- 第 18-19 行：默认值 `appApi = /app-api`，`adminApi = /admin-api`
- **用户可覆盖**：在 `application.yml` 中写 `yudao.web.admin-api.prefix: /my-api` 即可
- **Starter 关键设计**：`Properties` 类是 Starter 与用户配置的"接口"

## 4. 关键要点总结

- **Starter = pom 依赖 + 自动配置 + 配置属性**
- **标准结构**：autoconfigure 模块（代码） + starter 模块（仅 pom）
- **命名规范**：`{name}-spring-boot-autoconfigure` + `{name}-spring-boot-starter`
- **注册方式**：`META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`
- **核心注解**：`@AutoConfiguration` + `@EnableConfigurationProperties` + `@ConditionalOnMissingBean`
- ruoyi-vue-pro 的 starter 模式：`yudao-spring-boot-starter-{name}` 包含多个相关功能模块
- **设计原则**：通过 Starter 复用通用功能，业务模块只关注业务

## 5. 练习题

### 练习 1：基础（必做）

在 ruoyi-vue-pro 中列出所有 `yudao-spring-boot-starter-*` 模块，理解每个模块的职责（web、redis、mq、security 等）。

### 练习 2：进阶

阅读 `yudao-spring-boot-starter-web` 的 `META-INF/spring/...imports` 文件，列出所有注册的自动配置类，并说明每个的作用。

### 练习 3：挑战（选做）

仿照 `yudao-spring-boot-starter-web`，自定义一个 `yudao-spring-boot-starter-email`：
- Properties：`yudao.email.host`、`yudao.email.port`、`yudao.email.username`、`yudao.email.password`
- 自动配置：注册 `JavaMailSender` Bean
- 用户只需引入依赖 + 配置即可使用

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/YudaoWebAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/WebProperties.java`
- 自定义 Starter 教程：https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.developing-auto-configuration.custom-starter
- 芋道自定义 Starter：https://doc.iocoder.cn/spring-boot-starter-custom/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
