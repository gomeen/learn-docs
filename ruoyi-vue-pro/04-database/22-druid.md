# 22 Druid 连接池

> Druid 是阿里开源的 JDBC 连接池，ruoyi 默认使用。理解 Druid 配置是性能调优的基础。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解数据库连接池的作用
- 掌握 Druid 的核心配置项
- 知道 Druid 监控页面的使用
- 了解 Druid 防火墙（WallFilter）的作用

## 📚 前置知识

- JDBC 基础
- 19-dynamic-datasource.md

## 1. 核心概念

### 1.1 为什么需要连接池？

```
没有连接池：每次 SQL 执行都新建连接（TCP 握手 100ms+）
有了连接池：连接复用，省去握手时间
```

### 1.2 Druid 的核心能力

1. **连接池**：管理数据库连接的生命周期
2. **监控**：SQL 执行统计、慢 SQL 记录、Web 监控页面
3. **防 SQL 注入**：WallFilter（基于 SQL 语法解析）
4. **扩展性**：Filter 链机制（stat、wall、slf4j、log4j 等）

### 1.3 ruoyi 中 Druid 的位置

```
spring:
  datasource:
    druid:           ← 监控配置（web-stat、stat-view）
      filter:
        stat:        ← 慢 SQL 记录
        wall:        ← SQL 注入防护
    dynamic:
      druid:         ← 连接池参数（initial-size、max-active）
```

## 2. 代码示例

### 2.1 Druid 完整配置

```yaml
spring:
  datasource:
    druid:
      # 1. 监控页面
      web-stat-filter:
        enabled: true
      stat-view-servlet:
        enabled: true
        url-pattern: /druid/*
        login-username: admin
        login-password: admin
        allow: 127.0.0.1
      # 2. SQL 监控 + 慢 SQL
      filter:
        stat:
          enabled: true
          log-slow-sql: true
          slow-sql-millis: 1000
          merge-sql: true
        # 3. SQL 注入防护
        wall:
          config:
            multi-statement-allow: true  # 允许批量语句
        # 4. 日志输出
        slf4j:
          enabled: true
          statement-log-error-enabled: true
```

### 2.2 连接池参数调优

```yaml
spring:
  datasource:
    dynamic:
      druid:
        # 初始连接数
        initial-size: 1
        # 最小空闲连接
        min-idle: 1
        # 最大活跃连接
        max-active: 20
        # 获取连接超时（毫秒）
        max-wait: 60000
        # 检测间隔（毫秒）
        time-between-eviction-runs-millis: 60000
        # 连接最小生存时间
        min-evictable-idle-time-millis: 600000
        # 连接最大生存时间
        max-evictable-idle-time-millis: 1800000
        # 有效性检查 SQL
        validation-query: SELECT 1 FROM DUAL
        # 借出连接时是否检查
        test-while-idle: true
        test-on-borrow: false
        test-on-return: false
        # PreparedStatement 缓存
        pool-prepared-statements: true
        max-pool-prepared-statement-per-connection-size: 20
```

### 2.3 编程方式配置（可选）

```java
@Configuration
public class DruidConfig {

    @Bean
    @ConfigurationProperties("spring.datasource.druid")
    public DataSource druidDataSource() {
        return new DruidDataSource();
    }

    @Bean
    public ServletRegistrationBean<StatViewServlet> statViewServlet() {
        ServletRegistrationBean<StatViewServlet> bean = new ServletRegistrationBean<>(
            new StatViewServlet(), "/druid/*");
        bean.addInitParameter("loginUsername", "admin");
        bean.addInitParameter("loginPassword", "admin");
        return bean;
    }
}
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的 Druid 监控配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`

```yaml
spring:
  datasource:
    druid:
      web-stat-filter:
        enabled: true
      stat-view-servlet:
        enabled: true
        allow:
        url-pattern: /druid/*
        login-username:
        login-password:
      filter:
        stat:
          enabled: true
          log-slow-sql: true
          slow-sql-millis: 100
          merge-sql: true
        wall:
          config:
            multi-statement-allow: true
```

**解读**：
- 第 4-5 行：web-stat-filter（URI 级别监控，自动统计每个 URL 的请求次数/时间）
- 第 6-11 行：stat-view-servlet（监控页面，`/druid/*`）
  - `allow:` 空表示允许所有（开发用），生产应填白名单 IP
  - `login-username/login-password:` 空表示无密码（开发用），生产必须设置
- 第 12-17 行：stat filter
  - `log-slow-sql: true` 慢 SQL 记录
  - `slow-sql-millis: 100` 阈值 100ms（比 MySQL 默认 10s 严格得多）
  - `merge-sql: true` 合并相似 SQL（如参数不同的同结构 SQL）
- 第 18-20 行：wall filter（SQL 防火墙）
  - `multi-statement-allow: true` 允许多语句（ruoyi 批量操作需要）

### 3.2 连接池参数

**文件位置**：同文件

```yaml
    dynamic:
      druid:
        initial-size: 1
        min-idle: 1
        max-active: 20
        max-wait: 60000
        time-between-eviction-runs-millis: 60000
        min-evictable-idle-time-millis: 600000
        max-evictable-idle-time-millis: 1800000
        validation-query: SELECT 1 FROM DUAL
        test-while-idle: true
        test-on-borrow: false
        test-on-return: false
        pool-prepared-statements: true
        max-pool-prepared-statement-per-connection-size: 20
```

**解读**：
- `initial-size: 1` 初始连接数（启动时建 1 个）
- `max-active: 20` 最大活跃连接（控制最大并发）
- `max-wait: 60000` 获取连接最大等待 60s（超时抛异常）
- `validation-query: SELECT 1 FROM DUAL` 用 Dual 表验证连接有效
- `test-while-idle: true` 空闲时检测连接有效性
- `pool-prepared-statements: true` 启用 PreparedStatement 缓存（性能提升）

### 3.3 Druid 监控文档

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/《芋道 Spring Boot 数据库连接池入门》.md`

**核心内容（节选）**：

> 启动应用后访问 `http://localhost:48080/druid`，即可看到：
> - 数据源监控（连接池状态）
> - SQL 监控（每条 SQL 的执行次数、时间分布、慢 SQL 列表）
> - URI 监控（每个 URL 的请求统计）
> - Session 监控
> - Spring 监控（Bean 调用链）

## 4. 关键要点总结

- Druid = 连接池 + 监控 + 防火墙三位一体
- `slow-sql-millis: 100` 是 ruoyi 的调优点（比 MySQL 默认严格）
- `wall` filter 防止 SQL 注入（生产必开）
- 监控页面 `/druid/*` 在生产环境必须配置密码 + IP 白名单
- `max-active` 控制最大并发，超过会等待或抛异常

## 5. 练习题

### 练习 1：基础（必做）

启动 ruoyi 应用，访问 `http://localhost:48080/druid`，执行几次业务请求，观察 SQL 监控页面，记录：执行次数最多的 SQL、最慢的 SQL、平均耗时。

### 练习 2：进阶

将 `max-active` 从 20 调整到 5，启动一个并发 100 的压测，观察应用日志：是否出现「获取连接超时」异常？说明连接池参数的影响。

### 练习 3：挑战（选做）

为 ruoyi 增加「Druid 自定义告警」：当某条 SQL 平均耗时 > 500ms 时，发送告警到企业微信（提示：用 Druid 的 StatFilter 扩展 + 定时任务）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/《芋道 Spring Boot 数据库连接池入门》.md`
- Druid 官方文档：https://github.com/alibaba/druid/wiki/

---

**文档版本**：v1.0
**最后更新**：2026-07-13