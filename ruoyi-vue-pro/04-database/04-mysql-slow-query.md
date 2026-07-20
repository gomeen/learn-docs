# 04 MySQL 慢查询分析

> 慢 SQL 是系统性能的隐形杀手。ruoyi 通过 Druid 监控 + 自定义慢 SQL 阈值定位问题。

## 🎯 学习目标

完成本文档后，你将能够：
- 开启 MySQL 慢查询日志
- 使用 `EXPLAIN` 分析慢 SQL
- 掌握常见慢 SQL 优化手段
- 理解 ruoyi 中 Druid 的 `log-slow-sql` 配置

## 📚 前置知识

- [01-mysql-basics.md](./01-mysql-basics.md)
- [03-mysql-index.md](./03-mysql-index.md)
- 应用侧慢 SQL 打印见 [12-slow-sql](../03-spring-boot-starters/14-slow-sql.md)；Druid 监控见 [22-druid](./26-druid.md)

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

## 3. 关键要点总结

- 慢查询日志是发现问题的起点
- `EXPLAIN` 是分析慢 SQL 的必备工具
- 慢 SQL 优化优先级：**索引 > SQL 改写 > 架构优化（分库分表）**
- ruoyi 中 Druid 阈值设为 100ms（远低于 MySQL 默认 10 秒），便于早期发现问题
- 生产环境建议通过 Druid 监控页面 + ELK 日志分析组合排查

---

**文档版本**：v1.0
**最后更新**：2026-07-13
