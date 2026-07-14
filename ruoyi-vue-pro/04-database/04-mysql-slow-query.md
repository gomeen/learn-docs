# 04 MySQL 慢查询分析

> 慢 SQL 是系统性能的隐形杀手。ruoyi 通过 Druid 监控 + 自定义慢 SQL 阈值定位问题。

## 🎯 学习目标

完成本文档后，你将能够：
- 开启 MySQL 慢查询日志
- 使用 `EXPLAIN` 分析慢 SQL
- 掌握常见慢 SQL 优化手段
- 理解 ruoyi 中 Druid 的 `log-slow-sql` 配置

## 📚 前置知识

- 01-mysql-basics.md
- 03-mysql-index.md

## 1. 核心概念

### 1.1 什么是慢查询？

执行时间超过 `long_query_time`（默认 10 秒）的 SQL，会被记录到慢查询日志。

### 1.2 慢查询分析流程

```
开启慢查询日志 → 收集慢 SQL → EXPLAIN 分析 → 优化（加索引/改写/分页）
```

### 1.3 慢查询根因分类

| 根因 | 解决方案 |
|------|---------|
| 缺少索引 | 添加合适索引 |
| 索引失效 | 改写 SQL 命中索引 |
| 深度分页 | 游标分页 / 子查询优化 |
| 数据量大 | 分库分表 |
| 锁竞争 | 缩短事务、避免长事务 |
| 全表扫描 | 强制走索引 / 加条件 |

## 2. 代码示例

### 2.1 开启 MySQL 慢查询日志

```sql
-- 查看当前配置
SHOW VARIABLES LIKE 'slow_query%';
SHOW VARIABLES LIKE 'long_query_time';

-- 动态开启（无需重启）
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1;  -- 单位：秒，1 秒即记录
SET GLOBAL slow_query_log_file = '/var/log/mysql/slow.log';

-- 永久生效：修改 my.cnf
[mysqld]
slow_query_log = ON
long_query_time = 1
slow_query_log_file = /var/log/mysql/slow.log
log_output = FILE
```

### 2.2 使用 EXPLAIN 分析

```sql
EXPLAIN SELECT * FROM system_user
WHERE username = 'admin' AND status = 0;
```

输出示例：
```
id  select_type  table         type  possible_keys     key              rows  Extra
1   SIMPLE       system_user   ref   uk_username       uk_username       1    Using where
```

### 2.3 慢 SQL 改写案例

```sql
-- ❌ 深度分页慢（扫描 1000020 行后丢弃前 1000000）
SELECT * FROM system_user ORDER BY id LIMIT 1000000, 20;

-- ✅ 延迟关联（先查 id 再 join）
SELECT u.* FROM system_user u
INNER JOIN (SELECT id FROM system_user ORDER BY id LIMIT 1000000, 20) t
ON u.id = t.id;

-- ✅ 游标分页（如果业务允许）
SELECT * FROM system_user WHERE id > 1000000 ORDER BY id LIMIT 20;
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 慢 SQL 监控配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
**核心代码**（行 14-32）：

```yaml
spring:
  autoconfigure:
    exclude:
      - com.alibaba.druid.spring.boot.autoconfigure.DruidDataSourceAutoConfigure # 排除 Druid 的自动配置，使用 dynamic-datasource-spring-boot-starter 配置多数据源
  datasource:
    druid: # Druid 【监控】相关的全局配置
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
          log-slow-sql: true # 慢 SQL 记录
          slow-sql-millis: 100 # 阈值 100ms
          merge-sql: true
        wall:
          config:
            multi-statement-allow: true
```

**解读**：
- 第 27 行：`log-slow-sql: true` —— 启用慢 SQL 日志
- 第 28 行：`slow-sql-millis: 100` —— **阈值 100ms**（比 MySQL 默认的 10 秒严格得多）
- 第 29 行：`merge-sql: true` —— 合并相似 SQL（如参数不同的同结构 SQL）
- 第 30-32 行：Wall 防火墙，启用 `multi-statement-allow`（允许多语句执行，用于批量更新）
- **设计意图**：开发/本地环境开启慢 SQL 监控，生产可通过 SQL 监控页面 (`/druid/*`) 实时查看

### 3.2 ruoyi 性能分析入口

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/《芋道 Spring Boot MyBatis 入门》.md`

**核心内容（节选）**：

> 启动应用后访问 `http://localhost:48080/druid`，使用配置的账号密码登录（默认无密码），即可看到：
> - 数据源监控（连接数、活跃数）
> - SQL 监控（每条 SQL 的执行次数、时间分布）
> - 慢 SQL 列表（按时间倒序）
> - SQL 执行 wall 防火墙拦截记录

**解读**：
- 这是 Druid 的内置监控页面，对开发排查性能问题至关重要
- **关键字段**：SQL 监控页面展示每条 SQL 的「执行次数、平均耗时、最大耗时、结果集大小」
- **使用建议**：开发环境打开监控 → 模拟典型业务 → 看慢 SQL → 用 EXPLAIN 分析

## 4. 关键要点总结

- 慢查询日志是发现问题的起点
- `EXPLAIN` 是分析慢 SQL 的必备工具
- 慢 SQL 优化优先级：**索引 > SQL 改写 > 架构优化（分库分表）**
- ruoyi 中 Druid 阈值设为 100ms（远低于 MySQL 默认 10 秒），便于早期发现问题
- 生产环境建议通过 Druid 监控页面 + ELK 日志分析组合排查

## 5. 练习题

### 练习 1：基础（必做）

开启本地 MySQL 慢查询日志（`long_query_time = 1`），执行 5 条不同查询，找到最慢的那条，用 `EXPLAIN` 分析。

### 练习 2：进阶

在 ruoyi 中执行「查询所有状态为 0 的用户，按创建时间倒序，分页第 100 页」，定位生成的 SQL，用 `EXPLAIN` 分析索引使用情况。

### 练习 3：挑战（选做）

设计一个慢 SQL 监控告警系统：当某条 SQL 平均耗时 > 500ms 时，通过企业微信发送告警消息（提示：可以基于 Druid 的 SQL 监控数据 + 定时任务）。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-framework/yudao-spring-boot-starter-mybatis/《芋道 Spring Boot MyBatis 入门》.md`
- MySQL 慢查询日志：https://dev.mysql.com/doc/refman/8.0/en/slow-query-log.html
- Druid 监控文档：https://github.com/alibaba/druid/wiki/

---

**文档版本**：v1.0
**最后更新**：2026-07-13