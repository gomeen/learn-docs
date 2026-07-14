# 6.3 慢 SQL 分析

> 理解慢 SQL 的常见原因与排查方法，掌握 MySQL 慢查询日志 + Druid 监控 + EXPLAIN 执行计划分析。

## 🎯 学习目标

完成本文档后，你将能够：
- 识别慢 SQL 的常见类型（全表扫描、深分页、函数运算）
- 掌握 MySQL 慢查询日志配置
- 能用 EXPLAIN 分析 SQL 执行计划
- 知道 ruoyi 的 Druid 慢 SQL 监控配置

## 📚 前置知识

- MySQL 基础
- 索引原理（B+Tree）
- `18-actuator.md`

## 1. 核心概念

### 1.1 什么是慢 SQL？

**慢 SQL** 指执行时间超过预设阈值的 SQL（通常 1 秒以上）。

慢 SQL 的危害：
- 占用数据库连接池
- 锁等待 / 阻塞其他事务
- 拖垮整个数据库

### 1.2 常见慢 SQL 类型

| 类型 | 例子 | 优化 |
|------|------|------|
| **全表扫描** | `SELECT * FROM user WHERE name LIKE '%张三%'` | 避免前导通配符 |
| **深分页** | `LIMIT 1000000, 20` | 用主键游标分页 |
| **函数运算** | `WHERE YEAR(create_time) = 2026` | 改为范围查询 |
| **隐式转换** | `WHERE phone = 13800138000`（phone 是 varchar） | 避免类型不一致 |
| **大字段** | `SELECT *`（含 text/blob） | 列出具体字段 |
| **缺失索引** | 频繁 WHERE 的列无索引 | 添加索引 |

### 1.3 慢 SQL 排查工具链

```
发现问题 → 定位 SQL → 分析原因 → 优化
  ↓          ↓          ↓          ↓
 慢日志     Druid     EXPLAIN    加索引/重写 SQL
```

## 2. 代码示例

### 2.1 MySQL 慢查询日志

```sql
-- 开启慢查询日志
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 1;  -- 阈值 1 秒
SET GLOBAL log_queries_not_using_indexes = ON;  -- 记录未使用索引的 SQL

-- 查看慢查询日志路径
SHOW VARIABLES LIKE 'slow_query_log_file';
```

### 2.2 EXPLAIN 执行计划

```sql
EXPLAIN SELECT * FROM user WHERE name = '张三';
```

**关键字段**：

| 字段 | 含义 | 优化目标 |
|------|------|---------|
| `type` | 访问类型 | 至少 `ref`，最好 `const` |
| `key` | 实际使用的索引 | 不为 NULL |
| `rows` | 扫描行数 | 越小越好 |
| `Extra` | 额外信息 | 避免 `Using filesort` / `Using temporary` |

**type 性能排序**：`system > const > eq_ref > ref > range > index > ALL`

### 2.3 慢 SQL 改写案例

```sql
-- ❌ 深分页（扫描 1000020 行）
SELECT * FROM orders ORDER BY id LIMIT 1000000, 20;

-- ✅ 游标分页（扫描 20 行）
SELECT * FROM orders WHERE id > 1000000 ORDER BY id LIMIT 20;
```

```sql
-- ❌ 函数运算（不走索引）
SELECT * FROM user WHERE DATE(create_time) = '2026-07-13';

-- ✅ 范围查询（走索引）
SELECT * FROM user WHERE create_time >= '2026-07-13' AND create_time < '2026-07-14';
```

## 3. ruoyi 仓库源码解读

### 3.1 ruoyi 的 Druid 慢 SQL 监控

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
**核心代码**（行 24-32）：

```yaml
    filter:
      stat:
        enabled: true
        log-slow-sql: true # 慢 SQL 记录
        slow-sql-millis: 100
        merge-sql: true
      wall:
        config:
          multi-statement-allow: true
```

**解读**：
- 第 2-3 行：开启 Druid Stat 过滤器
- 第 4 行：`log-slow-sql: true` — 开启慢 SQL 日志
- 第 5 行：`slow-sql-millis: 100` — 阈值 100ms
- 第 6 行：`merge-sql: true` — 合并相同 SQL（避免日志爆炸）
- 第 7-9 行：Wall 防火墙（防 SQL 注入）

### 3.2 启用 Druid 监控 Web UI

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
**核心代码**（行 15-23）：

```yaml
    druid: # Druid 【监控】相关的全局配置
      web-stat-filter:
        enabled: true
      stat-view-servlet:
        enabled: true
        allow: # 设置白名单，不填则允许所有访问
        url-pattern: /druid/*
        login-username: # 控制台管理用户名和密码
        login-password:
```

**解读**：
- 第 2-3 行：开启 Web Stat Filter（统计 HTTP 请求）
- 第 4-8 行：开启 Stat View Servlet（监控 UI）
- 访问 `http://localhost:48080/druid/` 查看 SQL 监控
- 包含：**SQL 执行统计 / URI 监控 / Session 监控 / 慢 SQL 列表**

