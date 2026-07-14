# 10 配置文件：application.yml 多环境

> 掌握 Spring Boot 配置文件的语法、加载顺序、多环境分离，能正确管理 ruoyi-vue-pro 的配置。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `application.yml` 的语法（层级、数组、占位符）
- 掌握配置加载顺序：命令行 > 环境变量 > application-{profile}.yml > application.yml
- 掌握 `@ConfigurationProperties` 和 `@Value` 的差异
- 能在 ruoyi-vue-pro 中定位配置问题

## 📚 前置知识

- 06-profile.md
- 09-custom-starter.md

## 1. 核心概念

### 1.1 application.yml 语法

```yaml
# 字符串
yudao:
  name: "yudao-server"
  # 多行字符串
  description: |
    line 1
    line 2

# 数组
yudao:
  regions:
    - beijing
    - shanghai
    - shenzhen

# Map
yudao:
  databases:
    master: jdbc:mysql://localhost:3306/master
    slave: jdbc:mysql://localhost:3306/slave

# 占位符
yudao:
  name: "yudao-server"
  full-name: "${yudao.name}-v1"  # → yudao-server-v1

# 默认值
yudao:
  timeout: "${TIMEOUT:3000}"  # 优先用环境变量 TIMEOUT，默认 3000
```

### 1.2 加载顺序（优先级从高到低）

1. 命令行参数：`--server.port=8081`
2. `SPRING_APPLICATION_JSON` 内嵌 JSON
3. JNDI 属性
4. ServletContext 初始化参数
5. ServletConfig 初始化参数
6. 系统属性（`-D` 参数）
7. **操作系统环境变量**
8. **RandomValuePropertySource**（random.*）
9. **Jar 包外的 `application-{profile}.yml`**
10. **Jar 包内的 `application-{profile}.yml`**
11. **Jar 包外的 `application.yml`**
12. **Jar 包内的 `application.yml`**
13. `@PropertySource` 注解
14. 默认属性（SpringApplication.setDefaultProperties）

### 1.3 `@Value` vs `@ConfigurationProperties`

| 特性 | `@Value` | `@ConfigurationProperties` |
|------|---------|--------------------------|
| 注入单个值 | ✅ 擅长 | ✅ 支持 |
| 注入复杂对象（Map/List） | ❌ 麻烦 | ✅ 擅长 |
| 校验（`@Valid`） | ❌ | ✅ |
| IDE 元数据提示 | ❌ | ✅ |
| 松散绑定（`kebab-case`） | ❌ | ✅ |
| 推荐场景 | 简单值（端口、路径） | 业务配置类 |

## 2. 代码示例

### 2.1 简单配置 + @Value

```java
@Value("${server.port}")
private Integer port;

@Value("${yudao.name:yudao}")  // 默认值 yudao
private String name;
```

### 2.2 复杂配置 + @ConfigurationProperties

```java
// 文件：MyProperties.java
@Data
@ConfigurationProperties(prefix = "yudao.email")
@Validated
public class EmailProperties {
    @NotBlank
    private String host;
    @Min(1) @Max(65535)
    private Integer port = 465;
    private String username;
    private String password;
    private Duration timeout = Duration.ofSeconds(10);
}
```

```yaml
# application.yml
yudao:
  email:
    host: smtp.example.com
    port: 465
    username: noreply@example.com
    password: ${EMAIL_PASSWORD}  # 来自环境变量
    timeout: 30s
```

### 2.3 激活 Profile

```yaml
# application.yml
spring:
  profiles:
    active: dev  # 激活 application-dev.yml
```

## 3. ruoyi-vue-pro 仓库源码解读

### 3.1 WebProperties 配置类

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/WebProperties.java`
**核心代码**（行 1-50）：

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

    @Data
    @AllArgsConstructor
    @NoArgsConstructor
    @Valid
    public static class Api {

        /**
         * API 前缀，实现所有 Controller 提供的 RESTFul API 的统一前缀
         */
        @NotEmpty(message = "API 前缀不能为空")
        private String prefix;

        /**
         * Controller 所在包的 Ant 路径规则
         */
        @NotEmpty(message = "Controller 所在包不能为空")
        private String controller;

    }
```

