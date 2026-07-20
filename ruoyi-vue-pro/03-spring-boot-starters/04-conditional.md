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

## 3. 关键要点总结

- **`@Conditional*` 系列**让 starter 变得**可插拔**——jar 在不在、配置写不写都能控制
- **`@ConditionalOnClass`** 是 Starter 中最常用的"依赖可选模块"控制
- **`@ConditionalOnMissingBean`** 让业务方**始终能覆盖** starter 的默认 Bean
- **`@ConditionalOnProperty`** 用于 starter 总开关（如 `yudao.tenant.enable`）
- **ruoyi 大量使用嵌套 `@Configuration`** 模式实现按需装配

---

**文档版本**：v1.0
**最后更新**：2026-07-13
