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
- [23-dynamic-datasource.md](./23-dynamic-datasource.md)
- 慢 SQL 见 [04-mysql-slow-query](./04-mysql-slow-query.md)

## 1. 核心概念

### 1.1 为什么需要连接池？

```
没有连接池：每次 SQL 执行都新建连接（TCP 握手 100ms+）
有了连接池：连接复用，省去握手时间
```

### 1.2 Druid 的核心能力

1. **连接池**：管理数据库连接的生命周期
2. **监控**：SQL 执行统计、慢 SQL 记录、Web 监控页面
3. **防火墙**：WallFilter 防 SQL 注入（SQL 注入见 [SQL 注入](../../_common/05-web-security/03-sql-injection.md)）
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

## 3. 关键要点总结

- Druid = 连接池 + 监控 + 防火墙三位一体
- `slow-sql-millis: 100` 是 ruoyi 的调优点（比 MySQL 默认严格）
- `wall` filter 防止 SQL 注入（生产必开）
- 监控页面 `/druid/*` 在生产环境必须配置密码 + IP 白名单
- `max-active` 控制最大并发，超过会等待或抛异常

---

**文档版本**：v1.0
**最后更新**：2026-07-13