**解读**：
- 第 13 行：`@ConfigurationProperties(prefix = "yudao.web")` 把 `yudao.web.*` 配置注入
- 第 14 行：`@Validated` 启用 JSR-303 校验
- 第 18-19 行：默认值 `appApi = /app-api`，可在 `application.yml` 中覆盖
- 第 21-23 行：`Api` 内部类用 `@Valid` 级联校验
- **用户使用方式**：

```yaml
yudao:
  web:
    admin-api:
      prefix: /admin-api
      controller: "**.controller.admin.**"
    admin-ui:
      url: https://www.yudao.com
```

### 3.2 Cache 配置（Redis）

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
**核心代码**（行 26-50）：

```java
/**
 * Cache 配置类，基于 Redis 实现
 */
@AutoConfiguration
@EnableConfigurationProperties({CacheProperties.class, YudaoCacheProperties.class})
@EnableCaching
public class YudaoCacheAutoConfiguration {

    /**
     * RedisCacheConfiguration Bean
     */
    @Bean
    @Primary
    public RedisCacheConfiguration redisCacheConfiguration(CacheProperties cacheProperties) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig();
        // 设置使用 : 单冒号，而不是双 :: 冒号，避免 Redis Desktop Manager 多余空格
        config = config.computePrefixWith(cacheName -> {
            String keyPrefix = cacheProperties.getRedis().getKeyPrefix();
            if (StringUtils.hasText(keyPrefix)) {
                keyPrefix = keyPrefix.lastIndexOf(StrUtil.COLON) == -1 ? keyPrefix + StrUtil.COLON : keyPrefix;
                return keyPrefix + cacheName + StrUtil.COLON;
            }
            return cacheName + StrUtil.COLON;
        });
```

**解读**：
- 第 28-29 行：同时启用 Spring 内置 `CacheProperties` 和 ruoyi 自定义 `YudaoCacheProperties`
- 第 30 行：`@Primary` 标记为主 Bean，Spring 注入时优先选这个
- 第 32-44 行：自定义 Redis Key 前缀（如 `yudao:user:1`），避免与其他系统冲突
- **配置生效**：

```yaml
spring:
  cache:
    type: redis
    redis:
      time-to-live: 1h         # 1 小时过期
      cache-null-values: false # 不缓存 null
      key-prefix: "yudao:cache:"
```

## 4. 关键要点总结

- **`application.yml` 优先级低于命令行参数和环境变量**
- **多环境配置**：`application-{profile}.yml` + `spring.profiles.active`
- **`@ConfigurationProperties` 适合复杂配置类**，`@Value` 适合简单值
- **ruoyi 配置约定**：`yudao.{module}.{key}` 命名空间
- **`@Validated`** 让配置类启动时校验，配置错误立即失败
- **常见错误**：配置项没生效 → 检查 Profile、yaml 缩进、占位符语法

## 5. 练习题

### 练习 1：基础（必做）

在 ruoyi-vue-pro 的 `application.yml` 中找到 `yudao.web.admin-api.prefix`，尝试修改为 `/api` 并重启验证。

### 练习 2：进阶

解释 `application.yml` 中 `spring.profiles.active: dev` 和启动参数 `--spring.profiles.active=prod` 的优先级关系。

### 练习 3：挑战（选做）

实现一个 `JwtProperties` 配置类，支持 `yudao.jwt.secret`、`yudao.jwt.expire-minutes` 等配置，并通过 `@ConfigurationProperties` 注入到 `JwtUtil` 工具类中。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-web/src/main/java/cn/iocoder/yudao/framework/web/config/WebProperties.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
- Spring Boot 配置官方文档：https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.external-config
- 芋道配置文件：https://doc.iocoder.cn/spring-boot-configuration-properties/

---

**文档版本**：v1.0
**最后更新**：2026-07-13
