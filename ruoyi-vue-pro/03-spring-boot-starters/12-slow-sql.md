# 2.7 慢 SQL 监控与打印

> 掌握 yudao 中慢 SQL 的检测与打印机制，能配置 SQL 监控。

## 🎯 学习目标

完成本文档后，你将能够：
- 理解 yudao 的 SQL 打印机制（基于 p6spy）
- 掌握慢 SQL 阈值配置
- 了解 MyBatis Plus 的 SQL 分析插件
- 能在 yudao 中开启/关闭 SQL 打印

## 📚 前置知识

- [06-mybatis-starter.md](./06-mybatis-starter.md)
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

## 3. ruoyi 仓库源码解读

### 3.1 SQL 输出格式控制

yudao 通过 `MyBatisUtils.addOrder` 等工具方法格式化 SQL，但没有内置慢 SQL 插件——主要通过 **p6spy + 日志框架**实现。

### 3.2 BlockAttackInnerInterceptor

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`
**核心代码**（行 49-53）：

```java
@Bean
public MybatisPlusInterceptor mybatisPlusInterceptor() {
    MybatisPlusInterceptor mybatisPlusInterceptor = new MybatisPlusInterceptor();
    mybatisPlusInterceptor.addInnerInterceptor(new PaginationInnerInterceptor());
    // ↓↓↓ 按需开启，可能会影响到 updateBatch 的地方 ↓↓↓
    // mybatisPlusInterceptor.addInnerInterceptor(new BlockAttackInnerInterceptor());
    return mybatisPlusInterceptor;
}
```

**解读**：
- `BlockAttackInnerInterceptor` 是 MP 的**防全表攻击**插件
- 拦截没有 `WHERE` 条件的 `UPDATE` / `DELETE`，直接抛异常
- **默认注释**：因为会影响正常的批量更新（`updateBatch`）

### 3.3 Druid 集成（可选）

yudao-starter-mybatis 的 `YudaoDataSourceAutoConfiguration` 引入了 Druid 连接池，可以配置慢 SQL 监控：

```java
// Druid 配置（不在 yudao 默认开启）
@Bean
public DruidDataSource druidDataSource() {
    DruidDataSource ds = new DruidDataSource();
    ds.setFilters("stat,wall");  // stat 提供慢 SQL 监控
    return ds;
}
```

## 4. 关键要点总结

- **yudao 不直接做慢 SQL 监控**，主要依赖 p6spy + 日志框架
- **p6spy 是生产级** SQL 拦截方案
- **`BlockAttackInnerInterceptor`** 防全表攻击（默认关闭）
- **Druid 的 stat filter** 是更专业的方案

## 5. 练习题

### 练习 1：基础（必做）

在 yudao-server 中引入 p6spy，开启 SQL 打印。访问一个分页接口，观察控制台输出。

### 练习 2：进阶

把慢 SQL 阈值设置为 50ms，构造一个慢查询（用 `SELECT SLEEP(1)`），看是否被检测到。

### 练习 3：挑战（选做）

用 Druid 的 `StatFilter` 替代 p6spy，把慢 SQL 写入数据库表，搭一个慢 SQL 监控面板。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/src/main/java/cn/iocoder/yudao/framework/mybatis/config/YudaoMybatisAutoConfiguration.java`
- p6spy 文档：https://github.com/p6spy/p6spy
- Druid 监控文档：https://github.com/alibaba/druid/wiki/%E5%90%84%E7%A7%8D%E6%8E%A5%E5%8F%A3%E7%9A%84%E4%BD%BF%E7%94%A8%E6%96%B9%E6%B3%95

---

**文档版本**：v1.0
**最后更新**：2026-07-13
