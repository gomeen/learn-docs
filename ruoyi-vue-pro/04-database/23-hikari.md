# 23 HikariCP 连接池

> HikariCP 是 Spring Boot 默认的连接池，「以快著称」。理解与 Druid 的差异有助于选型。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 HikariCP 的设计理念
- 掌握 HikariCP 的核心配置
- 知道 HikariCP 与 Druid 的差异
- 在 ruoyi 中切换使用 HikariCP

## 📚 前置知识

- [22-druid.md](./22-druid.md)
- Spring Boot 自动配置（详见 [08-auto-config](../02-spring-boot/08-auto-config.md)）

## 1. 核心概念

### 1.1 HikariCP 是什么？

HikariCP（"光"）是 Spring Boot 2.x+ 默认的 JDBC 连接池：
- 性能最优（号称「最快的连接池」）
- 配置极简（核心参数只有 10 个左右）
- 代码质量高（字节码优化）

### 1.2 HikariCP vs Druid

| 维度 | HikariCP | Druid |
|------|----------|-------|
| 性能 | 最快 | 良好 |
| 监控 | 无（需外部） | 内置 Web 监控 |
| SQL 防火墙 | 无 | 内置 Wall |
| 配置复杂度 | 简单 | 中等 |
| 适用 | 性能敏感场景 | 需要监控/防护 |
| ruoyi 默认 | 否 | 是 |

### 1.3 何时用 HikariCP

- 应用简单，无需复杂监控
- 性能要求高（如：高并发微服务）
- 已用 APM 工具（如：SkyWalking）做 SQL 监控
- 单库单实例，无需 SQL 防火墙

## 2. 代码示例

### 2.1 Spring Boot 默认 HikariCP

```yaml
spring:
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/ruoyi?useSSL=false
    username: root
    password: 123456
    driver-class-name: com.mysql.cj.jdbc.Driver
    hikari:
      pool-name: RuoyiHikariPool
      maximum-pool-size: 20
      minimum-idle: 5
      connection-timeout: 30000
      idle-timeout: 600000
      max-lifetime: 1800000
      connection-test-query: SELECT 1
```

### 2.2 核心参数详解

```yaml
spring:
  datasource:
    hikari:
      # 必填项（但有默认值）
      maximum-pool-size: 20       # 最大连接数（含空闲+活跃）
      minimum-idle: 5             # 最小空闲连接
      connection-timeout: 30000   # 获取连接超时（毫秒），默认 30s
      idle-timeout: 600000        # 空闲连接超时（毫秒），默认 10 分钟
      max-lifetime: 1800000       # 连接最大生存时间（毫秒），默认 30 分钟
      connection-test-query: SELECT 1  # 连接有效性检查 SQL
      pool-name: MyHikariCP       # 连接池名称
      auto-commit: true           # 自动提交
      # 性能优化
      data-source-properties:
        cachePrepStmts: true      # 开启 PreparedStatement 缓存
        prepStmtCacheSize: 250
        prepStmtCacheSqlLimit: 2048
        useServerPrepStmts: true
```

### 2.3 编程方式配置

```java
@Configuration
public class HikariConfig {

    @Bean
    @ConfigurationProperties("spring.datasource.hikari")
    public HikariDataSource dataSource(DataSourceProperties properties) {
        return properties.initializeDataSourceBuilder()
                .type(HikariDataSource.class)
                .build();
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 默认使用 Druid 而非 HikariCP

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`

```yaml
spring:
  autoconfigure:
    exclude:
      - com.alibaba.druid.spring.boot.autoconfigure.DruidDataSourceAutoConfigure  # 排除 Druid 自动配置
      ...
```

**解读**：
- ruoyi 排除 Druid 的自动配置是因为用 `dynamic-datasource` 接管数据源
- ruoyi 默认连接池仍是 **Druid**（在 `dynamic-datasource` 内部指定）
- **原因**：Druid 提供监控 + SQL 防火墙，对 ruoyi 这类管理后台更重要

### 3.2 切换为 HikariCP 的方法

如果想在 ruoyi 中使用 HikariCP，需要修改两处：

**第一步**：修改 `dynamic-datasource` 的配置，指定使用 HikariCP 作为连接池：

```yaml
spring:
  datasource:
    dynamic:
      hikari:  # 改用 hikari 代替 druid
        maximum-pool-size: 20
        minimum-idle: 5
        connection-timeout: 30000
      primary: master
      datasource:
        master:
          url: jdbc:mysql://127.0.0.1:3306/ruoyi
          username: root
          password: 123456
```

**第二步**：移除 Druid 排除配置：

```yaml
spring:
  autoconfigure:
    exclude:
      # - com.alibaba.druid.spring.boot.autoconfigure.DruidDataSourceAutoConfigure  # 注释掉
      - org.springframework.boot.autoconfigure.quartz.QuartzAutoConfiguration
```

**注意**：`dynamic-datasource-spring-boot3-starter` 默认支持 Druid，切换到 HikariCP 需引入 `HikariCP` 依赖：

```xml
<dependency>
    <groupId>com.zaxxer</groupId>
    <artifactId>HikariCP</artifactId>
</dependency>
```

### 3.3 性能对比参考

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/《芋道 Spring Boot 数据库连接池入门》.md`

**核心内容（节选）**：

> ruoyi 选择 Druid 的核心理由：
> 1. **监控**：内置 Web 监控页面，开发运维方便
> 2. **SQL 防火墙**：防止 SQL 注入，降低安全风险
> 3. **慢 SQL 记录**：内置支持，对性能调优至关重要
> 4. **生态成熟**：中文文档完善
>
> 若追求极致性能且已有 APM 工具，可考虑 HikariCP。

## 4. 关键要点总结

- HikariCP 性能最优，但功能简单（无监控、无防火墙）
- Druid 功能丰富（监控 + 慢 SQL + 防火墙），是 ruoyi 默认
- 选择标准：是否需要监控/防火墙 → Druid；纯性能需求 → HikariCP
- ruoyi 通过 `dynamic-datasource` 整合连接池（不直接绑定 Druid）
- 切换连接池是「改配置 + 改依赖」的简单操作

## 5. 练习题

### 练习 1：基础（必做）

新建 Spring Boot 项目，默认使用 HikariCP，配置 `maximum-pool-size: 5`，启动一个并发 20 的请求，观察获取连接耗时。

### 练习 2：进阶

在 ruoyi 中尝试切换为 HikariCP（按文档 3.2 修改），启动应用，确认 Druid 监控页面 `/druid/*` 不可用，但应用正常运行。

### 练习 3：挑战（选做）

为 ruoyi 设计一个「Druid + HikariCP 混合」方案：核心业务用 Druid（享受监控），高频读用 HikariCP（极致性能），通过 `@DS` 切换。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/《芋道 Spring Boot 数据库连接池入门》.md`
- HikariCP 官方文档：https://github.com/brettwooldridge/HikariCP

---

**文档版本**：v1.0
**最后更新**：2026-07-13