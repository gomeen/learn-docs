# 1.4 @Conditional 条件装配

> 掌握 Spring Boot 条件注解，能用条件注解控制 Bean 是否注册。

## 🎯 学习目标

完成本文档后，你将能够：
- 掌握 10+ 个 `@Conditional` 系列注解的用法
- 理解条件装配如何让 starter **可插拔**
- 能在 ruoyi 现有配置中识别条件注解
- 能用 `@ConditionalOnProperty` 实现配置开关

## 📚 前置知识

- [02-auto-configuration.md](./02-auto-configuration.md)
- Spring 表达式语言 SpEL 基础

## 1. 核心概念

### 1.1 条件装配的本质

条件装配解决了一个问题：**"这个 Bean 应不应该被注册？"**

判定依据包括：classpath 有什么、配置文件写了什么、容器里有什么 Bean。

### 1.2 常用条件注解

| 注解 | 作用 | 典型场景 |
|------|------|---------|
| `@ConditionalOnClass` | classpath 存在某类 | 依赖可选 jar 时 |
| `@ConditionalOnMissingClass` | classpath 缺失某类 | 排除某些场景 |
| `@ConditionalOnBean` | 容器中存在某 Bean | 依赖其他 Bean |
| `@ConditionalOnMissingBean` | 容器中缺失某 Bean | 允许用户覆盖 |
| `@ConditionalOnProperty` | 配置属性匹配 | 配置开关 |
| `@ConditionalOnResource` | 存在某资源文件 | 加载静态资源 |
| `@ConditionalOnWebApplication` | 是 Web 应用 | Web 专用配置 |
| `@ConditionalOnExpression` | SpEL 表达式 | 复杂条件 |

## 2. 代码示例

### 2.1 多条件组合

```java
@AutoConfiguration
@ConditionalOnClass(name = "com.example.SomeDependency")
@ConditionalOnProperty(prefix = "feature", name = "enable", havingValue = "true")
public class FeatureAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public FeatureService featureService() {
        return new FeatureService();
    }
}
```

### 2.2 嵌套配置类实现可选模块

```java
@AutoConfiguration
public class DatabaseAutoConfiguration {

    @Bean
    public DataSource dataSource() {
        return new HikariDataSource();
    }

    // 当 classpath 有 MyBatis 时才加载
    @Configuration(proxyBeanMethods = false)
    @ConditionalOnClass(name = "org.apache.ibatis.session.SqlSessionFactory")
    public static class MybatisConfiguration {

        @Bean
        public SqlSessionFactory sqlSessionFactory(DataSource dataSource) {
            // ...
        }
    }
}
```

### 2.3 常见错误：条件冲突

```java
// ❌ 错误：两个互斥条件
@ConditionalOnClass(name = "com.example.A")
@ConditionalOnMissingClass(name = "com.example.A")
public class BadConfiguration { }
```

```java
// ✅ 正确：用 @Conditional 组合
@Conditional(CustomCondition.class)
public class GoodConfiguration { }
```

## 3. ruoyi 仓库源码解读

### 3.1 Tenant 的总开关

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/config/YudaoTenantAutoConfiguration.java`
**核心代码**（行 55-58）：

```java
@AutoConfiguration
@ConditionalOnProperty(prefix = "yudao.tenant", value = "enable", matchIfMissing = true)
@EnableConfigurationProperties(TenantProperties.class)
public class YudaoTenantAutoConfiguration {
    // ...
}
```

**解读**：
- 第 56 行：`yudao.tenant.enable` 默认是 `true`，**默认开启多租户**
- 业务方可以通过 `application.yml` 设置 `yudao.tenant.enable=false` **完全关闭**多租户
- 这种"开关设计"让 starter 不会**强制**侵入业务——是良好实践

### 3.2 RedisMQ 的条件装配

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/config/YudaoTenantAutoConfiguration.java`
**核心代码**（行 161-194）：

```java
@Configuration(proxyBeanMethods = false)
@ConditionalOnClass(name = "cn.iocoder.yudao.framework.mq.redis.core.interceptor.RedisMessageInterceptor")
public static class TenantRedisMQConfiguration {
    @Bean
    public TenantRedisMessageInterceptor tenantRedisMessageInterceptor() {
        return new TenantRedisMessageInterceptor();
    }
}

@Configuration(proxyBeanMethods = false)
@ConditionalOnClass(name = "org.springframework.amqp.rabbit.core.RabbitTemplate")
public static class TenantRabbitMQConfiguration {
    @Bean
    public TenantRabbitMQInitializer tenantRabbitMQInitializer() {
        return new TenantRabbitMQInitializer();
    }
}

@Configuration(proxyBeanMethods = false)
@ConditionalOnClass(name = "org.apache.rocketmq.spring.core.RocketMQTemplate")
public static class TenantRocketMQConfiguration {
    @Bean
    public TenantRocketMQInitializer tenantRocketMQInitializer() {
        return new TenantRocketMQInitializer();
    }
}
```

**解读**：
- **三个内部 `@Configuration` 类**，分别对应 Redis MQ、RabbitMQ、RocketMQ
- 每个都用 `@ConditionalOnClass` 检测**客户端 jar 是否在 classpath**
- 业务方**用了哪个 MQ**，对应的拦截器才被注册——**零侵入**
- 这是 ruoyi 设计**最优雅**的部分之一

### 3.3 RedisCache 的条件装配

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
**核心代码**（节选）：

```java
@AutoConfiguration(after = YudaoRedisAutoConfiguration.class)
public class YudaoCacheAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public RedisCacheManager redisCacheManager(...) {
        return new TimeoutRedisCacheManager(...);
    }
}
```

**解读**：
- `after = YudaoRedisAutoConfiguration.class` 保证 Redis 客户端先就绪
- `@ConditionalOnMissingBean` 允许用户用自己的 `RedisCacheManager` 覆盖

## 4. 关键要点总结

- **`@Conditional*` 系列**让 starter 变得**可插拔**——jar 在不在、配置写不写都能控制
- **`@ConditionalOnClass`** 是 Starter 中最常用的"依赖可选模块"控制
- **`@ConditionalOnMissingBean`** 让业务方**始终能覆盖** starter 的默认 Bean
- **`@ConditionalOnProperty`** 用于 starter 总开关（如 `yudao.tenant.enable`）
- **ruoyi 大量使用嵌套 `@Configuration`** 模式实现按需装配

## 5. 练习题

### 练习 1：基础（必做）

阅读 `YudaoTenantAutoConfiguration.java` 的 230 行代码，列出所有 `@Conditional*` 注解及其触发条件。

### 练习 2：进阶

为 `YudaoMybatisAutoConfiguration` 添加一个条件：仅当 `yudao.mybatis.enable-page=true` 时注册分页插件。验证 `application.yml` 关闭后分页失效。

### 练习 3：挑战（选做）

设计一个多租户的"数据源路由"模块：使用 `@ConditionalOnClass` + `@ConditionalOnProperty` 实现：
- 启用租户时，自动添加租户过滤
- 关闭租户时，使用普通数据源
- 灰度发布时，按用户 ID 灰度

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-biz-tenant/src/main/java/cn/iocoder/yudao/framework/tenant/config/YudaoTenantAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-redis/src/main/java/cn/iocoder/yudao/framework/redis/config/YudaoCacheAutoConfiguration.java`
- Spring Boot 文档：https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.developing.auto-configuration.condition-annotations
- Spring 源码：`org.springframework.boot.autoconfigure.condition.*`

---

**文档版本**：v1.0
**最后更新**：2026-07-13
