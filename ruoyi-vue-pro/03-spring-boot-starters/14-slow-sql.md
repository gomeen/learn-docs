# 2.7 慢 SQL 监控与打印

> 掌握 yudao 中慢 SQL 的检测与打印机制，能配置 SQL 监控。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 yudao 的 SQL 打印机制（基于 p6spy）
- 掌握慢 SQL 阈值配置
- 了解 MyBatis Plus 的 SQL 分析插件
- 能在 yudao 中开启/关闭 SQL 打印

## 📚 前置知识

- [07-mybatis-starter.md](./07-mybatis-starter.md)
- p6spy 原理（JDBC 拦截器）
- MyBatis 拦截器
- MySQL 慢查询分析见 [04-mysql-slow-query](../04-database/04-mysql-slow-query.md)

## 1. 核心概念

### 1.1 为什么需要 SQL 打印？

开发期：方便调试（看到完整 SQL 与参数）。
生产期：检测慢 SQL（> 阈值时报警）。

### 1.2 yudao 的实现方式

yudao 通过 **p6spy** 实现 SQL 打印：
- p6spy 是一个 JDBC 拦截器，伪装成真实的 JDBC 驱动
- 所有 SQL 执行前先经过 p6spy，可以记录/改写

### 1.3 MyBatis Plus 的 SQL 分析插件

ruoyi 也支持 MP 的 `IllegalSQLInnerInterceptor`（防全表更新）、`PerformanceInterceptor`（已废弃）。

## 2. 代码示例

### 2.1 引入 p6spy 依赖

```xml
<dependency>
    <groupId>p6spy</groupId>
    <artifactId>p6spy</artifactId>
    <version>3.9.1</version>
</dependency>
```

### 2.2 配置 spy.properties

```properties
# 文件：spy.properties
module.log=com.p6spy.engine.logging.P6LogFactory
appender=com.p6spy.engine.spy.appender.StdoutLogger
logMessageFormat=com.p6spy.engine.spy.appender.MultiLineFormat
# 慢 SQL 阈值（毫秒）
executionThreshold=1000
# 过滤不需要的 SQL
filter=true
exclude=select 1
```

### 2.3 application.yml

```yaml
spring:
  datasource:
    url: jdbc:p6spy:mysql://localhost:3306/ruoyi-vue-pro
    driver-class-name: com.p6spy.engine.spy.P6SpyDriver
```

## 3. 关键要点总结

- **yudao 不直接做慢 SQL 监控**，主要依赖 p6spy + 日志框架
- **p6spy 是生产级** SQL 拦截方案
- **`BlockAttackInnerInterceptor`** 防全表攻击（默认关闭）
- **Druid 的 stat filter** 是更专业的方案

---

**文档版本**：v1.0
**最后更新**：2026-07-13
