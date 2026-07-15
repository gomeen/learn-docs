# 1.2 AutoConfiguration 自动装配

> 理解 Spring Boot 自动装配机制，能编写自定义 AutoConfiguration。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 `@AutoConfiguration` 注解的作用
- 掌握 `spring.factories` 与 `AutoConfiguration.imports` 的差异
- 学会使用 `@Conditional` 系列注解控制 Bean 的注册
- 能修改 ruoyi 现有 Starter 的配置行为

## 📚 前置知识

- [01-starter-mechanism.md](./01-starter-mechanism.md)
- Spring 条件注解（@ConditionalOnClass、@ConditionalOnBean；详见 [04-conditional](./04-conditional.md)）
- Spring Boot 启动流程（详见 [07-startup](../02-spring-boot/07-startup.md) / [08-auto-config](../02-spring-boot/08-auto-config.md)）

## 1. 核心概念

### 1.1 什么是自动装配？

**自动装配（Auto-Configuration）** 是 Spring Boot 的核心特性：根据 classpath 下的 jar 包、用户配置（`application.yml`）**自动注册** 合适的 Bean。

**触发时机**：Spring Boot 启动 → 读取 `AutoConfiguration.imports` → 加载类 → 通过 `@Conditional` 评估 → 注册 Bean。

### 1.2 @AutoConfiguration vs @Configuration

| 注解 | 用途 | 使用位置 |
|------|------|---------|
| `@Configuration` | 通用配置类 | 业务代码 |
| `@AutoConfiguration` | 自动装配专用 | Starter 中的 `*AutoConfiguration` 类 |

`@AutoConfiguration` 内部使用 `@Configuration(proxyBeanMethods = false)`，并提供自动配置加载顺序控制。

### 1.3 @Conditional 条件装配

只有条件满足时才注册 Bean，常见条件：

```java
@ConditionalOnClass       // classpath 存在某类
@ConditionalOnBean        // 容器中存在某 Bean
@ConditionalOnMissingBean // 容器中不存在某 Bean
@ConditionalOnProperty    // 配置文件中存在某属性
@ConditionalOnResource    // classpath 存在某资源
@ConditionalOnWebApplication // Web 应用
@ConditionalOnExpression  // SpEL 表达式
```

## 2. 代码示例

### 2.1 完整 AutoConfiguration 示例

```java
// 文件：MyAutoConfiguration.java
package com.example.starter;

import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;

@AutoConfiguration  // 标记为自动配置类
@ConditionalOnClass(name = "com.example.SomeThirdPartyClass")  // 必须有第三方类
@ConditionalOnProperty(prefix = "mystarter", name = "enable", havingValue = "true", matchIfMissing = true)
public class MyAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean  // 允许业务方覆盖
    public MyService myService(MyProperties properties) {
        return new MyService(properties);
    }
}
```

对应的 `application.yml`：

```yaml
mystarter:
  enable: true  # 启用 starter
  name: demo
```

### 2.2 常见错误：缺少 @ConditionalOnMissingBean

```java
// ❌ 错误：业务方自定义 Bean 无法覆盖
@Bean
public DataSource dataSource() {
    return new HikariDataSource();
}
```

```java
// ✅ 正确：业务方可以自己定义 DataSource Bean 来替换
@Bean
@ConditionalOnMissingBean(DataSource.class)
public DataSource dataSource() {
    return new HikariDataSource();
}
```

## 3. ruoyi 仓库源码解读

### 3.1 yudao MyBatis 自动配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`
**核心代码**（行 34-54）：

```java
@AutoConfiguration(before = MybatisPlusAutoConfiguration.class)
@MapperScan(value = "${yudao.info.base-package}", annotationClass = Mapper.class,
        lazyInitialization = "${mybatis.lazy-initialization:false}")
public class YudaoMybatisAutoConfiguration {

    static {
        JsqlParserGlobal.setJsqlParseCache(new JdkSerialCaffeineJsqlParseCache(
                (cache) -> cache.maximumSize(1024)
                        .expireAfterWrite(5, TimeUnit.SECONDS))
        );
    }

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor mybatisPlusInterceptor = new MybatisPlusInterceptor();
        mybatisPlusInterceptor.addInnerInterceptor(new PaginationInnerInterceptor());
        return mybatisPlusInterceptor;
    }

    @Bean
    public MetaObjectHandler defaultMetaObjectHandler() {
        return new DefaultDBFieldHandler();
    }
}
```

**解读**：
- 第 34 行：`before = MybatisPlusAutoConfiguration.class` 强制本配置先于 MP 加载，保证 `@MapperScan` 先注册
- 第 39-45 行：static 块在类加载时设置 JsqlParser 全局缓存，加速 SQL 解析
- 第 48-54 行：注册分页拦截器（PaginationInnerInterceptor），这是 MyBatis Plus 分页的核心
- 第 57-59 行：注册 `MetaObjectHandler` 用于自动填充 `createTime`、`creator` 等字段

### 3.2 多数据源自动配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/datasource/config/YudaoDataSourceAutoConfiguration.java`

**核心代码**（节选）：

```java
@AutoConfiguration(before = YudaoMybatisAutoConfiguration.class)
@EnableConfigurationProperties(DataSourceProperties.class)
public class YudaoDataSourceAutoConfiguration {

    @Bean
    public DynamicDataSourceAnnotationAdvisor dynamicDataSourceAnnotationAdvisor() {
        // 注册 @DS 注解的 AOP 切面
    }
}
```

**解读**：
- `before = YudaoMybatisAutoConfiguration.class` 保证数据源在 MyBatis 之前装配
- 通过 `@DS` 注解实现多数据源切换（ruoyi 经典特性）
- 整个 Starter 的装配顺序：`DataSource → Mybatis → Tenant → DataPermission`

## 4. 关键要点总结

- **`@AutoConfiguration`** 是 Spring Boot 3.x 专门为 Starter 设计的注解
- **`AutoConfiguration.imports`**（META-INF/spring/）替代了 Spring Boot 2.x 的 `spring.factories`
- **`@ConditionalOnMissingBean`** 让业务方可以**覆盖** starter 提供的 Bean，是 starter 可扩展的关键
- **装配顺序**由 `@AutoConfiguration(before = X.class)` 控制——ruoyi Starter 之间有严格顺序
- **避免**直接在 starter 中写业务逻辑，应通过 `@Conditional` 决定是否生效

## 5. 练习题

### 练习 1：基础（必做）

阅读 `YudaoMybatisAutoConfiguration` 的 `@Bean` 方法，回答：
- `mybatisPlusInterceptor` 的作用？
- `defaultMetaObjectHandler` 的作用？
- 能否通过 `application.yml` 关闭分页插件？

### 练习 2：进阶

给 `YudaoMybatisAutoConfiguration` 加一个开关（`mybatis-plus.print-sql`），开启后打印完整 SQL。提示：使用 `@ConditionalOnProperty`。

### 练习 3：挑战（选做）

阅读 `yudao-spring-boot-starter-biz-tenant` 的 `YudaoTenantAutoConfiguration`，画出"用户请求 → Tenant 装配 → DB 拦截器"的时序图。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/datasource/config/YudaoDataSourceAutoConfiguration.java`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`
- Spring Boot 自动装配源码：`org.springframework.boot.autoconfigure.AutoConfigurationImportSelector`
- Spring Boot 文档：https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.developing.auto-configuration

---

**文档版本**：v1.0
**最后更新**：2026-07-13
