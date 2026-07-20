# 06 ruoyi 的 SQL 初始化脚本

> 理解 ruoyi-vue-pro 的初始化 SQL 脚本结构，能帮助你快速搭建数据库环境并理解表设计意图。

## 🎯 学习目标

完成本文档后，你将能够：
- 找到 ruoyi 的 SQL 初始化脚本
- 理解多数据库适配（MySQL、PostgreSQL、Oracle 等）
- 掌握 Quartz 调度表结构
- 能本地初始化 ruoyi 数据库

## 📚 前置知识

- [01-mysql-basics.md](./01-mysql-basics.md)
- SQL DDL 基本语法
- 结构迁移工具见 [07-flyway](./08-flyway.md)

## 1. 核心概念

### 1.1 ruoyi SQL 脚本目录结构

```
sql/
├── db2/                 # IBM DB2
├── dm/                  # 达梦数据库
├── highgo/              # 瀚高数据库
├── kingbase/            # 人大金仓
├── mysql/               # MySQL（最常用）
│   ├── ruoyi-vue-pro.sql  # 主脚本（含所有业务表）
│   └── quartz.sql         # Quartz 调度表
├── opengauss/           # openGauss
├── oracle/              # Oracle
├── postgresql/          # PostgreSQL
├── sqlserver/           # SQL Server
└── tools/               # 工具脚本（如 Redis Lua）
```

### 1.2 多数据库适配策略

ruoyi 通过：
1. 提供每种数据库的独立 SQL 脚本
2. MyBatis Plus 注解（如 `@KeySequence`）兼容不同数据库的自增主键
3. `JdbcUtils.getDbType()` 运行时判断当前数据库类型

### 1.3 Quartz 调度表的作用

Quartz 是 Spring 默认的定时任务调度框架，需要在数据库中持久化：
- 任务定义（QRTZ_JOB_DETAILS）
- 触发器（QRTZ_TRIGGERS）
- 调度历史（QRTZ_FIRED_TRIGGERS）

## 2. 代码示例

### 2.1 MySQL 初始化流程

```bash
# 1. 创建数据库
mysql -u root -p -e "CREATE DATABASE ruoyi-vue-pro DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2. 导入业务表
mysql -u root -p ruoyi-vue-pro < sql/mysql/ruoyi-vue-pro.sql

# 3. 导入 Quartz 表
mysql -u root -p ruoyi-vue-pro < sql/mysql/quartz.sql

# 4. 验证
mysql -u root -p ruoyi-vue-pro -e "SHOW TABLES;" | head
```

### 2.2 Quartz 表结构

```sql
-- 任务详情表：存储 JobDetail 配置
CREATE TABLE QRTZ_JOB_DETAILS (
    SCHED_NAME        VARCHAR(120) NOT NULL,
    JOB_NAME          VARCHAR(200) NOT NULL,
    JOB_GROUP         VARCHAR(200) NOT NULL,
    DESCRIPTION       VARCHAR(250) NULL,
    JOB_CLASS_NAME    VARCHAR(250) NOT NULL,  -- Job 类全限定名
    IS_DURABLE        VARCHAR(1)   NOT NULL,
    IS_NONCONCURRENT  VARCHAR(1)   NOT NULL,
    IS_UPDATE_DATA    VARCHAR(1)   NOT NULL,
    REQUESTS_RECOVERY VARCHAR(1)   NOT NULL,
    JOB_DATA          BLOB NULL,
    PRIMARY KEY (SCHED_NAME, JOB_NAME, JOB_GROUP)
);

-- 触发器表
CREATE TABLE QRTZ_TRIGGERS (
    SCHED_NAME    VARCHAR(120) NOT NULL,
    TRIGGER_NAME  VARCHAR(200) NOT NULL,
    TRIGGER_GROUP VARCHAR(200) NOT NULL,
    JOB_NAME      VARCHAR(200) NOT NULL,
    JOB_GROUP     VARCHAR(200) NOT NULL,
    ...
    PRIMARY KEY (SCHED_NAME, TRIGGER_NAME, TRIGGER_GROUP),
    FOREIGN KEY (SCHED_NAME, JOB_NAME, JOB_GROUP)
        REFERENCES QRTZ_JOB_DETAILS(SCHED_NAME, JOB_NAME, JOB_GROUP)
);
```

## 3. 关键要点总结

- ruoyi 通过「每种数据库一个 SQL 目录」实现多数据库适配
- MySQL 是最常用的开发数据库，脚本最完善
- Quartz 调度表是 ruoyi 定时任务的基础
- 每个表的 `creator/create_time/updater/update_time/deleted/tenant_id` 是 ruoyi 的标准字段

---

**文档版本**：v1.0
**最后更新**：2026-07-13