### 3.3 ruoyi 的 MyBatis Plus 配置

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application.yaml`
**核心代码**（行 66-78）：

```yaml
# MyBatis Plus 的配置项
mybatis-plus:
  configuration:
    map-underscore-to-camel-case: true # 虽然默认为 true ，但是还是显示去指定下。
  global-config:
    db-config:
      id-type: NONE # “智能”模式，基于 IdTypeEnvironmentPostProcessor + 数据源的类型，自动适配成 AUTO、INPUT 模式。
#      id-type: AUTO # 自增 ID，适合 MySQL 等直接自增的数据库
#      id-type: INPUT # 用户输入 ID，适合 Oracle、PostgreSQL、Kingbase、DB2、H2 数据库
#      id-type: ASSIGN_ID # 分配 ID，默认使用雪花算法。注意，Oracle、PostgreSQL、Kingbase、DB2、H2 数据库时，需要去除实体类上的 @KeySequence 注解
      logic-delete-value: 1 # 逻辑已删除值(默认为 1)
      logic-not-delete-value: 0 # 逻辑未删除值(默认为 0)
    banner: false # 关闭控制台的 Banner 打印
  type-aliases-package: ${yudao.info.base-package}.module.*.dal.dataobject
  encryptor:
    password: XDV71a+xqStEA3WH # 加解密的秘钥，可使用 https://www.imaegoo.com/2020/aes-key-generator/ 网站生成
```

**解读**：
- 第 3 行：`map-underscore-to-camel-case: true` — `user_name` ↔ `userName` 映射
- 第 5-10 行：ID 策略（**NONE = 智能模式**，根据数据库类型自动选）
- 第 11-12 行：逻辑删除（1 = 已删除，0 = 未删除）
- **关键**：ruoyi 用 MyBatis Plus + Druid 组合，可控性高

### 3.4 日志中按模块打印 SQL

**文件位置**：`/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
**核心代码**（行 178-200）：

```yaml
  level:
    # 配置自己写的 MyBatis Mapper 打印日志
    cn.iocoder.yudao.module.bpm.dal.mysql: debug
    cn.iocoder.yudao.module.infra.dal.mysql: debug
    cn.iocoder.yudao.module.infra.dal.mysql.logger.ApiErrorLogMapper: INFO # 配置 ApiErrorLogMapper 的日志级别为 info，避免和 GlobalExceptionHandler 重复打印
    cn.iocoder.yudao.module.infra.dal.mysql.job.JobLogMapper: INFO
    cn.iocoder.yudao.module.infra.dal.mysql.file.FileConfigMapper: INFO
    cn.iocoder.yudao.module.pay.dal.mysql: debug
    cn.iocoder.yudao.module.pay.dal.mysql.notify.PayNotifyTaskMapper: INFO
    cn.iocoder.yudao.module.system.dal.mysql: debug
    cn.iocoder.yudao.module.system.dal.mysql.sms.SmsChannelMapper: INFO
    cn.iocoder.yudao.module.tool.dal.mysql: debug
    cn.iocoder.yudao.module.member.dal.mysql: debug
    ...
```

**解读**：
- 每个 `*.dal.mysql` 包级别设为 `debug` — 打印 SQL
- `*ErrorLogMapper`、`JobLogMapper` 等用 `INFO` — 避免重复记录
- **设计意图**：通过 logback 配置，按模块精细控制 SQL 日志

## 4. 关键要点总结

- 慢 SQL 常见原因：全表扫描、深分页、函数运算、隐式转换
- 排查工具链：MySQL 慢日志 → Druid 监控 → EXPLAIN 执行计划
- EXPLAIN 关键字段：`type`（访问类型）、`key`（索引）、`rows`（扫描行数）
- ruoyi 用 Druid Stat 监控慢 SQL，阈值 100ms
- 访问 `/druid/` 查看 SQL 执行统计和慢 SQL 列表
- **深分页**用主键游标代替 `LIMIT OFFSET`
- **函数运算**改范围查询才能走索引

## 5. 练习题

### 练习 1：基础（必做）

启动 yudao-server + MySQL，访问 `/druid/`，查看"SQL 执行"标签页，统计执行次数最多的 SQL。

### 练习 2：进阶

打开 MySQL 慢查询日志，故意构造一条慢 SQL（`SELECT * FROM sys_user WHERE username LIKE '%admin%'`），查看是否被记录。

### 练习 3：挑战（选做）

为 ruoyi 的 `sys_user` 表添加 100 万条测试数据，对一个无索引的列执行查询，用 EXPLAIN 对比"加索引前后"的 type 和 rows 变化。

## 6. 参考资料

- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application-local.yaml`
- `/Users/xu/code/github/ruoyi-vue-pro/yudao-server/src/main/resources/application.yaml`
- [Druid 官方文档](https://github.com/alibaba/druid)
- [MySQL EXPLAIN 官方文档](https://dev.mysql.com/doc/refman/8.0/en/explain.html)

---

**文档版本**：v1.0
**最后更新**：2026-07-13
